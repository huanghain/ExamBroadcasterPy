"""
离线语音生成工具 (独立脚本，不集成到主程序)

使用 edge-tts 为 6 条默认提醒生成 MP3 录音文件，存入 sound/ 文件夹。
离线模式下主程序检测到默认提醒文字时自动调用对应录音。

用法:
    python tools/generate_offline_audio.py              # 生成全部 6 条
    python tools/generate_offline_audio.py --list       # 列出将要生成的文件
    python tools/generate_offline_audio.py --voice zh-CN-YunxiNeural  # 指定语音

依赖:
    pip install edge-tts --break-system-packages
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 6 条默认提醒 -> 与 services/scheduler.py 中 DEFAULT_TTS_TEXTS 保持一致
PRESETS = [
    ("start", 15, "请监考老师组织考生有序进入考场"),
    ("start", 10, "请监考老师发放答题卡、草稿纸"),
    ("start", 5,  "请监考老师发放试卷"),
    ("start", 0,  "考试开始，请考生开始答题"),
    ("end",   15, "距离考试结束还有15分钟，请考生注意把握时间"),
    ("end",   0,  "考试结束，请考生立即停止答题"),
]

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
from config import SOUND_DIR


def filename(rtype: str, mins: int) -> str:
    return f"{rtype}_{mins}.mp3"


async def generate_one(rtype: str, mins: int, text: str, voice: str):
    """生成单条录音"""
    import edge_tts

    out_path = SOUND_DIR / filename(rtype, mins)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))
    return out_path


async def generate_all(voice: str):
    """生成全部 6 条默认录音"""
    SOUND_DIR.mkdir(parents=True, exist_ok=True)

    print(f"语音: {voice}")
    print(f"输出目录: {SOUND_DIR}")
    print(f"共 {len(PRESETS)} 条:\n")

    for rtype, mins, text in PRESETS:
        label = "开考前" if rtype == "start" else "结束前"
        if mins == 0:
            label = "开始考试" if rtype == "start" else "考试结束"
        else:
            label = f"{label} {mins} 分钟"

        print(f"  [{label}] 生成中... ", end="", flush=True)
        try:
            out = await generate_one(rtype, mins, text, voice)
            size_kb = out.stat().st_size / 1024
            print(f"OK ({size_kb:.1f} KB)")
        except Exception as e:
            print(f"FAIL: {e}")

    print(f"\n完成。文件位于: {SOUND_DIR}")


def list_presets():
    """列出将要生成的文件"""
    print(f"输出目录: {SOUND_DIR}")
    print(f"{'文件':<20} {'类型':<12} {'文字'}")
    print("-" * 70)
    for rtype, mins, text in PRESETS:
        label = "开考前" if rtype == "start" else "结束前"
        if mins == 0:
            label = "开始考试" if rtype == "start" else "考试结束"
        else:
            label = f"{label} {mins} 分钟"
        print(f"{filename(rtype, mins):<20} {label:<12} {text}")


def main():
    parser = argparse.ArgumentParser(description="离线语音生成工具 (edge-tts)")
    parser.add_argument("--list", action="store_true", help="列出将要生成的文件")
    parser.add_argument("--voice", default=DEFAULT_VOICE,
                        help=f"edge-tts 语音名称 (默认: {DEFAULT_VOICE})")
    args = parser.parse_args()

    if args.list:
        list_presets()
        return

    asyncio.run(generate_all(args.voice))


if __name__ == "__main__":
    main()