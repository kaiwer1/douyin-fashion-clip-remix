# 常见问题排查 / Troubleshooting

## 分类阶段 / Classification Issues

### API 返回 429 错误

**原因**: 豆包 API 有调用频率限制（Safe Experience Mode 或 Burst Too Fast）。

**解决**:
1. 检查是否开启了安全体验模式 → 关闭（详见 [api-setup.md](api-setup.md)）
2. 系统已在 `classifier.py` 中内置指数退避重试（5s, 10s, 20s, 40s）
3. 如果持续 429，尝试分批处理（每次 2 个素材）

### 所有帧都标为 transition (confidence=0.3)

**原因**: 豆包 API 完全不可用（可能是额度耗尽或服务故障）。

**解决**: 检查 API Key 是否有效；检查火山引擎控制台是否有余额。

### JSON 解析失败

偶尔 API 返回的 JSON 格式不完整。系统会降级为 `transition` 标签，
可以正常处理，推荐的商品组合可能不够准确。

## 组合阶段 / Composition Issues

### 生成版本太少（少于 4 个）

素材数量不足或片段类型不全。建议：
- 确保素材包含产品特写、穿搭展示、促单话术三种类型
- 增加素材数量至 8 条以上

### 版本时长过短（不到 40 秒）

素材中可用片段太少。建议：
- 使用更长的切片（每条 1~2 分钟以上）
- 增加素材数量

## 渲染阶段 / Rendering Issues

### FFmpeg 找不到

确保 FFmpeg 已安装并在 PATH 中，或设置 `FFMPEG_PATH` 环境变量：
```bash
export FFMPEG_PATH="/usr/local/bin/ffmpeg"
export FFPROBE_PATH="/usr/local/bin/ffprobe"
```

### Windows 环境

如果使用 Windows：
1. 下载 FFmpeg 安装包，解压到 `C:\ffmpeg\`
2. 将 `C:\ffmpeg\bin` 加入系统 PATH
3. 或在运行前设置环境变量：`set FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe`

### 渲染失败或输出黑屏

检查素材文件是否正常播放。部分下载工具可能损坏视频文件。
