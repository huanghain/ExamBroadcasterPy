# 考试智能广播系统 (ExamBroadcasterPy)

> 面向学校考场场景的智能语音广播与考试提醒桌面应用，基于 PyQt6 构建，支持 AI 语音生成、离线语音、定时播报、深色模式与 Windows 一键打包。

版本：`v2.1.3`

## 功能特性

- **考试提醒调度**：基于 APScheduler 的定时播报，覆盖考试开始、结束、结束前 15/5 分钟等关键节点；对超短时考试（如 10 分钟）自动禁用逻辑上不可能成立的提醒，避免误播。
- **AI 语音生成**：接入智谱 GLM-4-Flash 生成广播文案，配合 edge-tts 合成自然语音；API Key 使用 AES-256 加密本地存储。
- **离线语音**：预置考试开始/结束铃声与常用广播语音包，断网环境下仍可正常播报；缺失语音可一键补齐生成。
- **自定义界面**：无边框全屏窗口 + 自定义标题栏 + 侧边栏导航；浅色/深色双主题，切换时所有背景与文字颜色完整联动。
- **平滑动画**：页面切换使用"快照消隐"动画，避免复杂页（含 QTableView/QScrollArea）走软件渲染导致的卡顿；侧边栏选中高亮采用几何滑块动画。
- **Excel 导入**：通过 openpyxl 解析考试安排表，批量建立考试与提醒。
- **托盘常驻**：最小化到系统托盘，后台静默运行。
- **启动屏**：内置品牌背景图与图标，加载步骤可视化，深浅模式自适应。

## 技术栈

| 领域 | 选型 |
|------|------|
| GUI 框架 | PyQt6 |
| 数据库 | SQLite + SQLAlchemy |
| 任务调度 | APScheduler (Qt/Background) |
| 语音合成 | edge-tts (在线) + 离线 mp3 |
| AI 文案 | 智谱 GLM-4-Flash (httpx) |
| 加密 | cryptography (AES-256-CBC + PBKDF2) |
| 表格解析 | openpyxl |
| 打包 | PyInstaller (onefile / windowed) |

## 目录结构

```
ExamBroadcasterPy/
├── app.py                  # 程序入口、启动流程编排
├── config.py               # 路径、版本、AI/加密/TTS 配置
├── build.py                # PyInstaller 打包脚本（默认 onefile -w）
├── ExamBroadcaster.spec    # PyInstaller 打包配置（资源、依赖、图标）
├── key_encrypt_tool.py     # API Key 加密辅助工具
├── requirements.txt
├── picture/               # 启动屏背景图、应用图标
├── sound/                 # 铃声与离线语音（.gitkeep 占位，mp3 不入库）
├── models/                # SQLAlchemy 数据模型
├── services/              # 业务服务（数据库、调度、AI、TTS、加密、凭据）
├── ui/
│   ├── main_window.py     # 主窗口 + 侧边栏导航 + 高亮滑块动画
│   ├── styles.py          # 全局 QSS（浅色 + 深色覆盖）
│   ├── animations.py      # 页面切换与弹窗动画
│   ├── pages/             # 今日概览/考试管理/设置/关于/启动屏/模板
│   └── widgets/           # API Key 对话框等自定义控件
├── tools/                 # 离线语音生成脚本
└── utils/                 # 日志等工具
```

## 安装与运行

### 环境要求

- Python 3.10+
- Windows 10/11（推荐；Linux/macOS 可运行但未深度适配）

### 开发运行

```bash
# 1. 克隆
git clone <仓库地址>
cd ExamBroadcasterPy

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python app.py
```

首次运行会在用户数据目录下自动创建数据库与目录结构：
- Windows: `%LOCALAPPDATA%\ExamBroadcaster\`
- macOS: `~/Library/Application Support/ExamBroadcaster/`
- Linux: `~/.local/share/ExamBroadcaster/`

### API Key 配置

启动后在「设置 → 智谱 AI API Key」中填入 Key，程序使用 AES-256 加密存储于本地凭据文件，明文不落盘。未配置时 AI 功能自动禁用，离线语音仍可用。

## 打包发布

```bash
# 默认：单文件 + 无控制台（onefile -w）
python build.py

# 单目录模式（调试更快）
python build.py --onedir

# 带调试控制台
python build.py --debug
```

产物位于 `dist/ExamBroadcaster.exe`（onefile）或 `dist/ExamBroadcaster/`（onedir）。`picture/` 资源与 `sound/` 已内置打包。

## 配置说明

核心配置集中在 `config.py`：

- `APP_VERSION`：版本号（统一维护处）
- `AI_BASE_URL` / `AI_MODEL`：智谱 AI 接口与模型
- `FIXED_SEED` / `PBKDF2_ITERATIONS`：AES 加密参数
- `DEFAULT_VOICE` / `DEFAULT_SPEED` / `DEFAULT_VOLUME`：TTS 默认参数
- `BELL_FILE_NAME`：考试开始/结束铃声文件名

## 项目截图

> 待补充：启动屏、主界面（浅/深色）、设置页、播报弹窗

## 协议

<!-- LICENSE 占位：根据选择补充 MIT / Apache-2.0 / GPL-3.0 等 -->

## 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [edge-tts](https://github.com/rany2/edge-tts)
- [APScheduler](https://apscheduler.readthedocs.io/)
- [智谱 AI](https://open.bigmodel.cn/)
