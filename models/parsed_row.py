"""AI 解析后的考试行数据"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ParsedExamRow:
    subject: Optional[str] = None
    date: Optional[str] = None        # yyyy-MM-dd
    start_time: Optional[str] = None   # HH:mm
    end_time: Optional[str] = None     # HH:mm
    parse_warning: Optional[str] = None
    confidence: float = 1.0

    @property
    def has_missing_fields(self) -> bool:
        return not all([
            self.subject and self.subject.strip(),
            self.date and self.date.strip(),
            self.start_time and self.start_time.strip(),
            self.end_time and self.end_time.strip(),
        ])

    def get_missing_field_names(self) -> list[str]:
        missing = []
        if not self.subject or not self.subject.strip():
            missing.append("科目")
        if not self.date or not self.date.strip():
            missing.append("日期")
        if not self.start_time or not self.start_time.strip():
            missing.append("开始时间")
        if not self.end_time or not self.end_time.strip():
            missing.append("结束时间")
        return missing

    def normalize_time(self, time_str: str) -> str:
        """标准化时间格式为 HH:mm"""
        cleaned = time_str.strip()
        for prefix in ["上午", "下午", "AM", "PM", "am", "pm"]:
            cleaned = cleaned.replace(prefix, "")
        cleaned = cleaned.replace("点", ":").replace("时", ":")
        cleaned = cleaned.replace("分", "").replace("秒", "").strip()

        parts = cleaned.split(":")
        if len(parts) >= 2:
            try:
                h, m = int(parts[0]), int(parts[1])
                return f"{h:02d}:{m:02d}"
            except ValueError:
                pass
        return time_str

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "parse_warning": self.parse_warning,
            "confidence": self.confidence,
        }
