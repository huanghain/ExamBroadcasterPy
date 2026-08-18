"""
离线音频管理服务

管理 sound/ 文件夹中的预录音频文件，提供离线模式下的语音播放支持。
与 scheduler.py 中的 DEFAULT_TTS_TEXTS 按 (reminder_type, minutes_before) 键值对应。
"""
import os
import asyncio
from pathlib import Path
from typing import Optional, Callable

from config import SOUND_DIR

# 6 条默认提醒预设 — 与 scheduler.py 中 DEFAULT_TTS_TEXTS 保持一致
OFFLINE_PRESETS = [
    ("start", 15, "请监考老师组织考生有序进入考场"),
    ("start", 10, "请监考老师发放答题卡、草稿纸"),
    ("start", 5,  "请监考老师发放试卷"),
    ("start", 0,  "考试开始，请考生开始答题"),
    ("end",   15, "距离考试结束还有15分钟，请考生注意把握时间"),
    ("end",   0,  "考试结束，请考生立即停止答题"),
]

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


def _preset_filename(rtype: str, mins: int) -> str:
    return f"{rtype}_{mins}.mp3"


def _preset_label(rtype: str, mins: int) -> str:
    """生成预设标签"""
    if rtype == "start":
        return "开始考试" if mins == 0 else f"考前 {mins} 分钟"
    else:
        return "考试结束" if mins == 0 else f"结束前 {mins} 分钟"


async def _generate_one_async(rtype: str, mins: int, text: str, voice: str = DEFAULT_VOICE) -> Path:
    """生成单条离线语音"""
    import edge_tts
    out_path = SOUND_DIR / _preset_filename(rtype, mins)

    # 确保目录可写
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    if not os.access(str(SOUND_DIR), os.W_OK):
        raise PermissionError(f"无法写入目录: {SOUND_DIR}（可能是只读的打包临时目录）")

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(f"文件生成成功但为空: {out_path}")
    return out_path


def check_edge_tts_available() -> tuple[bool, str]:
    """检查 edge_tts 是否可用（打包后可能缺失依赖）"""
    try:
        import edge_tts
        import aiohttp
    except ImportError as e:
        return False, f"缺少依赖: {e}"
    except Exception as e:
        return False, f"初始化失败: {e}"

    # 检查 SOUND_DIR 是否可写
    try:
        SOUND_DIR.mkdir(parents=True, exist_ok=True)
        if not os.access(str(SOUND_DIR), os.W_OK):
            return False, f"音频目录不可写: {SOUND_DIR}"
    except Exception as e:
        return False, f"无法创建音频目录: {SOUND_DIR} ({e})"

    return True, "edge_tts 可用"


# ──────────────────────────────────────────────
#  新函数：检测已有/缺失语音
# ──────────────────────────────────────────────

def check_offline_audio_status() -> dict:
    """
    检测现有语音文件状态。

    Returns:
        dict: {
            "total": 6,
            "existing": [{"rtype": "start", "mins": 15, "label": "考前 15 分钟", ...}, ...],
            "missing": [{"rtype": "start", "mins": 5, "label": "考前 5 分钟", "text": "..."}, ...],
            "existing_count": N,
            "missing_count": N,
        }
    """
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    missing = []

    for rtype, mins, text in OFFLINE_PRESETS:
        fpath = SOUND_DIR / _preset_filename(rtype, mins)
        label = _preset_label(rtype, mins)
        entry = {"rtype": rtype, "mins": mins, "text": text, "label": label}
        if fpath.exists() and fpath.stat().st_size > 0:
            entry["size_kb"] = round(fpath.stat().st_size / 1024, 1)
            entry["path"] = str(fpath)
            existing.append(entry)
        else:
            missing.append(entry)

    return {
        "total": len(OFFLINE_PRESETS),
        "existing": existing,
        "missing": missing,
        "existing_count": len(existing),
        "missing_count": len(missing),
    }


async def generate_missing_offline_audio(
    voice: str = DEFAULT_VOICE,
    on_progress: Optional[Callable] = None,
    on_status_change: Optional[Callable] = None,
) -> list[dict]:
    """
    仅生成缺失的离线语音文件。进度条基于全部 6 条（已有 + 缺失）计分。

    Args:
        voice: edge-tts 语音名称
        on_progress: 进度回调 (idx, total, label, text, status, path_or_error)
                      idx 从 0 到 total-1，total = 6（全部预设数）
        on_status_change: 状态回调 (message) — 用于弹窗显示"检测到 X 条已有..."

    Returns:
        list[dict]: 全部 6 条的生成结果 (已有标记为 skipped)
    """
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    status = check_offline_audio_status()
    total = status["total"]
    all_results = []

    # 先报告总状态
    if on_status_change:
        msg = f"检测到 {status['existing_count']} 条已有语音，需要生成 {status['missing_count']} 条"
        on_status_change(msg)

    current_idx = 0

    # 已有文件的：标记为 skipped，直接推进索引
    for entry in status["existing"]:
        all_results.append({
            "rtype": entry["rtype"],
            "mins": entry["mins"],
            "text": entry["text"],
            "label": entry["label"],
            "success": True,
            "skipped": True,
            "path": entry.get("path", ""),
            "size_kb": entry.get("size_kb", 0),
        })
        if on_progress:
            on_progress(current_idx, total, entry["label"], entry["text"], "skip", entry.get("path", ""))
        current_idx += 1

    # 缺失文件的：逐个生成
    for entry in status["missing"]:
        rtype, mins, text = entry["rtype"], entry["mins"], entry["text"]
        label = entry["label"]
        try:
            out = await _generate_one_async(rtype, mins, text, voice)
            size_kb = round(out.stat().st_size / 1024, 1)
            all_results.append({
                "rtype": rtype, "mins": mins, "text": text,
                "label": label, "success": True, "skipped": False,
                "path": str(out), "size_kb": size_kb,
            })
            if on_progress:
                on_progress(current_idx, total, label, text, "ok", str(out))
        except Exception as e:
            error_detail = f"{e}"
            if isinstance(e, ImportError) or "No module" in str(e):
                error_detail = f"模块导入失败: {e}（打包后可能缺失依赖）"
            elif isinstance(e, PermissionError):
                error_detail = f"权限不足，无法写入文件: {e}"
            elif "Connection" in str(e) or "network" in str(e).lower() or "timeout" in str(e).lower():
                error_detail = f"网络错误（edge-tts 需要联网）: {e}"
            all_results.append({
                "rtype": rtype, "mins": mins, "text": text,
                "label": label, "success": False, "skipped": False,
                "error": error_detail,
            })
            if on_progress:
                on_progress(current_idx, total, label, text, "fail", error_detail)
        current_idx += 1

    return all_results


# ──────────────────────────────────────────────
#  兼容旧接口
# ──────────────────────────────────────────────

async def generate_all_offline_audio(
    voice: str = DEFAULT_VOICE,
    on_progress: Optional[Callable] = None
) -> list[dict]:
    """
    [兼容旧接口] 生成全部 6 条默认离线语音（不跳过已存在的）。
    新代码应优先使用 generate_missing_offline_audio()。
    """
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(OFFLINE_PRESETS)

    for idx, (rtype, mins, text) in enumerate(OFFLINE_PRESETS):
        label = _preset_label(rtype, mins)
        try:
            out = await _generate_one_async(rtype, mins, text, voice)
            size_kb = round(out.stat().st_size / 1024, 1)
            results.append({
                "rtype": rtype, "mins": mins, "text": text,
                "label": label, "success": True, "path": str(out),
                "size_kb": size_kb,
            })
            if on_progress:
                on_progress(idx, total, label, text, "ok", str(out))
        except Exception as e:
            error_detail = f"{e}"
            if isinstance(e, ImportError) or "No module" in str(e):
                error_detail = f"模块导入失败: {e}（打包后可能缺失依赖）"
            elif isinstance(e, PermissionError):
                error_detail = f"权限不足，无法写入文件: {e}"
            elif "Connection" in str(e) or "network" in str(e).lower() or "timeout" in str(e).lower():
                error_detail = f"网络错误（edge-tts 需要联网）: {e}"
            results.append({
                "rtype": rtype, "mins": mins, "text": text,
                "label": label, "success": False, "error": error_detail,
            })
            if on_progress:
                on_progress(idx, total, label, text, "fail", error_detail)

    return results


def has_any_offline_audio() -> bool:
    """检查 sound 文件夹中是否存在任何离线音频文件"""
    if not SOUND_DIR.exists():
        return False
    return any(SOUND_DIR.glob("*.mp3"))


class OfflineAudioService:
    """离线音频管理服务 — 将提醒类型映射到本地音频文件"""

    def __init__(self):
        self._sound_dir = SOUND_DIR
        self._sound_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sound_dir(self) -> Path:
        return self._sound_dir

    def get_audio_path(self, reminder_type: str, minutes_before: int) -> Optional[str]:
        """根据提醒类型和分钟数获取本地音频文件路径"""
        filename = f"{reminder_type}_{minutes_before}.mp3"
        path = self._sound_dir / filename
        if path.exists():
            return str(path)
        return None

    def has_offline_audio(self, reminder_type: str, minutes_before: int) -> bool:
        """检查是否存在对应的离线音频文件"""
        return self.get_audio_path(reminder_type, minutes_before) is not None

    def list_available(self) -> list[dict]:
        """列出所有可用的离线音频文件"""
        available = []
        if not self._sound_dir.exists():
            return available

        for f in sorted(self._sound_dir.glob("*.mp3")):
            name = f.stem  # 如 "start_15"
            parts = name.split("_", 1)
            if len(parts) == 2:
                rtype, mins_str = parts
                try:
                    mins = int(mins_str)
                except ValueError:
                    continue
                available.append({
                    "reminder_type": rtype,
                    "minutes_before": mins,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                })
        return available

    def summary(self) -> str:
        """返回可用音频摘要"""
        available = self.list_available()
        if not available:
            return "未找到离线音频文件，请先运行 tools/generate_offline_audio.py"
        return f"已找到 {len(available)} 个离线音频文件"

    def check_status(self) -> dict:
        """便捷方法：检查已有/缺失状态"""
        return check_offline_audio_status()