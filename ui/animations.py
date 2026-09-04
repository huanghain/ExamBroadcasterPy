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
    QVariant, QEasingCurve, QPropertyAnimation, Qt,
)
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect, QApplication


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
#  页面切换：整页淡入（新页真实渲染，绝无黑色背景）
# ─────────────────────────────────────────────────────
def switch_page(
    stack: QWidget,
    new_widget: QWidget,
    duration: int = 200,
) -> None:
    """页面切换：新页以整页透明度做淡入，不做抓图、不叠加遮罩。

    为什么抓图遮罩有约 0.8s 黑背景（实测定位结论）：
      此前方案 setCurrentWidget 切到新页后立即撤掉旧遮罩，而新页"首帧"
      尚未真正渲染进屏幕后备缓冲（grab() 只是离屏渲染，不能把新页置为
      屏幕就绪）。从撤遮罩到新页首帧落屏之间是段"未渲染窗口"，Windows
      合成层把它显示为黑色，窗口时长≈新页首次屏幕绘制耗时，复杂页面
      （设置页 40+ 控件）可达约 0.8s。

    本方案从机制上消灭该窗口：
      1) setCurrentWidget 让新页真正成为当前页并真实渲染，首帧即正确；
      2) 给新页挂 QGraphicsOpacityEffect，opacity 0→1 淡入；
         0 透明度时透出的下方内容不是"未渲染区"，而是 QStackedWidget
         的实心主题底色（见 main_window._apply_page_container_bg），非黑，
         故起始帧也绝对没有黑色背景；
      3) 淡入结束移除 effect，恢复新页原生硬件渲染，无持续性能负担。

    快速连点 / 覆盖式切换均安全：旧页 effect 会被清除，新目标页重新淡入。
    """
    old_widget = stack.currentWidget()
    if old_widget is None:
        stack.setCurrentWidget(new_widget)
        return
    if old_widget is new_widget:
        _clear_effect(new_widget)
        return
    if new_widget.parent() is not stack:
        stack.setCurrentWidget(new_widget)
        return

    # 结束旧页可能残留的在途过渡/透明度效果
    _clear_effect(old_widget)

    # 真实切页：新页作为当前页从第一帧就在屏幕上渲染
    stack.setCurrentWidget(new_widget)

    eff = QGraphicsOpacityEffect(new_widget)
    eff.setOpacity(0.0)
    new_widget.setGraphicsEffect(eff)

    fade = QPropertyAnimation(eff, b"opacity", new_widget)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _done():
        try:
            # 结束后恢复原生渲染；widget 可能已被销毁则忽略
            _clear_effect(new_widget)
        except RuntimeError:
            pass

    fade.finished.connect(_done)
    fade.start()


def cancel_active_switch(stack: QWidget) -> None:
    """立即结束 stack 上仍在进行的页面过渡（如有）。

    供需要直接操作 setCurrentWidget 的代码（如全屏强制切页）调用：
    清掉当前页可能残留的透明度效果即可。
    """
    cur = stack.currentWidget()
    if cur is not None:
        try:
            _clear_effect(cur)
        except RuntimeError:
            pass