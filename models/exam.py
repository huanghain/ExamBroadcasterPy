"""考试科目实体"""
from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Time
from sqlalchemy.orm import relationship
from services.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(200), nullable=False)
    exam_date = Column(String(10), nullable=False)  # yyyy-MM-dd
    start_time = Column(String(5), nullable=False)   # HH:mm
    end_time = Column(String(5), nullable=False)     # HH:mm
    notes = Column(String(1000), default="")

    # 旧提醒字段（保留向后兼容，新逻辑使用 reminders 关系）
    reminder_enabled = Column(Boolean, default=True)
    reminder_minutes_before = Column(Integer, default=30)
    reminder_end_enabled = Column(Boolean, default=False)
    reminder_end_minutes_before = Column(Integer, default=15)

    broadcast_template_id = Column(Integer, ForeignKey("broadcast_templates.id"), nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    broadcast_template = relationship("BroadcastTemplate", back_populates="exams")
    reminders = relationship("ExamReminder", back_populates="exam", cascade="all, delete-orphan",
                             order_by="ExamReminder.reminder_type.desc(), ExamReminder.minutes_before.desc()")

    @property
    def start_datetime_str(self) -> str:
        return f"{self.exam_date} {self.start_time}"

    @property
    def end_datetime_str(self) -> str:
        return f"{self.exam_date} {self.end_time}"

    @property
    def active_reminders(self) -> list:
        """获取所有启用的提醒（优先使用新表，回退到旧字段）"""
        from models.exam_reminder import ExamReminder
        from sqlalchemy.orm.exc import DetachedInstanceError
        # 尝试从新表获取
        try:
            if self.reminders:
                return [r for r in self.reminders if r.is_enabled]
        except DetachedInstanceError:
            pass  # 对象已脱管且关系未加载，回退到旧字段
        # 回退到旧字段
        result = []
        if self.reminder_enabled:
            result.append(_LegacyReminder("start", self.reminder_minutes_before or 30))
        if self.reminder_end_enabled:
            result.append(_LegacyReminder("end", self.reminder_end_minutes_before or 15))
        return result

    @property
    def reminder_text(self) -> str:
        """提醒设置的可读描述"""
        active = self.active_reminders
        if not active:
            return "未启用"
        parts = []
        for r in active:
            mins = r.minutes_before or 0
            if mins == 0:
                parts.append(f"{'开考' if r.reminder_type == 'start' else '结束'}即时")
            else:
                parts.append(f"{'考前' if r.reminder_type == 'start' else '结束前'}{mins}分钟")
        return " + ".join(parts)

    @property
    def reminder_time(self) -> str:
        """第一个开考前提醒的触发时间 (HH:mm)"""
        active = self.active_reminders
        start_reminders = [r for r in active if r.reminder_type == "start"]
        if not start_reminders:
            return ""
        r = start_reminders[0]
        try:
            h, m = map(int, self.start_time.split(":"))
            total = h * 60 + m - (r.minutes_before or 0)
            if total < 0:
                total += 24 * 60
            return f"{total // 60:02d}:{total % 60:02d}"
        except (ValueError, AttributeError):
            return ""

    @property
    def all_reminder_times(self) -> list[str]:
        """所有提醒的触发时间列表"""
        active = self.active_reminders
        times = []
        for r in active:
            try:
                time_str = self.start_time if r.reminder_type == "start" else self.end_time
                h, m = map(int, time_str.split(":"))
                total = h * 60 + m - (r.minutes_before or 0)
                if total < 0:
                    total += 24 * 60
                times.append(f"{total // 60:02d}:{total % 60:02d}")
            except (ValueError, AttributeError):
                pass
        return times

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "exam_date": self.exam_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "notes": self.notes,
            "reminder_enabled": self.reminder_enabled,
            "reminder_minutes_before": self.reminder_minutes_before,
            "reminder_end_enabled": self.reminder_end_enabled,
            "reminder_end_minutes_before": self.reminder_end_minutes_before,
            "broadcast_template_id": self.broadcast_template_id,
            "is_enabled": self.is_enabled,
        }

    def __repr__(self):
        return f"<Exam {self.subject} {self.exam_date} {self.start_time}-{self.end_time}>"


class _LegacyReminder:
    """旧字段兼容包装"""
    def __init__(self, reminder_type: str, minutes_before: int):
        self.reminder_type = reminder_type
        self.minutes_before = minutes_before
        self.is_enabled = True