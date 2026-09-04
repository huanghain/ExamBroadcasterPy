"""主窗口 - 无边框全屏 + 自定义标题栏"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QStatusBar,
    QLabel, QFrame, QSizePolicy, QPushButton, QSystemTrayIcon,
    QMenu, QApplication, QDialog,
)
from PyQt6.QtCore import Qt, QSize, QPoint, QEasingCurve, QPropertyAnimation, QEvent, QTimer
from PyQt6.QtGui import QFont, QAction, QIcon
import sys
from datetime import datetime

from ui.pages.today_page import TodayPage
from ui.pages.exam_page import ExamPage, BroadcastPopup
from ui.pages.settings_page import SettingsPage
from ui.pages.about_page import AboutPage
from config import APP_DISPLAY_NAME, APP_ICON_ICO_PATH
from services import audio_gate
from services.exam_window import any_exam_in_mute_window
from ui.widgets.toast import ask_confirm


class TitleBar(QFrame):
    """自定义标题栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(30)
        self._drag_pos: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 4, 0)
        layout.setSpacing(0)

        # 图标 + 标题
        icon_label = QLabel("EB")
        icon_label.setObjectName("titleBarIcon")
        layout.addWidget(icon_label)

        self._title = QLabel(APP_DISPLAY_NAME)
        self._title.setObjectName("titleBarTitle")
        layout.addWidget(self._title)

        # 离线模式状态标签
        self._offline_tag = QLabel("")
        self._offline_tag.setObjectName("titleBarOfflineTag")
        self._offline_tag.setVisible(False)
        layout.addWidget(self._offline_tag)

        layout.addStretch()

        # 窗口控制按钮
        # 全屏广播模式开关（切换后屏蔽声音/键盘，仅保留考试提醒）
        self._fs_btn = QPushButton("全屏模式")
        self._fs_btn.setObjectName("titleBarFullscreenBtn")
        self._fs_btn.setToolTip("进入全屏广播模式：屏蔽除考试提醒外的所有声音与键盘输入")
        self._fs_btn.clicked.connect(self._on_fullscreen_toggle)
        layout.addWidget(self._fs_btn)

        # 退出软件（真正退出，不最小化到托盘）
        self._quit_btn = QPushButton("退出")
        self._quit_btn.setObjectName("titleBarQuitBtn")
        self._quit_btn.setToolTip("退出软件")
        self._quit_btn.clicked.connect(self._on_quit)
        layout.addWidget(self._quit_btn)

        self._min_btn = QPushButton("─")
        self._min_btn.setObjectName("titleBarMinBtn")
        self._min_btn.clicked.connect(self._on_minimize)
        layout.addWidget(self._min_btn)

        self._close_btn = QPushButton("X")
        self._close_btn.setObjectName("titleBarCloseBtn")
        self._close_btn.clicked.connect(self._on_close)
        layout.addWidget(self._close_btn)

    def _on_fullscreen_toggle(self):
        window = self.window()
        if hasattr(window, "_toggle_fullscreen"):
            window._toggle_fullscreen()

    def _on_minimize(self):
        window = self.window()
        if hasattr(window, "request_minimize"):
            window.request_minimize()
        else:
            window.showMinimized()

    def _on_close(self):
        window = self.window()
        if hasattr(window, "request_close"):
            window.request_close()
        else:
            window.close()

    def _on_quit(self):
        """退出软件 - 真正退出"""
        window = self.window()
        if hasattr(window, "request_quit"):
            window.request_quit()
        elif hasattr(window, "_quit_app"):
            window._quit_app()
        else:
            QApplication.quit()

    def set_offline_mode(self, enabled: bool):
        """设置离线模式状态标签"""
        self._offline_tag.setVisible(enabled)
        if enabled:
            self._offline_tag.setText("离线")
            self._offline_tag.setProperty("state", "offline")
        else:
            self._offline_tag.setVisible(False)
        self._offline_tag.style().unpolish(self._offline_tag)
        self._offline_tag.style().polish(self._offline_tag)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


class _SilentTip(QLabel):
    """全屏模式无声提示层：置顶、无边框、无声音，显示后自动隐藏。

    仅用于全屏模式下的提示（键盘屏蔽提示、进入/退出提示等），
    不触发任何系统提示音。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # 独立顶层 Tool 窗口，避免吸附局内影响布局；置顶显示
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setObjectName("fullscreenTip")
        # 显示时不抢焦点，避免打断鼠标操作
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_message(self, text: str, ms: int = 2500):
        self.setText(text)
        self.adjustSize()
        # 限制最大宽度，过长的消息自动换行
        width = min(self.sizeHint().width(), 520)
        self.setFixedWidth(width)
        self.adjustSize()
        # 居中显示在可用屏区
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(sg.center().x() - self.width() // 2,
                      sg.center().y() - self.height() // 2)
        self.show()
        self.raise_()
        self._hide_timer.start(max(ms, 500))


class MainWindow(QMainWindow):
    """主窗口 — 无边框全屏"""

    NAV_ITEMS = [
        ("  ", "今日概览"),
        ("  ", "考试管理"),
    ]

    def __init__(self, app_context: dict):
        super().__init__()
        self._ctx = app_context
        self._pages: dict[str, QWidget] = {}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setFixedSize(1280, 720)

        # 无边框窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window
        )

        # 中央容器
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 自定义标题栏 ──
        self._title_bar = TitleBar(self)
        root.addWidget(self._title_bar)

        # ── 主体区域 ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # ---- 左侧导航 ----
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_frame.setFixedWidth(200)
        self._nav_frame = nav_frame  # 供全屏模式隐藏/恢复（沉浸式 F11 效果）
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 10, 0, 6)

        # 导航列表
        self._nav_list = QListWidget()
        self._nav_list.setObjectName("navList")
        self._nav_list.setIconSize(QSize(16, 16))
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        # 导航项较短，无需横向滚动；显式关闭以消除横向滑动条
        self._nav_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        for icon, text in self.NAV_ITEMS:
            item = QListWidgetItem(f"  {icon}  {text}")
            item.setSizeHint(QSize(182, 34))
            self._nav_list.addItem(item)

        nav_layout.addWidget(self._nav_list)

        # ── 侧边栏选中高亮滑块 ──
        # 以"背景滑块"呈现选中态：滑块作为列表底层 child widget，
        # 通过几何动画在导航项间平滑滑动；viewport 在其上，故文字始终清晰；
        # ::item:selected 背景置为透明，由滑块承载高亮，避免瞬间跳变。
        self._nav_highlight = QFrame(self._nav_list)
        self._nav_highlight.setObjectName("navHighlight")
        self._nav_highlight.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._nav_highlight.resize(0, 0)
        self._nav_highlight.show()
        # 让列表内容(viewport)叠在滑块之上，文字/图标在最上层可读
        self._nav_list.viewport().raise_()
        self._nav_anim: QPropertyAnimation | None = None
        # 高亮滑块跟随真实选中行（含离线拦截回退到第 0 项的情况）
        self._nav_list.currentRowChanged.connect(self._animate_nav_highlight)

        # 底部设置
        nav_layout.addStretch()
        sep = QFrame()
        sep.setObjectName("divider")
        nav_layout.addWidget(sep)

        settings_item = QListWidgetItem("    设置")
        settings_item.setSizeHint(QSize(182, 34))
        self._nav_list.addItem(settings_item)
        self._settings_nav_item = settings_item

        about_item = QListWidgetItem("    关于")
        about_item.setSizeHint(QSize(182, 34))
        self._nav_list.addItem(about_item)
        self._about_nav_item = about_item

        body.addWidget(nav_frame)

        # ---- 右侧内容区 ----
        self._stack = QStackedWidget()
        self._stack.setObjectName("pageContainer")
        # 给内容容器一块"真实实心底色"，使整页淡入在 0 透明度起始帧透出的
        # 都是渲染好的主题底色（浅 #F4F6F9 / 深 #1E1E2E），而非系统默认的
        # 未初始化黑色。用调色板(QPalette)+自动填充而非样式表，是因为
        # QStackedWidget 不绘制样式表 background-color（需 WA_StyledBackground），
        # 而 palette 的 Window 角色对 QFrame/QWidget 天然生效、跨平台可靠。
        self._stack.setAutoFillBackground(True)
        # 从持久化设置读取深色模式（ctx 不一定携带），保证容器底色与主题一致
        _dark = False
        try:
            import json as _json
            import config as _cfg
            if getattr(_cfg, "SETTINGS_PATH", None) and _cfg.SETTINGS_PATH.exists():
                _dark = bool(_json.loads(
                    _cfg.SETTINGS_PATH.read_text(encoding="utf-8")
                ).get("dark_mode", False))
        except Exception:
            pass
        self._apply_page_container_bg(_dark)

        # 创建页面（懒加载）：默认只实例化"今日"首页，其余页面在首次访问时
        # 按需创建（见 _get_page），可显著降低启动时间与常驻内存占用。
        self._page_factory = {
            "today": TodayPage,
            "exam": ExamPage,
            "settings": SettingsPage,
            "about": AboutPage,
        }
        self._pages["today"] = TodayPage(self._ctx)
        for page in self._pages.values():
            self._stack.addWidget(page)

        body.addWidget(self._stack, 1)
        root.addLayout(body, 1)

        # ── 状态栏 ──
        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("statusBar")
        self._status_label = QLabel("就绪")
        self._status_label.setObjectName("statusLabel")
        self._status_bar.addWidget(self._status_label)
        root.addWidget(self._status_bar)

        # 默认选中第一项
        self._nav_list.setCurrentRow(0)

        # 连接提醒信号
        scheduler = self._ctx.get("scheduler")
        if scheduler:
            scheduler.reminder_triggered.connect(self._on_reminder_triggered)

        # 创建播报弹窗
        self._broadcast_popup = BroadcastPopup(self)

        # 连接 TTS 完成信号 → 自动关闭弹窗
        tts = self._ctx.get("tts_service")
        if tts:
            tts.finished.connect(self._broadcast_popup.close_popup)
            tts.error.connect(self._broadcast_popup.close_popup)

        # 初始化系统托盘
        self._init_tray_icon()

        # 初始化离线模式 UI 状态
        self._on_offline_mode_changed(self._ctx.get("offline_mode", False))

        # ── 全屏广播模式状态 ──
        self._fullscreen_active = False
        self._last_key_warn_at = 0.0
        # 无声提示层（键盘屏蔽提示/退出警告，均不发声）
        self._tip = _SilentTip(self)
        # 全局键盘过滤：全屏模式下屏蔽键盘输入
        QApplication.instance().installEventFilter(self)

        # ── 考试时段自动弹窗静音（考前30分钟~考后5分钟）──
        self._popup_mute_active = False
        self._popup_mute_enabled = self._ctx.get("popup_mute_enabled", True)
        self._mute_timer = QTimer(self)
        self._mute_timer.setInterval(15000)  # 15s 轮询，及时捕捉窗口边界
        self._mute_timer.timeout.connect(self._on_mute_check)
        self._mute_timer.start()
        # 启动后短暂延迟执行首次检测，避免阻塞界面构建
        QTimer.singleShot(500, self._on_mute_check)
        # 空闲预加载设置页：把首开设置页的整页同步构建耗时移出"点击-切换"热路径。
        # 首次点开设置时页面早已构建完毕，切页快照动画照常播放且全程不卡顿，
        # 实现真正的"无感加载"；仍保持"今日页优先渲染、其余按需创建"的轻启动。
        QTimer.singleShot(1200, self._preload_pages)

    # ── 考试时段自动弹窗静音 ──────────────────────────

    def _on_mute_check(self):
        """周期检测考试静音窗口，自动化开关弹窗静音。

        "要求同全屏模式"：窗口内屏蔽除考试提醒外的所有弹窗声音；
        考试提醒走 force 分支不受影响，仍正常播报。
        """
        # 功能关闭时确保静音复位
        if not self._popup_mute_enabled:
            if self._popup_mute_active:
                self._popup_mute_active = False
                audio_gate.set_popup_mute(False)
            return

        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            exams = self._ctx["exam_service"].get_by_date(today_str)
            in_window = any_exam_in_mute_window(exams)
        except Exception:
            in_window = False

        if in_window and not self._popup_mute_active:
            self._popup_mute_active = True
            audio_gate.set_popup_mute(True)
            # 全屏模式本就已抑制声音，避免覆盖全屏状态栏文案
            if not self._fullscreen_active:
                self._status_label.setText("考试静音时段 · 弹窗静音（除考试提醒外）")
                self._show_tip("已进入考试静音时段，弹窗将静音（考试提醒仍正常播报）。", 2500)
        elif not in_window and self._popup_mute_active:
            self._popup_mute_active = False
            audio_gate.set_popup_mute(False)
            if not self._fullscreen_active:
                self._status_label.setText("已退出考试静音时段，声音已恢复")
                self._show_tip("考试静音时段已结束，声音已恢复。", 2000)

    def _on_popup_mute_setting_changed(self):
        """设置页开关变化后立即应用（读取最新 ctx 值）"""
        self._popup_mute_enabled = self._ctx.get("popup_mute_enabled", True)
        self._on_mute_check()

    # ── 全屏广播模式 ──────────────────────────────────

    def _toggle_fullscreen(self):
        """标题栏"全屏模式"按钮：进入/退出全屏广播模式"""
        if self._fullscreen_active:
            if self._confirm_exit_fullscreen():
                self._exit_fullscreen()
            else:
                self._show_tip("已取消退出全屏模式，继续保障考试播报。", 2200)
        else:
            self._enter_fullscreen()

    def _set_keep_awake(self, enabled: bool):
        """全屏广播期间阻止系统自动睡眠/熄屏，保持屏幕常亮（Windows）。

        使用 Windows API SetThreadExecutionState：
          - ES_CONTINUOUS(0x80000000) 持续生效直到下次调用清除
          - ES_SYSTEM_REQUIRED(0x1)    阻止系统自动睡眠
          - ES_DISPLAY_REQUIRED(0x2)   阻止显示器自动熄灭
        macOS/Linux 无统一进程级保持唤醒 API，此处保持 no-op（返回）。
        """
        if sys.platform != "win32":
            return
        try:
            import ctypes
            # 始终携带 ES_CONTINUOUS，避免标志随线程/调用失效
            flags = 0x80000000 | (0x00000001 | 0x00000002 if enabled else 0)
            ctypes.windll.kernel32.SetThreadExecutionState(flags)
        except Exception:
            # 权限/平台不支持时静默忽略，不影响主流程
            pass

    def _enter_fullscreen(self):
        """进入全屏广播模式：放大至全屏 + 屏蔽非考试提醒声音 + 屏蔽键盘

        全屏呈现做沉浸式增强（类似 F11）：
          - 隐藏左侧导航栏，让含考试信息的今日概览铺满整个屏幕
          - 强制窗口置顶（WindowStaysOnTopHint），避免被其他窗口遮挡
          - showFullScreen() 在真实桌面上还会自动隐藏系统任务栏
        """
        self._fullscreen_active = True
        self._ctx["fullscreen_mode"] = True
        audio_gate.set_fullscreen(True)
        self._title_bar._fs_btn.setText("退出全屏")
        # 全屏广播期间阻止系统自动睡眠/熄屏，保持亮屏持续播报
        self._set_keep_awake(True)
        # 置顶需要在 show 前应用 flag；设置后再补齐全屏态
        self._nav_frame.hide()
        # 全屏广播始终以“今日概览”为呈现页：无论进入前停留在哪个页面，
        # 都自动切回今日页（今日页为全屏下的基础广播画面）。
        # 先终止在途页面过渡，防止其收尾时把页面又切回目标页。
        from ui.animations import cancel_active_switch
        cancel_active_switch(self._stack)
        self._stack.setCurrentWidget(self._get_page("today"))
        self._nav_list.blockSignals(True)
        self._nav_list.setCurrentRow(0)
        self._nav_list.blockSignals(False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.show()
        if not self.isFullScreen():
            self.showFullScreen()
        self._status_label.setText("全屏广播模式 · 键盘已屏蔽 · 仅考试提醒可发声")
        self._show_tip("已进入全屏广播模式，除考试提醒外所有声音已屏蔽。", 2500)

    def _exit_fullscreen(self):
        """退出全屏广播模式，恢复声音、键盘、导航栏与正常窗口状态"""
        self._fullscreen_active = False
        self._ctx["fullscreen_mode"] = False
        audio_gate.set_fullscreen(False)
        self._title_bar._fs_btn.setText("全屏模式")
        # 退出全屏后恢复系统原生的睡眠/熄屏策略
        self._set_keep_awake(False)
        self._nav_frame.show()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.show()
        self.showNormal()
        self._status_label.setText("已退出全屏模式，声音与键盘已恢复")
        self._tip.hide()

    def request_minimize(self):
        """最小化请求（全屏模式下拦截，防止影响考试播报）"""
        if self._fullscreen_active:
            self._show_tip("全屏模式禁止最小化窗口，以免影响考试播报。", 2200)
            return
        self.showMinimized()

    def request_close(self):
        """关闭请求（全屏模式下转为退出全屏确认）"""
        if self._fullscreen_active:
            self._request_exit_fullscreen()
            return
        self.close()

    def request_quit(self):
        """退出请求（全屏下先确认退出全屏；非全屏也统一二次确认后退出）"""
        if self._fullscreen_active:
            self._request_exit_fullscreen()
            return
        self._confirm_and_quit()

    def _request_exit_fullscreen(self):
        """非按钮途径触发的退出全屏（关闭/最小化/退出），先弹无声确认"""
        if self._confirm_exit_fullscreen():
            self._exit_fullscreen()

    def _confirm_exit_fullscreen(self) -> bool:
        """无声退出警告：确认是否退出全屏模式。返回 True 表示确认退出。"""
        dlg = QDialog(self)
        dlg.setObjectName("fullscreenConfirmDlg")
        dlg.setWindowTitle("退出全屏模式")
        dlg.setModal(True)
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)
        msg = QLabel("为了保障考试播报安全，请不要随意关闭软件。\n确定要退出全屏模式吗？")
        msg.setObjectName("fullscreenConfirmMsg")
        msg.setWordWrap(True)
        lay.addWidget(msg)
        hint = QLabel("考试提醒仍会自动播报，不受全屏模式影响。")
        hint.setObjectName("fullscreenConfirmHint")
        lay.addWidget(hint)
        btns = QHBoxLayout()
        lay.addLayout(btns)
        yes = QPushButton("确定")
        yes.setObjectName("primaryBtn")
        no = QPushButton("取消")
        no.setObjectName("cancelBtn")
        yes.setMinimumWidth(88)
        no.setMinimumWidth(88)
        yes.clicked.connect(dlg.accept)
        no.clicked.connect(dlg.reject)
        btns.addStretch()
        btns.addWidget(yes)
        btns.addWidget(no)
        return dlg.exec() == QDialog.DialogCode.Accepted

    def _show_tip(self, text: str, ms: int = 2500):
        """显示无声提示层（居中置顶，自动隐藏）"""
        self._tip.show_message(text, ms)

    def eventFilter(self, obj, event):
        """全局事件过滤：全屏模式下屏蔽键盘输入"""
        if self._fullscreen_active and event is not None:
            et = event.type()
            if et in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease,
                      QEvent.Type.ShortcutOverride):
                # 弹有模态对话框(如退出确认)时放行键盘，便于按钮操作
                modal = QApplication.activeModalWidget()
                if modal is not None:
                    return super().eventFilter(obj, event)
                # 其余一律屏蔽键盘，检测到输入时给无声提示
                if et == QEvent.Type.KeyPress:
                    self._warn_keyboard_blocked()
                return True  # 吞掉键盘事件
        return super().eventFilter(obj, event)

    def _warn_keyboard_blocked(self):
        """键盘被屏蔽时给无声提示（节流，避免刷屏）"""
        from time import monotonic
        now = monotonic()
        if now - self._last_key_warn_at > 3.0:
            self._last_key_warn_at = now
            self._show_tip("全屏模式已屏蔽键盘输入，请使用鼠标操作。", 2000)

    def showEvent(self, event):
        """窗口显示 - 布局就绪后校正高亮滑块初始位置"""
        super().showEvent(event)
        self._animate_nav_highlight(self._nav_list.currentRow(), instant=True)

    def _animate_nav_highlight(self, row: int, instant: bool = False):
        """驱动侧边栏高亮滑块在导航项间平滑滑动。

        用几何(pos)动画移动背景滑块，QWidget 几何动画走原生路径，
        不触发整页软件渲染，因而流畅且不影响列表/页面性能。
        快速连续切换时先停止旧动画再起新动画，避免抖跳。
        """
        if row < 0:
            return
        item = self._nav_list.item(row)
        if item is None:
            return

        rect = self._nav_list.visualItemRect(item)          # viewport 坐标
        org = self._nav_list.viewport().mapTo(self._nav_list, rect.topLeft())

        inset = 4
        target_x = org.x() + inset
        target_w = max(self._nav_list.width() - inset * 2, 8)
        target_y = org.y() + inset
        target_h = max(rect.height() - inset * 2, 8)

        # 首次或尺寸变化：直接定形到位
        if self._nav_highlight.width() != target_w or self._nav_highlight.height() != target_h:
            self._nav_highlight.setGeometry(target_x, target_y, target_w, target_h)

        if instant:
            self._nav_highlight.move(target_x, target_y)
            return

        start_pos = self._nav_highlight.pos()
        if self._nav_anim is not None:
            self._nav_anim.stop()
            self._nav_anim = None

        anim = QPropertyAnimation(self._nav_highlight, b"pos", self._nav_highlight)
        anim.setDuration(200)
        anim.setStartValue(QPoint(target_x, start_pos.y()))
        anim.setEndValue(QPoint(target_x, target_y))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._nav_anim = anim
        anim.start()

    def _get_page(self, key: str):
        """按需创建页面（懒加载）：首次访问时实例化并加入栈，已创建则直接返回。

        不缩减任何功能，仅推迟非必要页面的构建时机，降低启动时间与常驻内存。
        """
        page = self._pages.get(key)
        if page is None:
            page = self._page_factory[key](self._ctx)
            self._pages[key] = page
            self._stack.addWidget(page)
        return page

    def _apply_page_container_bg(self, dark: bool):
        """同步设置内容容器(#pageContainer)的实心底色。

        供启动初始化和深色模式切换时调用，保证整页淡入在 0 透明度
        起始帧透出的是渲染好的主题底色而非黑色。
        """
        from PyQt6.QtGui import QColor, QPalette
        color = QColor("#1E1E2E" if dark else "#F4F6F9")
        pal = self._stack.palette()
        pal.setColor(QPalette.ColorRole.Window, color)
        pal.setColor(QPalette.ColorRole.Base, color)
        self._stack.setPalette(pal)

    def _preload_pages(self):
        """空闲时预构建设置页，避免首次访问时的同步卡顿。

        设置页包含 5 个分组、约 50 个控件且需解密读取 API Key、
        扫描离线语音目录，整页构建耗时最长。因其视觉复杂度最高、被访问
        频率也高，故在启动空闲期提前构建；仅当存在设置页且非离线模式下执行。
        其余页面仍保持按需懒加载，兼顾启动速度与内存占用。
        """
        if self._ctx.get("offline_mode", False):
            return
        if "settings" not in self._pages:
            self._get_page("settings")

    def _on_nav_changed(self, index: int):
        page_keys = ["today", "exam", "settings", "about"]
        if 0 <= index < len(page_keys):
            key = page_keys[index]

            # 离线模式下阻止进入设置页
            if self._ctx.get("offline_mode", False) and key == "settings":
                self._nav_list.setCurrentRow(0)
                return

            # 更换页面：掩护式交叉淡入（见 ui.animations.switch_page）。
            # 顺序：先 refresh 再过渡 —— 新页在旧页仍显示时完成数据刷新，
            # 过渡快照即为最终内容；动画结束后掩护切页，无黑帧/纯色帧。
            from ui.animations import switch_page
            page = self._get_page(key)
            if hasattr(page, "refresh"):
                page.refresh()
            switch_page(self._stack, page)

    def _on_reminder_triggered(self, exam_id: int, reminder_text: str,
                               reminder_type: str = "", minutes_before: int = 0):
        self._status_label.setText(reminder_text)

        # 显示播报弹窗
        exam_svc = self._ctx.get("exam_service")
        if exam_svc:
            exam = exam_svc.get_by_id(exam_id)
            if exam:
                self._broadcast_popup.show_broadcast(
                    exam.subject, reminder_type, minutes_before, reminder_text
                )

        # ── 播报后立即刷新主页 ──
        # 让已触发的提醒从"即将到来提醒"表移除、倒计时即时更新，
        # 避免出现"已播报过的提醒仍显示 N 小时倒计时/23小时59分钟"的陈旧状态。
        today_page = self._pages.get("today")
        if today_page is not None:
            today_page.refresh()

    def set_status(self, message: str):
        self._status_label.setText(message)

    def _on_offline_mode_changed(self, is_offline: bool):
        """离线模式切换时更新 UI"""
        # 禁用/启用设置页并更新标签
        if is_offline:
            self._settings_nav_item.setFlags(
                self._settings_nav_item.flags() & ~Qt.ItemFlag.ItemIsEnabled
            )
            self._settings_nav_item.setText("    设置 (离线禁用)")
        else:
            self._settings_nav_item.setFlags(
                self._settings_nav_item.flags() | Qt.ItemFlag.ItemIsEnabled
            )
            self._settings_nav_item.setText("    设置")

        # 如果当前在设置页，跳回今日概览
        if is_offline and self._stack.currentWidget() == self._pages.get("settings"):
            self._nav_list.setCurrentRow(0)

        # 更新考试页的 AI 按钮状态
        exam_page = self._pages.get("exam")
        if exam_page and hasattr(exam_page, "_on_offline_mode_changed"):
            exam_page._on_offline_mode_changed(is_offline)

        # 更新标题栏状态
        self._title_bar.set_offline_mode(is_offline)

        # 更新状态栏
        if is_offline:
            self._status_label.setText("离线模式 - 使用本地录音，AI 功能已禁用")
        else:
            self._status_label.setText("在线模式")

    # ── 系统托盘 ──────────────────────────────────────

    def _init_tray_icon(self):
        """初始化系统托盘图标"""
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setToolTip(APP_DISPLAY_NAME)

        # 创建应用图标：优先加载品牌图标(app_icon.ico)并设为窗口+托盘图标。
        # QIcon 直接引用 ico 源，Qt 会依据目标位置（任务栏/托盘 16、24、32px 等）
        # 自动选用合适尺寸并缩放，从根源上避免“图标像素过大/位置偏移”。
        if APP_ICON_ICO_PATH.is_file():
            icon = QIcon(str(APP_ICON_ICO_PATH))
        else:
            # 品牌图标缺失时回退内置标准图标
            icon = QIcon()
            pixmap = self.style().standardIcon(
                self.style().StandardPixmap.SP_ComputerIcon
            ).pixmap(32, 32)
            icon.addPixmap(pixmap)
        self.setWindowIcon(icon)
        self._tray_icon.setIcon(icon)

        # 托盘菜单
        tray_menu = QMenu()

        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self._show_from_tray)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._confirm_and_quit)

        self._tray_icon.setContextMenu(tray_menu)

        # 双击托盘图标显示主窗口
        self._tray_icon.activated.connect(self._on_tray_activated)

        self._tray_icon.show()

    def _on_tray_activated(self, reason):
        """托盘图标点击事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        """从托盘恢复显示主窗口"""
        # 全屏广播模式下禁止通过托盘还原来退出全屏态（防止绕过确认）
        if self._fullscreen_active:
            self._show_tip("全屏广播模式下禁止切换窗口，以免影响考试播报。", 2200)
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _confirm_and_quit(self):
        """统一退出入口：全屏下先确认退出全屏；非全屏下二次确认后才真正退出。

        所有“退出应用”的直接入口（标题栏退出、托盘退出）均收敛到此接口，
        避免误触直接退出，也保证全屏广播模式的锁定不被绕过。
        """
        # 全屏广播模式下，不允许直接退出，先走退出全屏的确认流程
        if self._fullscreen_active:
            self._request_exit_fullscreen()
            return
        # 非全屏：统一二次确认（无系统音的自绘弹窗），防误触
        if not ask_confirm(
            self, APP_DISPLAY_NAME,
            "确定要退出考试广播系统吗？退出后将不再播报任何考试提醒。",
            yes_text="退出",
            no_text="取消",
        ):
            return
        self._quit_app()

    def _quit_app(self):
        """彻底退出应用（供标题栏“退出”等非托盘入口复用）"""
        # 全屏广播模式下，不允许直接退出
        if self._fullscreen_active:
            self._request_exit_fullscreen()
            return
        self._tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """关闭窗口时最小化到托盘而非退出"""
        # 全屏广播模式下，任何窗口关闭请求(Alt+F4 / 系统 WM_CLOSE / 任务栏关闭)
        # 都必须先走退出全屏的确认流程，不允许直接隐藏或绕过确认。
        if self._fullscreen_active:
            event.ignore()
            self._request_exit_fullscreen()
            return
        if self._tray_icon and self._tray_icon.isVisible():
            event.ignore()
            self.hide()
            self._tray_icon.showMessage(
                APP_DISPLAY_NAME,
                "程序已最小化到系统托盘，将继续为您播报提醒。",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            event.accept()