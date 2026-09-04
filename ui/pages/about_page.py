"""作者信息页"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QDialog, QTextEdit, QPushButton, QHBoxLayout, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication
import logging
import io
import sys
import traceback

from config import APP_VERSION, APP_DISPLAY_NAME
from ui.widgets.toast import show_toast


class LogDialog(QDialog):
    """日志查看弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统日志")
        self.setMinimumSize(600, 400)
        self.resize(650, 450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 日志文本区
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setObjectName("logText")
        layout.addWidget(self._log_text)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._load_logs)
        refresh_btn.setFixedHeight(30)
        refresh_btn.setObjectName("aboutRefreshBtn")
        refresh_btn.setProperty("state", "primary")
        refresh_btn.style().unpolish(refresh_btn)
        refresh_btn.style().polish(refresh_btn)
        btn_row.addWidget(refresh_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedHeight(30)
        close_btn.setObjectName("aboutCloseBtn")
        close_btn.setProperty("state", "default")
        close_btn.style().unpolish(close_btn)
        close_btn.style().polish(close_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._load_logs()

    def _load_logs(self):
        """加载日志内容"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {APP_DISPLAY_NAME} {APP_VERSION} - 系统日志")
        lines.append("=" * 60)
        lines.append("")

        # Python 版本信息
        lines.append(f"[系统信息]")
        lines.append(f"  Python 版本: {sys.version}")
        lines.append(f"  平台: {sys.platform}")
        lines.append(f"  可执行路径: {sys.executable}")
        lines.append("")

        # 导入关键模块信息
        lines.append("[模块信息]")
        try:
            import PyQt6
            from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            lines.append(f"  PyQt6 版本: {PYQT_VERSION_STR}")
            lines.append(f"  Qt 版本: {QT_VERSION_STR}")
        except Exception:
            lines.append("  PyQt6: 无法获取版本")

        try:
            from apscheduler import version as aps_version
            lines.append(f"  APScheduler 版本: {aps_version}")
        except Exception:
            lines.append("  APScheduler: 无法获取版本")

        try:
            from sqlalchemy import __version__ as sa_version
            lines.append(f"  SQLAlchemy 版本: {sa_version}")
        except Exception:
            lines.append("  SQLAlchemy: 无法获取版本")

        try:
            import edge_tts
            lines.append(f"  edge-tts: 已安装")
        except ImportError:
            lines.append("  edge-tts: 未安装")

        try:
            import httpx
            lines.append(f"  httpx 版本: {httpx.__version__}")
        except Exception:
            lines.append("  httpx: 无法获取版本")

        lines.append("")

        # 数据库信息
        lines.append("[数据库信息]")
        try:
            from config import DB_PATH, SOUND_DIR, AUDIO_CACHE_DIR, APP_DATA_DIR
            import os
            lines.append(f"  应用数据目录: {APP_DATA_DIR}")
            lines.append(f"  数据库路径: {DB_PATH}")
            lines.append(f"  数据库存在: {'是' if os.path.exists(DB_PATH) else '否'}")
            if os.path.exists(DB_PATH):
                size = os.path.getsize(DB_PATH)
                lines.append(f"  数据库大小: {size / 1024:.1f} KB")
            lines.append(f"  语音文件夹: {SOUND_DIR}")
            lines.append(f"  音频缓存: {AUDIO_CACHE_DIR}")

            # 检查离线音频
            if os.path.exists(SOUND_DIR):
                audio_files = [f for f in os.listdir(SOUND_DIR) if f.endswith(('.mp3', '.wav', '.ogg'))]
                lines.append(f"  离线音频文件数: {len(audio_files)}")
                if audio_files:
                    for f in sorted(audio_files):
                        lines.append(f"    - {f}")
            else:
                lines.append("  离线音频文件夹不存在")
        except Exception as e:
            lines.append(f"  数据库信息获取失败: {e}")

        lines.append("")

        # 考试数据统计
        lines.append("[考试数据]")
        try:
            from services.database import get_session
            from models.exam import Exam
            from models.exam_reminder import ExamReminder
            from datetime import datetime
            session = get_session()
            try:
                total = session.query(Exam).count()
                today = datetime.now().strftime("%Y-%m-%d")
                today_exams = session.query(Exam).filter(Exam.exam_date == today).count()
                upcoming = session.query(Exam).filter(Exam.exam_date >= today).count()
                reminders = session.query(ExamReminder).count()
                lines.append(f"  考试总数: {total}")
                lines.append(f"  今日考试: {today_exams}")
                lines.append(f"  待考考试: {upcoming}")
                lines.append(f"  提醒总数: {reminders}")
            finally:
                session.close()
        except Exception as e:
            lines.append(f"  考试数据获取失败: {e}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("  日志结束")
        lines.append("=" * 60)

        self._log_text.setText("\n".join(lines))


class AboutPage(QWidget):
    """作者信息页面"""

    def __init__(self, ctx: dict):
        super().__init__()
        self._ctx = ctx
        self._click_count = 0
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        title = QLabel("作者信息")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        layout.addSpacing(20)

        # 卡片容器
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(28, 24, 28, 24)

        # 标题 - 可点击（彩蛋：点击7次弹出日志）
        self._app_title = QLabel(f"{APP_DISPLAY_NAME} {APP_VERSION}")
        self._app_title.setObjectName("aboutAppTitle")
        self._app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._app_title.setCursor(Qt.CursorShape.PointingHandCursor)
        self._app_title.mousePressEvent = self._on_title_click
        card_layout.addWidget(self._app_title)
        card_layout.addSpacing(16)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("aboutDivider")
        card_layout.addWidget(sep)
        card_layout.addSpacing(8)

        # 信息行
        info_items = [
            ("作者", "𝒞ℯ𝓃𝓉."),
            ("QQ", "3848043045"),
            ("日期", f"2026-08-16  {APP_VERSION}"),
        ]

        for label_text, value in info_items:
            row = QLabel(f"{label_text}：{value}")
            row.setObjectName("aboutInfoRow")
            row.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(row)

        card_layout.addSpacing(12)

        # 免责声明
        warning = QLabel(
            "此软件免费开源，无任何收费通道。\n"
            "如您是付费购买此软件，恭喜您，您被骗了。"
        )
        warning.setObjectName("aboutWarning")
        warning.setProperty("state", "warning")
        warning.style().unpolish(warning)
        warning.style().polish(warning)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning.setWordWrap(True)
        card_layout.addWidget(warning)
        card_layout.addSpacing(8)

        # 更新链接
        self._update_link = "https://cent.lanzoub.com/b016l00b5g"
        self._update_pwd = "cent"
        update_info = QLabel(
            f"更新链接：{self._update_link}\n"
            f"密码：{self._update_pwd}"
        )
        update_info.setObjectName("aboutUpdateInfo")
        update_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        update_info.setCursor(Qt.CursorShape.PointingHandCursor)
        update_info.setToolTip("点击复制更新链接")
        update_info.mousePressEvent = self._on_update_link_click
        card_layout.addWidget(update_info)

        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()

    def _on_title_click(self, event):
        """标题点击事件 - 7次点击后弹出日志"""
        self._click_count += 1
        remaining = 7 - self._click_count
        if remaining > 0:
            self._app_title.setToolTip(f"再点击 {remaining} 次...")
        else:
            self._click_count = 0
            self._app_title.setToolTip("")
            self._show_log_dialog()

    def _show_log_dialog(self):
        """显示日志弹窗"""
        dlg = LogDialog(self)
        dlg.exec()

    def _on_update_link_click(self, event):
        """点击更新链接 - 弹出复制弹窗"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_update_dialog()

    def _show_update_dialog(self):
        """弹出更新链接复制弹窗"""
        dlg = QDialog(self)
        dlg.setWindowTitle("获取更新")
        dlg.setMinimumWidth(420)
        dlg.setObjectName("dialog")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("更新链接")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # 链接
        link_label = QLabel(self._update_link)
        link_label.setObjectName("aboutUpdateLink")
        link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        link_label.setWordWrap(True)
        layout.addWidget(link_label)

        # 密码
        pwd_row = QHBoxLayout()
        pwd_label = QLabel(f"提取码：{self._update_pwd}")
        pwd_label.setObjectName("aboutUpdateInfo")
        pwd_row.addWidget(pwd_label)
        pwd_row.addStretch()
        layout.addLayout(pwd_row)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        copy_btn = QPushButton("复制链接")
        copy_btn.setObjectName("accentBtn")
        copy_btn.clicked.connect(lambda: self._copy_text(self._update_link))
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dlg.close)
        close_btn.setObjectName("dialogCloseBtn")
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)
        dlg.exec()

    def _copy_text(self, text: str):
        """复制文本到剪贴板"""
        QGuiApplication.clipboard().setText(text)
        show_toast(self, "更新链接已复制到剪贴板！", "success")