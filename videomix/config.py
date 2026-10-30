"""集中配置。

OpenAPI 为可选默认服务；地址、模型及凭据可由用户配置。
所有值都可以用环境变量覆盖。
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------- 默认服务
# 品牌
BRAND_NAME = "厉影AI"
BRAND_PRODUCT = "厉影AI 混剪"
BRAND_TAGLINE = "一句话主题，直接出片"

# 中转站站点主页，README 与 Web 界面上的"获取 Key"指向这里
STATION_HOME = "https://api.openapi.cn"

# OpenAI 兼容底座地址
DEFAULT_BASE_URL = "https://api.openapi.cn/v1"

# 中转站上的模型名
DEFAULT_CHAT_MODEL = "deepseek-v4.1-flash"
DEFAULT_TTS_MODEL = "indextts2-v1"
DEFAULT_ASR_MODEL = "whisper-large-v3-turbo"

# 输出规格
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 30
DEFAULT_CLIP_SECONDS = 4.0


def base_url() -> str:
    return os.environ.get("VIDEOMIX_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def brand_name() -> str:
    return os.environ.get("VIDEOMIX_BRAND", BRAND_NAME).strip()


def api_key() -> str:
    return (
        os.environ.get("VIDEOMIX_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()


def chat_model() -> str:
    return (os.environ.get("VIDEOMIX_CHAT_MODEL") or os.environ.get("VIDEOMIX_MODEL") or DEFAULT_CHAT_MODEL).strip()


def tts_model() -> str:
    return os.environ.get("VIDEOMIX_TTS_MODEL", DEFAULT_TTS_MODEL).strip()


def asr_model() -> str:
    return os.environ.get("VIDEOMIX_ASR_MODEL", DEFAULT_ASR_MODEL).strip()


def tts_voice() -> str:
    return os.environ.get("VIDEOMIX_TTS_VOICE", "").strip()
