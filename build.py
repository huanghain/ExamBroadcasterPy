#!/usr/bin/env python3
"""
PyInstaller 打包脚本
默认构成为单文件 + 无控制台窗口（GUI 应用，即 -w）。

用法:
    python build.py                  # 单文件 + 无控制台（默认，分发用）
    python build.py --onedir         # 单目录模式（启动快，调试用）
    python build.py --debug          # 保留控制台窗口（调试用，可组合）
    python build.py --clean          # 清理后重新构建，默认参数仍为单文件+无控制台
组合示例:
    python build.py --onedir --clean --debug
    python build.py --clean --onefile
"""

import os
import re
import sys
import shutil
import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.resolve()
SPEC_FILE = PROJECT_ROOT / "ExamBroadcaster.spec"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
APP_NAME = "ExamBroadcaster"


def clean():
    """清理之前的构建产物"""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"[清理] 已删除: {d}")
    # 清理历史上生成的临时 spec 文件
    for tmp in PROJECT_ROOT.glob("ExamBroadcaster_*.spec"):
        tmp.unlink(missing_ok=True)
    # 清理 __pycache__
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)


def install_pyinstaller():
    """确认 PyInstaller 已安装，未安装则自动安装"""
    try:
        import PyInstaller
        print(f"[检查] PyInstaller {PyInstaller.__version__} 已安装")
        return True
    except ImportError:
        print("[安装] 正在安装 PyInstaller...")
        cmd = [sys.executable, "-m", "pip", "install", "pyinstaller"]
        # 优先带 --break-system-packages（PEP 668 环境），失败则去掉直接装
        for extra in (["--break-system-packages"], []):
            try:
                subprocess.check_call(cmd + extra)
                return True
            except subprocess.CalledProcessError:
                continue
        print("[错误] PyInstaller 安装失败，请手动安装后重试")
        print("       建议执行: pip install pyinstaller")
        sys.exit(1)


def _inject_spec_settings(onefile: bool, console: bool) -> Path:
    """基于 spec 生成一份临时 spec，注入 _ONE_FILE 与 console 开关，返回临时 spec 路径"""
    spec_content = SPEC_FILE.read_text(encoding="utf-8")

    # 1) 注入打包模式 _ONE_FILE（用正则，兼容空格/换行差异）
    onefile_val = "True" if onefile else "False"
    new_content, n1 = re.subn(
        r"_ONE_FILE\s*=\s*(True|False)",
        f"_ONE_FILE = {onefile_val}",
        spec_content,
        count=1,
    )
    if n1 == 0:
        print("[警告] spec 中未找到 _ONE_FILE 定义，已追加到文件末尾")
        new_content += f"\n_ONE_FILE = {onefile_val}\n"

    # 2) 注入控制台开关 console（--debug 时保留控制台，便于调试）
    spec_content = new_content
    console_val = "True" if console else "False"
    new_content, n2 = re.subn(
        r"console\s*=\s*(True|False)",
        f"console={console_val}",
        spec_content,
        count=1,
    )
    if n2 == 0:
        print("[警告] spec 中未找到 console= 配置，无法启用调试控制台")

    # 3) 写入临时 spec
    tag = "onefile" if onefile else "onedir"
    temp_spec = PROJECT_ROOT / f"ExamBroadcaster_{tag}.spec"
    temp_spec.write_text(new_content, encoding="utf-8")
    return temp_spec


def _clean_unmatched_output(onefile: bool):
    """清理与当前模式不匹配的遗留产物，避免 dist 中混淆。

    - onefile 模式：移除 onedir 构建残留的文件夹 dist/ExamBroadcaster/
    - onedir  模式：移除 onefile 构建残留的单文件 dist/ExamBroadcaster(.exe)
    """
    if onefile:
        # 单文件模式：删除 onedir 残留目录
        onedir_out = DIST_DIR / APP_NAME
        if onedir_out.exists():
            shutil.rmtree(onedir_out)
            print(f"[清理] 已删除 onedir 残留目录: {onedir_out}")
    else:
        # 单目录模式：删除单文件残留
        candidates = [
            DIST_DIR / APP_NAME,
            DIST_DIR / f"{APP_NAME}.exe",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                c.unlink()
                print(f"[清理] 已删除 onefile 残留文件: {c}")


def build(onefile: bool = True, console: bool = False):
    """执行打包 — 默认单文件 + 无控制台（-w）"""
    os.chdir(PROJECT_ROOT)

    mode = "单文件 (--onefile)" if onefile else "单目录 (--onedir)"
    console_tag = "启用控制台(调试)" if console else "无控制台(GUI)"
    print(f"[模式] {mode} | {console_tag}")

    # 清理与当前模式不匹配的遗留产物，确保 dist 只保留本次构建结果
    _clean_unmatched_output(onefile)

    temp_spec = _inject_spec_settings(onefile=onefile, console=console)
    try:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(temp_spec),
            "--noconfirm",
        ]
        print(f"[执行] {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode == 0:
            print("\n[OK] 打包成功!")
            if onefile:
                exe = DIST_DIR / ("ExamBroadcaster.exe" if sys.platform == "win32" else "ExamBroadcaster")
                print(f"[输出] {exe}")
            else:
                print(f"[输出] {DIST_DIR / APP_NAME}")
        else:
            print("\n[FAIL] 打包失败，详见上方错误信息")
            sys.exit(1)
    finally:
        # 清理临时 spec 文件
        if temp_spec.exists():
            temp_spec.unlink()


def main():
    parser = argparse.ArgumentParser(description="PyInstaller 打包脚本")
    # 打包模式：默认单文件；--onedir 可切换为单目录
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--onefile", dest="onefile", action="store_true",
        help="打包为单个可执行文件（默认）",
    )
    mode_group.add_argument(
        "--onedir", dest="onefile", action="store_false",
        help="打包为单目录模式（调试用）",
    )
    parser.set_defaults(onefile=True)  # 默认单文件
    parser.add_argument("--clean", action="store_true", help="清理旧的构建产物")
    parser.add_argument(
        "--debug", action="store_true",
        help="保留控制台窗口（默认无控制台，即 -w；此开关用于调试）",
    )
    args = parser.parse_args()

    if args.clean:
        clean()

    install_pyinstaller()
    build(onefile=args.onefile, console=args.debug)


if __name__ == "__main__":
    main()