"""
考试智能广播系统 - 应用程序入口
Python + PyQt6 版本

运行方式：
    python app.py
"""
import sys
import os
import asyncio
import socket
import json
from pathlib import Path

# 将项目根目录加入 Python 搜索路径，确保无论从哪里运行都能正确导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel,
    QProgressBar, QPushButton, QTextEdit,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from services.database import init_db, backup_database
from services.encryption import AesEncryptionService
from services.credential_store import SecureCredentialStore
from services.ai_service import ZhipuAIService
from services.exam_service import ExamService
from services.file_parser import FileParserService
from services.scheduler import SchedulerService
from services.tts_service import TTSService
from services.offline_audio import (
    OfflineAudioService,
    generate_missing_offline_audio, check_edge_tts_available,
    check_offline_audio_status,
)
from ui.main_window import MainWindow
from ui.widgets.api_key_dialog import ApiKeyDialog
from ui.pages.splash_screen import SplashScreen
from ui.styles import GLOBAL_STYLESHEET
from ui.widgets.toast import show_toast, ask_confirm
from config import (
    DEFAULT_VOLUME, DB_PATH, SETTINGS_PATH, APP_VERSION, APP_DISPLAY_NAME,
    SOUND_DIR, BELL_FILE_NAME,
)
from utils.logger import setup_logger, get_logger

# 初始化日志系统
logger = setup_logger("ExamBroadcaster")


def check_network_available() -> bool:
    """检测网络是否可用"""
    try:
        socket.create_connection(("open.bigmodel.cn", 443), timeout=3)
        return True
    except (OSError, socket.timeout):
        pass
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except (OSError, socket.timeout):
        return False


def _load_settings() -> dict:
    """从 settings.json 加载用户偏好设置"""
    try:
        if SETTINGS_PATH.exists():
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("加载设置失败: %s", e)
    return {}


def _save_settings(settings: dict):
    """保存用户偏好设置到 settings.json"""
    try:
        SETTINGS_PATH.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("保存设置失败: %s", e)


def create_app_context() -> dict:
    """创建应用上下文（依赖注入容器）"""
    # 初始化加密服务
    encryption = AesEncryptionService()

    # 安全凭据存储
    credential_store = SecureCredentialStore(encryption)

    # 获取 API Key（如果已配置）
    api_key = credential_store.get_api_key()

    # AI 服务（如果未配置 Key 则为 None）
    ai_service = ZhipuAIService(api_key) if api_key else None

    # 考试管理服务
    exam_service = ExamService()

    # 文件解析服务
    file_parser = FileParserService()

    # 调度引擎
    scheduler = SchedulerService()

    # TTS 服务
    tts_service = TTSService()
    tts_service.set_volume(DEFAULT_VOLUME)

    # 离线音频服务
    offline_audio = OfflineAudioService()

    return {
        "encryption_service": encryption,
        "credential_store": credential_store,
        "ai_service": ai_service,
        "exam_service": exam_service,
        "file_parser": file_parser,
        "scheduler": scheduler,
        "tts_service": tts_service,
        "offline_audio": offline_audio,
        "offline_mode": False,
        "network_available": True,
    }


def check_api_key_on_startup(ctx: dict) -> bool:
    """启动时检测 API Key，如未配置则弹窗要求输入"""
    store: SecureCredentialStore = ctx["credential_store"]
    if store.has_api_key:
        return True

    dlg = ApiKeyDialog(store)
    if dlg.exec() and dlg.was_accepted:
        # 用户成功配置了 Key，更新 context 中的 ai_service
        new_key = store.get_api_key()
        if new_key:
            ctx["ai_service"] = ZhipuAIService(new_key)
        return True
    else:
        # 用户跳过：无系统音的 toast 提示（不触发系统提示音）
        show_toast(
            None, "尚未配置 AI API Key，AI 功能暂时禁用。\n"
                  "您可在 [设置] 页面随时配置。",
            "warning", duration=3600,
        )
        return False


# ──────────────────────────────────────────────
#  启动时离线语音生成弹窗（自动关闭）
# ──────────────────────────────────────────────

class _OfflineGenWorker(QThread):
    """离线语音生成后台线程（仅生成缺失的语音）"""
    progress = pyqtSignal(int, int, str, str, str, str)  # idx, total, label, text, status, detail
    status_change = pyqtSignal(str)  # 状态消息（如"检测到 X 条已有..."）
    finished = pyqtSignal(int, int)  # success_count, total
    error = pyqtSignal(str)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                generate_missing_offline_audio(on_progress=self._on_progress, on_status_change=self._on_status)
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


class _StartupOfflineGenDialog(QDialog):
    """启动时离线语音生成弹窗 — 生成完毕后自动关闭"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("生成离线语音")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._worker = None
        self._generation_done = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("正在生成离线语音")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        self._info_label = QLabel("检测中...")
        self._info_label.setWordWrap(True)
        self._info_label.setObjectName("infoLabel")
        layout.addWidget(self._info_label)

        self._progress = QProgressBar()
        self._progress.setObjectName("dialogProgressBar")
        self._progress.setMinimum(0)
        self._progress.setMaximum(6)
        self._progress.setValue(0)
        self._progress.setFormat("")
        layout.addWidget(self._progress)

        self._status_label = QLabel("准备中...")
        self._status_label.setObjectName("dialogStatusLabel")
        layout.addWidget(self._status_label)

        self._log = QTextEdit()
        self._log.setObjectName("dialogLog")
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(150)
        layout.addWidget(self._log)

        self._close_btn = QPushButton("跳过")
        self._close_btn.setObjectName("dialogCloseBtn")
        self._close_btn.setFixedHeight(30)
        self._close_btn.clicked.connect(self._on_close_clicked)
        layout.addWidget(self._close_btn)

    def start_generation(self):
        """启动生成线程"""
        # 预检查 edge_tts
        available, msg = check_edge_tts_available()
        if not available:
            self._info_label.setText(f"edge-tts 不可用，跳过离线语音生成。")
            self._info_label.setProperty("state", "error")
            self._info_label.style().unpolish(self._info_label)
            self._info_label.style().polish(self._info_label)
            self._log.append(f"[ERROR] {msg}")
            self._log.append("请安装 edge-tts: pip install edge-tts aiohttp")
            self._close_btn.setText("关闭")
            return

        self._close_btn.setEnabled(False)
        self._worker = _OfflineGenWorker()
        self._worker.status_change.connect(self._on_status_change)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_status_change(self, msg):
        """收到状态消息（已有/缺失检测结果）"""
        self._info_label.setText(msg)
        self._log.append(f"[INFO] {msg}")

    def _on_progress(self, idx, total, label, text, status, detail):
        """更新进度（含成功/失败/跳过状态）"""
        self._progress.setValue(idx + 1)
        if status == "ok":
            self._log.append(f"[OK] {label}  ({detail})")
        elif status == "skip":
            self._log.append(f"[SKIP] {label}  (已存在)")
        else:
            self._log.append(f"[FAIL] {label}: {detail}")
        self._status_label.setText(f"({idx + 1}/{total}) {label}")

    def _on_finished(self, success_count, total):
        """全部完成 — 自动关闭弹窗"""
        self._generation_done = True
        self._progress.setValue(total)
        self._log.append(f"[完成] 离线语音生成完毕")
        self._close_btn.setText("继续")
        self._close_btn.setEnabled(True)
        self._status_label.setText("生成完成，继续加载...")
        self._status_label.setProperty("state", "success")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        # 自动关闭
        QTimer.singleShot(800, self.accept)

    def _on_error(self, error_msg):
        self._generation_done = True
        self._status_label.setText(f"生成失败: {error_msg}")
        self._status_label.setProperty("state", "error")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self._log.append(f"[ERROR] {error_msg}")
        self._close_btn.setText("继续")
        self._close_btn.setEnabled(True)
        # 仍然自动关闭
        QTimer.singleShot(1500, self.accept)

    def _on_close_clicked(self):
        if self._generation_done:
            self.accept()
        else:
            self.reject()


# ──────────────────────────────────────────────
#  启动流程
# ──────────────────────────────────────────────

def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION.lstrip("v"))
    app.setStyleSheet(GLOBAL_STYLESHEET)

    logger.info(f"===== {APP_DISPLAY_NAME} {APP_VERSION} 启动 =====")

    # ── 立即显示启动页 ──
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # ── Step 1: 初始化数据库 ──
    splash.set_step_running("database", "正在初始化数据库...")
    app.processEvents()
    try:
        init_db()
        # 自动备份数据库
        backup_path = backup_database()
        if backup_path:
            logger.info("数据库已自动备份: %s", backup_path)
        splash.set_step_done("database", "数据库初始化完成")
        logger.info("数据库初始化完成")
    except Exception as e:
        splash.set_step_error("database", f"数据库初始化失败: {e}")
        app.processEvents()
        logger.critical("数据库初始化失败: %s", e)
        # 致命错误也用无系统音弹窗（退出前允许用户读到错误信息）
        ask_confirm(
            None, "致命错误",
            f"数据库初始化失败，程序无法继续运行。\n\n错误详情: {e}\n\n"
            f"数据库路径: {DB_PATH}\n"
            "请检查磁盘空间和目录权限。",
            yes_text="退出",
            no_text=None,
        )
        sys.exit(1)
    app.processEvents()

    # ── 创建应用上下文 ──
    ctx = create_app_context()

    # ── Step 2: 检测网络连接 ──
    splash.set_step_running("network", "正在检测网络连接...")
    app.processEvents()
    network_ok = check_network_available()
    ctx["network_available"] = network_ok

    # 加载用户偏好设置
    user_settings = _load_settings()
    user_offline = user_settings.get("offline_mode_override")
    if user_offline is not None:
        ctx["offline_mode"] = user_offline
        logger.info("使用用户设置的离线模式: %s", user_offline)
    else:
        ctx["offline_mode"] = not network_ok

    # 加载深色模式设置
    if user_settings.get("dark_mode", False):
        from ui.styles import DARK_STYLESHEET
        # 深色模式 = 浅色(GLOBAL) + 深色覆盖(DARK)，
        # 使只覆盖颜色的控件自动继承浅色中的字号、边距等布局属性（避免大标题/时间变小）
        app.setStyleSheet(GLOBAL_STYLESHEET + DARK_STYLESHEET)
        logger.info("已应用深色模式")
    ctx["dark_mode"] = user_settings.get("dark_mode", False)

    # 考试时段自动弹窗静音开关（默认开启）
    ctx["popup_mute_enabled"] = user_settings.get("popup_mute_enabled", True)

    if network_ok:
        splash.set_step_done("network", "网络连接正常")
    else:
        splash.set_step_done("network", "网络不可用，切换至离线模式")
    app.processEvents()

    # ── Step 3: 检测 API Key ──
    splash.set_step_running("apikey", "正在检测 API Key 配置...")
    app.processEvents()
    check_api_key_on_startup(ctx)
    store: SecureCredentialStore = ctx["credential_store"]
    if store.has_api_key:
        splash.set_step_done("apikey", "API Key 已配置")
    else:
        splash.set_step_done("apikey", "API Key 未配置，AI 功能已禁用")
    app.processEvents()

    # ── Step 4: 检查离线语音 ──
    splash.set_step_running("offline", "正在检查离线语音文件...")
    app.processEvents()

    status = check_offline_audio_status()
    if status["missing_count"] == 0:
        splash.set_step_done("offline", f"离线语音完整（{status['existing_count']}/{status['total']} 条）")
    else:
        splash.set_progress_text(f"检测到 {status['missing_count']} 条语音缺失，正在生成...")
        app.processEvents()

        # 弹出生成弹窗（模态，显示在启动页上方）
        dlg = _StartupOfflineGenDialog()
        dlg.start_generation()
        dlg.exec()

        # 关闭后刷新状态
        status = check_offline_audio_status()
        if status["missing_count"] == 0:
            splash.set_step_done("offline", f"离线语音已全部生成（{status['existing_count']}/{status['total']} 条）")
        else:
            splash.set_step_done("offline", f"离线语音：{status['existing_count']}/{status['total']} 条")
    app.processEvents()

    # ── Step 5: 加载主界面 ──
    splash.set_step_running("done", "正在加载主界面...")
    app.processEvents()

    # 启动调度引擎
    scheduler: SchedulerService = ctx["scheduler"]
    scheduler.set_offline_audio_service(ctx["offline_audio"])
    scheduler.start()

    # 设置广播回调（使用调度器的持久事件循环）
    tts: TTSService = ctx["tts_service"]

    def on_broadcast(exam, node):
        """广播执行回调"""
        logger.info("广播触发: %s - %s: %s", exam.subject, node.name, node.broadcast_text)
        loop = scheduler._get_event_loop()
        try:
            loop.run_until_complete(
                tts.speak(node.broadcast_text, node.voice_name, node.speed_percent,
                          force=True)  # 考试广播：全屏模式也必须播报
            )
        except Exception as e:
            logger.exception("广播播放失败: %s", e)

    scheduler.set_broadcast_callback(on_broadcast)

    # 设置提醒回调（使用调度器的持久事件循环）
    def on_reminder(exam, reminder_text, custom_audio_path=None,
                    reminder_type="", minutes_before=0):
        """提醒执行回调"""
        logger.info(
            "提醒触发: %s: %s (type=%s, %d分钟前)",
            exam.subject, reminder_text, reminder_type, minutes_before,
        )
        loop = scheduler._get_event_loop()

        def _play_bell():
            """考试开始/结束时先播放铃声"""
            try:
                # 同时支持开发环境(SOUND_DIR)与打包环境(_MEIPASS 临时解压目录)
                bell_path = SOUND_DIR / BELL_FILE_NAME
                if not bell_path.exists():
                    import sys as _sys
                    meipass_sound = Path(getattr(_sys, "_MEIPASS", "")) / "sound" / BELL_FILE_NAME
                    if meipass_sound.exists():
                        bell_path = meipass_sound
                if not bell_path.exists():
                    logger.warning("铃声文件不存在，跳过铃声: %s", bell_path)
                    return False
                loop.run_until_complete(tts.play_file(str(bell_path), force=True))
                return True
            except Exception as e:
                logger.warning("铃声播放失败: %s", e)
                return False

        try:
            # 考试开始(0分钟前)/结束(0分钟前)时先响铃声
            if reminder_type in ("start", "end") and minutes_before == 0:
                _play_bell()

            if custom_audio_path:
                loop.run_until_complete(tts.play_file(custom_audio_path, force=True))
            elif ctx.get("offline_mode"):
                offline_audio = ctx.get("offline_audio")
                offline_path = None
                if offline_audio:
                    from services.scheduler import DEFAULT_TTS_TEXTS
                    for (rtype, mins), default_text in DEFAULT_TTS_TEXTS.items():
                        if reminder_text == default_text:
                            offline_path = offline_audio.get_audio_path(rtype, mins)
                            if offline_path:
                                break
                if offline_path:
                    loop.run_until_complete(tts.play_file(offline_path, force=True))
                else:
                    logger.warning("离线模式: 未找到本地音频，跳过播报: %s", reminder_text)
            else:
                loop.run_until_complete(tts.speak(reminder_text, force=True))
        except Exception as e:
            logger.exception("提醒播放失败: %s", e)

    scheduler.set_reminder_callback(on_reminder)

    # 创建主窗口
    window = MainWindow(ctx)
    splash.set_step_done("done", "加载完成")

    # 关闭启动页，显示主窗口
    splash.close_splash()
    window.show()

    logger.info("===== 考试智能广播系统启动完成 =====")

    # 刷新今日概览
    if "today" in window._pages:
        window._pages["today"].refresh()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()