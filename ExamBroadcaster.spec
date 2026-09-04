# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
生成方式: pyinstaller --name ExamBroadcaster --windowed app.py
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

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

# ---- 收集 Qt 插件（按需裁剪，显著缩小体积） ----
# 只保留程序实际用到的插件类别与文件，避免全量打包：
#   platforms    → 仅当前操作系统原生平台插件
#   imageformats → 仅 jpg/png/ico/gif（启动屏背景、应用图标加载）
#   styles       → 仅原生窗口样式
#   multimedia   → QMediaPlayer 音频播放所需后端（保留，体积最大的部分）
# 主动剔除 iconengines(svg)、tls(QtNetwork)、sqldrivers 等未使用插件。
_PLATFORM_PLUGIN = {
    "win32":   ["qwindows"],
    "darwin":  ["libqcocoa.dylib"],
    "linux":   ["libqxcb", "libqoffscreen", "libqminimal"],
}.get(sys.platform, ["libqxcb", "libqoffscreen", "libqminimal"])

def _collect_qt_plugins(subdir, allowed=None):
    """收集 Qt 插件目录；allowed 为文件名前缀集合，None 表示全收"""
    if PYQT6_DIR is None:
        return []
    plugin_dir = PYQT6_DIR / "Qt6" / "plugins" / subdir
    if not plugin_dir.exists():
        return []
    binaries = []
    for f in plugin_dir.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix not in (".dll", ".so", ".dylib") and f.suffix != "":
            continue
        if allowed is not None and not any(f.name.startswith(p) for p in allowed):
            continue
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

# ---- 收集边缘 TTS / aiohttp / charset_normalizer 的子模块 ----
# 三者均为纯 Python 包，其二进制/数据已由 Analysis 依据 import 自动发现，
# 无需 collect_all 全量收集，改用 collect_submodules 兜底动态 import，体积更小。
_edge_datas, edge_binaries, edge_hidden = [], [], []
_aiohttp_datas, aiohttp_binaries, aiohttp_hidden = [], [], []
_cs_datas, cs_binaries, cs_hidden = [], [], []
try:
    edge_hidden = collect_submodules('edge_tts')
    print(f"[spec] collect_submodules('edge_tts'): {len(edge_hidden)} modules")
except Exception as e:
    print(f"[spec] collect_submodules('edge_tts') 失败: {e}")

try:
    aiohttp_hidden = collect_submodules('aiohttp')
    print(f"[spec] collect_submodules('aiohttp'): {len(aiohttp_hidden)} modules")
except Exception as e:
    print(f"[spec] collect_submodules('aiohttp') 失败: {e}")

# charset_normalizer — aiohttp/requests 的字符编码检测依赖（打包后可能缺失）
try:
    cs_hidden = collect_submodules('charset_normalizer')
    print(f"[spec] collect_submodules('charset_normalizer'): {len(cs_hidden)} modules")
except Exception as e:
    print(f"[spec] collect_submodules('charset_normalizer') 失败: {e}")

# ---- cryptography（AES 加密）----
# cryptography 内含 Rust 编译的二进制扩展（cryptography.hazmat.bindings._rust 等），
# collect_submodules 只能收集纯 Python 模块，无法收集这些二进制，导致打包后
# 运行期解密（如删除 API Key 后重启）报 ModuleNotFoundError。
# 故改用 collect_all 把 datas/binaries/hiddenimports 一并纳入。
_cr_datas, _cr_binaries, _cr_hidden = [], [], []
try:
    _cr_datas, _cr_binaries, _cr_hidden = collect_all('cryptography')
    print(f"[spec] collect_all('cryptography'): {len(_cr_hidden)} modules, {len(_cr_binaries)} binaries")
except Exception as e:
    print(f"[spec] collect_all('cryptography') 失败: {e}")

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
        _collect_qt_plugins("platforms", _PLATFORM_PLUGIN) +
        _collect_qt_plugins("styles", ["qwindowsvistastyle"]) +
        _collect_qt_plugins("imageformats", ["qjpeg", "qpng", "qico", "qgif"]) +
        _collect_qt_multimedia() +
        _cr_binaries
    ),
    datas=_sound_datas + _picture_datas + _cr_datas,
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
    ] + edge_hidden + aiohttp_hidden + cs_hidden + _cr_hidden,
    hookspath=[],
    # 限制 PyInstaller PyQt6 钩子默认全量收集的 Qt 插件类别，
    # 仅保留实际使用到的（platforms/multimedia），配合上方手动按需收集，
    # 大幅减少 Qt 插件体积（sql 驱动、tls、iconengines 等不再被打进包）。
    hooksconfig={
        "PyQt6": {
            "plugins": ["platforms", "multimedia", "mediaservice"],
        },
    },
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
        "PyQt5.QtCore",
        "pytest",
        "setuptools",
        "pip",
        # 未使用的标准库（调试/诊断/邮件/编解码等），安全排除
        "unittest",
        "doctest",
        "pdb",
        "pydoc",
        "idlelib",
        "lib2to3",
        "turtledemo",
        # 注意：不要排除 email —— aiohttp / openpyxl/http.cookiejar 等会隐式
        # import email.utils，强制排除会在运行期触发 ImportError。
        "pstats",
        "cProfile",
    ],
    noarchive=False,
    # optimize=2：比 1 额外剥离字节码中的 docstring（相当于 python -OO），
    # 进一步缩小 PYZ 体积与加载时间，且不影响任何功能。
    optimize=2,
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