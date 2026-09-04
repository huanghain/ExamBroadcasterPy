"""
考试时段自动弹窗静音：窗口判定

静音窗口 = [考试开始前 EXAM_WINDOW_START_BEFORE 分钟, 考试结束后 EXAM_WINDOW_END_AFTER 分钟]。
窗口内软件弹窗静音（除考试提醒外，考试提醒走 force 分支不受影响）。
纯函数实现，便于单元测试与离屏验证。
"""
from datetime import datetime, timedelta

# 静音窗口参数
EXAM_WINDOW_START_BEFORE = 30  # 开始前30分钟
EXAM_WINDOW_END_AFTER = 5      # 结束后5分钟

_TIME_FMT = "%Y-%m-%d %H:%M"


def exam_in_mute_window(exam, now: datetime | None = None) -> bool:
    """判定单场考试当前是否处于静音窗口。

    exam 需具有 exam_date/start_time/end_time 字段（字符串）。
    时间解析失败一律视为不在窗口内，避免异常影响主流程。
    """
    try:
        start = datetime.strptime(f"{exam.exam_date} {exam.start_time}", _TIME_FMT)
        end = datetime.strptime(f"{exam.exam_date} {exam.end_time}", _TIME_FMT)
    except (ValueError, TypeError, AttributeError):
        return False

    if now is None:
        now = datetime.now()

    window_start = start - timedelta(minutes=EXAM_WINDOW_START_BEFORE)
    window_end = end + timedelta(minutes=EXAM_WINDOW_END_AFTER)
    return window_start <= now <= window_end


def any_exam_in_mute_window(exams) -> bool:
    """任意一场启用的考试处于静音窗口即返回 True。"""
    for exam in exams or []:
        if getattr(exam, "is_enabled", True) and exam_in_mute_window(exam):
            return True
    return False