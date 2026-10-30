> **已停止维护（2026-10-30）**：本轻量版仅保留历史源码，不再发布新版本。请使用 [混剪桌面版](https://github.com/liying-main/liying-videomix)。后续产品维护集中在两款桌面版。

<div align="center">

<img src="web/logo.png" width="96" alt="厉影AI" />

# 厉影AI 混剪 · 免费开源工具

本地素材 → 分镜 → 裁切拼接 → 字幕 → MP4；可选云端写稿与配音。

</div>

软件按 MIT 许可免费使用、修改和分发。**纯本地模式无需注册或 API Key**，使用已有分镜或内置文案模板，通过 ffmpeg 完成混剪。

## 安装与首次使用

需要 Python 3.10+ 和带 `libx264`、`libass` 支持的 ffmpeg；Python 部分仅用标准库，无需 `pip install`。

```powershell
# Windows 安装 ffmpeg；也可使用你已安装的版本
winget install Gyan.FFmpeg
```

安装后重新打开终端，确认 `ffmpeg -version` 和 `ffprobe -version` 可用。macOS 可用 `brew install ffmpeg`，Ubuntu 可用 `sudo apt install ffmpeg`。也可将 `VIDEOMIX_FFMPEG_DIR` 指向含 ffmpeg/ffprobe 的目录。

```powershell
cd videomix-open
python -m videomix --web
```

本机页面为 `http://127.0.0.1:8756`。默认纯本地模式，输入主题与素材目录，点击生成。路径是本机文件路径。无素材时输出演示用渐变占位画面，放入自己的图片/视频即可替换。

## 命令行用法

```powershell
# 无 Key、无云端请求：已有脚本 + 本地素材
python -m videomix --local --script-file .\examples\local-script.json --assets .\assets

# 按主题填充本地模板
python -m videomix --local --topic "我的周末记录" --assets .\assets

# 批量生成，自定义输出目录
python -m videomix --local --topic "我的周末记录" --count 3 --out .\my-output

# Web 使用指定素材与输出目录
python -m videomix --web --assets .\assets --out .\my-output
```

结果默认写入 `output/`，中间分镜、片段与字幕保留在 `output/.work/`。同名成片与相同序号的工作文件会被后续任务覆盖，需保留的结果请先移走。没有配音或背景音乐时输出无声视频。

已有脚本也可配合 `--no-tts` 离线运行；`--local` 明确禁用所有云端功能，即使配置了 Key 或参考音频也不会调用。

## 可选云端写稿与配音

在 Web 切换到云端模式，展开配置，填写对应服务的地址与 Key。默认连接的 [OpenAPI](https://api.openapi.cn) 是本项目维护团队提供的可选云端服务，可前往站点获取 Key，也可换成其他兼容服务。

**软件免费不代表云端调用免费**：写稿、配音按所选服务的实时价格、额度和规则执行；如有体验额度，以服务端公布为准，项目不承诺赠送额度。

```powershell
$env:VIDEOMIX_API_KEY="你的服务Key"
python -m videomix --topic "秋季通勤穿搭" --assets .\assets

# 增加云端配音；参考音频用于克隆音色
python -m videomix --topic "秋季通勤穿搭" --assets .\assets --voice-ref .\assets\ref.wav

# 可选本地背景音乐，取目录中第一条音频
python -m videomix --local --script-file .\examples\local-script.json --bgm-dir .\bgm
```

`python -m videomix --check` 会真实调用云端写稿，可能消耗额度，不属于离线检查。缺 Key 时云端模式会提示配置；云端写稿失败时会提示原因并退回本地模板。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `VIDEOMIX_BASE_URL` | `https://api.openapi.cn/v1` | 可替换服务地址 |
| `VIDEOMIX_API_KEY` | 空 | 仅云端功能需要 |
| `VIDEOMIX_CHAT_MODEL` | `deepseek-v4.1-flash` | 写稿模型 |
| `VIDEOMIX_TTS_MODEL` | `indextts2-v1` | 配音模型 |
| `VIDEOMIX_FFMPEG_DIR` | 自动查找 | ffmpeg/ffprobe 所在目录 |

CLI 可用 `--base-url`，Web 可直接改地址；模型名从环境变量读取，更换后重新启动。写稿需要 `/chat/completions`，配音需要支持参考音频参数的 `/audio/speech`，详细协议见 [videomix/station.py](videomix/station.py)。聊天兼容不保证配音也兼容。

## 当前能力边界

- 素材按文件名关键词匹配，未匹配时轮流取用；不分析画面语义，也不联网下载素材。
- 本地模板不是 AI 写稿，可编辑 [examples/local-script.json](examples/local-script.json) 自定义标题、分镜文案与时长。
- 字幕时间来自分镜时长，没有语音强制对齐。输入视频短于分镜时长时字幕可能偏移，建议使用足够长的素材。画面统一裁切，原视频音轨不保留。
- 批量模式在使用同一脚本时会重复相同分镜；未实现自动去重和随机变体。
- 中文字幕需安装可用中文字体；无素材的文字占位画面还需要 ffmpeg 的 `drawtext` 支持。

## Key 与素材

纯本地模式不发送素材到云端。云端写稿发送主题，配音发送文案与参考音频；本地混剪素材不会自动上传。请使用有权处理的素材与声音。

Key 不保存在项目或浏览器存储中，未加入遥测；配置接口只返回是否已配置。Web 更换地址后须填写对应服务的 Key。建议使用终端环境变量，避免把 Key 放进共享脚本或 Git。Web 仅监听本机 `127.0.0.1`，请勿将端口直接暴露到公网。

## 开发验证

```powershell
python -m unittest discover -s tests -v
```

测试不调用收费 API。许可见 [LICENSE](LICENSE)。

## 相关开源项目

- [数字人桌面版 / 口播智能体](https://github.com/liying-main/liying_ai)
- [混剪桌面版](https://github.com/liying-main/liying-videomix)
