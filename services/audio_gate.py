"""
全局音频抑制开关（全屏广播模式 + 考试时段自动弹窗静音）

任一来源开启时，除考试提醒(force)外的所有声音均在播放前被拦截：
  - 全屏广播模式：手动开启，屏蔽除考试提醒外的所有声音并屏蔽键盘；
  - 考试时段静音：按时间自动开启，考前 EXAM_WINDOW_START_BEFORE 分钟至
    考后 EXAM_WINDOW_END_AFTER 分钟内对弹窗静音。

考试提醒/广播走 TTSService 的 force 分支，不受任何来源抑制影响，
从而保证考试播报永不中断。
"""
_FULLSCREEN = False   # 全屏广播模式抑制
_POPUP_MUTE = False   # 考试时段自动弹窗静音


def set_fullscreen(suppressed: bool) -> None:
    """设置全屏广播模式抑制状态（True = 屏蔽非考试提醒声音）"""
    global _FULLSCREEN
    _FULLSCREEN = bool(suppressed)


def set_popup_mute(on: bool) -> None:
    """设置考试时段自动弹窗静音状态"""
    global _POPUP_MUTE
    _POPUP_MUTE = bool(on)


def is_popup_mute() -> bool:
    """读取是否处于考试时段弹窗静音状态"""
    return _POPUP_MUTE


def is_suppressed() -> bool:
    """是否处于抑制状态（任一来源开启即视为抑制）"""
    return _FULLSCREEN or _POPUP_MUTE