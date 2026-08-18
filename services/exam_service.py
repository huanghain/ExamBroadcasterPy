"""考试管理服务"""
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_
from services.database import get_session
from models.exam import Exam
from models.exam_reminder import ExamReminder
from models.parsed_row import ParsedExamRow


class ExamService:
    """考试管理 CRUD 服务"""

    def check_conflicts(self, exam_date: str, start_time: str, end_time: str,
                        exclude_exam_id: int = None) -> list[Exam]:
        """检测指定时间段内是否有冲突的考试

        返回冲突的考试列表。
        """
        session = get_session()
        try:
            query = (
                session.query(Exam)
                .filter(Exam.exam_date == exam_date)
                .filter(Exam.is_enabled == True)
                .filter(
                    # 时间段重叠检测：A.start < B.end AND A.end > B.start
                    and_(
                        Exam.start_time < end_time,
                        Exam.end_time > start_time,
                    )
                )
            )
            if exclude_exam_id is not None:
                query = query.filter(Exam.id != exclude_exam_id)
            return query.order_by(Exam.start_time).all()
        finally:
            session.close()

    def get_all(self) -> list[Exam]:
        session = get_session()
        try:
            return (
                session.query(Exam)
                .options(selectinload(Exam.reminders))
                .order_by(Exam.exam_date, Exam.start_time)
                .all()
            )
        finally:
            session.close()

    def get_by_date(self, date_str: str) -> list[Exam]:
        session = get_session()
        try:
            return (
                session.query(Exam)
                .options(selectinload(Exam.reminders))
                .filter(Exam.exam_date == date_str)
                .order_by(Exam.start_time)
                .all()
            )
        finally:
            session.close()

    def get_upcoming(self, within_days: int = 7) -> list[Exam]:
        session = get_session()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            future = (datetime.now() + timedelta(days=within_days)).strftime("%Y-%m-%d")
            return (
                session.query(Exam)
                .options(selectinload(Exam.reminders))
                .filter(Exam.exam_date >= today)
                .filter(Exam.exam_date <= future)
                .filter(Exam.is_enabled == True)
                .order_by(Exam.exam_date, Exam.start_time)
                .all()
            )
        finally:
            session.close()

    def get_by_id(self, exam_id: int) -> Exam | None:
        session = get_session()
        try:
            return (
                session.query(Exam)
                .options(selectinload(Exam.reminders))
                .filter(Exam.id == exam_id)
                .first()
            )
        finally:
            session.close()

    def add(self, exam: Exam) -> Exam:
        """添加考试，返回带 id 的脱管对象"""
        session = get_session()
        try:
            session.add(exam)
            session.commit()
            # expire_on_commit=False，属性不会过期
            session.refresh(exam)
            # 显式 expunge 使对象脱管，避免后续 session 关闭后出问题
            session.expunge(exam)
            return exam
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, exam: Exam):
        session = get_session()
        try:
            exam.updated_at = datetime.now()
            session.merge(exam)
            session.commit()
        finally:
            session.close()

    def delete(self, exam_id: int):
        session = get_session()
        try:
            exam = session.get(Exam, exam_id)
            if exam:
                session.delete(exam)
                session.commit()
        finally:
            session.close()

    # ── 旧接口兼容 ──────────────────────────────────

    def update_reminder(self, exam_id: int, enabled: bool, minutes_before: int,
                        end_enabled: bool = False, end_minutes_before: int = 15):
        """更新考试的旧提醒设置（兼容旧代码）"""
        session = get_session()
        try:
            exam = session.get(Exam, exam_id)
            if exam:
                exam.reminder_enabled = enabled
                exam.reminder_minutes_before = minutes_before
                exam.reminder_end_enabled = end_enabled
                exam.reminder_end_minutes_before = end_minutes_before
                exam.updated_at = datetime.now()
                session.commit()
        finally:
            session.close()

    # ── 多次提醒 CRUD ────────────────────────────────

    def get_reminders(self, exam_id: int) -> list[ExamReminder]:
        """获取考试的所有提醒"""
        session = get_session()
        try:
            return (
                session.query(ExamReminder)
                .filter(ExamReminder.exam_id == exam_id)
                .order_by(ExamReminder.reminder_type.desc(), ExamReminder.minutes_before.desc())
                .all()
            )
        finally:
            session.close()

    def add_reminder(self, exam_id: int, reminder_type: str, minutes_before: int) -> ExamReminder:
        """添加一条提醒"""
        session = get_session()
        try:
            reminder = ExamReminder(
                exam_id=exam_id,
                reminder_type=reminder_type,
                minutes_before=minutes_before,
                is_enabled=True,
            )
            session.add(reminder)
            session.commit()
            session.refresh(reminder)
            session.expunge(reminder)
            return reminder
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_reminder_by_id(self, reminder_id: int, reminder_type: str = None,
                              minutes_before: int = None, is_enabled: bool = None,
                              custom_audio_path: str = None,
                              custom_tts_text: str = None):
        """更新单条提醒"""
        session = get_session()
        try:
            reminder = session.get(ExamReminder, reminder_id)
            if reminder:
                if reminder_type is not None:
                    reminder.reminder_type = reminder_type
                if minutes_before is not None:
                    reminder.minutes_before = minutes_before
                if is_enabled is not None:
                    reminder.is_enabled = is_enabled
                if custom_audio_path is not None:
                    reminder.custom_audio_path = custom_audio_path
                if custom_tts_text is not None:
                    reminder.custom_tts_text = custom_tts_text
                session.commit()
        finally:
            session.close()

    def delete_reminder(self, reminder_id: int):
        """删除单条提醒"""
        session = get_session()
        try:
            reminder = session.get(ExamReminder, reminder_id)
            if reminder:
                session.delete(reminder)
                session.commit()
        finally:
            session.close()

    def replace_reminders(self, exam_id: int, reminders_data: list[dict]):
        """替换考试的所有提醒（删除旧的，插入新的）"""
        session = get_session()
        try:
            # 删除旧提醒
            session.query(ExamReminder).filter(ExamReminder.exam_id == exam_id).delete()
            # 插入新提醒
            for data in reminders_data:
                reminder = ExamReminder(
                    exam_id=exam_id,
                    reminder_type=data.get("reminder_type", "start"),
                    minutes_before=data.get("minutes_before", 30),
                    is_enabled=data.get("is_enabled", True),
                    custom_audio_path=data.get("custom_audio_path"),
                    custom_tts_text=data.get("custom_tts_text"),
                )
                session.add(reminder)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def import_from_parsed_rows(self, rows: list[ParsedExamRow]) -> list[Exam]:
        """从 AI 解析结果批量导入"""
        imported = []
        session = get_session()
        try:
            for row in rows:
                if row.has_missing_fields:
                    continue
                exam = Exam(
                    subject=row.subject or "",
                    exam_date=row.date or "",
                    start_time=row.start_time or "",
                    end_time=row.end_time or "",
                    reminder_enabled=True,
                    reminder_minutes_before=30,
                )
                session.add(exam)
                imported.append(exam)
            session.commit()
            for e in imported:
                session.refresh(e)
            return imported
        finally:
            session.close()