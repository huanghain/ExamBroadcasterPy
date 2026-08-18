"""设置页面 - API Key 安全管理 + 离线语音生成 + 深色模式"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFormLayout, QCheckBox, QSlider,
    QMessageBox, QApplication, QDialog, QTextEdit, QProgressBar,
    QSizePolicy, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from services.credential_store import SecureCredentialStore
from services.encryption import AesEncryptionService
from services.ai_service import ZhipuAIService
from services.offline_audio import (
    generate_missing_offline_audio, OFFLINE_PRESETS, has_any_offline_audio,
    check_edge_tts_available, check_offline_audio_status,
)
from ui.widgets.api_key_dialog import ApiKeyDialog
from ui.styles import GLOBAL_STYLESHEET, DARK_STYLESHEET
from config import APP_DATA_DIR, SOUND_DIR, SETTINGS_PATH
import json


class ConnectionTestWorker(QThread):
    """连接测试后台线程"""
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, ai_svc: ZhipuAIService):
        super().__init__()
        self._ai = ai_svc

    def run(self):
        try:
            result = self._ai.test_connection()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class OfflineAudioProgressDialog(QDialog):
    """离线语音生成进度弹窗 — 先检测已有/缺失，仅生成缺失的"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("生成离线语音")
        self.setMinimumWidth(500)
        self.setMaximumWidth(550)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("正在生成离线语音")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # 信息（已有/缺失检测结果）
        self._info_label = QLabel("检测中...")
        self._info_label.setWordWrap(True)
        self._info_label.setObjectName("infoLabel")
        layout.addWidget(self._info_label)

        # 进度条
        self._progress = QProgressBar()
        self._progress.setObjectName("dialogProgressBar")
        self._progress.setMinimum(0)
        self._progress.setMaximum(len(OFFLINE_PRESETS))
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat(f"%v / {len(OFFLINE_PRESETS)} 条")
        layout.addWidget(self._progress)

        # 当前状态
        self._status_label = QLabel("准备中...")
        self._status_label.setObjectName("dialogStatusLabel")
        layout.addWidget(self._status_label)

        # 日志区域
        self._log = QTextEdit()
        self._log.setObjectName("dialogLog")
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(200)
        layout.addWidget(self._log)

        # 关闭按钮（初始隐藏）
        self._close_btn = QPushButton("关闭")
        self._close_btn.setObjectName("dialogCloseBtn")
        self._close_btn.setFixedHeight(30)
        self._close_btn.setVisible(False)
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)

    def on_status_change(self, msg: str):
        """收到状态消息（已有/缺失检测结果）"""
        self._info_label.setText(msg)
        self._log.append(f"[INFO] {msg}")

    def on_progress(self, idx: int, total: int, label: str, text: str, status: str, detail: str):
        """更新进度（含跳过/成功/失败）"""
        self._progress.setValue(idx + 1)
        if status == "ok":
            self._log.append(f"[OK] {label}  ({detail})")
        elif status == "skip":
            self._log.append(f"[SKIP] {label}  (已存在)")
        else:
            self._log.append(f"[FAIL] {label}: {detail}")
        self._status_label.setText(f"({idx + 1}/{total}) {label}")

    def on_finished(self, success_count: int, total: int):
        """全部完成"""
        self._progress.setValue(total)
        if success_count == total or (success_count == 0 and total == len(OFFLINE_PRESETS)):
            self._status_label.setText(f"全部完成！已生成 {success_count} 条新语音")
            self._status_label.setProperty("state", "success")
        else:
            failed = total - success_count
            self._status_label.setText(f"完成：{success_count} 成功，{failed} 失败")
            self._status_label.setProperty("state", "failure")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self._close_btn.setVisible(True)


class GenerateOfflineAudioWorker(QThread):
    """离线语音生成后台线程 — 仅生成缺失的"""
    progress = pyqtSignal(int, int, str, str, str, str)  # idx, total, label, text, status, detail
    status_change = pyqtSignal(str)  # 状态消息
    finished = pyqtSignal(int, int)  # success_count, total
    error = pyqtSignal(str)

    def run(self):
        """在子线程中运行 asyncio 事件循环"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                generate_missing_offline_audio(
                    on_progress=self._on_progress,
                    on_status_change=self._on_status,
                )
            )
            success_count = sum(1 for r in results if r["success"] and not r.get("skipped"))
            self.finished.emit(success_count, len(results))
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()

    def _on_progress(self, idx, total, label, text, status, detail):
        self.progress.emit(idx, total, label, text, status, detail)

    def _on_status(self, msg):
        self.status_change.emit(msg)


class SettingsPage(QWidget):
    """设置页面"""

    def __init__(self, ctx: dict):
        super().__init__()
        self._ctx = ctx
        self._credential_store: SecureCredentialStore = ctx["credential_store"]
        self._worker: ConnectionTestWorker | None = None
        self._audio_worker: GenerateOfflineAudioWorker | None = None
        self._init_ui()

    def _init_ui(self):
        # 滚动容器，避免内容过多时文字重叠/溢出
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("设置")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # ===== API Key 安全配置 =====
        api_group = QGroupBox("智谱 AI API Key")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(16)

        info = QLabel(
            "API Key 使用 AES-256-CBC 加密存储，密钥与当前机器用户绑定。\n"
            f"凭据文件位置: {APP_DATA_DIR}"
        )
        info.setWordWrap(True)
        info.setObjectName("infoLabel")
        info.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        info.setMinimumHeight(70)
        info.setTextFormat(Qt.TextFormat.PlainText)
        api_layout.addWidget(info)

        # 当前状态
        self._status_label = QLabel()
        self._status_label.setObjectName("apiKeyStatus")
        api_layout.addWidget(self._status_label)

        # 已配置 Key 显示
        key_row = QHBoxLayout()
        self._masked_key = QLabel()
        self._masked_key.setObjectName("maskedKey")
        key_row.addWidget(QLabel("当前 Key:"))
        key_row.addWidget(self._masked_key)
        key_row.addStretch()
        api_layout.addLayout(key_row)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._change_btn = QPushButton("更改 API Key")
        self._change_btn.setObjectName("accentBtn")
        self._change_btn.setMinimumWidth(150)
        self._change_btn.clicked.connect(self._change_key)
        btn_row.addWidget(self._change_btn)

        self._delete_btn = QPushButton("删除 API Key")
        self._delete_btn.setObjectName("dangerBtn")
        self._delete_btn.setMinimumWidth(150)
        self._delete_btn.clicked.connect(self._delete_key)
        btn_row.addWidget(self._delete_btn)

        self._test_btn = QPushButton("测试连接")
        self._test_btn.setMinimumWidth(130)
        self._test_btn.clicked.connect(self._test_connection)
        btn_row.addWidget(self._test_btn)

        btn_row.addStretch()

        self._test_status = QLabel("")
        self._test_status.setObjectName("testStatus")
        self._test_status.setMinimumHeight(24)
        btn_row.addWidget(self._test_status)
        api_layout.addLayout(btn_row)

        layout.addWidget(api_group)

        # ===== 存储信息 =====
        storage_group = QGroupBox("数据存储")
        storage_layout = QFormLayout(storage_group)
        storage_layout.setSpacing(12)
        storage_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        for label_text, value_text in [
            ("数据目录:", str(APP_DATA_DIR)),
            ("数据库:", str(APP_DATA_DIR / 'exam_broadcaster.db')),
            ("凭据文件:", str(APP_DATA_DIR / 'credentials.json')),
        ]:
            lbl = QLabel(label_text)
            lbl.setObjectName("storageLabel")
            lbl.setMinimumHeight(28)
            lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            val = QLabel(value_text)
            val.setObjectName("storageValue")
            val.setWordWrap(True)
            val.setMinimumHeight(28)
            val.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setTextFormat(Qt.TextFormat.PlainText)
            storage_layout.addRow(lbl, val)
        layout.addWidget(storage_group)

        # ===== 离线语音生成 =====
        offline_group = QGroupBox("离线语音")
        offline_layout = QVBoxLayout(offline_group)
        offline_layout.setSpacing(12)

        offline_info = QLabel(
            "使用 edge-tts 为 6 条默认提醒预生成 MP3 录音文件，\n"
            "离线模式下无需网络即可播报提醒语音。\n"
            f"语音目录: {SOUND_DIR}"
        )
        offline_info.setWordWrap(True)
        offline_info.setObjectName("infoLabel")
        offline_info.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        offline_info.setMinimumHeight(80)
        offline_info.setTextFormat(Qt.TextFormat.PlainText)
        offline_layout.addWidget(offline_info)

        # 生成状态
        self._offline_status = QLabel(self._get_offline_audio_status())
        self._offline_status.setObjectName("offlineStatus")
        offline_layout.addWidget(self._offline_status)

        # 生成按钮
        gen_btn_row = QHBoxLayout()
        gen_btn_row.setSpacing(10)

        self._gen_offline_btn = QPushButton("生成离线语音")
        self._gen_offline_btn.setObjectName("accentBtn")
        self._gen_offline_btn.setMinimumWidth(170)
        self._gen_offline_btn.clicked.connect(self._generate_offline_audio)
        gen_btn_row.addWidget(self._gen_offline_btn)
        gen_btn_row.addStretch()
        offline_layout.addLayout(gen_btn_row)

        layout.addWidget(offline_group)

        # ===== 深色模式 =====
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(12)

        theme_info = QLabel(
            "切换应用程序的深色/浅色显示模式，立即生效。"
        )
        theme_info.setWordWrap(True)
        theme_info.setObjectName("infoLabel")
        theme_info.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        theme_info.setMinimumHeight(50)
        theme_info.setTextFormat(Qt.TextFormat.PlainText)
        theme_layout.addWidget(theme_info)

        # 获取当前深色模式状态
        is_dark = self._ctx.get("dark_mode", False)

        self._dark_mode_switch = QCheckBox("深色模式")
        self._dark_mode_switch.setObjectName("darkModeSwitch")
        self._dark_mode_switch.setChecked(is_dark)
        self._dark_mode_switch.toggled.connect(self._on_dark_mode_toggled)
        theme_layout.addWidget(self._dark_mode_switch)

        layout.addWidget(theme_group)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # 初始加载状态
        self._update_status()

    def _update_status(self):
        has_key = self._credential_store.has_api_key
        if has_key:
            key = self._credential_store.get_api_key()
            self._status_label.setText("已配置 (AES-256 加密存储)")
            self._status_label.setProperty("state", "configured")
            if key:
                masked = key[:4] + "*" * min(len(key) - 8, 20) + key[-4:]
                self._masked_key.setText(masked)
            self._delete_btn.setEnabled(True)
            self._test_btn.setEnabled(True)
        else:
            self._status_label.setText("未配置 - AI 功能已禁用")
            self._status_label.setProperty("state", "unconfigured")
            self._masked_key.setText("")
            self._delete_btn.setEnabled(False)
            self._test_btn.setEnabled(False)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _change_key(self):
        """弹出 API Key 输入弹窗"""
        dlg = ApiKeyDialog(self._credential_store, self)
        if dlg.exec() and dlg.was_accepted:
            self._update_status()
            QMessageBox.information(self, "成功", "API Key 已更新！\nAI 功能已启用。")

    def _delete_key(self):
        """删除 API Key 并重启软件"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除已保存的 API Key 吗？\n\n删除后 AI 功能将被禁用，软件将自动重启。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._credential_store.clear_api_key()
            QMessageBox.information(self, "已删除", "API Key 已删除，软件将重启。")
            # 重启软件
            import sys, os
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)

    def _test_connection(self):
        api_key = self._credential_store.get_api_key()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先配置 API Key")
            return

        self._test_btn.setEnabled(False)
        self._test_status.setText("测试中...")

        ai_svc = ZhipuAIService(api_key)
        self._worker = ConnectionTestWorker(ai_svc)
        self._worker.finished.connect(self._on_test_result)
        self._worker.error.connect(self._on_test_error)
        self._worker.start()

    def _on_test_result(self, success: bool):
        self._test_btn.setEnabled(True)
        if success:
            self._test_status.setText("连接成功！")
            self._test_status.setProperty("state", "success")
        else:
            self._test_status.setText("连接失败")
            self._test_status.setProperty("state", "failure")
        self._test_status.style().unpolish(self._test_status)
        self._test_status.style().polish(self._test_status)

    def _on_test_error(self, error_msg: str):
        self._test_btn.setEnabled(True)
        self._test_status.setText(f"{error_msg}")
        self._test_status.setProperty("state", "failure")
        self._test_status.style().unpolish(self._test_status)
        self._test_status.style().polish(self._test_status)

    def _get_offline_audio_status(self) -> str:
        """获取离线音频状态描述"""
        status = check_offline_audio_status()
        if status["existing_count"] == status["total"]:
            return f"已生成全部 {status['total']} 条离线语音 (位于 {SOUND_DIR})"
        elif status["existing_count"] > 0:
            return f"已生成 {status['existing_count']}/{status['total']} 条离线语音 ({status['missing_count']} 条缺失)"
        return "尚未生成离线语音"

    def _generate_offline_audio(self):
        """触发离线语音生成"""
        # 预检查 edge_tts 是否可用
        available, msg = check_edge_tts_available()
        if not available:
            QMessageBox.critical(
                self, "无法生成离线语音",
                f"edge-tts 不可用，无法生成离线语音。\n\n原因: {msg}\n\n"
                "请确保已安装 edge-tts 和 aiohttp:\n"
                "  pip install edge-tts aiohttp"
            )
            return

        self._gen_offline_btn.setEnabled(False)

        dlg = OfflineAudioProgressDialog(self)
        self._audio_worker = GenerateOfflineAudioWorker()
        self._audio_worker.status_change.connect(dlg.on_status_change)
        self._audio_worker.progress.connect(dlg.on_progress)
        self._audio_worker.finished.connect(
            lambda success, total: self._on_offline_audio_done(dlg, success, total)
        )
        self._audio_worker.error.connect(
            lambda e: self._on_offline_audio_error(dlg, e)
        )
        self._audio_worker.start()
        dlg.exec()

    def _on_offline_audio_done(self, dlg, success_count, total):
        dlg.on_finished(success_count, total)
        self._gen_offline_btn.setEnabled(True)
        self._offline_status.setText(self._get_offline_audio_status())

    def _on_offline_audio_error(self, dlg, error_msg):
        dlg._log.append(f"[ERROR] {error_msg}")
        dlg._status_label.setText(f"生成失败: {error_msg}")
        dlg._status_label.setProperty("state", "error")
        dlg._status_label.style().unpolish(dlg._status_label)
        dlg._status_label.style().polish(dlg._status_label)
        dlg._close_btn.setVisible(True)
        self._gen_offline_btn.setEnabled(True)

    def _on_dark_mode_toggled(self, enabled: bool):
        """深色模式切换处理"""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            if enabled:
                # 深色 = 浅色 + 深色覆盖，继承字号/边距，避免大标题、时间显示变小
                app.setStyleSheet(GLOBAL_STYLESHEET + DARK_STYLESHEET)
            else:
                app.setStyleSheet(GLOBAL_STYLESHEET)

        # 持久化设置
        settings = {}
        try:
            if SETTINGS_PATH.exists():
                settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        settings["dark_mode"] = enabled
        try:
            SETTINGS_PATH.write_text(
                json.dumps(settings, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def refresh(self):
        self._update_status()
        self._offline_status.setText(self._get_offline_audio_status())