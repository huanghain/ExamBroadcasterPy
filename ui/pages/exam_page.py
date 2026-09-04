"""考试管理页面 — 左右分栏布局 + 多次提醒 + 自定义语音 + 编辑考试"""
import csv
import io
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDateEdit, QTimeEdit, QTabWidget, QFileDialog, QTextEdit,
    QFormLayout, QSizePolicy, QSpinBox, QCheckBox,
    QGroupBox, QFrame, QDialog, QDialogButtonBox, QGridLayout,
    QSplitter, QScrollArea, QComboBox,
)
from PyQt6.QtCore import Qt, QDate, QTime, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

from models.exam import Exam
from models.exam_reminder import ExamReminder
from models.parsed_row import ParsedExamRow
from services.exam_service import ExamService
from services.ai_service import ZhipuAIService
from services.file_parser import FileParserService
from services.scheduler import DEFAULT_TTS_TEXTS
from ui.widgets.toast import show_toast, ask_confirm


# ── 后台线程 ──────────────────────────────────────────

class AITaskWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args):
        super().__init__()
        self._func = func
        self._args = args

    def run(self):
        try:
            result = self._func(*self._args)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ReminderPreviewWorker(QThread):
    """提醒语音试听后台线程"""

    def __init__(self, text: str, volume: int = 80):
        super().__init__()
        self._text = text
        self._volume = volume

    def run(self):
        """合成并播放语音"""
        import asyncio
        import tempfile
        from pathlib import Path
        from config import AUDIO_CACHE_DIR, DEFAULT_VOICE
        import edge_tts

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".mp3", dir=AUDIO_CACHE_DIR, delete=False
            )
            output_path = temp_file.name
            temp_file.close()

            loop.run_until_complete(
                edge_tts.Communicate(self._text, DEFAULT_VOICE).save(output_path)
            )

            # 在主线程播放
            self._play_audio(output_path)
        except Exception as e:
            print(f"[预览] 语音合成失败: {e}")
        finally:
            loop.close()

    def _play_audio(self, file_path: str):
        """在主线程播放音频文件"""
        from PyQt6.QtWidgets import QApplication
        # 全屏广播模式下屏蔽非考试提醒声音（试听音频不播放）
        from services import audio_gate
        if audio_gate.is_suppressed():
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception:
                pass
            return
        QApplication.processEvents()
        # 使用 QMediaPlayer 播放
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        player.setAudioOutput(audio_output)
        audio_output.setVolume(self._volume / 100.0)
        url = QUrl.fromLocalFile(file_path)
        player.setSource(url)
        player.play()

        # 等待播放完成（最多 30 秒）
        import time
        timeout = 30
        while player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
            QApplication.processEvents()

        # 清理临时文件
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass


# ── 考试编辑弹窗 ──────────────────────────────────────

class ExamEditDialog(QDialog):
    """考试信息编辑弹窗 — 允许修改科目、日期、时间、备注"""

    def __init__(self, exam: Exam, parent=None):
        super().__init__(parent)
        self._exam = exam
        self.setWindowTitle(f"编辑考试 - {exam.subject}")
        self.setMinimumWidth(380)
        self.setModal(True)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 16)

        # ── 标题 ──
        title = QLabel("编辑考试信息")
        title.setObjectName("examDialogTitle")
        layout.addWidget(title)

        # ── 表单 ──
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 科目
        self._subject_input = QLineEdit()
        self._subject_input.setPlaceholderText("如：高等数学")
        self._subject_input.setMinimumHeight(28)
        form.addRow("科目", self._subject_input)

        # 日期
        self._date_input = QDateEdit()
        self._date_input.setCalendarPopup(True)
        self._date_input.setDisplayFormat("yyyy-MM-dd")
        self._date_input.setMinimumHeight(28)
        form.addRow("日期", self._date_input)

        # 开始时间
        self._start_time_input = QTimeEdit()
        self._start_time_input.setDisplayFormat("HH:mm")
        self._start_time_input.setMinimumHeight(28)
        form.addRow("开始时间", self._start_time_input)

        # 结束时间
        self._end_time_input = QTimeEdit()
        self._end_time_input.setDisplayFormat("HH:mm")
        self._end_time_input.setMinimumHeight(28)
        form.addRow("结束时间", self._end_time_input)

        # 备注
        self._notes_input = QTextEdit()
        self._notes_input.setPlaceholderText("可选备注信息")
        self._notes_input.setMaximumHeight(60)
        form.addRow("备注", self._notes_input)

        layout.addLayout(form)

        # ── 预览 ──
        self._preview_label = QLabel("")
        self._preview_label.setObjectName("examPreviewLabel")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label)

        # ── 按钮 ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # 连接预览更新
        self._subject_input.textChanged.connect(self._update_preview)
        self._date_input.dateChanged.connect(self._update_preview)
        self._start_time_input.timeChanged.connect(self._update_preview)
        self._end_time_input.timeChanged.connect(self._update_preview)

    def _load_data(self):
        """加载考试数据到表单"""
        self._subject_input.setText(self._exam.subject)
        try:
            date = QDate.fromString(self._exam.exam_date, "yyyy-MM-dd")
            if date.isValid():
                self._date_input.setDate(date)
        except Exception:
            pass
        try:
            h, m = map(int, self._exam.start_time.split(":"))
            self._start_time_input.setTime(QTime(h, m))
        except Exception:
            pass
        try:
            h, m = map(int, self._exam.end_time.split(":"))
            self._end_time_input.setTime(QTime(h, m))
        except Exception:
            pass
        self._notes_input.setPlainText(self._exam.notes or "")
        self._update_preview()

    def _update_preview(self):
        """更新预览"""
        subject = self._subject_input.text().strip() or "未命名"
        date = self._date_input.date().toString("yyyy-MM-dd")
        start = self._start_time_input.time().toString("HH:mm")
        end = self._end_time_input.time().toString("HH:mm")

        parts = [f"<b>{subject}</b>", date, f"{start} ~ {end}"]
        self._preview_label.setText(" &nbsp;|&nbsp; ".join(parts))

    def _validate_and_accept(self):
        """验证并确认"""
        if not self._subject_input.text().strip():
            show_toast(self, "请输入科目名称", "warning")
            return
        start = self._start_time_input.time()
        end = self._end_time_input.time()
        if start >= end:
            show_toast(self, "开始时间必须早于结束时间", "warning")
            return
        self.accept()

    def get_exam_data(self) -> dict:
        """获取编辑后的考试数据"""
        return {
            "subject": self._subject_input.text().strip(),
            "exam_date": self._date_input.date().toString("yyyy-MM-dd"),
            "start_time": self._start_time_input.time().toString("HH:mm"),
            "end_time": self._end_time_input.time().toString("HH:mm"),
            "notes": self._notes_input.toPlainText().strip(),
        }


# ── 多次提醒编辑弹窗 ──────────────────────────────────

class ReminderEditDialog(QDialog):
    """多次提醒编辑弹窗 — 支持添加/删除/编辑多个提醒 + 自定义语音"""

    REMINDER_PRESETS = [0, 5, 10, 15, 30, 60]
    AUDIO_FILTER = "音频文件 (*.mp3 *.wav *.ogg *.m4a *.flac *.aac);;所有文件 (*)"

    def __init__(self, exam: Exam, exam_svc: ExamService, parent=None, play_preview=None):
        super().__init__(parent)
        self._exam = exam
        self._exam_svc = exam_svc
        self._reminder_rows: list[dict] = []
        self._row_widgets: list[dict] = []
        self._play_preview = play_preview  # 试听回调
        self.setWindowTitle(f"提醒设置 - {exam.subject}")
        self.setMinimumWidth(680)
        self.resize(680, 600)
        self.setModal(True)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 16)

        # ── 考试信息摘要 ──
        info = QLabel(
            f"<b style='font-size:13px;'>{self._exam.subject}</b>"
            f"<span> &nbsp;|&nbsp; {self._exam.exam_date}</span>"
            f"<span> &nbsp;|&nbsp; {self._exam.start_time}~{self._exam.end_time}</span>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setObjectName("examReminderInfo")
        info.setWordWrap(True)
        layout.addWidget(info)

        # ── 提醒列表标题 ──
        header_row = QHBoxLayout()
        header_label = QLabel("提醒列表")
        header_label.setObjectName("examReminderHeader")
        header_row.addWidget(header_label)
        header_row.addStretch()

        add_btn = QPushButton("+ 添加提醒")
        add_btn.setObjectName("accentBtn")
        
        add_btn.setFixedHeight(30)
        add_btn.clicked.connect(self._add_reminder_row)
        header_row.addWidget(add_btn)
        layout.addLayout(header_row)

        # ── 提醒列表滚动区 ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setMinimumHeight(180)
        self._scroll.setMaximumHeight(420)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(8)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_container)
        layout.addWidget(self._scroll)

        # ── 预览区 ──
        self._preview_label = QLabel("")
        self._preview_label.setObjectName("examPreviewArea")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label)

        # ── 按钮 ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_data(self):
        """从数据库加载现有提醒"""
        reminders = self._exam_svc.get_reminders(self._exam.id)

        if reminders:
            for r in reminders:
                self._add_reminder_row(
                    reminder_type=r.reminder_type,
                    minutes_before=r.minutes_before,
                    is_enabled=r.is_enabled,
                    custom_audio_path=r.custom_audio_path,
                    custom_tts_text=r.custom_tts_text,
                )
        else:
            # 回退到旧字段
            if self._exam.reminder_enabled:
                self._add_reminder_row("start", self._exam.reminder_minutes_before or 30, True)
            if self._exam.reminder_end_enabled:
                self._add_reminder_row("end", self._exam.reminder_end_minutes_before or 15, True)

        # 如果一条都没有，添加默认6条提醒
        if not self._row_widgets:
            self._add_reminder_row("start", 15, True, custom_tts_text=DEFAULT_TTS_TEXTS.get(("start", 15), ""))
            self._add_reminder_row("start", 10, True, custom_tts_text=DEFAULT_TTS_TEXTS.get(("start", 10), ""))
            self._add_reminder_row("start", 5, True, custom_tts_text=DEFAULT_TTS_TEXTS.get(("start", 5), ""))
            self._add_reminder_row("start", 0, True, custom_tts_text=DEFAULT_TTS_TEXTS.get(("start", 0), ""))
            self._add_reminder_row("end", 15, True, custom_tts_text=DEFAULT_TTS_TEXTS.get(("end", 15), ""))
            self._add_reminder_row("end", 0, True, custom_tts_text=DEFAULT_TTS_TEXTS.get(("end", 0), ""))

        self._update_preview()

    def _add_reminder_row(self, reminder_type: str = "start",
                          minutes_before: int = 30, is_enabled: bool = True,
                          custom_audio_path: str = None,
                          custom_tts_text: str = None):
        """添加一行提醒控件"""
        # 外层容器
        row_frame = QFrame()
        row_frame.setObjectName("examReminderRow")
        main_layout = QVBoxLayout(row_frame)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)

        # ── 第一行：基本设置 ──
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        # 启用复选框
        enable_check = QCheckBox()
        enable_check.setChecked(is_enabled)
        enable_check.setFixedSize(18, 18)
        row1.addWidget(enable_check)

        # 类型下拉
        type_combo = QComboBox()
        type_combo.addItem("开考前", "start")
        type_combo.addItem("结束前", "end")
        type_combo.setCurrentIndex(0 if reminder_type == "start" else 1)
        type_combo.setMinimumWidth(70)
        type_combo.currentIndexChanged.connect(self._update_preview)
        row1.addWidget(type_combo)

        # "提前"标签
        row1.addWidget(QLabel("提前"))

        # 分钟数
        mins_spin = QSpinBox()
        mins_spin.setRange(0, 600)
        mins_spin.setValue(minutes_before)
        mins_spin.setSuffix(" 分钟")
        mins_spin.setSingleStep(5)
        mins_spin.setMinimumWidth(90)
        mins_spin.valueChanged.connect(self._update_preview)
        row1.addWidget(mins_spin)

        # 快捷预设
        for mins in self.REMINDER_PRESETS:
            tag = QPushButton(f"{mins}")
            tag.setObjectName("tagBtn")
            tag.setFixedSize(40, 24)
            tag.clicked.connect(
                lambda checked, s=mins_spin, m=mins: s.setValue(m)
            )
            row1.addWidget(tag)

        row1.addStretch()

        # 预览时间
        time_label = QLabel("")
        time_label.setObjectName("examTimeLabel")
        row1.addWidget(time_label)

        # 删除按钮
        del_btn = QPushButton("删除")
        del_btn.setObjectName("tableDeleteBtn")
        del_btn.setFixedSize(50, 24)
        del_btn.setToolTip("删除此提醒")
        row1.addWidget(del_btn)

        main_layout.addLayout(row1)

        # ── 第二行：语音设置 ──
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.setContentsMargins(24, 0, 0, 0)

        voice_label = QLabel("语音:")
        voice_label.setObjectName("examVoiceLabel")
        row2.addWidget(voice_label)

        # 语音来源标签
        audio_status_label = QLabel("")
        audio_status_label.setObjectName("examAudioStatus")
        row2.addWidget(audio_status_label)

        # 选择音频按钮
        pick_btn = QPushButton("选择音频文件")
        pick_btn.setFixedHeight(24)
        pick_btn.setObjectName("examPickAudioBtn")
        row2.addWidget(pick_btn)

        # 清除音频按钮
        clear_audio_btn = QPushButton("清除")
        clear_audio_btn.setFixedHeight(24)
        clear_audio_btn.setObjectName("examClearAudioBtn")
        clear_audio_btn.setToolTip("使用默认 TTS 语音")
        row2.addWidget(clear_audio_btn)

        # 试听按钮
        preview_btn = QPushButton("试听")
        preview_btn.setFixedHeight(24)
        preview_btn.setObjectName("examPreviewBtn")
        preview_btn.setToolTip("播报试听语音")
        row2.addWidget(preview_btn)

        row2.addStretch()
        main_layout.addLayout(row2)

        # ── 第三行：自定义 TTS 文字 ──
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.setContentsMargins(24, 0, 0, 0)

        tts_label = QLabel("TTS文字:")
        tts_label.setObjectName("examTtsLabel")
        row3.addWidget(tts_label)

        tts_text_edit = QLineEdit()
        tts_text_edit.setPlaceholderText("自定义播报文字（留空则使用默认文字）")
        tts_text_edit.setObjectName("examTtsInput")
        tts_text_edit.setMinimumHeight(26)
        if custom_tts_text:
            tts_text_edit.setText(custom_tts_text)
        tts_text_edit.textChanged.connect(self._update_preview)
        row3.addWidget(tts_text_edit, 1)

        main_layout.addLayout(row3)

        # 插入到 stretch 之前
        insert_pos = self._list_layout.count() - 1
        self._list_layout.insertWidget(insert_pos, row_frame)

        # 存储控件引用
        row_data = {
            "frame": row_frame,
            "enable_check": enable_check,
            "type_combo": type_combo,
            "mins_spin": mins_spin,
            "time_label": time_label,
            "del_btn": del_btn,
            "audio_status_label": audio_status_label,
            "audio_path": custom_audio_path,
            "tts_text_edit": tts_text_edit,
            "tts_text": custom_tts_text,
        }
        self._row_widgets.append(row_data)

        # 更新音频状态显示
        self._update_audio_status(row_data)

        # 连接删除
        del_btn.clicked.connect(lambda checked, rd=row_data: self._remove_reminder_row(rd))

        # 连接预览更新
        enable_check.stateChanged.connect(self._update_preview)
        type_combo.currentIndexChanged.connect(self._update_preview)

        # 连接 TTS 自动同步：当类型/分钟变化时自动填充预设文字
        type_combo.currentIndexChanged.connect(lambda: self._sync_tts_preset(row_data))
        mins_spin.valueChanged.connect(lambda: self._sync_tts_preset(row_data))

        # 连接音频选择
        pick_btn.clicked.connect(lambda checked, rd=row_data: self._pick_audio_file(rd))
        clear_audio_btn.clicked.connect(lambda checked, rd=row_data: self._clear_audio(rd))
        preview_btn.clicked.connect(lambda checked, rd=row_data: self._preview_reminder(rd))

        self._update_preview()

    def _sync_tts_preset(self, row_data: dict):
        """当类型/分钟变化时，自动填充对应预设 TTS 文字（除非用户已手动输入自定义文字）"""
        r_type = row_data["type_combo"].currentData()
        mins = row_data["mins_spin"].value()
        preset = DEFAULT_TTS_TEXTS.get((r_type, mins), "")
        current = row_data["tts_text_edit"].text().strip()

        # 如果当前文字为空、或匹配某个预设（说明是自动生成的），则自动更新
        is_auto = (not current) or any(current == v for v in DEFAULT_TTS_TEXTS.values())
        if is_auto and preset:
            row_data["tts_text_edit"].setText(preset)
        elif is_auto and not preset:
            row_data["tts_text_edit"].clear()

    def _pick_audio_file(self, row_data: dict):
        """选择自定义音频文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择提醒语音文件", "", self.AUDIO_FILTER
        )
        if path:
            row_data["audio_path"] = path
            self._update_audio_status(row_data)
            self._update_preview()

    def _clear_audio(self, row_data: dict):
        """清除自定义音频，恢复为 TTS"""
        row_data["audio_path"] = None
        self._update_audio_status(row_data)
        self._update_preview()

    def _preview_reminder(self, row_data: dict):
        """试听提醒语音"""
        text = row_data["tts_text_edit"].text().strip()
        if not text:
            text = "这是一条试听语音"
        if self._play_preview:
            self._play_preview(text)
        else:
            worker = ReminderPreviewWorker(text)
            worker.start()

    def _update_audio_status(self, row_data: dict):
        """更新音频状态标签"""
        path = row_data.get("audio_path")
        if path:
            name = os.path.basename(path)
            if len(name) > 20:
                name = name[:17] + "..."
            row_data["audio_status_label"].setText(f"自定义: {name}")
            row_data["audio_status_label"].setProperty("state", "custom")
            row_data["audio_status_label"].style().unpolish(row_data["audio_status_label"])
            row_data["audio_status_label"].style().polish(row_data["audio_status_label"])
        else:
            row_data["audio_status_label"].setText("默认 TTS 语音")
            row_data["audio_status_label"].setProperty("state", "default")
            row_data["audio_status_label"].style().unpolish(row_data["audio_status_label"])
            row_data["audio_status_label"].style().polish(row_data["audio_status_label"])

    def _remove_reminder_row(self, row_data: dict):
        """删除一行提醒"""
        self._list_layout.removeWidget(row_data["frame"])
        row_data["frame"].deleteLater()
        self._row_widgets.remove(row_data)
        self._update_preview()

    def _update_preview(self):
        """更新预览时间和总览"""
        if not self._row_widgets:
            self._preview_label.setText("暂无提醒")
            return

        parts = []
        for rd in self._row_widgets:
            enabled = rd["enable_check"].isChecked()
            r_type = rd["type_combo"].currentData()
            mins = rd["mins_spin"].value()
            audio_path = rd.get("audio_path")

            if not enabled:
                continue

            # 计算提醒时间
            try:
                time_str = self._exam.start_time if r_type == "start" else self._exam.end_time
                h, m = map(int, time_str.split(":"))
                total = h * 60 + m - mins
                if total < 0:
                    total += 24 * 60
                time_str = f"{total // 60:02d}:{total % 60:02d}"
            except (ValueError, AttributeError):
                time_str = "—"

            type_label = "开考前" if r_type == "start" else "结束前"
            if mins == 0:
                desc = "开始考试" if r_type == "start" else "考试结束"
            else:
                desc = f"{type_label}{mins}分钟"

            audio_tag = " [自定义]" if audio_path else ""
            tts_tag = " [TTS]" if rd.get("tts_text") else ""

            rd["time_label"].setText(time_str)
            rd["time_label"].setProperty("type", r_type)
            rd["time_label"].style().unpolish(rd["time_label"])
            rd["time_label"].style().polish(rd["time_label"])

            parts.append(f"{time_str} {desc}{audio_tag}{tts_tag}")

        if parts:
            self._preview_label.setText("  |  ".join(parts))
        else:
            self._preview_label.setText("所有提醒均已禁用")

    def get_reminders_data(self) -> list[dict]:
        """获取所有提醒数据"""
        result = []
        for rd in self._row_widgets:
            result.append({
                "reminder_type": rd["type_combo"].currentData(),
                "minutes_before": rd["mins_spin"].value(),
                "is_enabled": rd["enable_check"].isChecked(),
                "custom_audio_path": rd.get("audio_path"),
                "custom_tts_text": rd["tts_text_edit"].text().strip() or None,
            })
        return result


# ── 添加考试弹窗 ──────────────────────────────────────

class AddExamDialog(QDialog):
    """添加考试弹窗 — 参考网页版设计"""

    REMINDER_PRESETS = [0, 5, 10, 15, 30, 60]
    AUDIO_FILTER = "音频文件 (*.mp3 *.wav *.ogg *.m4a *.flac *.aac);;所有文件 (*)"

    def __init__(self, parent=None, play_preview=None):
        super().__init__(parent)
        self.setWindowTitle("添加考试")
        self.setMinimumWidth(720)
        self.resize(720, 560)
        self.setModal(True)
        self._reminder_rows: list[dict] = []
        self._play_preview = play_preview  # 试听回调
        self._init_ui()
        # 默认6条提醒，带预设TTS文字
        self._add_reminder_row("start", 15, True, tts_text=DEFAULT_TTS_TEXTS.get(("start", 15), ""))
        self._add_reminder_row("start", 10, True, tts_text=DEFAULT_TTS_TEXTS.get(("start", 10), ""))
        self._add_reminder_row("start", 5, True, tts_text=DEFAULT_TTS_TEXTS.get(("start", 5), ""))
        self._add_reminder_row("start", 0, True, tts_text=DEFAULT_TTS_TEXTS.get(("start", 0), ""))
        self._add_reminder_row("end", 15, True, tts_text=DEFAULT_TTS_TEXTS.get(("end", 15), ""))
        self._add_reminder_row("end", 0, True, tts_text=DEFAULT_TTS_TEXTS.get(("end", 0), ""))

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 16)

        # ── 标题 ──
        title = QLabel("添加新考试")
        title.setObjectName("examAddTitle")
        layout.addWidget(title)

        # ── 考试信息区 ──
        exam_group = QGroupBox("考试信息")
        exam_group.setObjectName("examAddGroup")
        eg = QGridLayout(exam_group)
        eg.setVerticalSpacing(8)
        eg.setHorizontalSpacing(8)

        eg.addWidget(QLabel("考试名称"), 0, 0)
        self._subject_input = QLineEdit()
        self._subject_input.setPlaceholderText("如：高等数学")
        self._subject_input.setMinimumHeight(28)
        eg.addWidget(self._subject_input, 0, 1, 1, 3)

        eg.addWidget(QLabel("日期"), 1, 0)
        self._date_input = QDateEdit()
        self._date_input.setCalendarPopup(True)
        self._date_input.setDate(QDate.currentDate())
        self._date_input.setDisplayFormat("yyyy-MM-dd")
        self._date_input.setMinimumHeight(28)
        eg.addWidget(self._date_input, 1, 1)

        eg.addWidget(QLabel("开始时间"), 1, 2)
        self._start_time_input = QTimeEdit()
        self._start_time_input.setTime(QTime(9, 0))
        self._start_time_input.setDisplayFormat("HH:mm")
        self._start_time_input.setMinimumHeight(28)
        self._start_time_input.timeChanged.connect(self._refresh_previews)
        eg.addWidget(self._start_time_input, 1, 3)

        eg.addWidget(QLabel("结束时间"), 2, 0)
        self._end_time_input = QTimeEdit()
        self._end_time_input.setTime(QTime(11, 0))
        self._end_time_input.setDisplayFormat("HH:mm")
        self._end_time_input.setMinimumHeight(28)
        self._end_time_input.timeChanged.connect(self._refresh_previews)
        eg.addWidget(self._end_time_input, 2, 1)

        layout.addWidget(exam_group)

        # ── 提醒设置区 ──
        reminder_group = QGroupBox("提醒设置")
        reminder_group.setObjectName("examAddReminderGroup")
        rg_layout = QVBoxLayout(reminder_group)
        rg_layout.setSpacing(4)

        # 提醒列表滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(160)
        scroll.setMaximumHeight(250)

        self._reminders_widget = QWidget()
        self._reminders_container = QVBoxLayout(self._reminders_widget)
        self._reminders_container.setSpacing(6)
        self._reminders_container.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self._reminders_widget)
        rg_layout.addWidget(scroll)

        add_btn = QPushButton("+ 添加提醒")
        add_btn.setObjectName("accentBtn")
        
        add_btn.setFixedHeight(28)
        add_btn.clicked.connect(lambda: self._add_reminder_row("start", 30, True))
        rg_layout.addWidget(add_btn)

        self._preview_label = QLabel("")
        self._preview_label.setObjectName("examPreviewLabel")
        self._preview_label.setWordWrap(True)
        rg_layout.addWidget(self._preview_label)

        layout.addWidget(reminder_group)

        # ── 按钮 ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._refresh_previews()

    def _add_reminder_row(self, rtype="start", mins=30, enabled=True, audio=None, tts_text=None):
        row_frame = QFrame()
        row_frame.setObjectName("examReminderRow")
        ml = QVBoxLayout(row_frame)
        ml.setContentsMargins(8, 6, 8, 6)
        ml.setSpacing(3)

        row1 = QHBoxLayout()
        row1.setSpacing(6)

        enable_check = QCheckBox()
        enable_check.setChecked(enabled)
        enable_check.setFixedSize(18, 18)
        enable_check.stateChanged.connect(self._refresh_previews)
        row1.addWidget(enable_check)

        type_combo = QComboBox()
        type_combo.addItem("开考前", "start")
        type_combo.addItem("结束前", "end")
        type_combo.setCurrentIndex(0 if rtype == "start" else 1)
        type_combo.setMinimumWidth(70)
        type_combo.currentIndexChanged.connect(self._refresh_previews)
        row1.addWidget(type_combo)

        row1.addWidget(QLabel("提前"))

        mins_spin = QSpinBox()
        mins_spin.setRange(0, 600)
        mins_spin.setValue(mins)
        mins_spin.setSuffix(" 分钟")
        mins_spin.setSingleStep(5)
        mins_spin.setMinimumWidth(90)
        mins_spin.valueChanged.connect(self._refresh_previews)
        row1.addWidget(mins_spin)

        for m in self.REMINDER_PRESETS:
            tag = QPushButton(f"{m}")
            tag.setObjectName("tagBtn")
            tag.setFixedSize(40, 24)
            tag.clicked.connect(lambda checked, s=mins_spin, v=m: s.setValue(v))
            row1.addWidget(tag)

        row1.addStretch()

        time_label = QLabel("")
        time_label.setObjectName("examTimeLabel")
        row1.addWidget(time_label)

        del_btn = QPushButton("删除")
        del_btn.setObjectName("tableDeleteBtn")
        del_btn.setFixedSize(50, 24)
        row1.addWidget(del_btn)

        ml.addLayout(row1)

        # 语音行
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.setContentsMargins(24, 0, 0, 0)
        voice_label = QLabel("语音:")
        voice_label.setObjectName("examVoiceLabel")
        row2.addWidget(voice_label)

        audio_label = QLabel("")
        audio_label.setObjectName("examAddAudioLabel")
        row2.addWidget(audio_label)

        pick_btn = QPushButton("选择音频文件")
        pick_btn.setFixedHeight(24)
        pick_btn.setObjectName("examAddPickAudioBtn")
        row2.addWidget(pick_btn)

        clear_btn = QPushButton("清除")
        clear_btn.setFixedHeight(24)
        clear_btn.setObjectName("examAddClearAudioBtn")
        row2.addWidget(clear_btn)

        # 试听按钮
        preview_btn = QPushButton("试听")
        preview_btn.setFixedHeight(24)
        preview_btn.setObjectName("examPreviewBtn")
        preview_btn.setToolTip("播报试听语音")
        row2.addWidget(preview_btn)

        row2.addStretch()
        ml.addLayout(row2)

        # TTS 文字行
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.setContentsMargins(24, 0, 0, 0)
        tts_label = QLabel("TTS文字:")
        tts_label.setObjectName("examTtsLabel")
        row3.addWidget(tts_label)

        tts_text_edit = QLineEdit()
        tts_text_edit.setPlaceholderText("自定义播报文字（留空则使用默认文字）")
        tts_text_edit.setObjectName("examTtsInput")
        tts_text_edit.setMinimumHeight(26)
        if tts_text:
            tts_text_edit.setText(tts_text)
        tts_text_edit.textChanged.connect(self._refresh_previews)
        row3.addWidget(tts_text_edit, 1)
        ml.addLayout(row3)

        self._reminders_container.addWidget(row_frame)

        rd = {
            "frame": row_frame, "enable_check": enable_check,
            "type_combo": type_combo, "mins_spin": mins_spin,
            "time_label": time_label, "audio_label": audio_label,
            "audio_path": audio,
            "tts_text_edit": tts_text_edit,
            "tts_text": tts_text,
        }
        self._reminder_rows.append(rd)

        self._update_audio_label(rd)
        del_btn.clicked.connect(lambda checked, r=rd: self._remove_row(r))
        pick_btn.clicked.connect(lambda checked, r=rd: self._pick_audio(r))
        clear_btn.clicked.connect(lambda checked, r=rd: self._clear_audio(r))
        preview_btn.clicked.connect(lambda checked, r=rd: self._preview_reminder(r))

        # 连接 TTS 自动同步
        type_combo.currentIndexChanged.connect(lambda: self._sync_tts_preset(rd))
        mins_spin.valueChanged.connect(lambda: self._sync_tts_preset(rd))

        self._refresh_previews()

    def _remove_row(self, rd):
        self._reminders_container.removeWidget(rd["frame"])
        rd["frame"].deleteLater()
        self._reminder_rows.remove(rd)
        self._refresh_previews()

    def _sync_tts_preset(self, rd):
        """当类型/分钟变化时，自动填充对应预设 TTS 文字（除非用户已手动输入自定义文字）"""
        r_type = rd["type_combo"].currentData()
        mins = rd["mins_spin"].value()
        preset = DEFAULT_TTS_TEXTS.get((r_type, mins), "")
        current = rd["tts_text_edit"].text().strip()

        # 如果当前文字为空、或匹配某个预设（说明是自动生成的），则自动更新
        is_auto = (not current) or any(current == v for v in DEFAULT_TTS_TEXTS.values())
        if is_auto and preset:
            rd["tts_text_edit"].setText(preset)
        elif is_auto and not preset:
            rd["tts_text_edit"].clear()

    def _pick_audio(self, rd):
        path, _ = QFileDialog.getOpenFileName(self, "选择提醒语音文件", "", self.AUDIO_FILTER)
        if path:
            rd["audio_path"] = path
            self._update_audio_label(rd)
            self._refresh_previews()

    def _clear_audio(self, rd):
        rd["audio_path"] = None
        self._update_audio_label(rd)
        self._refresh_previews()

    def _preview_reminder(self, rd):
        """试听提醒语音"""
        text = rd["tts_text_edit"].text().strip()
        if not text:
            text = "这是一条试听语音"
        if self._play_preview:
            self._play_preview(text)
        else:
            worker = ReminderPreviewWorker(text)
            worker.start()

    def _update_audio_label(self, rd):
        path = rd.get("audio_path")
        if path:
            name = os.path.basename(path)
            if len(name) > 20:
                name = name[:17] + "..."
            rd["audio_label"].setText(f"自定义: {name}")
            rd["audio_label"].setProperty("state", "custom")
            rd["audio_label"].style().unpolish(rd["audio_label"])
            rd["audio_label"].style().polish(rd["audio_label"])
        else:
            rd["audio_label"].setText("默认 TTS")
            rd["audio_label"].setProperty("state", "default")
            rd["audio_label"].style().unpolish(rd["audio_label"])
            rd["audio_label"].style().polish(rd["audio_label"])

    def _refresh_previews(self):
        if not self._reminder_rows:
            self._preview_label.setText("暂无提醒，点击 [+ 添加提醒] 添加")
            return
        parts = []
        for rd in self._reminder_rows:
            enabled = rd["enable_check"].isChecked()
            r_type = rd["type_combo"].currentData()
            mins = rd["mins_spin"].value()
            audio = rd.get("audio_path")
            try:
                bt = self._start_time_input.time() if r_type == "start" else self._end_time_input.time()
                total = bt.hour() * 60 + bt.minute() - mins
                if total < 0:
                    total += 24 * 60
                ts = f"{total // 60:02d}:{total % 60:02d}"
            except Exception:
                ts = "—"
            tl = "开考前" if r_type == "start" else "结束前"
            if mins == 0:
                desc = "开始考试" if r_type == "start" else "考试结束"
            else:
                desc = f"{tl}{mins}分钟"
            at = " [自定义]" if audio else ""
            tt = " [TTS]" if rd.get("tts_text_edit") and rd["tts_text_edit"].text().strip() else ""
            rd["time_label"].setText(ts)
            rd["time_label"].setProperty("type", r_type)
            rd["time_label"].style().unpolish(rd["time_label"])
            rd["time_label"].style().polish(rd["time_label"])
            if enabled:
                parts.append(f"{ts} {desc}{at}{tt}")
        self._preview_label.setText("  |  ".join(parts) if parts else "所有提醒均已禁用")

    def _validate_and_accept(self):
        if not self._subject_input.text().strip():
            show_toast(self, "请输入考试名称", "warning")
            return
        s = self._start_time_input.time()
        e = self._end_time_input.time()
        if s >= e:
            show_toast(self, "开始时间必须早于结束时间", "warning")
            return
        self.accept()

    def get_exam_data(self) -> dict:
        return {
            "subject": self._subject_input.text().strip(),
            "exam_date": self._date_input.date().toString("yyyy-MM-dd"),
            "start_time": self._start_time_input.time().toString("HH:mm"),
            "end_time": self._end_time_input.time().toString("HH:mm"),
        }

    def get_reminders_data(self) -> list[dict]:
        result = []
        for rd in self._reminder_rows:
            result.append({
                "reminder_type": rd["type_combo"].currentData(),
                "minutes_before": rd["mins_spin"].value(),
                "is_enabled": rd["enable_check"].isChecked(),
                "custom_audio_path": rd.get("audio_path"),
                "custom_tts_text": rd["tts_text_edit"].text().strip() or None,
            })
        return result


# ── 单条提醒编辑弹窗 ──────────────────────────────────

class SingleReminderEditDialog(QDialog):
    """编辑单条提醒"""

    REMINDER_PRESETS = [0, 5, 10, 15, 30, 60]
    AUDIO_FILTER = "音频文件 (*.mp3 *.wav *.ogg *.m4a *.flac *.aac);;所有文件 (*)"

    def __init__(self, exam: Exam, reminder: ExamReminder, parent=None):
        super().__init__(parent)
        self._exam = exam
        self._reminder = reminder
        self._audio_path = reminder.custom_audio_path
        self._tts_text = reminder.custom_tts_text or ""
        self.setWindowTitle(f"编辑提醒 - {exam.subject}")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 16, 18, 18)

        # 标题
        title = QLabel("编辑提醒")
        title.setObjectName("examDialogTitle")
        layout.addWidget(title)

        # 考试信息
        info = QLabel(
            f"<b>{self._exam.subject}</b>"
            f"<span> &nbsp;|&nbsp; {self._exam.exam_date}</span>"
            f"<span> &nbsp;|&nbsp; {self._exam.start_time}~{self._exam.end_time}</span>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setObjectName("examSingleInfo")
        info.setWordWrap(True)
        layout.addWidget(info)

        # 基本设置
        basic = QGroupBox("提醒设置")
        fg = QGridLayout(basic)
        fg.setVerticalSpacing(8)
        fg.setHorizontalSpacing(8)

        self._enable_check = QCheckBox("启用")
        self._enable_check.setChecked(self._reminder.is_enabled)
        fg.addWidget(self._enable_check, 0, 0, 1, 2)

        self._type_combo = QComboBox()
        self._type_combo.addItem("开考前", "start")
        self._type_combo.addItem("结束前", "end")
        self._type_combo.addItem("开始考试", "start")
        self._type_combo.addItem("考试结束", "end")
        self._type_combo.setCurrentIndex(0 if self._reminder.reminder_type == "start" else 1)
        fg.addWidget(QLabel("类型"), 1, 0)
        fg.addWidget(self._type_combo, 1, 1)

        self._mins_spin = QSpinBox()
        self._mins_spin.setRange(0, 600)
        self._mins_spin.setValue(self._reminder.minutes_before or 0)
        self._mins_spin.setSuffix(" 分钟")
        self._mins_spin.setSingleStep(5)
        self._mins_spin.setMinimumWidth(100)
        self._mins_spin.valueChanged.connect(self._update_preview)
        fg.addWidget(QLabel("提前"), 2, 0)
        fg.addWidget(self._mins_spin, 2, 1)

        # 快捷预设
        tag_row = QHBoxLayout()
        tag_row.setSpacing(4)
        for m in self.REMINDER_PRESETS:
            tag = QPushButton(f"{m}")
            tag.setObjectName("tagBtn")
            tag.setFixedSize(40, 24)
            tag.clicked.connect(lambda checked, s=self._mins_spin, v=m: s.setValue(v))
            tag_row.addWidget(tag)
        tag_row.addStretch()
        fg.addWidget(QLabel("快捷"), 3, 0)
        fg.addLayout(tag_row, 3, 1)

        layout.addWidget(basic)

        # 语音设置
        voice_group = QGroupBox("语音设置")
        vg = QVBoxLayout(voice_group)
        vg.setSpacing(6)

        self._audio_label = QLabel("")
        self._update_audio_status()
        vg.addWidget(self._audio_label)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(6)
        pick_btn = QPushButton("选择音频文件")
        pick_btn.setFixedHeight(24)
        pick_btn.clicked.connect(self._pick_audio)
        audio_row.addWidget(pick_btn)

        clear_btn = QPushButton("清除")
        clear_btn.setFixedHeight(24)
        clear_btn.setObjectName("examSingleClearBtn")
        clear_btn.clicked.connect(self._clear_audio)
        audio_row.addWidget(clear_btn)
        audio_row.addStretch()
        vg.addLayout(audio_row)

        # TTS 自定义文字
        tts_row = QHBoxLayout()
        tts_row.setSpacing(6)
        tts_label = QLabel("TTS文字:")
        tts_label.setObjectName("examTtsLabel")
        tts_row.addWidget(tts_label)

        self._tts_edit = QLineEdit()
        self._tts_edit.setPlaceholderText("自定义播报文字（留空则使用默认文字）")
        self._tts_edit.setObjectName("examSingleTtsInput")
        self._tts_edit.setMinimumHeight(28)
        self._tts_edit.setText(self._tts_text)
        self._tts_edit.textChanged.connect(self._update_preview)
        tts_row.addWidget(self._tts_edit, 1)
        vg.addLayout(tts_row)

        layout.addWidget(voice_group)

        # 预览
        self._preview = QLabel("")
        self._preview.setObjectName("examSinglePreview")
        layout.addWidget(self._preview)

        self._type_combo.currentIndexChanged.connect(self._update_preview)
        self._update_preview()

        # 连接 TTS 自动同步
        self._type_combo.currentIndexChanged.connect(self._auto_sync_tts)
        self._mins_spin.valueChanged.connect(self._auto_sync_tts)

        # 按钮
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _pick_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择提醒语音文件", "", self.AUDIO_FILTER)
        if path:
            self._audio_path = path
            self._update_audio_status()

    def _clear_audio(self):
        self._audio_path = None
        self._update_audio_status()

    def _update_audio_status(self):
        if self._audio_path:
            name = os.path.basename(self._audio_path)
            if len(name) > 25:
                name = name[:22] + "..."
            self._audio_label.setText(f"自定义: {name}")
            self._audio_label.setProperty("state", "custom")
            self._audio_label.style().unpolish(self._audio_label)
            self._audio_label.style().polish(self._audio_label)
        else:
            self._audio_label.setText("默认 TTS 语音")
            self._audio_label.setProperty("state", "default")
            self._audio_label.style().unpolish(self._audio_label)
            self._audio_label.style().polish(self._audio_label)

    def _update_preview(self):
        r_type = self._type_combo.currentData()
        mins = self._mins_spin.value()
        try:
            time_str = self._exam.start_time if r_type == "start" else self._exam.end_time
            h, m = map(int, time_str.split(":"))
            total = h * 60 + m - mins
            if total < 0:
                total += 24 * 60
            ts = f"{total // 60:02d}:{total % 60:02d}"
        except Exception:
            ts = "—"
        tl = "开考前" if r_type == "start" else "结束前"
        if mins == 0:
            desc = "开始考试" if r_type == "start" else "考试结束"
        else:
            desc = f"{tl}{mins}分钟"
        tts_hint = " [TTS自定义]" if self._tts_edit.text().strip() else ""
        self._preview.setText(f"提醒时间: {ts}  ({desc}){tts_hint}")

    def _auto_sync_tts(self):
        """当类型/分钟变化时，自动填充对应预设 TTS 文字（除非用户已手动输入自定义文字）"""
        r_type = self._type_combo.currentData()
        mins = self._mins_spin.value()
        preset = DEFAULT_TTS_TEXTS.get((r_type, mins), "")
        current = self._tts_edit.text().strip()

        # 如果当前文字为空、或匹配某个预设（说明是自动生成的），则自动更新
        is_auto = (not current) or any(current == v for v in DEFAULT_TTS_TEXTS.values())
        if is_auto and preset:
            self._tts_edit.setText(preset)
        elif is_auto and not preset:
            self._tts_edit.clear()

    def get_data(self) -> dict:
        return {
            "reminder_type": self._type_combo.currentData(),
            "minutes_before": self._mins_spin.value(),
            "is_enabled": self._enable_check.isChecked(),
            "custom_audio_path": self._audio_path,
            "custom_tts_text": self._tts_edit.text().strip() or None,
        }


# ── 考试管理页面 ──────────────────────────────────────

class BroadcastPopup(QDialog):
    """语音播报通知弹窗 — 播放时显示，播完自动关闭"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("语音播报")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMinimumWidth(380)
        self.setMaximumWidth(460)
        self._init_ui()
        self.setObjectName("broadcastPopup")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(8)

        # 标题行
        self._title_label = QLabel("")
        self._title_label.setObjectName("broadcastTitle")
        self._title_label.setWordWrap(True)
        layout.addWidget(self._title_label)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("broadcastSep")
        layout.addWidget(sep)

        # 播报内容
        self._content_label = QLabel("")
        self._content_label.setObjectName("broadcastContent")
        self._content_label.setWordWrap(True)
        self._content_label.setMinimumHeight(40)
        layout.addWidget(self._content_label)

        # 底部状态
        self._hint_label = QLabel("正在播报...")
        self._hint_label.setObjectName("broadcastHint")
        layout.addWidget(self._hint_label)

    def show_broadcast(self, exam_subject: str, reminder_type: str,
                       minutes_before: int, tts_text: str):
        """显示播报弹窗"""
        if reminder_type == "start":
            if minutes_before == 0:
                type_desc = "开始考试"
            else:
                type_desc = f"考前 {minutes_before} 分钟"
        else:
            if minutes_before == 0:
                type_desc = "考试结束"
            else:
                type_desc = f"结束前 {minutes_before} 分钟"

        self._title_label.setText(f"{exam_subject} - {type_desc}")
        self._content_label.setText(tts_text)
        self.adjustSize()

        # 居中显示
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.center().x() - self.width() // 2
            y = parent_geo.center().y() - self.height() // 2
            self.move(x, y)

        self.show()

        # 平滑出现：上滑 + 淡入，并让“正在播报”提示呼吸闪烁
        if hasattr(self, "_popup_anim"):
            self._popup_anim.stop()
        if hasattr(self, "_hint_pulse"):
            self._hint_pulse.stop()
        from ui.animations import slide_fade_in, pulse
        self._popup_anim = slide_fade_in(self, duration=320, slide_offset=20)
        self._hint_pulse = pulse(self._hint_label, duration=900, min_opacity=0.4)
        self.raise_()

    def close_popup(self):
        """关闭弹窗"""
        self.hide()
        if hasattr(self, "_popup_anim"):
            self._popup_anim.stop()
        if hasattr(self, "_hint_pulse"):
            self._hint_pulse.stop()


class ExamPage(QWidget):
    """考试管理页面 — 两列卡片式布局，参考网页版"""

    REMINDER_PRESETS = [0, 5, 10, 15, 30, 60]
    def __init__(self, ctx: dict):
        super().__init__()
        self._exam_svc: ExamService = ctx["exam_service"]
        self._ai_svc: ZhipuAIService | None = ctx.get("ai_service")
        self._file_parser: FileParserService = ctx["file_parser"]
        self._scheduler = ctx.get("scheduler")
        self._worker: AITaskWorker | None = None
        self._selected_exam_id: int | None = None
        self._exam_cards: dict[int, QFrame] = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # ── 标题栏 ──
        header = QHBoxLayout()
        title = QLabel("考试管理")
        title.setObjectName("examPageTitle")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setMinimumWidth(70)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # ── 两列主体 ──
        body = QHBoxLayout()
        body.setSpacing(8)

        # 左列：考试列表
        left = self._create_exam_list_panel()
        body.addWidget(left, 3)

        # 右列：提醒设置
        right = self._create_reminder_panel()
        body.addWidget(right, 2)

        layout.addLayout(body, 1)

        # 状态栏
        self._status = QLabel("")
        self._status.setObjectName("examPageStatus")
        layout.addWidget(self._status)

    def _create_exam_list_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("cardFrame")
        panel.setObjectName("examPageCardFrame")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(10, 10, 10, 10)
        pl.setSpacing(6)

        # 标题行
        hdr = QHBoxLayout()
        lbl = QLabel("考试列表")
        lbl.setObjectName("examPageSectionLabel")
        hdr.addWidget(lbl)
        hdr.addStretch()

        count_label = QLabel("")
        count_label.setObjectName("examPageCountLabel")
        self._count_label = count_label
        hdr.addWidget(count_label)
        pl.addLayout(hdr)

        # 添加按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        add_btn = QPushButton("+ 添加考试")
        add_btn.setObjectName("accentBtn")
        
        add_btn.clicked.connect(self._open_add_exam_dialog)
        btn_row.addWidget(add_btn)

        ai_btn = QPushButton("AI 添加")
        ai_btn.setFixedHeight(30)
        ai_btn.setToolTip("用自然语言描述考试安排")
        ai_btn.clicked.connect(self._open_ai_dialog)
        btn_row.addWidget(ai_btn)
        self._ai_btn = ai_btn

        import_btn = QPushButton("导入文件")
        import_btn.setFixedHeight(30)
        import_btn.setToolTip("从 Excel/CSV 导入")
        import_btn.clicked.connect(self._import_file)
        btn_row.addWidget(import_btn)
        self._import_btn = import_btn

        export_btn = QPushButton("导出")
        export_btn.setFixedHeight(30)
        export_btn.setToolTip("导出考试列表为 CSV")
        export_btn.clicked.connect(self._export_exams)
        btn_row.addWidget(export_btn)

        btn_row.addStretch()
        pl.addLayout(btn_row)

        # 卡片滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("examPageScroll")

        self._exam_list_container = QWidget()
        self._exam_list_layout = QVBoxLayout(self._exam_list_container)
        self._exam_list_layout.setSpacing(8)
        self._exam_list_layout.setContentsMargins(0, 0, 0, 0)
        self._exam_list_layout.addStretch()
        scroll.setWidget(self._exam_list_container)

        pl.addWidget(scroll, 1)
        return panel

    def _create_reminder_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("cardFrame")
        panel.setObjectName("examPageCardFrame")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(10, 10, 10, 10)
        pl.setSpacing(6)

        hdr = QHBoxLayout()
        lbl = QLabel("提醒设置")
        lbl.setObjectName("examPageSectionLabel")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self._reminder_count_label = QLabel("")
        self._reminder_count_label.setObjectName("examPageCountLabel")
        hdr.addWidget(self._reminder_count_label)
        pl.addLayout(hdr)

        # 提醒标题（显示选中考试）
        self._reminder_title = QLabel("请从左侧选择考试")
        self._reminder_title.setObjectName("examPageReminderTitle")
        self._reminder_title.setWordWrap(True)
        pl.addWidget(self._reminder_title)

        add_reminder_btn = QPushButton("+ 添加提醒")
        add_reminder_btn.setObjectName("accentBtn")
        
        add_reminder_btn.setFixedHeight(30)
        add_reminder_btn.clicked.connect(self._add_reminder_for_selected)
        pl.addWidget(add_reminder_btn)

        # 提醒卡片滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("examPageScroll")

        self._reminder_list_container = QWidget()
        self._reminder_list_layout = QVBoxLayout(self._reminder_list_container)
        self._reminder_list_layout.setSpacing(8)
        self._reminder_list_layout.setContentsMargins(0, 0, 0, 0)
        self._reminder_list_layout.addStretch()
        scroll.setWidget(self._reminder_list_container)

        pl.addWidget(scroll, 1)
        return panel

    # ── 刷新 ──────────────────────────────────────────

    def refresh(self):
        self._refresh_exam_list()
        self._refresh_reminder_list()

    def _refresh_exam_list(self):
        # 清除旧卡片
        for w in self._exam_cards.values():
            self._exam_list_layout.removeWidget(w)
            w.deleteLater()
        self._exam_cards.clear()

        # 移除旧 stretch
        for i in reversed(range(self._exam_list_layout.count())):
            item = self._exam_list_layout.itemAt(i)
            if item and item.spacerItem():
                self._exam_list_layout.removeItem(item)

        exams = self._exam_svc.get_upcoming(30)
        self._count_label.setText(f"共 {len(exams)} 场")

        for exam in exams:
            card = self._render_exam_card(exam)
            self._exam_cards[exam.id] = card
            self._exam_list_layout.addWidget(card)

        self._exam_list_layout.addStretch()

        # 如果之前选中的考试已不在列表中，清除选中
        if self._selected_exam_id and self._selected_exam_id not in self._exam_cards:
            self._selected_exam_id = None

    def _render_exam_card(self, exam: Exam) -> QFrame:
        card = QFrame()
        card.setObjectName("examCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        cl = QVBoxLayout(card)
        cl.setSpacing(4)
        cl.setContentsMargins(0, 0, 0, 0)

        # 标题行
        hdr = QHBoxLayout()
        hdr.setSpacing(6)

        subject_label = QLabel(f"{exam.subject}")
        subject_label.setObjectName("examPageCardSubject")
        hdr.addWidget(subject_label)
        hdr.addStretch()

        # 状态标签
        from datetime import datetime
        now = datetime.now()
        try:
            exam_start = datetime.strptime(f"{exam.exam_date} {exam.start_time}", "%Y-%m-%d %H:%M")
            exam_end = datetime.strptime(f"{exam.exam_date} {exam.end_time}", "%Y-%m-%d %H:%M")
            if now < exam_start:
                status_text = "即将开始"
            elif exam_start <= now <= exam_end:
                status_text = "进行中"
            else:
                status_text = "已结束"
        except Exception:
            status_text = "—"

        status_badge = QLabel(status_text)
        status_badge.setObjectName("examPageCardStatus")
        status_badge.setProperty("state", status_text)
        status_badge.style().unpolish(status_badge)
        status_badge.style().polish(status_badge)
        status_badge.setFixedHeight(20)
        hdr.addWidget(status_badge)
        cl.addLayout(hdr)

        # 详情行
        detail = QLabel(
            f"{exam.exam_date}  |  {exam.start_time} ~ {exam.end_time}"
        )
        detail.setObjectName("examPageCardDetail")
        detail.setWordWrap(True)
        cl.addWidget(detail)

        # 提醒摘要
        active = exam.active_reminders
        if active:
            parts = []
            for r in active:
                m = r.minutes_before or 0
                if r.reminder_type == "start":
                    label = "开始考试" if m == 0 else f"考前{m}分"
                else:
                    label = "考试结束" if m == 0 else f"结束前{m}分"
                audio = "[自定义]" if getattr(r, 'custom_audio_path', None) else ""
                tts = "[TTS]" if getattr(r, 'custom_tts_text', None) else ""
                parts.append(f"{label}{audio}{tts}")
            remind_summary = QLabel("  " + " + ".join(parts))
            remind_summary.setObjectName("examPageCardRemindSummary")
        else:
            remind_summary = QLabel("  未设置提醒")
            remind_summary.setProperty("state", "empty")
            remind_summary.style().unpolish(remind_summary)
            remind_summary.style().polish(remind_summary)
        cl.addWidget(remind_summary)

        # 提醒时间
        if active:
            times = exam.all_reminder_times
            time_label = QLabel("  " + " / ".join(times))
            time_label.setObjectName("examPageCardTime")
            cl.addWidget(time_label)

        # 操作按钮行
        ops = QHBoxLayout()
        ops.setSpacing(4)
        ops.addStretch()

        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("tableActionBtn")
        edit_btn.setFixedSize(44, 22)
        edit_btn.clicked.connect(lambda checked, eid=exam.id: self._edit_exam(eid))
        ops.addWidget(edit_btn)

        del_btn = QPushButton("删除")
        del_btn.setObjectName("tableDeleteBtn")
        del_btn.setFixedSize(48, 22)
        del_btn.clicked.connect(lambda checked, eid=exam.id: self._delete_exam(eid))
        ops.addWidget(del_btn)

        cl.addLayout(ops)

        # 点击卡片选中
        card.mousePressEvent = lambda e, eid=exam.id: self._select_exam(eid)
        return card

    def _select_exam(self, exam_id: int):
        self._selected_exam_id = exam_id
        # 更新选中样式
        for eid, card in self._exam_cards.items():
            card.setProperty("selected", eid == exam_id)
            card.style().unpolish(card)
            card.style().polish(card)
        self._refresh_reminder_list()

    def _refresh_reminder_list(self):
        # 清除旧提醒卡片
        for i in reversed(range(self._reminder_list_layout.count())):
            w = self._reminder_list_layout.itemAt(i)
            if w and w.widget():
                w.widget().deleteLater()
            elif w and w.spacerItem():
                self._reminder_list_layout.removeItem(w)

        if not self._selected_exam_id:
            self._reminder_title.setText("请从左侧选择考试")
            self._reminder_title.setProperty("state", "empty")
            self._reminder_title.style().unpolish(self._reminder_title)
            self._reminder_title.style().polish(self._reminder_title)
            self._reminder_count_label.setText("")
            self._reminder_list_layout.addStretch()
            return

        exam = self._exam_svc.get_by_id(self._selected_exam_id)
        if not exam:
            self._reminder_title.setText("考试不存在")
            self._reminder_count_label.setText("")
            self._reminder_list_layout.addStretch()
            return

        self._reminder_title.setText(
            f"<b>{exam.subject}</b> &nbsp;|&nbsp; {exam.exam_date} &nbsp;|&nbsp; "
            f"{exam.start_time}~{exam.end_time}"
        )
        self._reminder_title.setTextFormat(Qt.TextFormat.RichText)

        reminders = self._exam_svc.get_reminders(exam.id)
        enabled_count = sum(1 for r in reminders if r.is_enabled)
        self._reminder_count_label.setText(f"{len(reminders)} 条提醒，{enabled_count} 条已启用")

        for r in reminders:
            card = self._render_reminder_card(r)
            self._reminder_list_layout.addWidget(card)

        if not reminders:
            empty = QLabel("暂无提醒，点击上方按钮添加")
            empty.setObjectName("examPageEmptyLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._reminder_list_layout.addWidget(empty)

        self._reminder_list_layout.addStretch()

    def _render_reminder_card(self, reminder) -> QFrame:
        card = QFrame()
        card.setObjectName("reminderCard")
        # 禁用状态：降低透明度 + 灰色边框
        if not reminder.is_enabled:
            card.setProperty("state", "disabled")
            card.style().unpolish(card)
            card.style().polish(card)
        else:
            card.setProperty("state", "enabled")
            card.style().unpolish(card)
            card.style().polish(card)

        cl = QVBoxLayout(card)
        cl.setSpacing(3)
        cl.setContentsMargins(0, 0, 0, 0)

        # 标题行
        hdr = QHBoxLayout()
        hdr.setSpacing(6)

        rlabel = QLabel(f"{reminder.description}")
        if reminder.is_enabled:
            rlabel.setObjectName("examPageReminderLabel")
        else:
            rlabel.setProperty("state", "disabled")
            rlabel.style().unpolish(rlabel)
            rlabel.style().polish(rlabel)
        hdr.addWidget(rlabel)
        hdr.addStretch()

        # 启用/禁用切换按钮
        toggle_btn = QPushButton("已启用" if reminder.is_enabled else "已禁用")
        toggle_btn.setObjectName("examPageToggleBtn")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(reminder.is_enabled)
        toggle_btn.setProperty("state", "enabled" if reminder.is_enabled else "disabled")
        toggle_btn.style().unpolish(toggle_btn)
        toggle_btn.style().polish(toggle_btn)
        toggle_btn.setFixedHeight(20)
        toggle_btn.clicked.connect(lambda checked, r=reminder: self._toggle_reminder(r))
        hdr.addWidget(toggle_btn)
        cl.addLayout(hdr)

        # 提醒时间
        rt = reminder.reminder_time
        if rt:
            time_info = QLabel(f"提醒时间: {rt}")
            time_info.setObjectName("examPageReminderTime")
            cl.addWidget(time_info)

        # 语音
        audio_label = QLabel(reminder.audio_label)
        if reminder.has_custom_audio:
            audio_label.setProperty("state", "custom")
            audio_label.style().unpolish(audio_label)
            audio_label.style().polish(audio_label)
        else:
            audio_label.setProperty("state", "default")
            audio_label.style().unpolish(audio_label)
            audio_label.style().polish(audio_label)
        cl.addWidget(audio_label)

        # 操作
        ops = QHBoxLayout()
        ops.setSpacing(4)
        ops.addStretch()

        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("tableActionBtn")
        edit_btn.setFixedSize(44, 20)
        edit_btn.clicked.connect(lambda checked, r=reminder: self._edit_single_reminder(r))
        ops.addWidget(edit_btn)

        del_btn = QPushButton("删除")
        del_btn.setObjectName("tableDeleteBtn")
        del_btn.setFixedSize(48, 20)
        del_btn.clicked.connect(lambda checked: self._delete_single_reminder(reminder.id))
        ops.addWidget(del_btn)

        cl.addLayout(ops)
        return card

    def _toggle_reminder(self, reminder):
        """切换单条提醒的启用/禁用状态"""
        new_enabled = not reminder.is_enabled
        try:
            self._exam_svc.update_reminder_by_id(
                reminder.id,
                is_enabled=new_enabled,
            )
            if self._scheduler:
                try:
                    updated = self._exam_svc.get_by_id(self._selected_exam_id)
                    if updated:
                        self._scheduler.generate_tasks_for_exam(updated)
                except Exception:
                    pass
            self.refresh()
            status = "启用" if new_enabled else "禁用"
            self._status.setText(f"提醒已{status}")
        except Exception as e:
            show_toast(self, f"操作失败：{e}", "error")

    def _add_reminder_for_selected(self):
        # 未选中或没有任何考试时：仅给静音的文字提示，绝不打开任何
        # 会触发试听/播报声的界面（不进入编辑弹窗、不播放音频）。
        if not self._selected_exam_id:
            has_exam = bool(getattr(self, "_exam_cards", None))
            msg = (
                "当前没有任何考试，无法添加提醒。请先添加考试。"
                if not has_exam
                else "请先从左侧选择一场考试，再为它添加提醒。"
            )
            show_toast(self, msg, "warning", duration=3600)
            return
        self._edit_reminder(self._selected_exam_id)

    def _delete_single_reminder(self, reminder_id: int):
        if not ask_confirm(
            self, "确认删除", "确定要删除这条提醒吗？",
            yes_text="删除", no_text="取消",
        ):
            return
        self._exam_svc.delete_reminder(reminder_id)
        self.refresh()
        self._status.setText("已删除提醒")

    # ── 添加考试 ──────────────────────────────────────

    def _open_add_exam_dialog(self):
        dlg = AddExamDialog(self, play_preview=self._play_reminder_preview)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_exam_data()
            reminders_data = dlg.get_reminders_data()

            start_r = next((r for r in reminders_data if r["reminder_type"] == "start"), None)
            end_r = next((r for r in reminders_data if r["reminder_type"] == "end"), None)

            # 冲突检测
            conflicts = self._exam_svc.check_conflicts(
                data["exam_date"], data["start_time"], data["end_time"]
            )
            if conflicts:
                names = "、".join([c.subject for c in conflicts])
                if not ask_confirm(
                    self, "时间冲突检测",
                    f"该时间段与以下考试存在冲突：\n{names}\n\n是否仍然添加？",
                    yes_text="仍然添加",
                    no_text="取消",
                ):
                    return

            exam = Exam(
                subject=data["subject"],
                exam_date=data["exam_date"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                reminder_enabled=start_r is not None,
                reminder_minutes_before=start_r["minutes_before"] if start_r else 30,
                reminder_end_enabled=end_r is not None,
                reminder_end_minutes_before=end_r["minutes_before"] if end_r else 15,
            )

            try:
                self._exam_svc.add(exam)
            except Exception as e:
                show_toast(self, f"保存考试失败：{e}", "error")
                return

            if reminders_data:
                try:
                    self._exam_svc.replace_reminders(exam.id, reminders_data)
                except Exception:
                    pass

            if self._scheduler:
                try:
                    self._scheduler.generate_tasks_for_exam(exam)
                except Exception:
                    pass

            self._status.setText(f"已添加 [{exam.subject}]")
            self.refresh()

    def _open_ai_dialog(self):
        if not self._ai_svc:
            show_toast(self, "未配置 AI API Key，请在设置页面配置", "warning")
            return

        dlg = AIDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text = dlg.get_text()
            reminders = dlg.get_reminders()

            self._ai_worker = AITaskWorker(self._ai_svc.parse_natural_language, text)
            self._ai_worker.finished.connect(
                lambda row: self._on_ai_result_static(row, reminders)
            )
            self._ai_worker.error.connect(
                lambda e: show_toast(self, f"AI 解析失败：{e}", "error")
            )
            self._ai_worker.start()

    def _on_ai_result_static(self, row: ParsedExamRow, reminders: list[dict]):
        if row.has_missing_fields:
            missing = ", ".join(row.get_missing_field_names())
            show_toast(self, f"解析不完整，缺失字段：{missing}，请手动补充", "warning", duration=3600)
            return

        exam = Exam(
            subject=row.subject or "",
            exam_date=row.date or "",
            start_time=row.start_time or "",
            end_time=row.end_time or "",
            reminder_enabled=bool(reminders),
            reminder_minutes_before=reminders[0]["minutes_before"] if reminders else 30,
            reminder_end_enabled=False,
            reminder_end_minutes_before=15,
        )
        self._exam_svc.add(exam)

        if reminders:
            try:
                self._exam_svc.replace_reminders(exam.id, reminders)
            except Exception:
                pass

        if self._scheduler:
            try:
                self._scheduler.generate_tasks_for_exam(exam)
            except Exception:
                pass

        self._status.setText(f"AI 解析成功，已添加 [{exam.subject}]")
        self.refresh()

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "Excel/CSV 文件 (*.xlsx *.csv *.tsv)"
        )
        if not path:
            return

        try:
            # 解析为 CSV 文本
            csv_text = self._file_parser.parse_file(path)
            reader = csv.reader(io.StringIO(csv_text))
            rows = list(reader)

            if not rows:
                show_toast(self, "导入文件为空", "warning")
                return

            # 解析表头，建立列索引
            header = [h.strip() for h in rows[0]]
            col_map = self._build_column_map(header)

            imported = 0
            skipped = 0

            for row_data in rows[1:]:
                if not any(cell.strip() for cell in row_data):
                    continue  # 跳过空行

                try:
                    exam_data = self._parse_exam_row(row_data, col_map)
                except ValueError:
                    skipped += 1
                    continue

                if not exam_data["subject"] or not exam_data["exam_date"]:
                    skipped += 1
                    continue

                exam = Exam(
                    subject=exam_data["subject"],
                    exam_date=exam_data["exam_date"],
                    start_time=exam_data["start_time"],
                    end_time=exam_data["end_time"],
                    reminder_enabled=bool(exam_data.get("reminders")),
                    reminder_minutes_before=30,
                )
                self._exam_svc.add(exam)

                # 保存提醒
                reminders = exam_data.get("reminders", [])
                if reminders:
                    self._exam_svc.replace_reminders(exam.id, reminders)

                if self._scheduler:
                    try:
                        updated = self._exam_svc.get_by_id(exam.id)
                        if updated:
                            self._scheduler.generate_tasks_for_exam(updated)
                    except Exception:
                        pass

                imported += 1

            self._status.setText(f"导入成功: {imported} 场考试" +
                                 (f"，跳过 {skipped} 行" if skipped else ""))
            self.refresh()
        except Exception as e:
            show_toast(self, f"导入失败：{e}", "error")

    def _build_column_map(self, header: list[str]) -> dict:
        """根据表头建立列名 → 列索引的映射"""
        col_map = {}
        for i, h in enumerate(header):
            h_lower = h.lower().replace(" ", "")
            if h in ("科目", "考试名称", "考试", "subject", "name"):
                col_map["subject"] = i
            elif h in ("日期", "考试日期", "date"):
                col_map["date"] = i
            elif h in ("开始时间", "start_time", "start"):
                col_map["start_time"] = i
            elif h in ("结束时间", "end_time", "end"):
                col_map["end_time"] = i
            elif h in ("提醒时间", "提醒触发时间"):
                col_map["reminder_times"] = i
            elif h in ("提醒设置", "提醒描述"):
                col_map["reminder_descs"] = i
            elif h in ("提醒次数", "提醒数量"):
                col_map["reminder_count"] = i
        return col_map

    def _parse_exam_row(self, row_data: list[str], col_map: dict) -> dict:
        """解析单行数据为考试字典"""
        def get(col_name, default=""):
            idx = col_map.get(col_name)
            if idx is not None and idx < len(row_data):
                return row_data[idx].strip()
            return default

        subject = get("subject")
        exam_date = get("date")
        start_time = get("start_time")
        end_time = get("end_time")

        # 标准化日期格式
        exam_date = self._normalize_date(exam_date)
        start_time = self._normalize_time(start_time)
        end_time = self._normalize_time(end_time)

        # 解析提醒
        reminders = self._parse_reminders(row_data, col_map)

        return {
            "subject": subject,
            "exam_date": exam_date,
            "start_time": start_time,
            "end_time": end_time,
            "reminders": reminders,
        }

    def _normalize_date(self, raw: str) -> str:
        """标准化日期为 yyyy-MM-dd"""
        raw = raw.strip()
        if not raw:
            return ""
        # 尝试常见格式
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        # 如果已经是 yyyy-MM-dd 格式
        if len(raw) == 10 and raw[4] == "-":
            return raw
        return raw

    def _normalize_time(self, raw: str) -> str:
        """标准化时间为 HH:mm"""
        raw = raw.strip()
        if not raw:
            return ""
        # 尝试常见格式
        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%H.%M"):
            try:
                return datetime.strptime(raw, fmt).strftime("%H:%M")
            except ValueError:
                continue
        if len(raw) == 5 and raw[2] == ":":
            return raw
        return raw

    def _parse_reminders(self, row_data: list[str], col_map: dict) -> list[dict]:
        """从行数据中解析提醒列表"""
        reminders = []

        # 优先从"提醒设置"列解析
        descs_idx = col_map.get("reminder_descs")
        if descs_idx is not None and descs_idx < len(row_data):
            descs_text = row_data[descs_idx].strip()
            if descs_text and descs_text != "未设置" and descs_text != "—":
                reminders = self._parse_reminder_descs(descs_text)
                if reminders:
                    return reminders

        # 回退：从"提醒时间"列反推
        times_idx = col_map.get("reminder_times")
        if times_idx is not None and times_idx < len(row_data):
            times_text = row_data[times_idx].strip()
            if times_text and times_text != "—":
                reminders = self._parse_reminder_times(times_text)
                if reminders:
                    return reminders

        # 默认：无提醒时给一条考前30分钟
        return []

    def _parse_reminder_descs(self, text: str) -> list[dict]:
        """解析提醒描述文本，如 '考前15分; 考前10分; 开始考试; 结束前15分; 考试结束'"""
        import re
        reminders = []
        parts = re.split(r"[;；,，/]", text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            rtype, mins = self._parse_single_desc(part)
            if rtype:
                reminders.append({
                    "reminder_type": rtype,
                    "minutes_before": mins,
                    "is_enabled": True,
                })
        return reminders

    def _parse_single_desc(self, desc: str) -> tuple:
        """解析单个提醒描述，如 '考前15分' → ('start', 15)"""
        import re
        desc = desc.strip()
        if desc in ("开始考试", "开考", "考试开始"):
            return ("start", 0)
        if desc in ("考试结束", "结束考试", "结束"):
            return ("end", 0)
        m = re.match(r"(考前|开考前|开始前)\s*(\d+)\s*分?", desc)
        if m:
            return ("start", int(m.group(2)))
        m = re.match(r"(结束前|考前结束|末尾前)\s*(\d+)\s*分?", desc)
        if m:
            return ("end", int(m.group(2)))
        return (None, 0)

    def _parse_reminder_times(self, text: str) -> list[dict]:
        """从提醒时间反推提醒（备用方案，假设为考前递减）"""
        import re
        times = re.findall(r"(\d{2}:\d{2})", text)
        if not times:
            return []
        reminders = []
        for t in times:
            reminders.append({
                "reminder_type": "start",
                "minutes_before": 30,  # 无法精确反推，给默认值
                "is_enabled": True,
            })
        return reminders

    # ── 导出考试列表 ──────────────────────────────────

    def _export_exams(self):
        """导出考试列表为 CSV 文件"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出考试列表", "考试列表.csv",
            "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if not path:
            return

        # 获取所有考试（含提醒数据）
        exams = self._exam_svc.get_all()

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # 表头
                writer.writerow([
                    "科目", "日期", "开始时间", "结束时间",
                    "提醒次数", "提醒时间", "提醒设置", "状态"
                ])
                # 数据行
                for exam in exams:
                    # 获取全部提醒（含禁用）
                    reminders = self._exam_svc.get_reminders(exam.id) if exam.id else []

                    # 提醒次数
                    reminder_count = len(reminders)

                    # 提醒时间：计算每条提醒的触发时间
                    reminder_times = []
                    reminder_descs = []
                    for r in reminders:
                        m = r.minutes_before or 0
                        try:
                            ref_time = exam.start_time if r.reminder_type == "start" else exam.end_time
                            hh, mm = map(int, ref_time.split(":"))
                            total = hh * 60 + mm - m
                            if total < 0:
                                total += 24 * 60
                            trigger = f"{total // 60:02d}:{total % 60:02d}"
                        except (ValueError, AttributeError):
                            trigger = "—"
                        reminder_times.append(trigger)

                        if r.reminder_type == "start":
                            desc = "开始考试" if m == 0 else f"考前{m}分"
                        else:
                            desc = "考试结束" if m == 0 else f"结束前{m}分"
                        reminder_descs.append(desc)

                    # 状态
                    now = datetime.now()
                    try:
                        exam_start = datetime.strptime(
                            f"{exam.exam_date} {exam.start_time}", "%Y-%m-%d %H:%M"
                        )
                        exam_end = datetime.strptime(
                            f"{exam.exam_date} {exam.end_time}", "%Y-%m-%d %H:%M"
                        )
                        if now < exam_start:
                            status = "即将开始"
                        elif exam_start <= now <= exam_end:
                            status = "进行中"
                        else:
                            status = "已结束"
                    except Exception:
                        status = "—"

                    writer.writerow([
                        exam.subject,
                        exam.exam_date,
                        exam.start_time,
                        exam.end_time,
                        reminder_count,
                        " / ".join(reminder_times) if reminder_times else "—",
                        "; ".join(reminder_descs) if reminder_descs else "未设置",
                        status,
                    ])

            self._status.setText(f"已导出 {len(exams)} 场考试")
            show_toast(self, f"已导出 {len(exams)} 场考试到:\n{path}", "success", duration=3600)
        except Exception as e:
            show_toast(self, f"导出失败：{e}", "error")

    # ── 编辑考试信息 ──────────────────────────────────

    def _edit_exam(self, exam_id: int):
        exam = self._exam_svc.get_by_id(exam_id)
        if not exam:
            return

        dlg = ExamEditDialog(exam, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_exam_data()

            # 冲突检测（排除自身）
            conflicts = self._exam_svc.check_conflicts(
                data["exam_date"], data["start_time"], data["end_time"],
                exclude_exam_id=exam_id
            )
            if conflicts:
                names = "、".join([c.subject for c in conflicts])
                if not ask_confirm(
                    self, "时间冲突检测",
                    f"修改后的时间段与以下考试存在冲突：\n{names}\n\n是否仍然保存？",
                    yes_text="仍然保存",
                    no_text="取消",
                ):
                    return

            exam.subject = data["subject"]
            exam.exam_date = data["exam_date"]
            exam.start_time = data["start_time"]
            exam.end_time = data["end_time"]
            exam.notes = data["notes"]

            try:
                self._exam_svc.update(exam)
            except Exception as e:
                show_toast(self, f"保存考试信息失败：{e}", "error")
                return

            if self._scheduler:
                try:
                    updated = self._exam_svc.get_by_id(exam_id)
                    if updated:
                        self._scheduler.generate_tasks_for_exam(updated)
                except Exception:
                    pass

            self.refresh()
            self._status.setText(f"已更新 [{data['subject']}] 的考试信息")

    def _play_reminder_preview(self, text: str):
        """试听提醒语音"""
        worker = ReminderPreviewWorker(text)
        worker.start()

    # ── 编辑提醒 ──────────────────────────────────────

    def _edit_reminder(self, exam_id: int):
        exam = self._exam_svc.get_by_id(exam_id)
        if not exam:
            return

        dlg = ReminderEditDialog(exam, self._exam_svc, self, play_preview=self._play_reminder_preview)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            reminders_data = dlg.get_reminders_data()
            self._exam_svc.replace_reminders(exam_id, reminders_data)

            if self._scheduler:
                try:
                    updated = self._exam_svc.get_by_id(exam_id)
                    if updated:
                        self._scheduler.generate_tasks_for_exam(updated)
                except Exception:
                    pass

            self.refresh()
            self._status.setText(f"已更新 [{exam.subject}] 的提醒设置")

    def _edit_single_reminder(self, reminder):
        """编辑单条提醒"""
        exam = self._exam_svc.get_by_id(self._selected_exam_id)
        if not exam:
            return

        dlg = SingleReminderEditDialog(exam, reminder, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()

            try:
                self._exam_svc.update_reminder_by_id(
                    reminder.id,
                    reminder_type=data["reminder_type"],
                    minutes_before=data["minutes_before"],
                    is_enabled=data["is_enabled"],
                    custom_audio_path=data["custom_audio_path"],
                    custom_tts_text=data["custom_tts_text"],
                )
            except Exception as e:
                show_toast(self, f"保存提醒失败：{e}", "error")
                return

            if self._scheduler:
                try:
                    updated = self._exam_svc.get_by_id(self._selected_exam_id)
                    if updated:
                        self._scheduler.generate_tasks_for_exam(updated)
                except Exception:
                    pass

            self.refresh()
            self._status.setText(f"已更新 [{exam.subject}] 的提醒")

    # ── 删除 ──────────────────────────────────────────

    def _delete_exam(self, exam_id: int):
        exam = self._exam_svc.get_by_id(exam_id)
        name = exam.subject if exam else "未知"

        if not ask_confirm(
            self, "确认删除",
            f"确定要删除 [{name}] 吗？\n关联的提醒任务也会一并清除。",
            yes_text="删除", no_text="取消",
        ):
            return
        if self._selected_exam_id == exam_id:
            self._selected_exam_id = None
        self._exam_svc.delete(exam_id)
        self.refresh()
        self._status.setText(f"已删除 [{name}]")

    def _on_offline_mode_changed(self, is_offline: bool):
        """离线模式切换：禁用/启用 AI 按钮和导入按钮"""
        if hasattr(self, "_ai_btn"):
            self._ai_btn.setEnabled(not is_offline)
        if hasattr(self, "_import_btn"):
            self._import_btn.setEnabled(not is_offline)


# ── AI 对话弹窗 ──────────────────────────────────────

class AIDialog(QDialog):
    # 6 个内置默认提醒（与 DEFAULT_TTS_TEXTS 保持一致）
    PRESETS = [
        ("start", 15, "开考前 15 分钟"),
        ("start", 10, "开考前 10 分钟"),
        ("start", 5,  "开考前 5 分钟"),
        ("start", 0,  "考试开始"),
        ("end",   15, "结束前 15 分钟"),
        ("end",   0,  "考试结束"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 添加考试")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 16, 18, 18)

        layout.addWidget(QLabel("用自然语言描述考试安排："))

        self._ai_input = QTextEdit()
        self._ai_input.setPlaceholderText(
            "例如：下周三上午9点到11点考高数，在A101教室"
        )
        self._ai_input.setMinimumHeight(60)
        self._ai_input.setMaximumHeight(90)
        layout.addWidget(self._ai_input)

        # 6 个内置默认提醒
        layout.addWidget(QLabel("默认提醒（可取消不需要的）："))
        self._reminder_checks: dict[str, QCheckBox] = {}
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, (rtype, mins, label) in enumerate(self.PRESETS):
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setObjectName("examAiCheckbox")
            key = f"{rtype}_{mins}"
            self._reminder_checks[key] = cb
            row = i // 2
            col = i % 2
            grid.addWidget(cb, row, col)
        layout.addLayout(grid)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate(self):
        if not self._ai_input.toPlainText().strip():
            show_toast(self, "请输入考试描述", "warning")
            return
        self.accept()

    def get_text(self) -> str:
        return self._ai_input.toPlainText().strip()

    def get_reminders(self) -> list[dict]:
        """返回用户选中的提醒列表"""
        result = []
        for rtype, mins, label in self.PRESETS:
            key = f"{rtype}_{mins}"
            cb = self._reminder_checks.get(key)
            if cb and cb.isChecked():
                result.append({
                    "reminder_type": rtype,
                    "minutes_before": mins,
                    "is_enabled": True,
                })
        return result
