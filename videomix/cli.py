"""命令行入口：python -m videomix --topic "主题" """

from __future__ import annotations

import argparse
import sys

from . import config
from .mix import run_batch
from .station import StationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="videomix",
        description=f"{config.BRAND_PRODUCT} 免费开源工具",
    )
    parser.add_argument("--topic", "-t", default="", help="视频主题，例如：秋季通勤穿搭")
    parser.add_argument("--script-file", default="", help="已有脚本 JSON，跳过模型写稿")
    parser.add_argument("--assets", default="assets", help="素材目录（默认 assets）")
    parser.add_argument("--out", default="output", help="输出目录（默认 output）")
    parser.add_argument("--count", type=int, default=1, help="生成几条成片")
    parser.add_argument("--shots", type=int, default=4, help="每条成片几个镜头")
    parser.add_argument("--voice-ref", default="", help="配音参考音频（3-10 秒人声）")
    parser.add_argument("--bgm-dir", default="bgm", help="背景音乐目录")
    parser.add_argument("--no-tts", action="store_true", help="不生成配音")
    parser.add_argument("--local", action="store_true", help="纯本地混剪，不联网、不需要 Key；使用自备脚本或本地模板")
    parser.add_argument("--width", type=int, default=config.DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=config.DEFAULT_HEIGHT)
    parser.add_argument("--fps", type=int, default=config.DEFAULT_FPS)
    parser.add_argument("--api-key", default="", help="覆盖 VIDEOMIX_API_KEY")
    parser.add_argument("--base-url", default="", help="覆盖所选服务地址")
    parser.add_argument("--web", action="store_true", help="启动本地 Web 界面")
    parser.add_argument("--port", type=int, default=8756, help="Web 界面端口")
    parser.add_argument("--check", action="store_true", help="发起一次云端模型请求验证 Key，可能消耗服务端额度")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.web:
        from .web import serve
        serve(port=args.port, assets_dir=args.assets, out_dir=args.out,
              base_url=args.base_url or None, api_key=args.api_key or None)
        return 0

    if args.check:
        from .station import StationClient
        print(f"{config.BRAND_PRODUCT} 免费开源工具")
        print(f"服务地址：{args.base_url or config.base_url()}")
        print(f"文案模型：{config.chat_model()}｜配音模型：{config.tts_model()}")
        try:
            client = StationClient(base_url=args.base_url or None,
                                   api_key=args.api_key or None)
            reply = client.chat(
                [{"role": "user", "content": "回复两个字：正常"}], max_tokens=16
            )
            print(f"对话接口：可用（模型回复：{reply.strip()[:20]}）")
        except StationError as exc:
            print(f"对话接口：不可用 —— {exc}")
            return 1
        return 0

    if not args.topic and not args.script_file:
        print("请提供 --topic 或 --script-file（或加 --web 打开图形界面）")
        return 2

    voice_ref = args.voice_ref or config.tts_voice()
    print(f"{config.BRAND_PRODUCT} 免费开源工具")
    print("云端功能按所选服务的额度和规则执行。\n")
    try:
        results = run_batch(
            topic=args.topic or "未命名主题",
            assets_dir=args.assets,
            out_dir=args.out,
            count=args.count,
            shots=args.shots,
            voice_ref=voice_ref or None,
            bgm_dir=args.bgm_dir,
            script_file=args.script_file or None,
            api_key=args.api_key or None,
            base_url=args.base_url or None,
            width=args.width,
            height=args.height,
            fps=args.fps,
            use_tts=not args.no_tts,
            local_only=args.local,
        )
    except StationError as exc:
        print(f"\n[错误] {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI 需要把任何失败讲清楚
        print(f"\n[错误] {exc}")
        return 1

    print("\n产出：")
    for item in results:
        print(f"  {item['output']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
