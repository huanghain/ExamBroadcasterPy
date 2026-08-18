"""
全局动画工具 — 平滑过渡效果

提供一组基于 QVariantAnimation / QPropertyAnimation 的轻量动画，
不影响布局计算，动画结束后自动清理 GraphicsEffect 以恢复性能。

支持的动画：
    - fade_in      : 淡入（透明度 0 → 1）
    - slide_fade_in: 上滑 + 淡入（用于弹窗、页面切换）
    - fade_out     : 淡出（透明度 1 → 0）
    - pulse        : 呼吸闪烁（透明度循环，用于持久提示）
"""
from PyQt6.QtCore import (
    QVariant, QEasingCurve, QPropertyAnimation, Qt, QRect,
)
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect, QLabel


def _clear_effect(widget: QWidget):
    """移除透明度效果，恢复硬件渲染性能"""
    widget.setGraphicsEffect(None)


def _start_fade_anim(
    widget: QWidget,
    start_opacity: float,
    end_opacity: float,
    duration: int,
    easing: QEasingCurve.Type,
    loop: int = 1,
    on_complete=None,
) -> QPropertyAnimation:
    """统一驱动一个透明度动画。

    先清除控件上已有的动画效果，再挂载新效果，避免快速切换时残留。
    动画正常结束后自动清理 effect，并触发 on_complete 钩子。
    """
    # 若有旧动画/效果，先彻底清理，避免重复挂载导致资源泄漏
    _clear_effect(widget)

    eff = QGraphicsOpacityEffect(widget)
    eff.setOpacity(start_opacity)
    widget.setGraphicsEffect(eff)

    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start_opacity)
    anim.setEndValue(end_opacity)
    anim.setEasingCurve(easing)
    anim.setLoopCount(loop)

    def _cleanup():
        # 仅在动画已停止（自然结束或被外部 stop 且 Driver 确认）时清理
        if anim.state() == QPropertyAnimation.State.Stopped:
            _clear_effect(widget)
            if on_complete:
                on_complete()

    anim.stateChanged.connect(_cleanup)
    anim.start()
    return anim


# ─────────────────────────────────────────────────────
#  淡入
# ─────────────────────────────────────────────────────
def fade_in(
    widget: QWidget,
    duration: int = 260,
    start_opacity: float = 0.0,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QPropertyAnimation:
    """使控件从 start_opacity 淡入到 1.0。"""
    return _start_fade_anim(
        widget, start_opacity, 1.0, duration, easing,
    )


# ─────────────────────────────────────────────────────
#  上滑 + 淡入
# ─────────────────────────────────────────────────────
def slide_fade_in(
    widget: QWidget,
    duration: int = 280,
    slide_offset: int = 24,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QPropertyAnimation:
    """控件从下方 slide_offset 像素处上滑并淡入到位。"""
    _clear_effect(widget)
    eff = QGraphicsOpacityEffect(widget)
    eff.setOpacity(0.0)
    widget.setGraphicsEffect(eff)

    start_pos = widget.pos()
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)

    def _update_pos(v: QVariant):
        p = start_pos
        p.setY(int(p.y() - (1.0 - v) * slide_offset))
        if widget.parentWidget():
            widget.move(p)

    anim.valueChanged.connect(_update_pos)

    def _cleanup():
        if anim.state() == QPropertyAnimation.State.Stopped:
            _clear_effect(widget)

    anim.finished.connect(_cleanup)
    anim.start()
    return anim


# ─────────────────────────────────────────────────────
#  淡出（可选，供确认类弹窗关闭时使用）
# ─────────────────────────────────────────────────────
def fade_out(
    widget: QWidget,
    duration: int = 180,
    on_finished=None,
) -> QPropertyAnimation:
    """控件淡出到 0 透明。动画结束后触发 on_finished 钩子。"""
    return _start_fade_anim(
        widget, 1.0, 0.0, duration, QEasingCurve.Type.InCubic,
        on_complete=on_finished,
    )


# ─────────────────────────────────────────────────────
#  呼吸闪烁（用于“正在生成语音”等持久状态提示）
# ─────────────────────────────────────────────────────
def pulse(
    widget: QWidget,
    duration: int = 900,
    min_opacity: float = 0.35,
) -> QPropertyAnimation:
    """让控件透明度在 min_opacity↔1.0 之间循环，形成呼吸效果。"""
    _clear_effect(widget)
    eff = QGraphicsOpacityEffect(widget)
    eff.setOpacity(1.0)
    widget.setGraphicsEffect(eff)

    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(1.0)
    anim.setEndValue(min_opacity)
    anim.setEasingCurve(QEasingCurve.Type.InOutSine)
    anim.setLoopCount(-1)  # 无限循环

    def _cleanup():
        if anim.state() == QPropertyAnimation.State.Stopped:
            _clear_effect(widget)

    anim.stateChanged.connect(_cleanup)
    anim.start()
    return anim


# ─────────────────────────────────────────────────────
#  页面切换：快照消隐法（优化设置页等复杂页面的切换性能）
# ─────────────────────────────────────────────────────
def switch_page(
    stack: QWidget,
    new_widget: QWidget,
    duration: int = 210,
    slide_offset: int = 26,
) -> None:
    """轻量级页面切换过渡。

    根因与方案：
      在设置页、含 QTableView 的今日页等复杂整页上直接挂载 QGraphicsOpacityEffect，
      会强制整页软件渲染、逐帧重建离屏缓冲并合成，既拖慢切换，又导致
      QTableView 表头在逐帧重绘时残留/撕裂。
      本方案改为：切换后仅对"旧页快照"(单个 QPixmap)做淡出 + 轻微上移，
      透明度效果只作用于一个小而轻的像素图标签，渲染代价近乎常数。
      复杂页面始终以原生路径渲染，不触碰离屏缓冲，因而既不卡顿也不残留表头。

    旧页快照只在切换瞬间抓取一次，动画结束后自动回收。
    """
    old_widget = stack.currentWidget()
    if old_widget is None or old_widget is new_widget:
        return

    # 1) 先抓取旧页快照（此时旧页仍是当前页，可保证快照内容完整）
    snapshot = old_widget.grab()

    # 2) 切到新页 —— 新页是唯一真实渲染的页面（硬件友好、无软件缓冲）
    stack.setCurrentWidget(new_widget)

    # 3) 将快照作为过渡层盖在新页上方
    overlay = QLabel(stack)
    overlay.setPixmap(snapshot)
    overlay.setGeometry(stack.rect())
    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    overlay.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
    overlay.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    overlay.show()
    overlay.raise_()

    # 4) 对快照层做"淡出 + 轻微上移"，露出下方已渲染好的新页
    eff = QGraphicsOpacityEffect(overlay)
    overlay.setGraphicsEffect(eff)

    fade = QPropertyAnimation(eff, b"opacity", overlay)
    fade.setDuration(duration)
    fade.setStartValue(1.0)
    fade.setEndValue(0.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    start_rect = QRect(stack.rect())
    slide = QPropertyAnimation(overlay, b"geometry", overlay)
    slide.setDuration(duration)
    slide.setStartValue(start_rect)
    slide.setEndValue(start_rect.translated(0, -slide_offset))
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)

    fade.finished.connect(overlay.close)
    fade.start()
    slide.start()