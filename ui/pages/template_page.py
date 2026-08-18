"""模板库页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QFormLayout,
    QLineEdit, QGroupBox, QMessageBox, QSplitter,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from services.database import get_session
from models.template import BroadcastTemplate, BroadcastNode


class TemplatePage(QWidget):
    """模板库页面"""

    PRESET_TEMPLATES = [
        {
            "name": "高考标准流程",
            "keywords": "高考",
            "description": "标准高考广播流程，含开考提醒、收卷提醒等",
            "nodes": [
                {"name": "考前30分钟提醒", "offset": -30,
                 "text": "各位考生请注意，距离考试开始还有30分钟，请做好准备。"},
                {"name": "开考指令", "offset": 0,
                 "text": "考试开始，请考生开始答题。"},
                {"name": "收卷前15分钟提醒", "offset": -15,
                 "text": "各位考生请注意，距离考试结束还有15分钟，请检查答案。"},
                {"name": "考试结束", "offset": 0,
                 "text": "考试结束，请考生立即停止答题，将试卷和答题卡放在桌上。"},
            ],
        },
        {
            "name": "四六级标准流程",
            "keywords": "四六级 CET",
            "description": "大学英语四六级考试标准广播流程",
            "nodes": [
                {"name": "试音播放", "offset": -35,
                 "text": "现在开始试音播放，请考生调整好听音设备。"},
                {"name": "开考指令", "offset": 0,
                 "text": "考试开始，请考生开始答题。"},
                {"name": "考试结束", "offset": 0,
                 "text": "考试结束，请考生立即停止答题。"},
            ],
        },
        {
            "name": "期末考试简化流程",
            "keywords": "期末",
            "description": "适用于校内期末考试的简化广播流程",
            "nodes": [
                {"name": "开考提醒", "offset": 0,
                 "text": "考试开始，请考生开始答题。"},
                {"name": "结束提醒", "offset": -10,
                 "text": "距离考试结束还有10分钟。"},
                {"name": "考试结束", "offset": 0,
                 "text": "考试结束，请停止答题。"},
            ],
        },
    ]

    def __init__(self, ctx: dict):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # 标题
        header = QHBoxLayout()
        title = QLabel("广播模板库")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        init_btn = QPushButton("初始化预置模板")
        init_btn.setMinimumWidth(160)
        init_btn.clicked.connect(self._init_presets)
        header.addWidget(init_btn)
        layout.addLayout(header)

        # 分割器：左侧模板列表 + 右侧详情
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：模板列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._template_list = QListWidget()
        self._template_list.currentRowChanged.connect(self._on_template_selected)
        left_layout.addWidget(self._template_list)
        splitter.addWidget(left)

        # 右侧：模板详情
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._detail_name = QLabel("请选择一个模板")
        self._detail_name.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        right_layout.addWidget(self._detail_name)

        self._detail_desc = QLabel("")
        self._detail_desc.setWordWrap(True)
        right_layout.addWidget(self._detail_desc)

        right_layout.addWidget(QLabel("\n广播节点："))

        self._nodes_list = QListWidget()
        right_layout.addWidget(self._nodes_list)

        splitter.addWidget(right)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter, 1)

    def refresh(self):
        """刷新模板列表"""
        session = get_session()
        try:
            templates = session.query(BroadcastTemplate).all()
            self._template_list.clear()
            for t in templates:
                item = QListWidgetItem(f"{'[预设] ' if t.is_preset else ''}{t.name}")
                item.setData(Qt.ItemDataRole.UserRole, t.id)
                self._template_list.addItem(item)
        finally:
            session.close()

    def _on_template_selected(self, index: int):
        if index < 0:
            return
        item = self._template_list.item(index)
        template_id = item.data(Qt.ItemDataRole.UserRole)

        session = get_session()
        try:
            template = session.query(BroadcastTemplate).get(template_id)
            if not template:
                return

            self._detail_name.setText(template.name)
            self._detail_desc.setText(template.description)

            self._nodes_list.clear()
            for node in sorted(template.nodes, key=lambda n: n.time_offset_minutes):
                offset_str = (
                    f"考前{abs(node.time_offset_minutes)}分钟"
                    if node.time_offset_minutes < 0
                    else f"考后{node.time_offset_minutes}分钟"
                    if node.time_offset_minutes > 0
                    else "考试开始时刻"
                )
                self._nodes_list.addItem(f"[{offset_str}] {node.name}: {node.broadcast_text}")
        finally:
            session.close()

    def _init_presets(self):
        session = get_session()
        try:
            # 检查是否已有预置模板
            existing = session.query(BroadcastTemplate).filter_by(is_preset=True).count()
            if existing > 0:
                reply = QMessageBox.question(
                    self, "确认", "已存在预置模板，是否重新初始化？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                # 删除旧的预置模板
                session.query(BroadcastTemplate).filter_by(is_preset=True).delete()

            for preset in self.PRESET_TEMPLATES:
                template = BroadcastTemplate(
                    name=preset["name"],
                    keywords=preset["keywords"],
                    description=preset["description"],
                    is_preset=True,
                )
                session.add(template)
                session.flush()

                for i, node_data in enumerate(preset["nodes"]):
                    node = BroadcastNode(
                        template_id=template.id,
                        name=node_data["name"],
                        time_offset_minutes=node_data["offset"],
                        broadcast_text=node_data["text"],
                        order_index=i,
                    )
                    session.add(node)

            session.commit()
            QMessageBox.information(self, "成功", f"已初始化 {len(self.PRESET_TEMPLATES)} 个预置模板")
            self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "错误", str(e))
        finally:
            session.close()
