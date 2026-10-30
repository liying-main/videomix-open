"""字幕生成：SRT（通用）+ ASS（烧录，尺寸精确可控）。"""

from __future__ import annotations


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, rest = divmod(milliseconds, 3600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{int(hours)}:{int(minutes):02d}:{secs:05.2f}"


def wrap(text: str, width: int = 12) -> str:
    """按字符数折行，中文短视频字幕一般每行 10-14 字。"""
    text = (text or "").strip()
    if len(text) <= width:
        return text
    lines = [text[i:i + width] for i in range(0, len(text), width)]
    return "\n".join(lines[:3])


def write_srt(segments: list[dict], path: str, width: int = 12) -> str:
    """segments: [{"start": 0.0, "end": 4.0, "text": "..."}]"""
    blocks = []
    for index, segment in enumerate(segments, start=1):
        text = wrap(segment.get("text", ""), width)
        if not text:
            continue
        blocks.append(
            f"{index}\n"
            f"{_srt_time(segment['start'])} --> {_srt_time(segment['end'])}\n"
            f"{text}\n"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(blocks))
    return path


def write_ass(segments: list[dict], path: str, width: int = 1080,
              height: int = 1920, font: str = "Microsoft YaHei",
              font_size: int = 68, margin_v: int = 240,
              chars_per_line: int = 12) -> str:
    """生成 ASS 字幕。

    显式写 PlayResX/PlayResY，字号与边距按成片分辨率计算，
    避免 libass 用默认分辨率导致字号和位置失控。
    """
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},&H00FFFFFF,&H00FFFFFF,&H00202020,&H80000000,0,0,0,0,100,100,0,0,1,4,1,2,90,90,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for segment in segments:
        text = wrap(segment.get("text", ""), chars_per_line)
        if not text:
            continue
        text = text.replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_ass_time(segment['start'])},{_ass_time(segment['end'])},"
            f"Default,,0,0,0,,{text}"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(header + "\n".join(lines) + "\n")
    return path


def segments_from_shots(shots: list[dict]) -> list[dict]:
    """按分镜时长累加，生成字幕时间轴。"""
    segments = []
    cursor = 0.0
    for shot in shots:
        seconds = float(shot.get("seconds") or 4)
        text = (shot.get("subtitle") or shot.get("voiceover") or "").strip()
        if text:
            segments.append({"start": cursor, "end": cursor + seconds, "text": text})
        cursor += seconds
    return segments

