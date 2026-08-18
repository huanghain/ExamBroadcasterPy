"""考试提醒实体 — 支持一次考试多个提醒，支持自定义 TTS 文字"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from services.database import Base


class ExamReminder(Base):
    __tablename__ = "exam_reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    reminder_type = Column(String(10), default="start")  # "start"=开考前, "end"=结束前
    minutes_before = Column(Integer, default=30)          # 提前分钟数
    is_enabled = Column(Boolean, default=True)
    custom_audio_path = Column(String(500), nullable=True)  # 自定义语音文件路径
    custom_tts_text = Column(String(2000), nullable=True)   # 自定义 TTS 播报文字
    created_at = Column(DateTime, default=datetime.now)

    exam = relationship("Exam", back_populates="reminders")

    @property
    def type_label(self) -> str:
        """提醒类型中文标签"""
        if self.reminder_type == "start":
            return "开始考试" if (self.minutes_before or 0) == 0 else "开考前"
        else:
            return "考试结束" if (self.minutes_before or 0) == 0 else "结束前"

    @property
    def description(self) -> str:
        """可读描述"""
        mins = self.minutes_before or 0
        if self.reminder_type == "start":
            if mins == 0:
                return "开始考试"
            return f"开考前{mins}分钟"
        else:
            if mins == 0:
                return "考试结束"
            return f"结束前{mins}分钟"

    @property
    def has_custom_audio(self) -> bool:
        """是否有自定义语音文件"""
        return bool(self.custom_audio_path)

    @property
    def has_custom_tts(self) -> bool:
        """是否有自定义 TTS 文字"""
        return bool(self.custom_tts_text)

    @property
    def audio_label(self) -> str:
        """语音来源标签"""
        if self.custom_audio_path:
            import os
            name = os.path.basename(self.custom_audio_path)
            if len(name) > 15:
                name = name[:12] + "..."
            return f"[自定义] {name}"
        if self.custom_tts_text:
            text = self.custom_tts_text
            if len(text) > 15:
                text = text[:12] + "..."
            return f"[TTS] {text}"
        return "TTS"

    @property
    def reminder_time(self) -> str:
        """计算提醒触发时间 (HH:mm)"""
        from models.exam import Exam
        from services.database import get_session
        session = get_session()
        try:
            exam = session.get(Exam, self.exam_id)
            if not exam:
                return ""
            time_str = exam.start_time if self.reminder_type == "start" else exam.end_time
            h, m = map(int, time_str.split(":"))
            total = h * 60 + m - (self.minutes_before or 0)
            if total < 0:
                total += 24 * 60
            return f"{total // 60:02d}:{total % 60:02d}"
        except (ValueError, AttributeError):
            return ""
        finally:
            session.close()

    def __repr__(self):
        return f"<ExamReminder {self.reminder_type} {self.minutes_before}min>"