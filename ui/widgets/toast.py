"""
无系统音的自绘轻提示 Toast 与静音确认弹窗

背景
----
QMessageBox.information/warning/critical/question 在 Windows 上会播放系统提示音，
即使软件已通过 audio_gate 屏蔽了非考试提醒声音也无法完全消除（它走系统消息提示音，
不属于应用内音频门控范围）。为满足"除考试提醒外全部静音"的需求，这里提供：
  - show_toast(anchor, text, kind) : 角落浮现的轻提示，无任何系统音，自动消失
  - ask_confirm(anchor, title, text) : 自绘静音确认弹窗（返回 True/False）

三者均为纯自绘控件，不触发任何系统提示音效。
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PyQt6.QtWidgets import QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QApplication, QGraphicsOpacityEffect

# Toast 时长 (ms)
_DURATION = 2600
# 淡入淡出时长 (ms)
_FADE_MS = 180


def _resolve_anchor(anchor: QWidget | None) -> QWidget | None:
    """将锚点解析为有效的顶层窗口；无有效的则回退到当前活动窗口。"""
    if anchor is not None:
        win = anchor.window()
        if win is not None and win.isVisible():
            return win
    active = QApplication.activeWindow()
    if active is not None and active.isVisible():
        return active
    return None


def show_toast(anchor: QWidget | None, text: str, kind: str = "info", duration: int = _DURATION):
    """显示一条无系统音的自绘 Toast。

    Args:
        anchor: 显示在其上的父窗口（可为 None，自动取活动窗口）。
        text:   提示文本。
        kind:   info / success / warning / error，决定配色与图标着色。
    """
    host = _resolve_anchor(anchor)
    toast = Toast(text, kind, host)
    toast.popup()


# ─────────────────────────────────────────────
#  Toast 组件
# ─────────────────────────────────────────────
class Toast(QFrame):
    """无边框、无激活、自动淡入淡出自动关闭的轻提示框（不发声）。"""

    _LIVE: list["Toast"] = []

    def __init__(self, text: str, kind: str = "info", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("toast")
        # 工具窗口：不抢焦点、不置导航，天然无系统提示音
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._text = text
        self._kind = kind if kind in ("info", "success", "warning", "error") else "info"

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(8)
        marker = QLabel("\u2714" if self._kind == "success" else (
            "\u26a0" if self._kind == "warning" else (
                "\u2716" if self._kind == "error" else "\u2139")
        ))
        marker.setObjectName("toastIcon")
        marker.setProperty("kind", self._kind)
        self._icon = marker
        lay.addWidget(marker)
        label = QLabel(text)
        label.setObjectName("toastText")
        label.setWordWrap(True)
        self._label = label
        lay.addWidget(label, 1)

        self.adjustSize()
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        Toast._LIVE.append(self)

    # ---------- 布局定位 ----------
    def _target_geometry(self) -> QRect:
        if self.parent() is not None and self.parent().isVisible():
            rect = self.parent().frameGeometry()
            x = rect.center().x() - self.width() // 2
            y = rect.top() + 14
            return QRect(x, y, self.width(), self.height())
        screen = QApplication.primaryScreen()
        if screen is not None:
            r = screen.availableGeometry()
            return QRect(r.center().x() - self.width() // 2, r.top() + 14, self.width(), self.height())
        return self.frameGeometry()

    def popup(self):
        """显示并自动关闭（淡入 → 停留 → 淡出）。"""
        self.adjustSize()
        self.setGeometry(self._target_geometry())
        self.show()

        self._fade = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade.setDuration(_FADE_MS)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._fade.start()

        # 停留后淡出并销毁
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._fade_out)
        self._close_timer.start(_DURATION)

        # 叠加展示：避免多个 toast 完全重叠，微抬错位
        for i, t in enumerate(Toast._LIVE):
            t.move(t.x(), t.y() + i * 4)

    def _fade_out(self):
        # 从当前不透明度淡出并销毁（无论淡入是否已结束都执行淡出动画）
        self._fade = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade.setDuration(_FADE_MS)
        self._fade.setStartValue(self._effect.opacity())
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.InQuad)
        self._fade.finished.connect(self._cleanup)
        self._fade.start()

    def _cleanup(self):
        if self in Toast._LIVE:
            Toast._LIVE.remove(self)
        self.hide()
        self.deleteLater()


# ─────────────────────────────────────────────
#  静音确认弹窗
# ─────────────────────────────────────────────
def ask_confirm(anchor: QWidget | None, title: str, message: str,
                yes_text: str = "确定", no_text: str = "取消") -> bool:
    """自绘静音确认弹窗（无系统提示音），返回是否点了确定。

    当 no_text 传 None 时则隐藏取消按钮，退化为只有"确定"的静音提示弹窗
    （用于致命/启动类错误，避免 QMessageBox.critical 的系统提示音）。
    """
    host = _resolve_anchor(anchor)
    dlg = SilentConfirmDialog(title, message, yes_text, no_text, host)
    return dlg.exec() == QDialog.DialogCode.Accepted


class SilentConfirmDialog(QDialog):
    """无系统音的自绘确认对话框。"""

    def __init__(self, title: str, message: str, yes_text: str, no_text: str,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("fullscreenConfirmDlg")  # 复用现有弹窗按钮样式
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(14)

        t = QLabel(title)
        t.setObjectName("fullscreenConfirmMsg")
        t.setWordWrap(True)
        lay.addWidget(t)

        msg = QLabel(message)
        msg.setObjectName("fullscreenConfirmHint")
        msg.setWordWrap(True)
        lay.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
        if no_text:
            no = QPushButton(no_text)
            no.setObjectName("cancelBtn")
            no.setMinimumWidth(80)
            no.clicked.connect(self.reject)
            btn_row.addWidget(no)
        yes = QPushButton(yes_text)
        yes.setObjectName("primaryBtn")
        yes.setMinimumWidth(80)
        yes.setDefault(True)
        yes.clicked.connect(self.accept)
        btn_row.addWidget(yes)
        lay.addLayout(btn_row)