# 本次离线验证记录

验证日期：2026-10-30。

在项目根目录执行：

```powershell
python -m unittest discover -s tests -v
git diff --check
```

- Python：9 项通过。覆盖纯本地不创建云端客户端、固定脚本无配音免 Key、云端缺 Key 错误、本机 Web 的跨站限制、配置不回传 Key、自定义服务和输出目录、任务互斥。
- Web 内嵌 JavaScript 通过 `node --check`；Git 空白检查通过。
- 真实 ffmpeg 离线烟测：用 `examples/local-script.json`、空素材目录、`local_only=True`、320×568、12 fps 执行 `run_batch`，得到 6 秒 H.264 MP4（46,701 字节）。执行时将 `urllib.request.urlopen` 替换为立即失败，确保不调用云端；`ffprobe` 确认成片参数。ffmpeg 来自本机已有安装，不随源码分发。

没有调用收费 API。测试使用临时目录，成片和中间文件已移除。本文件记录结果，未保存含用户数据的原始日志。云端兼容性及不同系统的字体、ffmpeg 构建仍需各自验证。
