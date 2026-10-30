"""中转站客户端（只用标准库）。

覆盖四个端点：
  POST /v1/chat/completions      文案与分镜
  POST /v1/audio/speech          文字转语音
  POST /v1/audio/transcriptions  音频转文本
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
import uuid

from . import config


class StationError(RuntimeError):
    """中转站返回的错误，携带 HTTP 状态码与原始响应。"""

    def __init__(self, message: str, status: int = 0, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class StationClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 timeout: float = 180.0) -> None:
        self.base_url = (base_url or config.base_url()).rstrip("/")
        self.api_key = (api_key or config.api_key()).strip()
        self.timeout = timeout
        if not self.api_key:
            raise StationError(
                "缺少 API Key。请设置环境变量 VIDEOMIX_API_KEY，"
                f"或在 {config.STATION_HOME} 创建令牌。"
            )

    # ------------------------------------------------------------- 基础请求
    def _request(self, path: str, data: bytes | None = None,
                 headers: dict | None = None, method: str | None = None,
                 raw: bool = False):
        req_headers = {"Authorization": "Bearer " + self.api_key}
        if headers:
            req_headers.update(headers)
        request = urllib.request.Request(
            self.base_url + path, data=data, headers=req_headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                payload = resp.read()
                return payload if raw else json.loads(payload.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if self.api_key:
                body = body.replace(self.api_key, "[REDACTED]")
            raise StationError(self._explain(exc.code, body), exc.code, body) from None
        except urllib.error.URLError as exc:
            raise StationError(f"无法连接 {self.base_url}：{exc.reason}") from None

    @staticmethod
    def _explain(status: int, body: str) -> str:
        detail = body[:400]
        if status == 503 and "No available channel" in body:
            return (f"底座返回 503：当前令牌分组没有该模型的可用渠道。"
                    f"请在 {config.STATION_HOME} 确认令牌分组包含该模型。原始响应：{detail}")
        if status == 401:
            return f"底座返回 401：API Key 无效或已过期。原始响应：{detail}"
        if status == 402 or "insufficient" in body.lower():
            return f"底座返回 {status}：额度不足，请充值。原始响应：{detail}"
        return f"底座返回 {status}：{detail}"

    # ----------------------------------------------------------------- 对话
    def chat(self, messages: list[dict], model: str | None = None,
             temperature: float = 0.8, max_tokens: int = 2048,
             json_object: bool = False) -> str:
        payload: dict = {
            "model": model or config.chat_model(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_object:
            payload["response_format"] = {"type": "json_object"}
        data = json.dumps(payload).encode("utf-8")
        result = self._request(
            "/chat/completions", data, {"Content-Type": "application/json"}
        )
        try:
            return result["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise StationError(f"无法解析模型响应：{str(result)[:400]}") from None

    def chat_json(self, messages: list[dict], **kwargs) -> dict:
        text = self.chat(messages, json_object=True, **kwargs)
        return extract_json(text)

    # ----------------------------------------------------------------- 语音
    def tts(self, text: str, voice: str, model: str | None = None,
            response_format: str = "mp3", speed: float = 1.0) -> bytes:
        """文字转语音，返回音频二进制。voice 支持本地路径、URL 或 data URI。"""
        if not text.strip():
            raise StationError("TTS 文本为空")
        payload = {
            "model": model or config.tts_model(),
            "input": text,
            "voice": normalize_voice(voice),
            "response_format": response_format,
            "speed": speed,
        }
        data = json.dumps(payload).encode("utf-8")
        return self._request(
            "/audio/speech", data, {"Content-Type": "application/json"}, raw=True
        )

    def asr(self, audio_path: str, model: str | None = None,
            language: str = "zh", response_format: str = "json") -> dict:
        """音频转文本。"""
        if not os.path.isfile(audio_path):
            raise StationError(f"音频文件不存在：{audio_path}")
        fields = {
            "model": model or config.asr_model(),
            "language": language,
            "response_format": response_format,
        }
        body, headers = encode_multipart(fields, {"file": audio_path})
        return self._request("/audio/transcriptions", body, headers)


# --------------------------------------------------------------- 辅助函数
def normalize_voice(voice: str) -> str:
    """把本地参考音频转成 data URI；URL 原样返回。"""
    voice = (voice or "").strip()
    if not voice:
        raise StationError("缺少音色参考音频。设置 VIDEOMIX_TTS_VOICE 或传入 --voice-ref")
    if voice.startswith(("http://", "https://", "data:")):
        return voice
    if not os.path.isfile(voice):
        raise StationError(f"参考音频不存在：{voice}")
    ctype = mimetypes.guess_type(voice)[0] or "audio/wav"
    with open(voice, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    return f"data:{ctype};base64,{encoded}"


def encode_multipart(fields: dict, files: dict) -> tuple[bytes, dict]:
    boundary = "----videomix" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode("utf-8")
        )
    for name, path in files.items():
        filename = os.path.basename(path)
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'.encode("utf-8")
        )
        with open(path, "rb") as handle:
            chunks.append(handle.read())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }


def extract_json(text: str) -> dict:
    """从模型回复里取出 JSON（容忍 fenced code block 与前后解释）。"""
    text = (text or "").strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith(fence):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise StationError(f"模型没有返回合法 JSON：{text[:300]}")
