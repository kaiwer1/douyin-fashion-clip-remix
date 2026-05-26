# 抖音带货短视频混剪 / Douyin E-commerce Clip Remix

自动分析直播切片素材 → 分类 → 重组 → 渲染为多个不同版本的短视频。
Automatically analyze live-stream clips → classify → compose → render into multiple short video variants.

**支持品类 / Supported Categories:**
- ✅ **女装/服饰** (Fashion) — 穿搭展示、产品特写、促单话术
- ✅ **零食食品** (Snacks) — 口感展示、产品特写、促单话术（通过类型映射）

Designed for Douyin (TikTok) live-commerce short video remixing.

---

## 目录 / Table of Contents

- [快速开始 / Quick Start](#快速开始--quick-start)
- [工作流程 / Workflow](#工作流程--workflow)
- [安装 / Installation](#安装--installation)
- [使用方法 / Usage](#使用方法--usage)
- [配置 / Configuration](#配置--configuration)
- [项目结构 / Project Structure](#项目结构--project-structure)
- [许可证 / License](#许可证--license)

---

## 快速开始 / Quick Start

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置 API Key（豆包视觉模型）
export DOUBAO_API_KEY="your-api-key-here"

# 3. 准备素材 — 把同一商品的直播切片放到素材目录
#    Prepare clips — put same-product live-stream clips in a directory
#    文件名格式: clip01.mp4, clip02.mp4, ...

# 4. 一键运行 / One-click pipeline
python scripts/run_pipeline.py --clips-dir /path/to/clips

# 成品在 /path/to/clips/output/ 目录下
# Output files in /path/to/clips/output/
```

---

## 工作流程 / Workflow

系统分为三步 / Three stages:

### 第一步 分类 (Classify)
每 5 秒抽帧 → 调用豆包视觉 API → 按帧分类为:
Frame extraction every 5 seconds → Doubao Vision API → classify each frame as:

**女装镜头类型 / Fashion Labels:**

|| 标签 / Label | 描述 / Description |
|-------------|-------------------|
| `product_shot` | 产品特写 — 面料/细节近距离展示 / Close-up product detail |
| `outfit_demo` | 穿搭展示 — 模特的全身/半身效果 / Model wearing the outfit |
| `sales_pitch` | 促单话术 — 主播面对镜头的推荐 / Host selling to camera |
| `transition` | 过渡画面 / Scene transition |
| `other` | 其他 / Other |

**零食镜头类型（通过类型映射） / Snacks Labels (via Type Mapping):**

零食混剪复用同一分类器，通过类型映射适配：

|| 服装标签 | 零食映射 | 描述 |
|----------|---------|------|
| `outfit_demo` | `taste_demo` | 口感展示 — 试吃、咀嚼、表情（核心镜头） |
| `product_shot` | `product_closeup` | 产品特写 — 包装、外观、质感 |
| `sales_pitch` | `sales_pitch` | 促单口播 — 价格对比、限时限量 |
| `transition` | `usage_scene` | 场景使用 — 追剧、办公、聚会 |

### 第二步 组合 (Compose)
三段式模板 / Three-act template:
1. **产品展示段** (product_shot) — 15~25秒
2. **穿搭展示段** (outfit_demo) — 15~25秒
3. **促单段** (sales_pitch) — 8~15秒

每组素材自动生成 4 个不同版本（不同随机种子确保多样性）。
Generates 4 variants per batch with different random seeds.

### 第三步 渲染 (Render)
FFmpeg 居中剪切 → EBU R128 音量归一化 → 拼接输出。
Center-crop to 720x1280 → EBU R128 loudness normalization → concat.

---

## 安装 / Installation

### 前置依赖 / Prerequisites

| 软件 / Software | 说明 / Notes |
|---------------|-------------|
| Python 3.8+ | |
| FFmpeg | 需要 ffmpeg 和 ffprobe 在 PATH 中。下载: https://ffmpeg.org/download.html |
| 豆包 API Key | **需要自己申请。** 详见下文。|

### 豆包 API Key 申请 / Getting Doubao API Key

1. 前往 **火山引擎控制台** → **方舟平台** [console.volcengine.com/ark/](https://console.volcengine.com/ark/)
2. 登录后进入「模型推理」→「API Key 管理」
3. 创建 API Key
4. 设置到环境变量:

```bash
export DOUBAO_API_KEY="your-api-key-here"
```

也可以在 `.env` 文件中设置（需自行加载，本项目不附带 dotenv 依赖）。

### 安装

```bash
git clone https://github.com/YOUR-ORG/douyin-fashion-clip-remix.git
cd douyin-fashion-clip-remix
pip install -r requirements.txt
```

---

## 使用方法 / Usage

### 一键流水线 / One-Click Pipeline

```bash
python scripts/run_pipeline.py --clips-dir /path/to/clips
```

素材目录要求 / Requirements for clips directory:
- 文件命名: `clip01.mp4`, `clip02.mp4`, ...（固定前缀）
- 建议 5~15 条同一商品的直播切片
- MP4 格式

### 分步执行 / Step by Step

```bash
# 分类 / Classify
python scripts/classify.py /path/to/clips/clip*.mp4 --output segments.json

# 组合 / Compose
python scripts/compose.py segments.json --variants 4 --output edls.json

# 渲染 / Render
python scripts/render.py edls.json --output ./output/
```

---

## 配置 / Configuration

所有配置通过环境变量设置 / All config via environment variables:

| 变量 / Variable | 默认值 / Default | 说明 / Description |
|----------------|-----------------|-------------------|
| `DOUBAO_API_KEY` | **(必须)** | 豆包视觉 API Key / Doubao Vision API Key |
| `DOUBAO_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | API 基础地址 |
| `DOUBAO_MODEL` | `doubao-seed-1-6-vision-250815` | 视觉模型名 |
| `FFMPEG_PATH` | `ffmpeg` | ffmpeg 可执行文件路径 |
| `FFPROBE_PATH` | `ffprobe` | ffprobe 可执行文件路径 |
| `CLIP_REMIX_TMP` | `/tmp/clip-remix` | 临时工作目录 |

---

## 项目结构 / Project Structure

```
douyin-fashion-clip-remix/
├── src/
│   └── clip_remix/
│       ├── __init__.py      # 包入口 / Package init
│       ├── models.py        # 数据模型 / Data models
│       ├── utils.py         # 工具函数 / Utilities
│       ├── classifier.py    # 分类模块 / Frame classification
│       ├── composer.py      # 组合模块 / Video composition
│       └── renderer.py      # 渲染模块 / FFmpeg rendering
├── scripts/
│   ├── classify.py          # 分类入口 / Classify CLI
│   ├── compose.py           # 组合入口 / Compose CLI
│   ├── render.py            # 渲染入口 / Render CLI
│   └── run_pipeline.py      # 一键流水线 / One-click pipeline
├── docs/
│   ├── usage.md             # 详细使用说明 / Detailed usage
│   ├── api-setup.md         # API 配置指南 / API setup guide
│   └── troubleshooting.md   # 常见问题排查 / Troubleshooting
├── data/
│   └── violation_words/
│       └── default.yaml     # 违规词库 / Prohibited words
├── tests/
│   └── __init__.py
├── requirements.txt
├── setup.py
├── LICENSE                  # GPL v3
└── README.md                # 本文件
```

---

## 已知限制 / Known Limitations

- 依赖豆包视觉 API，需要网络连接和 API Key
- 需要安装 FFmpeg（建议 5.0+ 版本）
- 不包含字幕/OCR/片头片尾
- 每批素材建议 5~15 条切片
- API 有调用频率限制（约 17 批/5 分钟后触发 429）

---

## 许可证 / License

GNU General Public License v3.0 - 详见 [LICENSE](LICENSE) 文件。

这意味着：您可以自由使用、修改和分发本软件。如果您对本软件做了改进并对外发布，必须开源您的修改。
This means: you are free to use, modify, and distribute this software. If you publish modified versions, you must also open-source your changes.
