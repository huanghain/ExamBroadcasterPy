"""
应用配置
"""
import os
import sys
import platform
import json
from pathlib import Path

# ============================================================
#  路径配置
# ============================================================

APP_NAME = "ExamBroadcaster"

# 版本号（统一在此处维护，各界面显示处引用此常量）
# v2.2.3：设置页无感加载优化（空闲预构建 + 状态延后填充，保留切页动画）
APP_VERSION = "v2.2.3"
APP_DISPLAY_NAME = "考试智能广播系统"

if platform.system() == "Windows":
    APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", "~")) / APP_NAME
elif platform.system() == "Darwin":
    APP_DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
else:
    APP_DATA_DIR = Path.home() / ".local" / "share" / APP_NAME

APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DATA_DIR / "exam_broadcaster.db"
CREDENTIALS_PATH = APP_DATA_DIR / "credentials.json"
SETTINGS_PATH = APP_DATA_DIR / "settings.json"
AUDIO_CACHE_DIR = APP_DATA_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = APP_DATA_DIR / "logs"

# 离线语音文件夹
# 打包后：可执行文件同级目录下的 sound/（多用户共享，持久化）
# 开发环境：项目根目录下的 sound/
if getattr(sys, "frozen", False):
    # 打包后运行: 可执行文件所在目录 / sound/
    _exe_dir = Path(sys.executable).resolve().parent
    SOUND_DIR = _exe_dir / "sound"
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
else:
    # 开发环境: 项目根目录下的 sound/
    SOUND_DIR = Path(__file__).resolve().parent / "sound"
    SOUND_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
#  图片资源（启动屏背景、应用图标）
#  打包后(onefile)：解压到 sys._MEIPASS 临时目录下的 picture/
#  打包后(onedir)： 可执行文件同级 picture/
#  开发环境：      项目根目录 picture/
# ============================================================
if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", "")
    if _meipass:  # onefile 分支：资源解压在临时目录
        PICTURE_DIR = Path(_meipass) / "picture"
    else:         # onedir 分支：资源在可执行文件同级
        PICTURE_DIR = Path(sys.executable).resolve().parent / "picture"
else:
    PICTURE_DIR = Path(__file__).resolve().parent / "picture"
PICTURE_DIR.mkdir(parents=True, exist_ok=True)

# 启动屏背景图（用于 SplashScreen）与程序图标源文件
SPLASH_BG_PATH = PICTURE_DIR / "splash_bg.jpg"
APP_ICON_ICO_PATH = PICTURE_DIR / "app_icon.ico"
APP_ICON_SRC_PATH = PICTURE_DIR / "app_icon.jpg"  # 备用源图

# ============================================================
#  AI 配置
# ============================================================

# 考试开始/结束铃声文件（整体位于 SOUND_DIR 下）
BELL_FILE_NAME = "start_end_bell.mp3"

AI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
AI_MODEL = "glm-4-flash"

# ============================================================
#  AES 加密配置
# ============================================================

FIXED_SEED = b"ExamBroadcaster@2024#SecureKey!"
PBKDF2_ITERATIONS = 600_000
SALT_SIZE = 16
IV_SIZE = 16
KEY_SIZE = 32  # 256 bits

# ============================================================
#  TTS 配置
# ============================================================

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_SPEED = 0  # -50% ~ +100%
DEFAULT_VOLUME = 80
