"""调度任务实体"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from services.database import Base


class ScheduleTaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ScheduleTask(Base):
    __tablename__ = "schedule_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("broadcast_nodes.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(Enum(ScheduleTaskStatus), default=ScheduleTaskStatus.PENDING)
    executed_at = Column(DateTime, nullable=True)
    result_message = Column(String(500), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Task exam_id={self.exam_id} at {self.scheduled_time} [{self.status.value}]>"
