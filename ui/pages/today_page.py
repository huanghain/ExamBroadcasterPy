"""今日概览页面 — 参考网页版设计：时间显示 + 考试倒计时 + 考试列表"""
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QFrame, QSizePolicy,
    QProgressBar, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from services.exam_service import ExamService


class TodayPage(QWidget):
    """今日概览"""

    WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def __init__(self, ctx: dict):
        super().__init__()
        self._exam_svc: ExamService = ctx["exam_service"]
        self._scheduler = ctx.get("scheduler")
        self._ctx = ctx
        self._init_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time_display)
        self._timer.start(1000)

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── 日期标题 ──
        today = datetime.now()
        wd = self.WEEKDAYS[today.weekday()]
        self._date_label = QLabel(f"{today.strftime('%Y年%m月%d日')} {wd}")
        self._date_label.setObjectName("dateLabel")

        # 日期行 + 离线模式按钮
        date_row = QHBoxLayout()
        date_row.addWidget(self._date_label)
        date_row.addStretch()

        self._offline_btn = QPushButton()
        self._offline_btn.setCheckable(True)
        self._offline_btn.setFixedHeight(30)
        self._offline_btn.clicked.connect(self._toggle_offline_mode)
        self._update_offline_btn_style()
        date_row.addWidget(self._offline_btn)
        layout.addLayout(date_row)

        # ── 时间显示区（参考网页版 time-display + time-grid）──
        time_frame = QFrame()
        time_frame.setObjectName("cardFrame")
        tf_layout = QHBoxLayout(time_frame)
        tf_layout.setContentsMargins(20, 16, 20, 16)
        tf_layout.setSpacing(0)

        # ── 左侧：当前时间 ──
        time_item = QFrame()
        ti_layout = QVBoxLayout(time_item)
        ti_layout.setContentsMargins(16, 12, 16, 12)
        ti_layout.setSpacing(4)
        ti_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._time_label = QLabel("当前时间")
        self._time_label.setObjectName("sectionLabel")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ti_layout.addWidget(self._time_label)

        self._clock_value = QLabel("--:--:--")
        self._clock_value.setObjectName("clockValue")
        self._clock_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ti_layout.addWidget(self._clock_value)

        self._date_small = QLabel("")
        self._date_small.setObjectName("dateSmall")
        self._date_small.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ti_layout.addWidget(self._date_small)

        tf_layout.addWidget(time_item, 1)

        # 分隔
        spacer = QWidget()
        spacer.setFixedWidth(16)
        tf_layout.addWidget(spacer)

        # ── 右侧：下一科目考试倒计时 ──
        cd_item = QFrame()
        cd_layout = QVBoxLayout(cd_item)
        cd_layout.setContentsMargins(16, 12, 16, 12)
        cd_layout.setSpacing(4)
        cd_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._countdown_label = QLabel("下一科目考试")
        self._countdown_label.setObjectName("sectionLabel")
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cd_layout.addWidget(self._countdown_label)

        self._countdown_value = QLabel("--")
        self._countdown_value.setObjectName("countdownValue")
        self._countdown_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cd_layout.addWidget(self._countdown_value)

        self._countdown_sub = QLabel("")
        self._countdown_sub.setObjectName("countdownSub")
        self._countdown_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cd_layout.addWidget(self._countdown_sub)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setObjectName("todayProgressBar")
        cd_layout.addWidget(self._progress_bar)

        tf_layout.addWidget(cd_item, 1)

        layout.addWidget(time_frame)

        # ── 今日考试安排 ──
        sec_label = QLabel("今日考试安排")
        sec_label.setObjectName("sectionLabel")
        layout.addWidget(sec_label)

        self._exam_table = self._make_table(["科目", "时间", "备注", "提醒状态"])
        layout.addWidget(self._exam_table)

        # ── 即将到来的提醒 ──
        upcoming_label = QLabel("即将到来的提醒")
        upcoming_label.setObjectName("sectionLabel")
        layout.addWidget(upcoming_label)

        self._upcoming_table = self._make_table(["考试科目", "提醒类型", "触发时间", "倒计时"])
        self._upcoming_table.setMaximumHeight(200)
        layout.addWidget(self._upcoming_table)

        layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._update_time_display()

    def _update_time_display(self):
        """每秒更新时间和倒计时"""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # 更新时钟
        self._clock_value.setText(now.strftime("%H:%M:%S"))
        self._date_small.setText(
            f"{now.year}年{now.month}月{now.day}日 {self.WEEKDAYS[now.weekday()]}"
        )

        # 更新倒计时
        exams = self._exam_svc.get_by_date(today_str)
        if not exams:
            self._countdown_label.setText("今日无考试安排")
            self._countdown_value.setText("--")
            self._countdown_sub.setText("")
            self._progress_bar.setVisible(False)
            self._update_upcoming_countdowns(now)
            return

        # 找到下一场考试
        next_exam = None
        for exam in exams:
            try:
                exam_start = datetime.strptime(
                    f"{exam.exam_date} {exam.start_time}", "%Y-%m-%d %H:%M"
                )
                exam_end = datetime.strptime(
                    f"{exam.exam_date} {exam.end_time}", "%Y-%m-%d %H:%M"
                )
            except Exception:
                continue

            if now < exam_start:
                if next_exam is None or exam_start < next_exam[0]:
                    next_exam = (exam_start, exam_end, exam)
            elif exam_start <= now <= exam_end:
                next_exam = (exam_start, exam_end, exam)
                break

        if next_exam is None:
            self._countdown_label.setText("今日考试已全部结束")
            self._countdown_value.setText("--")
            self._countdown_sub.setText("")
            self._progress_bar.setVisible(False)
            self._update_upcoming_countdowns(now)
            return

        start, end, exam = next_exam

        if now < start:
            # 倒计时模式
            diff = start - now
            total_sec = int(diff.total_seconds())
            if total_sec < 0:
                total_sec = 0
            hours = total_sec // 3600
            minutes = (total_sec % 3600) // 60
            seconds = total_sec % 60

            self._countdown_label.setText("下一科目考试")
            self._countdown_value.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self._countdown_sub.setText(
                f"{exam.subject}  {exam.start_time}~{exam.end_time}"
            )
            self._progress_bar.setVisible(False)
        else:
            # 考试中模式
            total_duration = (end - start).total_seconds()
            elapsed = (now - start).total_seconds()
            remaining = total_duration - elapsed

            if total_duration > 0:
                pct = int(elapsed / total_duration * 100)
                self._progress_bar.setVisible(True)
                self._progress_bar.setValue(pct)

                rem_h = int(remaining) // 3600
                rem_m = (int(remaining) % 3600) // 60
                rem_s = int(remaining) % 60

                self._countdown_label.setText(f"正在考试: {exam.subject}")
                self._countdown_value.setText(
                    f"剩余 {rem_h:02d}:{rem_m:02d}:{rem_s:02d}"
                )
                self._countdown_sub.setText(
                    f"{exam.start_time}~{exam.end_time}  |  已进行 {int(elapsed // 60)} 分钟"
                )
            else:
                self._countdown_label.setText(f"正在考试: {exam.subject}")
                self._countdown_value.setText("--")
                self._countdown_sub.setText("")
                self._progress_bar.setVisible(False)

        self._update_upcoming_countdowns(now)

    def _update_upcoming_countdowns(self, now: datetime):
        """轻量更新即将到来的提醒倒计时列"""
        for i in range(self._upcoming_table.rowCount()):
            time_item = self._upcoming_table.item(i, 2)
            if not time_item:
                continue
            # 优先读取完整触发时间（UserRole），精确处理跨天；回退到 HH:MM 当天解析
            trigger_time = time_item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(trigger_time, datetime):
                trigger_str = time_item.text()
                try:
                    trigger_h, trigger_m = map(int, trigger_str.split(":"))
                    trigger_time = now.replace(hour=trigger_h, minute=trigger_m, second=0, microsecond=0)
                except (ValueError, AttributeError):
                    continue

            diff = trigger_time - now
            total_sec = int(diff.total_seconds())
            # 已到/已过去的提醒（已触发或刚过去）不显示，"--"，避免展示"23小时59分钟"
            if total_sec <= 0:
                countdown = "--"
            elif total_sec < 3600:
                countdown = f"{total_sec // 60}分钟"
            else:
                h = total_sec // 3600
                m = (total_sec % 3600) // 60
                countdown = f"{h}小时{m}分钟"
            item = QTableWidgetItem(countdown)
            self._upcoming_table.setItem(i, 3, item)

    def refresh(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        exams = self._exam_svc.get_by_date(today_str)

        self._exam_table.setRowCount(len(exams))
        for i, exam in enumerate(exams):
            self._exam_table.setItem(i, 0, QTableWidgetItem(exam.subject))
            self._exam_table.setItem(
                i, 1, QTableWidgetItem(f"{exam.start_time}~{exam.end_time}")
            )
            self._exam_table.setItem(i, 2, QTableWidgetItem(exam.notes or "-"))

            active = exam.active_reminders
            if active:
                times = exam.all_reminder_times
                status = " / ".join(times)
                item = QTableWidgetItem(status)
            else:
                item = QTableWidgetItem("未启用")
            self._exam_table.setItem(i, 3, item)

        self._refresh_upcoming_reminders()
        self._update_time_display()

    def _refresh_upcoming_reminders(self):
        """刷新即将到来的提醒列表"""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        upcoming = []

        # 获取今日和明天考试
        tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        for date_str in (today_str, tomorrow_str):
            exams = self._exam_svc.get_by_date(date_str)
            for exam in exams:
                reminders = exam.active_reminders
                for r in reminders:
                    r_type = r.reminder_type
                    r_mins = r.minutes_before or 0
                    try:
                        ref_time = exam.start_time if r_type == "start" else exam.end_time
                        ref_dt = datetime.strptime(
                            f"{exam.exam_date} {ref_time}", "%Y-%m-%d %H:%M"
                        )
                        trigger_time = ref_dt - timedelta(minutes=r_mins)
                        exam_start_dt = datetime.strptime(
                            f"{exam.exam_date} {exam.start_time}", "%Y-%m-%d %H:%M"
                        )
                    except (ValueError, AttributeError):
                        continue

                    # ── 极端情况防错：结束提醒必须不早于考试开始 ──
                    # 短考试（如10分钟）的"结束前N分钟"会早于开考时刻，属于无效提醒，
                    # 首页不展示、不调度，避免"考试未开始先播报结束、倒计时异常"。
                    if r_type == "end" and trigger_time < exam_start_dt:
                        continue

                    # 只显示未来24小时内的提醒
                    if now <= trigger_time <= now + timedelta(hours=24):
                        if r_type == "start":
                            type_label = "开始考试" if r_mins == 0 else f"考前{r_mins}分钟"
                        else:
                            type_label = "考试结束" if r_mins == 0 else f"结束前{r_mins}分钟"
                        upcoming.append((trigger_time, exam.subject, type_label, trigger_time))

        upcoming.sort(key=lambda x: x[0])

        self._upcoming_table.setRowCount(len(upcoming))
        for i, (trigger_time, subject, type_label, _) in enumerate(upcoming):
            self._upcoming_table.setItem(i, 0, QTableWidgetItem(subject))
            self._upcoming_table.setItem(i, 1, QTableWidgetItem(type_label))
            time_item = QTableWidgetItem(trigger_time.strftime("%H:%M"))
            # 完整触发时间存入 UserRole，供每秒刷新精确计算（避免跨天误判）
            time_item.setData(Qt.ItemDataRole.UserRole, trigger_time)
            self._upcoming_table.setItem(i, 2, time_item)
            diff = trigger_time - now
            total_sec = int(diff.total_seconds())
            if total_sec < 0:
                countdown = "--"
            elif total_sec < 3600:
                countdown = f"{total_sec // 60}分钟"
            else:
                h = total_sec // 3600
                m = (total_sec % 3600) // 60
                countdown = f"{h}小时{m}分钟"
            item = QTableWidgetItem(countdown)
            self._upcoming_table.setItem(i, 3, item)

    def _make_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.verticalHeader().setVisible(False)
        table.setMaximumHeight(240)
        table.setAlternatingRowColors(True)
        table.setObjectName("todayTable")
        return table

    def _update_offline_btn_style(self):
        """更新离线模式按钮样式"""
        is_offline = self._ctx.get("offline_mode", False)
        self._offline_btn.setChecked(is_offline)
        self._offline_btn.setObjectName("offlineModeBtn")
        if is_offline:
            self._offline_btn.setText("离线模式 (已开启)")
            self._offline_btn.setProperty("state", "offline")
        else:
            self._offline_btn.setText("在线模式")
            self._offline_btn.setProperty("state", "online")
        # 触发样式重新应用
        self._offline_btn.style().unpolish(self._offline_btn)
        self._offline_btn.style().polish(self._offline_btn)

    def _toggle_offline_mode(self):
        """切换离线/在线模式"""
        current = self._ctx.get("offline_mode", False)
        self._ctx["offline_mode"] = not current
        self._update_offline_btn_style()

        # 通知主窗口更新 UI（禁用/启用 AI 按钮和设置页）
        window = self.window()
        if hasattr(window, "_on_offline_mode_changed"):
            window._on_offline_mode_changed(not current)