"""
调度引擎

使用 APScheduler 实现定时任务调度，自动触发广播节点和考试提醒。
支持一次考试多次提醒。
"""
import asyncio
from datetime import datetime, timedelta
from typing import Callable
from PyQt6.QtCore import QObject, pyqtSignal

from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers.date import DateTrigger

from services.database import get_session
from models.schedule_task import ScheduleTask, ScheduleTaskStatus
from models.exam import Exam
from models.exam_reminder import ExamReminder
from models.template import BroadcastNode
from utils.logger import get_logger

logger = get_logger("scheduler")


class SchedulerService(QObject):
    """调度引擎服务"""

    task_triggered = pyqtSignal(object)
    task_status_changed = pyqtSignal(object)
    reminder_triggered = pyqtSignal(int, str, str, int)  # exam_id, reminder_text, reminder_type, minutes_before
    scheduler_started = pyqtSignal()
    scheduler_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._scheduler = QtScheduler()
        self._is_running = False
        self._broadcast_callback: Callable | None = None
        self._reminder_callback: Callable | None = None
        self._offline_audio = None
        # 持久事件循环，避免每次回调创建/销毁
        self._event_loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def set_offline_audio_service(self, service):
        """设置离线音频服务（用于离线模式播报）"""
        self._offline_audio = service

    def set_broadcast_callback(self, callback: Callable):
        self._broadcast_callback = callback

    def set_reminder_callback(self, callback: Callable):
        self._reminder_callback = callback

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """获取持久事件循环（按需创建）"""
        if self._event_loop is None or self._event_loop.is_closed():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    def start(self):
        if not self._is_running:
            self._scheduler.start()
            self._is_running = True
            logger.info("调度引擎已启动")
            self.scheduler_started.emit()

    def stop(self):
        if self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            # 关闭持久事件循环
            if self._event_loop and not self._event_loop.is_closed():
                self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                self._event_loop.close()
            logger.info("调度引擎已停止")
            self.scheduler_stopped.emit()

    def generate_tasks_for_exam(self, exam: Exam):
        """为指定考试生成调度任务（广播 + 提醒）

        关键修复：在内部 session 中重新查询 exam，避免使用脱管对象。
        """
        if not self._is_running:
            return

        session = get_session()
        try:
            # 重新查询，获得绑定到当前 session 的对象
            fresh_exam = session.get(Exam, exam.id)
            if not fresh_exam:
                return

            # ── 生成广播任务 ──
            if fresh_exam.broadcast_template:
                for node in fresh_exam.broadcast_template.nodes:
                    if not node.is_enabled:
                        continue

                    exam_start = datetime.strptime(
                        f"{fresh_exam.exam_date} {fresh_exam.start_time}", "%Y-%m-%d %H:%M"
                    )
                    trigger_time = exam_start + timedelta(minutes=node.time_offset_minutes)

                    if trigger_time < datetime.now():
                        continue

                    task = ScheduleTask(
                        exam_id=fresh_exam.id,
                        node_id=node.id,
                        scheduled_time=trigger_time,
                        status=ScheduleTaskStatus.PENDING,
                    )
                    session.add(task)
                    session.commit()
                    session.refresh(task)

                    self._scheduler.add_job(
                        self._execute_task,
                        trigger=DateTrigger(run_date=trigger_time),
                        args=[task.id],
                        id=f"task_{task.id}",
                        replace_existing=True,
                    )

            # ── 生成提醒任务（支持多次提醒）──
            self._schedule_reminders(fresh_exam, session)
        except Exception as e:
            logger.exception("generate_tasks_for_exam 出错")
            session.rollback()
        finally:
            session.close()

    def _schedule_reminders(self, exam: Exam, session=None):
        """为考试调度所有提醒任务（支持多次提醒）"""
        close_session = session is None
        if session is None:
            session = get_session()

        try:
            # 从 exam_reminders 表获取提醒
            reminders = (
                session.query(ExamReminder)
                .filter(ExamReminder.exam_id == exam.id)
                .filter(ExamReminder.is_enabled == True)
                .all()
            )

            # 如果新表没有数据，回退到旧字段
            if not reminders:
                if exam.reminder_enabled:
                    reminders = [_LegacyReminderData("start", exam.reminder_minutes_before or 30)]
                if exam.reminder_end_enabled:
                    reminders.append(_LegacyReminderData("end", exam.reminder_end_minutes_before or 15))

            if not reminders:
                return

            exam_start = datetime.strptime(
                f"{exam.exam_date} {exam.start_time}", "%Y-%m-%d %H:%M"
            )
            exam_end = datetime.strptime(
                f"{exam.exam_date} {exam.end_time}", "%Y-%m-%d %H:%M"
            )

            for idx, reminder in enumerate(reminders):
                r_type = reminder.reminder_type
                r_mins = reminder.minutes_before or 0

                if r_type == "start":
                    trigger_time = exam_start - timedelta(minutes=r_mins)
                else:
                    trigger_time = exam_end - timedelta(minutes=r_mins)
                    # ── 极端情况防错：结束提醒必须在考试开始之后才有意义 ──
                    # 若考试很短（如 10 分钟），"结束前 N 分钟"触发的时刻可能早于考试开始，
                    # 绝不允许在考试开始前播报"考试结束"等结束类提醒。
                    if trigger_time < exam_start:
                        logger.warning(
                            "考试(id=%s, %s %s~%s) 的长度只有 %s 分钟，"
                            "结束前%d分钟提醒早于考试开始，本次不调度并自动禁用",
                            exam.id, exam.exam_date, exam.start_time, exam.end_time,
                            int((exam_end - exam_start).total_seconds() // 60),
                            r_mins,
                        )
                        # 自动禁用此类无效提醒（仅对持久化的提醒对象；临时回退数据无需禁用）
                        real_id = getattr(reminder, "id", None)
                        if real_id is not None:
                            db_r = session.get(ExamReminder, real_id)
                            if db_r is not None and db_r.is_enabled:
                                db_r.is_enabled = False
                                session.commit()
                        continue

                if trigger_time < datetime.now():
                    continue

                reminder_id = getattr(reminder, 'id', None)
                job_id = f"reminder_{r_type}_{exam.id}_{idx}_{r_mins}min"
                try:
                    self._scheduler.add_job(
                        self._execute_reminder,
                        trigger=DateTrigger(run_date=trigger_time),
                        args=[exam.id, r_type, r_mins, reminder_id],
                        id=job_id,
                        replace_existing=True,
                    )
                except Exception as e:
                    logger.error("_schedule_reminders job 添加失败: %s", e)
        except (ValueError, TypeError) as e:
            logger.exception("_schedule_reminders 时间解析出错")
        finally:
            if close_session:
                session.close()

    def _execute_reminder(self, exam_id: int, reminder_type: str, minutes_before: int, reminder_id: int = None):
        """执行提醒任务"""
        session = get_session()
        try:
            exam = session.get(Exam, exam_id)
            if not exam:
                return

            # 查找自定义音频路径和 TTS 文字
            custom_audio_path = None
            custom_tts_text = None
            if reminder_id:
                reminder = session.get(ExamReminder, reminder_id)
                if reminder:
                    custom_audio_path = reminder.custom_audio_path
                    custom_tts_text = reminder.custom_tts_text

            if reminder_type == "start":
                if minutes_before == 0:
                    text = f"{exam.subject} 考试现在开始！"
                else:
                    text = f"提醒：{exam.subject} 将于 {minutes_before} 分钟后（{exam.start_time}）开始考试"
            else:
                if minutes_before == 0:
                    text = f"{exam.subject} 考试已结束！"
                else:
                    text = f"提醒：{exam.subject} 考试将于 {minutes_before} 分钟后结束"

            # 如果有自定义 TTS 文字，则使用自定义文字；否则使用预设默认文字
            if custom_tts_text:
                text = custom_tts_text
            else:
                default_key = (reminder_type, minutes_before)
                if default_key in DEFAULT_TTS_TEXTS:
                    text = DEFAULT_TTS_TEXTS[default_key]
                    # 离线模式：尝试匹配本地预录音频
                    if self._offline_audio and not custom_audio_path:
                        offline_path = self._offline_audio.get_audio_path(reminder_type, minutes_before)
                        if offline_path:
                            custom_audio_path = offline_path

            self.reminder_triggered.emit(exam_id, text, reminder_type, minutes_before)

            # 强制刷新 UI，确保播报弹窗在音频合成前显示
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            if self._reminder_callback:
                self._reminder_callback(
                    exam, text, custom_audio_path, reminder_type, minutes_before
                )
        finally:
            session.close()

    def generate_all_tasks(self):
        """为所有启用的考试生成调度任务"""
        session = get_session()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            exams = (
                session.query(Exam)
                .filter(Exam.is_enabled == True)
                .filter(Exam.exam_date >= today_str)
                .all()
            )
            for exam in exams:
                self.generate_tasks_for_exam(exam)
        finally:
            session.close()

    def get_today_tasks(self) -> list[ScheduleTask]:
        session = get_session()
        try:
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            return (
                session.query(ScheduleTask)
                .filter(ScheduleTask.scheduled_time >= datetime.combine(today, datetime.min.time()))
                .filter(ScheduleTask.scheduled_time < datetime.combine(tomorrow, datetime.min.time()))
                .order_by(ScheduleTask.scheduled_time)
                .all()
            )
        finally:
            session.close()

    def get_upcoming_tasks(self, within_minutes: int = 60) -> list[ScheduleTask]:
        session = get_session()
        try:
            now = datetime.now()
            deadline = now + timedelta(minutes=within_minutes)
            return (
                session.query(ScheduleTask)
                .filter(ScheduleTask.scheduled_time >= now)
                .filter(ScheduleTask.scheduled_time <= deadline)
                .filter(ScheduleTask.status == ScheduleTaskStatus.PENDING)
                .order_by(ScheduleTask.scheduled_time)
                .all()
            )
        finally:
            session.close()

    def _execute_task(self, task_id: int):
        """执行调度任务"""
        session = get_session()
        try:
            task = session.get(ScheduleTask, task_id)
            if not task or task.status != ScheduleTaskStatus.PENDING:
                return

            task.status = ScheduleTaskStatus.RUNNING
            session.commit()
            self.task_status_changed.emit(task)

            try:
                node = session.get(BroadcastNode, task.node_id)
                exam = session.get(Exam, task.exam_id)

                if self._broadcast_callback and node and exam:
                    self._broadcast_callback(exam, node)

                task.status = ScheduleTaskStatus.COMPLETED
                task.executed_at = datetime.now()
                task.result_message = "广播完成"
            except Exception as e:
                task.status = ScheduleTaskStatus.FAILED
                task.result_message = f"执行失败: {str(e)[:200]}"
                task.retry_count += 1
                logger.exception("_execute_task 失败 (task_id=%s)", task_id)

            session.commit()
            self.task_status_changed.emit(task)
            self.task_triggered.emit(task)
        finally:
            session.close()


# ── 默认 TTS 播报文字 ──────────────────────────────────

DEFAULT_TTS_TEXTS = {
    ("start", 15): "请监考老师组织考生有序进入考场",
    ("start", 10): "请监考老师发放答题卡、草稿纸",
    ("start", 5): "请监考老师发放试卷",
    ("start", 0): "考试开始，请考生开始答题",
    ("end", 15): "距离考试结束还有15分钟，请考生注意把握时间",
    ("end", 0): "考试结束，请考生立即停止答题",
}


class _LegacyReminderData:
    """旧字段数据包装（用于调度器内部）"""
    def __init__(self, reminder_type: str, minutes_before: int):
        self.reminder_type = reminder_type
        self.minutes_before = minutes_before
        self.is_enabled = True