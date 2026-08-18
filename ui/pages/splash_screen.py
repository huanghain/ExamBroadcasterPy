"""
启动页 - Visual Studio 风格

大字中央显示应用名，左下角小字轮换状态（带省略号动画），底部细进度条。
非模态窗口，不遮挡中途弹出的其他对话框（如 API Key 配置、离线语音生成）。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer

from config import APP_VERSION, APP_DISPLAY_NAME


# ── 步骤定义（仅用于进度条计算，不再显示步骤列表） ──
STEPS = [
    {"id": "database",  "label": "初始化数据库"},
    {"id": "network",   "label": "检测网络连接"},
    {"id": "apikey",    "label": "检测 API Key"},
    {"id": "offline",   "label": "检查离线语音"},
    {"id": "done",      "label": "加载主界面"},
]

STEP_STATUS_PENDING = "pending"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_DONE = "done"
STEP_STATUS_ERROR = "error"


class SplashScreen(QWidget):
    """启动页 — Visual Studio 风格，大字中央 + 左下角状态轮换"""

    def __init__(self):
        super().__init__(None)
        self.setWindowTitle(f"{APP_DISPLAY_NAME}")
        self.setFixedSize(560, 360)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("splashScreenRoot")

        self._step_states: dict[str, str] = {}
        self._current_step_index = -1

        # 状态文字动画相关
        self._base_status_text = "正在初始化"
        self._dot_count = 0
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(500)  # 每 500ms 轮换一次省略号
        self._dot_timer.timeout.connect(self._animate_dots)

        self._init_ui()
        self._center_on_screen()

        # 初始化所有步骤为待定
        for step in STEPS:
            self._step_states[step["id"]] = STEP_STATUS_PENDING

    def _init_ui(self):
        # 主垂直布局：上部居中大字，底部状态+进度条
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 背景图层（承载启动屏背景图，铺满并随窗口拉伸）──
        self._bg_label = QLabel(self)
        self._bg_label.setObjectName("splashBg")
        self._bg_label.setScaledContents(True)
        self._load_background()

        # 深色模式遮罩层（盖住背景、位于文字之下；深浅色外观由 QSS 控制）
        # z-order：背景 < 遮罩 < 布局内文字，故表层文字清晰且不被遮罩影响
        self._bg_overlay = QLabel(self)
        self._bg_overlay.setObjectName("splashBgOverlay")
        self._bg_overlay.setGeometry(0, 0, self.width(), self.height())
        self._bg_overlay.lower()
        self._bg_label.lower()
        self._bg_overlay.raise_()
        self._bg_label.lower()

        # 窗口尺寸固定，但仍同步二层的几何，确保铺满
        self._bg_label.setGeometry(0, 0, self.width(), self.height())

        # ── 中央区域：大字标题 + 版本 ──
        center_wrapper = QVBoxLayout()
        center_wrapper.setContentsMargins(40, 0, 40, 0)
        center_wrapper.setSpacing(4)

        center_wrapper.addStretch()

        # 应用名大字
        self._title_label = QLabel(APP_DISPLAY_NAME)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setObjectName("splashTitle")
        center_wrapper.addWidget(self._title_label)

        # 版本号
        self._version_label = QLabel(APP_VERSION)
        self._version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._version_label.setObjectName("splashVersion")
        center_wrapper.addWidget(self._version_label)

        center_wrapper.addStretch()

        root.addLayout(center_wrapper, 1)

        # ── 底部区域：左下角状态文字 + 进度条 ──
        bottom = QVBoxLayout()
        bottom.setContentsMargins(28, 0, 28, 22)
        bottom.setSpacing(10)

        # 状态文字（左对齐，小字）
        self._status_text = QLabel("正在初始化...")
        self._status_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._status_text.setObjectName("splashStatus")
        bottom.addWidget(self._status_text)

        # 底部细进度条
        self._progress = QProgressBar()
        self._progress.setMinimum(0)
        self._progress.setMaximum(len(STEPS))
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(2)
        self._progress.setObjectName("splashProgress")
        bottom.addWidget(self._progress)

        root.addLayout(bottom)

    def _load_background(self):
        """加载启动屏背景图（开发/打包环境均可），失败时优雅降级为纯色 QSS。"""
        from PyQt6.QtGui import QPixmap
        from config import SPLASH_BG_PATH
        try:
            if not SPLASH_BG_PATH.is_file():
                self._bg_label.hide()
                return
            pm = QPixmap(str(SPLASH_BG_PATH))
            if pm.isNull():
                self._bg_label.hide()
            else:
                self._bg_label.setPixmap(pm)
        except Exception:
            self._bg_label.hide()

    def _center_on_screen(self):
        """居中显示"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            x = (sg.width() - self.width()) // 2
            y = (sg.height() - self.height()) // 2
            self.move(x, y)

    def showEvent(self, event):
        """显示时应用圆角遮罩，使背景图四角贴合 root 圆角边框"""
        super().showEvent(event)
        self._apply_rounded_mask()

    def _apply_rounded_mask(self):
        """用 QRegion 将窗口裁成圆角（radius 10），让铺满的背景图四角不溢出直角。"""
        from PyQt6.QtGui import QPainterPath, QRegion
        radius = 10
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    # ── 省略号轮换动画 ──────────────────────────

    def _animate_dots(self):
        """轮换省略号：. → .. → ... → . → .. → ..."""
        self._dot_count = (self._dot_count % 3) + 1  # 循环: 1, 2, 3, 1, 2, 3...
        dots = "." * self._dot_count
        self._status_text.setText(f"{self._base_status_text}{dots}")

    def _start_dot_animation(self, base_text: str):
        """启动省略号轮换动画"""
        self._base_status_text = base_text
        self._dot_count = 0
        self._status_text.setText(f"{base_text}...")
        if not self._dot_timer.isActive():
            self._dot_timer.start()

    def _stop_dot_animation(self, final_text: str):
        """停止省略号轮换动画，显示最终文字"""
        self._dot_timer.stop()
        self._status_text.setText(final_text)

    # ── 公开方法（保持与 app.py 接口兼容） ──────────

    def set_step_pending(self, step_id: str):
        """将某个步骤设为待定状态"""
        self._set_step(step_id, STEP_STATUS_PENDING)

    def set_step_running(self, step_id: str, status_text: str = ""):
        """将某个步骤设为正在执行 — 启动省略号轮换动画"""
        self._set_step(step_id, STEP_STATUS_RUNNING)
        if status_text:
            # 去掉用户传入的尾部省略号，由动画统一管理
            clean_text = status_text.rstrip(".")
            self._start_dot_animation(clean_text)

    def set_step_done(self, step_id: str, status_text: str = ""):
        """将某个步骤设为已完成 — 停止动画，显示完成文字"""
        self._set_step(step_id, STEP_STATUS_DONE)
        if status_text:
            self._stop_dot_animation(status_text)

    def set_step_error(self, step_id: str, status_text: str = ""):
        """将某个步骤设为错误 — 停止动画，显示错误文字"""
        self._set_step(step_id, STEP_STATUS_ERROR)
        if status_text:
            self._stop_dot_animation(status_text)

    def _set_step(self, step_id: str, status: str):
        self._step_states[step_id] = status
        for i, step in enumerate(STEPS):
            if step["id"] == step_id:
                self._current_step_index = i
                break
        # 更新进度条
        done_count = sum(
            1 for s in STEPS
            if self._step_states.get(s["id"]) in (STEP_STATUS_DONE, STEP_STATUS_ERROR)
        )
        self._progress.setValue(done_count)

    def set_progress_text(self, text: str):
        """设置底部状态文字（带省略号轮换动画）"""
        clean_text = text.rstrip(".")
        self._start_dot_animation(clean_text)

    def close_splash(self):
        """关闭启动页"""
        self._dot_timer.stop()
        self.close()
        self.deleteLater()
