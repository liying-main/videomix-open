"""用中转站的对话模型生成混剪脚本。"""

from __future__ import annotations

import json

from .station import StationClient, StationError

SYSTEM_PROMPT = """你是短视频混剪编导。根据用户给的主题，产出**一条**竖屏短视频的脚本。
只输出 JSON，不要任何解释文字。JSON 结构：
{
  "title": "视频标题，12 字以内",
  "hashtags": ["话题1", "话题2", "话题3"],
  "shots": [
    {"voiceover": "这一镜的口播文案，20-40 字", "subtitle": "屏幕上显示的字幕，10 字以内", "keywords": ["挑素材用的关键词"], "seconds": 4}
  ]
}
要求：shots 数量与用户要求一致；每镜 seconds 取 3-6 之间的整数；口播文案连起来通顺、有钩子、结尾有引导。"""


def template_script(topic: str, shots: int) -> dict:
    result = []
    for index in range(shots):
        result.append({
            "voiceover": f"第 {index + 1} 个镜头：{topic}，这里放一句吸引人的口播。",
            "subtitle": f"{topic} 看点{index + 1}",
            "keywords": [topic],
            "seconds": 4,
        })
    return {"title": topic[:12], "hashtags": [topic], "shots": result}


def generate_script(client: StationClient, topic: str, shots: int = 4,
                    variation: str = "") -> dict:
    """生成一条成片的脚本；模型不可用时退回本地模板，保证流程不中断。"""
    user = f"主题：{topic}\n请生成 {shots} 个镜头的脚本。"
    if variation:
        user += f"\n本次要求的角度：{variation}"
    try:
        data = client.chat_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0.95,
            max_tokens=1600,
        )
    except StationError as exc:
        print(f"[videomix] 生成脚本失败，改用本地模板：{exc}")
        return template_script(topic, shots)

    cleaned = []
    for shot in data.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        try:
            seconds = float(shot.get("seconds") or 4)
        except (TypeError, ValueError):
            seconds = 4.0
        cleaned.append({
            "voiceover": str(shot.get("voiceover") or "").strip(),
            "subtitle": str(shot.get("subtitle") or "").strip(),
            "keywords": [str(k) for k in (shot.get("keywords") or [])][:6],
            "seconds": min(8.0, max(2.0, seconds)),
        })
    if not cleaned:
        print("[videomix] 模型返回的 shots 为空，改用本地模板")
        return template_script(topic, shots)
    return {
        "title": str(data.get("title") or topic)[:24],
        "hashtags": [str(h) for h in (data.get("hashtags") or [])][:6],
        "shots": cleaned,
    }


def load_script(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_script(script: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(script, handle, ensure_ascii=False, indent=2)

