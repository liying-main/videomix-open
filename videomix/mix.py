"""混剪管线：素材归一化 → 拼接 → 字幕 → 音轨 → 导出。"""

from __future__ import annotations

import os
import re
import shutil

from . import config
from .ffmpeg_tools import find_ffmpeg, find_ffprobe, log, probe_duration, run
from .script_gen import generate_script, save_script
from .station import StationClient, StationError
from .subtitle import segments_from_shots, write_ass, write_srt

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

_CJK_FONT_HINTS = [
    r"C:/Windows/Fonts/msyh.ttc",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def find_cjk_font() -> str | None:
    for path in _CJK_FONT_HINTS:
        if os.path.isfile(path):
            return path
    return None


def collect_assets(assets_dir: str) -> list[str]:
    """收集素材，按文件名排序。"""
    if not assets_dir or not os.path.isdir(assets_dir):
        return []
    items = []
    for name in sorted(os.listdir(assets_dir)):
        path = os.path.join(assets_dir, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in (VIDEO_EXT | IMAGE_EXT):
            items.append(path)
    return items


def find_bgm(bgm_dir: str | None) -> str | None:
    if not bgm_dir or not os.path.isdir(bgm_dir):
        return None
    for name in sorted(os.listdir(bgm_dir)):
        if os.path.splitext(name)[1].lower() in AUDIO_EXT:
            return os.path.join(bgm_dir, name)
    return None


def pick_asset(assets: list[str], shot: dict, index: int) -> str | None:
    """按关键词挑素材，挑不到就轮流用。"""
    if not assets:
        return None
    keywords = [k.lower() for k in shot.get("keywords") or [] if k]
    for keyword in keywords:
        for path in assets:
            if keyword and keyword in os.path.basename(path).lower():
                return path
    return assets[index % len(assets)]


def _normalize_filter(width: int, height: int, fps: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},setsar=1"
    )


def make_clip(ffmpeg: str, ffprobe: str | None, src: str | None, name: str,
              seconds: float, shot: dict, index: int, workdir: str,
              width: int, height: int, fps: int) -> str:
    """把一段素材（或占位画面）归一化成统一规格的片段。"""
    target = os.path.join(workdir, name)
    vf = _normalize_filter(width, height, fps)
    # ffmpeg 以 workdir 为工作目录运行，输入素材必须用绝对路径
    src_abs = os.path.abspath(src).replace("\\", "/") if src else None

    if src_abs and os.path.splitext(src_abs)[1].lower() in IMAGE_EXT:
        run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
             "-loop", "1", "-t", f"{seconds:.2f}", "-i", src_abs,
             "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-pix_fmt", "yuv420p", name], cwd=workdir)
        return name

    if src_abs:
        duration = probe_duration(ffprobe, src_abs)
        take = seconds if duration <= 0 else min(seconds, max(1.0, duration))
        run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
             "-i", src_abs, "-t", f"{take:.2f}",
             "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-pix_fmt", "yuv420p", name], cwd=workdir)
        return name

    # 没有素材：生成一段带字幕文字的占位画面，保证流程可跑通
    text = (shot.get("subtitle") or shot.get("voiceover") or f"镜头 {index + 1}").strip()
    text = re.sub(r"[:'\\%]", " ", text)[:24]
    font = find_cjk_font()
    drawtext = ""
    if font:
        escaped = font.replace(":", "\\:")
        drawtext = (
            f",drawtext=fontfile='{escaped}':text='{text}':fontcolor=white:fontsize=64:"
            f"x=(w-text_w)/2:y=220:box=1:boxcolor=black@0.35:boxborderw=24"
        )
    run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i",
         f"gradients=s={width}x{height}:d={seconds:.2f}:c0=0x1f2937:c1=0x4b5563",
         "-vf", vf + drawtext, "-an", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-pix_fmt", "yuv420p", "-t", f"{seconds:.2f}", name],
        cwd=workdir)
    return name


def concat_clips(ffmpeg: str, names: list[str], out_name: str, workdir: str) -> str:
    with open(os.path.join(workdir, "concat.txt"), "w", encoding="utf-8") as handle:
        for name in names:
            handle.write(f"file '{name}'\n")
    run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", "concat.txt",
         "-c", "copy", out_name], cwd=workdir)
    return out_name


def burn_subtitles(ffmpeg: str, src_name: str, srt_name: str, out_name: str,
                   workdir: str) -> str:
    vf = f"ass={srt_name}"
    run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-i", src_name, "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", out_name], cwd=workdir)
    return out_name


def mux_audio(ffmpeg: str, video_name: str, out_name: str, workdir: str,
              voiceover: str | None = None, bgm: str | None = None) -> str:
    args = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", video_name]
    if voiceover:
        args += ["-i", voiceover]
    if bgm:
        args += ["-i", bgm]

    if voiceover and bgm:
        graph = ("[1:a]volume=1.0[vo];[2:a]volume=0.16[bg];"
                 "[vo][bg]amix=inputs=2:duration=first:dropout_transition=2[a]")
        args += ["-filter_complex", graph, "-map", "0:v", "-map", "[a]"]
    elif voiceover:
        args += ["-map", "0:v", "-map", "1:a"]
    elif bgm:
        args += ["-filter_complex", "[1:a]volume=0.3[a]", "-map", "0:v", "-map", "[a]"]
    else:
        shutil.copyfile(os.path.join(workdir, video_name),
                        os.path.join(workdir, out_name))
        return out_name

    args += ["-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out_name]
    run(args, cwd=workdir)
    return out_name


def build_video(client: StationClient | None, topic: str, assets: list[str], out_dir: str,
                index: int, shots: int = 4, voice_ref: str | None = None,
                bgm: str | None = None, width: int = config.DEFAULT_WIDTH,
                height: int = config.DEFAULT_HEIGHT, fps: int = config.DEFAULT_FPS,
                script: dict | None = None, use_tts: bool = True) -> dict:
    """产出一条成片，返回结果信息。"""
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()
    workdir = os.path.join(out_dir, ".work", f"v{index + 1}")
    os.makedirs(workdir, exist_ok=True)

    if script is None:
        log(f"生成脚本（{index + 1}）…")
        if client is None:
            from .script_gen import template_script
            script = template_script(topic, shots)
            log("使用本地模板；可通过 --script-file 提供自己的分镜文案")
        else:
            script = generate_script(client, topic, shots=shots)
    save_script(script, os.path.join(workdir, "script.json"))

    shot_list = script.get("shots") or []
    log(f"共 {len(shot_list)} 个镜头，开始归一化素材")
    clip_names = []
    for position, shot in enumerate(shot_list):
        source = pick_asset(assets, shot, position)
        name = f"clip{position:02d}.mp4"
        make_clip(ffmpeg, ffprobe, source, name, float(shot.get("seconds") or 4),
                  shot, position, workdir, width, height, fps)
        clip_names.append(name)
    if not clip_names:
        raise RuntimeError("脚本里没有可用镜头")

    log("拼接片段")
    concat_clips(ffmpeg, clip_names, "merged.mp4", workdir)

    log("烧录字幕")
    segments = segments_from_shots(shot_list)
    write_srt(segments, os.path.join(workdir, "sub.srt"))
    write_ass(segments, os.path.join(workdir, "sub.ass"), width=width, height=height)
    burn_subtitles(ffmpeg, "merged.mp4", "sub.ass", "subbed.mp4", workdir)

    voiceover_name = None
    if use_tts and voice_ref:
        if client is None:
            raise StationError("云端配音需要配置服务地址与 API Key")
        text = " ".join(s.get("voiceover", "") for s in shot_list).strip()
        if text:
            log("生成配音（indextts2-v1）")
            audio = client.tts(text, voice_ref)
            voiceover_name = "voice.mp3"
            with open(os.path.join(workdir, voiceover_name), "wb") as handle:
                handle.write(audio)

    log("合成音轨")
    final_name = mux_audio(ffmpeg, "subbed.mp4", "final.mp4", workdir,
                           voiceover=voiceover_name, bgm=bgm)

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", script.get("title") or topic)[:40]
    output = os.path.join(out_dir, f"{index + 1:02d}_{safe_title}.mp4")
    shutil.copyfile(os.path.join(workdir, final_name), output)
    log(f"完成：{output}")
    return {
        "output": output,
        "title": script.get("title"),
        "hashtags": script.get("hashtags") or [],
        "shots": len(shot_list),
    }


def run_batch(topic: str, assets_dir: str, out_dir: str, count: int = 1,
              shots: int = 4, voice_ref: str | None = None,
              bgm_dir: str | None = None, script_file: str | None = None,
              api_key: str | None = None, base_url: str | None = None,
              width: int = config.DEFAULT_WIDTH, height: int = config.DEFAULT_HEIGHT,
              fps: int = config.DEFAULT_FPS, use_tts: bool = True,
              on_progress=None, local_only: bool = False) -> list[dict]:
    """批量出片入口，CLI 与 Web 界面共用。"""
    os.makedirs(out_dir, exist_ok=True)
    assets = collect_assets(assets_dir)
    if assets:
        log(f"素材目录 {assets_dir}，共 {len(assets)} 个素材")
    else:
        log("素材目录为空，将生成占位画面（把视频或图片放进 assets/ 即可替换）")

    bgm = find_bgm(bgm_dir)
    if bgm:
        bgm = os.path.abspath(bgm)
    fixed_script = None
    if script_file:
        from .script_gen import load_script
        fixed_script = load_script(script_file)

    if local_only:
        use_tts = False
    if use_tts and voice_ref and not os.path.isfile(voice_ref):
        raise StationError(f"参考音频不存在：{voice_ref}")
    needs_cloud = not local_only and (fixed_script is None or (use_tts and bool(voice_ref)))
    client = StationClient(base_url=base_url, api_key=api_key) if needs_cloud else None

    results = []
    for index in range(max(1, count)):
        result = build_video(
            client, topic, assets, out_dir, index, shots=shots,
            voice_ref=voice_ref, bgm=bgm, width=width, height=height, fps=fps,
            script=fixed_script, use_tts=use_tts,
        )
        results.append(result)
        if on_progress:
            on_progress(result, index + 1, max(1, count))
    return results
