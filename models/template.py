"""广播模板实体"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from services.database import Base


class BroadcastTemplate(Base):
    __tablename__ = "broadcast_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), default="")
    is_preset = Column(Boolean, default=False)
    keywords = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    nodes = relationship("BroadcastNode", back_populates="template", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="broadcast_template")

    def __repr__(self):
        return f"<Template {self.name} ({len(self.nodes)} nodes)>"


class BroadcastNode(Base):
    __tablename__ = "broadcast_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("broadcast_templates.id"), nullable=False)
    name = Column(String(200), nullable=False)
    time_offset_minutes = Column(Integer, default=0)  # 相对考试开始的偏移（分钟）
    broadcast_text = Column(String(2000), nullable=False)
    custom_audio_path = Column(String(500), nullable=True)
    is_enabled = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)
    voice_name = Column(String(100), default="zh-CN-XiaoxiaoNeural")
    speed_percent = Column(Integer, default=0)

    template = relationship("BroadcastTemplate", back_populates="nodes")

    def __repr__(self):
        return f"<Node {self.name} offset={self.time_offset_minutes}min>"
