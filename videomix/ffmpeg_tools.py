"""ffmpeg / ffprobe 定位与调用。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


class FfmpegMissing(RuntimeError):
    pass


_WINDOWS_HINTS = [
    r"C:\ffmpeg\bin",
    r"C:\Program Files\ffmpeg\bin",
    r"C:\ProgramData\chocolatey\bin",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
    os.path.expandvars(r"%USERPROFILE%\scoop\shims"),
]


def _candidates(name: str) -> list[str]:
    exe = name + (".exe" if os.name == "nt" else "")
    found: list[str] = []
    override = os.environ.get("VIDEOMIX_FFMPEG_DIR", "").strip()
    if override:
        found.append(os.path.join(override, exe))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found.append(os.path.join(here, "tools", "ffmpeg", "bin", exe))
    which = shutil.which(name)
    if which:
        found.append(which)
    if os.name == "nt":
        for hint in _WINDOWS_HINTS:
            found.append(os.path.join(hint, exe))
    return found


def find_ffmpeg() -> str:
    for path in _candidates("ffmpeg"):
        if path and os.path.isfile(path):
            return path
    raise FfmpegMissing(
        "找不到 ffmpeg。请先安装：\n"
        "  Windows:  winget install Gyan.FFmpeg\n"
        "  macOS:    brew install ffmpeg\n"
        "  Ubuntu:   sudo apt install ffmpeg\n"
        "装好后重开终端；也可以设置 VIDEOMIX_FFMPEG_DIR 指向 bin 目录，"
        "或把 ffmpeg 放进 tools/ffmpeg/bin/。"
    )


def find_ffprobe() -> str | None:
    for path in _candidates("ffprobe"):
        if path and os.path.isfile(path):
            return path
    return None


def run(args: list[str], cwd: str | None = None) -> None:
    """执行 ffmpeg 命令，失败时抛出带输出的异常。"""
    proc = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-12:]
        raise RuntimeError(
            "ffmpeg 执行失败：\n  " + " ".join(args) + "\n" + "\n".join(tail)
        )


def probe_duration(ffprobe: str | None, path: str) -> float:
    """读取媒体时长（秒），失败返回 0。"""
    if not ffprobe:
        return 0.0
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float((proc.stdout or "").strip())
    except ValueError:
        return 0.0


def log(message: str) -> None:
    print(f"[videomix] {message}", flush=True)
    sys.stdout.flush()

