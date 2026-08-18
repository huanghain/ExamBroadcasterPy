"""API Key 输入弹窗 — 启动检测 & 设置页更改使用"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from services.credential_store import SecureCredentialStore
from services.ai_service import ZhipuAIService


class ApiKeyTestWorker(QThread):
    """后台测试 API Key 有效性"""
    success = pyqtSignal()
    failure = pyqtSignal(str)

    def __init__(self, api_key: str):
        super().__init__()
        self._key = api_key

    def run(self):
        try:
            svc = ZhipuAIService(self._key)
            if svc.test_connection():
                self.success.emit()
            else:
                self.failure.emit("连接失败，请检查 Key 是否正确")
        except Exception as e:
            self.failure.emit(str(e))


class ApiKeyDialog(QDialog):
    """API Key 输入弹窗"""

    def __init__(self, credential_store: SecureCredentialStore, parent=None):
        super().__init__(parent)
        self._store = credential_store
        self._worker: ApiKeyTestWorker | None = None
        self._accepted = False
        self.setWindowTitle("API Key 配置")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # 标题
        title = QLabel("配置智谱 AI API Key")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # 说明
        desc = QLabel(
            "AI 功能（自然语言添加考试）需要智谱 AI API Key。\n"
            "Key 将使用 AES-256-CBC 加密存储在本地。\n\n"
            "获取方式：https://bigmodel.cn/apikey/platform → 注册 → API Keys"
        )
        desc.setWordWrap(True)
        desc.setObjectName("infoLabel")
        layout.addWidget(desc)

        # 输入框
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("输入 GLM-4-Flash API Key")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setMinimumHeight(38)
        self._key_input.setObjectName("apiKeyInput")
        layout.addWidget(self._key_input)

        # 进度条
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMinimumHeight(4)
        self._progress.setObjectName("dialogProgressBar")
        layout.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setObjectName("apiKeyStatus")
        layout.addWidget(self._status_label)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._skip_btn = QPushButton("暂时跳过")
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn)

        btn_row.addStretch()

        self._save_btn = QPushButton("保存并验证")
        self._save_btn.setObjectName("accentBtn")
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._save_btn)

        layout.addLayout(btn_row)

    def _on_save(self):
        key = self._key_input.text().strip()
        if not key:
            self._status_label.setText("请输入 API Key")
            self._status_label.setProperty("state", "unconfigured")
            self._status_label.style().unpolish(self._status_label)
            self._status_label.style().polish(self._status_label)
            return

        self._save_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status_label.setText("正在验证...")
        self._status_label.setProperty("state", "")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        self._worker = ApiKeyTestWorker(key)
        self._worker.success.connect(lambda: self._on_verify_ok(key))
        self._worker.failure.connect(self._on_verify_fail)
        self._worker.start()

    def _on_verify_ok(self, key: str):
        self._store.save_api_key(key)
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._status_label.setText("验证成功，已保存")
        self._status_label.setProperty("state", "configured")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self._accepted = True
        self.accept()

    def _on_verify_fail(self, error: str):
        self._save_btn.setEnabled(True)
        self._skip_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText(f"{error}")
        self._status_label.setProperty("state", "unconfigured")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _on_skip(self):
        self._accepted = False
        self.reject()

    @property
    def was_accepted(self) -> bool:
        return self._accepted