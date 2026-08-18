# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
生成方式: pyinstaller --name ExamBroadcaster --windowed app.py
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# ---- 基础配置 ----
APP_NAME = "ExamBroadcaster"
ENTRY_SCRIPT = "app.py"
# 应用图标（打包为可执行文件图标）。开发阶段已内置 picture/app_icon.ico；
# 若缺失则退回无图标（不中断打包）。
ICON_PATH = os.path.join(os.path.abspath(SPECPATH if 'SPECPATH' in dir() else os.path.dirname(os.path.abspath(ENTRY_SCRIPT))), "picture", "app_icon.ico")
if not os.path.isfile(ICON_PATH):
    ICON_PATH = None
    print("[spec] 未找到 picture/app_icon.ico，图标置空")

# ---- 自动查找 PyQt6 路径 ----
try:
    import PyQt6
    PYQT6_DIR = Path(PyQt6.__file__).parent
except ImportError:
    PYQT6_DIR = None

# ---- 收集 Qt 插件 ----
def _collect_qt_plugins(subdir):
    """收集 Qt 插件目录"""
    if PYQT6_DIR is None:
        return []
    plugin_dir = PYQT6_DIR / "Qt6" / "plugins" / subdir
    if not plugin_dir.exists():
        return []
    binaries = []
    for f in plugin_dir.rglob("*"):
        if f.is_file() and (f.suffix in (".dll", ".so", ".dylib") or not f.suffix):
            binaries.append((str(f), str(Path("PyQt6/Qt6/plugins") / subdir)))
    return binaries

# ---- 收集 Qt 多媒体后端 ----
def _collect_qt_multimedia():
    """收集 Qt 多媒体后端（QMediaPlayer 需要）"""
    if PYQT6_DIR is None:
        return []
    results = []
    candidates = [
        PYQT6_DIR / "Qt6" / "plugins" / "multimedia",
        PYQT6_DIR / "Qt6" / "plugins" / "mediaservice",
    ]
    for candidate in candidates:
        if candidate.exists():
            for f in candidate.rglob("*"):
                if f.is_file():
                    target = str(Path("PyQt6/Qt6/plugins") / candidate.name)
                    results.append((str(f), target))
    return results

# ---- 项目根目录 ----
# PyInstaller 6.x 用 exec() 执行 spec，SPECPATH 即为 spec 文件所在目录（项目根）。
_SPEC_DIR = os.path.abspath(SPECPATH) if 'SPECPATH' in dir() else os.path.dirname(os.path.abspath(ENTRY_SCRIPT))

# ---- 收集 edge_tts 和 aiohttp 的全部子模块/数据/二进制 ----
_edge_datas, edge_binaries, edge_hidden = [], [], []
_aiohttp_datas, aiohttp_binaries, aiohttp_hidden = [], [], []
_cs_datas, cs_binaries, cs_hidden = [], [], []
try:
    edge_datas, edge_binaries, edge_hidden = collect_all('edge_tts')
    print(f"[spec] collect_all('edge_tts'): {len(edge_datas)} datas, {len(edge_binaries)} binaries, {len(edge_hidden)} hiddenimports")
except Exception as e:
    print(f"[spec] collect_all('edge_tts') 失败: {e}")

try:
    aiohttp_datas, aiohttp_binaries, aiohttp_hidden = collect_all('aiohttp')
    print(f"[spec] collect_all('aiohttp'): {len(aiohttp_datas)} datas, {len(aiohttp_binaries)} binaries, {len(aiohttp_hidden)} hiddenimports")
except Exception as e:
    print(f"[spec] collect_all('aiohttp') 失败: {e}")

# charset_normalizer — aiohttp/requests 的字符编码检测依赖（打包后可能缺失）
try:
    _cs_datas, cs_binaries, cs_hidden = collect_all('charset_normalizer')
    print(f"[spec] collect_all('charset_normalizer'): {len(_cs_datas)} datas, {len(cs_binaries)} binaries, {len(cs_hidden)} hiddenimports")
except Exception as e:
    print(f"[spec] collect_all('charset_normalizer') 失败: {e}")

# ---- 离线语音文件夹（仅当存在时打包） ----
_sound_datas = []
_sound_dir = os.path.join(_SPEC_DIR, "sound")
if os.path.isdir(_sound_dir) and any(os.scandir(_sound_dir)):
    _sound_datas = [("sound/", "sound/")]
    print(f"[spec] 包含 sound/ 目录")
else:
    print(f"[spec] sound/ 目录不存在或为空，跳过")

# ---- 图片资源（启动屏背景、应用图标；打包内置到 picture/） ----
_picture_datas = []
_picture_dir = os.path.join(_SPEC_DIR, "picture")
if os.path.isdir(_picture_dir) and any(os.scandir(_picture_dir)):
    _picture_datas = [("picture/", "picture/")]
    print(f"[spec] 包含 picture/ 目录")
else:
    print(f"[spec] picture/ 目录不存在或为空，跳过")

# ---- 构建分析参数 ----
a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[_SPEC_DIR],
    binaries=(
        _collect_qt_plugins("platforms") +
        _collect_qt_plugins("styles") +
        _collect_qt_plugins("imageformats") +
        _collect_qt_plugins("iconengines") +
        _collect_qt_plugins("tls") +
        _collect_qt_multimedia() +
        edge_binaries +
        aiohttp_binaries +
        cs_binaries
    ),
    datas=_sound_datas + _picture_datas + edge_datas + aiohttp_datas + _cs_datas,
    hiddenimports=[
        # edge-tts 依赖（动态 import，PyInstaller 无法自动检测）
        "edge_tts",
        "edge_tts.communicate",
        "edge_tts.submaker",
        "edge_tts.util",
        "edge_tts.version",
        "edge_tts.exceptions",
        # edge-tts 间接依赖
        "aiohttp",
        "certifi",
        "multidict",
        "yarl",
        "frozenlist",
        "aiosignal",
        "async_timeout",
        "idna",
        # 字符编码检测（aiohttp/requests 依赖，打包后可能缺失）
        "charset_normalizer",
        "charset_normalizer.md",
        "chardet",
        # cryptography（AES 加密依赖）
        "cryptography",
        "cryptography.hazmat.backends.openssl",
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.primitives.kdf",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.primitives.padding",
        # SQLAlchemy（数据库 ORM）
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        # APScheduler（定时任务调度）
        "apscheduler",
        "apscheduler.schedulers.qt",
        "apscheduler.schedulers.background",
        "apscheduler.triggers.date",
        "apscheduler.triggers.cron",
        "apscheduler.jobstores.memory",
        "apscheduler.executors.pool",
        # 项目模型模块（init_db 中动态 import，PyInstaller 可能无法检测）
        "models",
        "models.exam",
        "models.exam_reminder",
        "models.template",
        "models.schedule_task",
        "models.parsed_row",
        # 项目 UI 模块（页面 + 主窗口 + 对话框）
        "ui.main_window",
        "ui.styles",
        "ui.pages.today_page",
        "ui.pages.exam_page",
        "ui.pages.settings_page",
        "ui.pages.about_page",
        "ui.pages.splash_screen",
        "ui.pages.template_page",
        "ui.widgets.api_key_dialog",
        # 项目服务模块
        "services.database",
        "services.exam_service",
        "services.scheduler",
        "services.ai_service",
        "services.tts_service",
        "services.offline_audio",
        "services.encryption",
        "services.credential_store",
        "services.file_parser",
        # 工具模块
        "utils.logger",
        # openpyxl（Excel 文件解析）
        "openpyxl",
        "openpyxl.cell",
        "openpyxl.styles",
        # httpx（AI API 调用）
        "httpx",
        "anyio",
    ] + edge_hidden + aiohttp_hidden + cs_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块减小体积
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "PyQt5",
        "pytest",
        "setuptools",
        "pip",
    ],
    noarchive=False,
    optimize=0,
)

# ---- 构建参数 ----
pyz = PYZ(a.pure)

# ---- 打包模式开关 ----
# _ONE_FILE = True  → 单文件模式（分发用，启动较慢）
# _ONE_FILE = False → 单目录模式（调试用，启动快）
# 默认单文件（即 -F），与 build.py 默认行为一致
_ONE_FILE = True

# 公用的 EXE 参数
_exe_kwargs = dict(
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 无控制台窗口（GUI 应用）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)

if _ONE_FILE:
    # 单文件模式：所有资源打包进 EXE，不需要 COLLECT
    # EXE 构造器参数顺序：pyz, scripts, binaries, datas, zipfiles
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        a.zipfiles,
        exclude_binaries=False,
        **_exe_kwargs,
    )
else:
    # 单目录模式：EXE 只包含引导代码，资源由 COLLECT 放到外部
    exe = EXE(
        pyz,
        a.scripts,
        [],
        [],
        exclude_binaries=True,
        **_exe_kwargs,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )