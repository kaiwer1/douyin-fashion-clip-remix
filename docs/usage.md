# 详细使用说明 / Detailed Usage Guide

## 素材准备 / Clip Preparation

1. 从直播回放中下载同一商品的 5~15 条切片，保存到同一目录
2. 文件名统一为 `clip01.mp4`、`clip02.mp4` 等
3. 推荐分辨率为 1080x1920（抖音竖屏高清标准）
4. 每条切片建议 30 秒 ~ 4 分钟

## 参数说明 / Parameters

### classify.py

```
python scripts/classify.py <video_paths...> [options]

参数:
  --interval INT    抽帧间隔秒数 (默认: 5)
  --output PATH     输出 JSON 路径 (默认: $CLIP_REMIX_TMP/segments.json)
```

### compose.py

```
python scripts/compose.py [segments.json] [options]

参数:
  --variants, -n INT   生成版本数 (默认: 4)
  --output PATH        输出 EDL JSON 路径 (默认: $CLIP_REMIX_TMP/edls.json)
  --clips-dir PATH     素材目录路径
```

### render.py

```
python scripts/render.py [edls.json] [options]

参数:
  --output, -o PATH   输出目录 (默认: $CLIP_REMIX_TMP/output/)
```

### run_pipeline.py

```
python scripts/run_pipeline.py [options]

参数:
  --clips-dir PATH    素材目录 (默认: /tmp/clips)
  --variants, -n INT  版本数 (默认: 4)
  --skip-classify     跳过分类步骤
  --skip-compose      跳过组合步骤
```

## 输出说明 / Output

每批素材生成 4 个版本:

| 文件 | 说明 |
|------|------|
| `output/v1.mp4` | 版本1 — 标准三段式（产品→穿搭→促单） |
| `output/v2.mp4` | 版本2 — 穿搭开头  |
| `output/v3.mp4` | 版本3 — 产品+促单先行 |
| `output/v4.mp4` | 版本4 — 四段式扩展 |

每个版本约 40~70 秒，1080x1920 分辨率，libx264 + AAC 编码。
