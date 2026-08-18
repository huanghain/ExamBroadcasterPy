"""主窗口 - 无边框全屏 + 自定义标题栏"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QStatusBar,
    QLabel, QFrame, QSizePolicy, QPushButton, QSystemTrayIcon,
    QMenu, QApplication,
)
from PyQt6.QtCore import Qt, QSize, QPoint, QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QFont, QAction, QIcon

from ui.pages.today_page import TodayPage
from ui.pages.exam_page import ExamPage, BroadcastPopup
from ui.pages.settings_page import SettingsPage
from ui.pages.about_page import AboutPage
from config import APP_DISPLAY_NAME


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

    def _on_minimize(self):
        self.window().showMinimized()

    def _on_close(self):
        self.window().close()

    def _on_quit(self):
        """退出软件 - 真正退出"""
        window = self.window()
        if hasattr(window, "_quit_app"):
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

        # 创建页面
        self._pages["today"] = TodayPage(self._ctx)
        self._pages["exam"] = ExamPage(self._ctx)
        self._pages["settings"] = SettingsPage(self._ctx)
        self._pages["about"] = AboutPage(self._ctx)

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

    def _on_nav_changed(self, index: int):
        page_keys = ["today", "exam", "settings", "about"]
        if 0 <= index < len(page_keys):
            key = page_keys[index]

            # 离线模式下阻止进入设置页
            if self._ctx.get("offline_mode", False) and key == "settings":
                self._nav_list.setCurrentRow(0)
                return

            # 更换页面：采用"快照消隐"过渡，兼顾动画还原与设置页性能。
            # 根因：把 QGraphicsOpacityEffect 直接挂到复杂整页（设置页 QScrollArea、
            # 今日页 QTableView）会强制整页软件渲染并逐帧重建离屏缓冲，导致
            # 1) 设置页切换卡顿; 2) 首页表头渲染残留。
            # 方案：只有"旧页快照"做淡出+上移，新页始终原生渲染，代价近常数。
            from ui.animations import switch_page
            switch_page(self._stack, self._pages[key])

            page = self._pages[key]
            if hasattr(page, "refresh"):
                page.refresh()

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

        # 创建应用图标（使用内置图标）
        icon = QIcon()
        # 使用可用的内置图标作为托盘图标
        pixmap = self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        ).pixmap(32, 32)
        icon.addPixmap(pixmap)
        self._tray_icon.setIcon(icon)

        # 托盘菜单
        tray_menu = QMenu()

        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self._show_from_tray)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)

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
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        """彻底退出应用"""
        self._tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """关闭窗口时最小化到托盘而非退出"""
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