# API Key 配置指南 / API Setup Guide

本项目使用 **火山引擎方舟平台** 的 Doubao 视觉模型进行帧分类。

## 注册与获取 API Key / Registration

### 步骤 1: 注册火山引擎

访问 [火山引擎官网](https://www.volcengine.com/) 注册账号。

### 步骤 2: 进入方舟平台

1. 登录后进入 [方舟控制台](https://console.volcengine.com/ark/)
2. 首次使用需开通服务
3. 进入「模型推理」→「在线推理」

### 步骤 3: 创建 API Key

1. 左侧菜单选择「API Key 管理」
2. 点击「创建 API Key」
3. 复制生成的 key（格式类似 `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）

### 步骤 4: 配置环境变量

```bash
# 推荐写入 shell 配置文件 (~/.bashrc 或 ~/.zshrc)
export DOUBAO_API_KEY="your-api-key-here"
export DOUBAO_MODEL="doubao-seed-1-6-vision-250815"
```

## 可选替代：小米 MiMo API

本项目也支持使用 **小米 MiMo-V2.5** 视觉模型替代豆包。

### 获取 MiMo API Key

1. 访问 [小米 MiMo 开放平台](https://platform.xiaomimimo.com/)
2. 注册账号并登录
3. 进入「API Key 管理」创建 Key
4. **推荐使用专用 Token Plan**（延迟更低、频率限制更宽松）

### 配置

```bash
# 通用 Key
export MIMO_API_KEY="sk-xxxxxxxx"
export MIMO_BASE_URL="https://api.xiaomimimo.com/v1"

# 或使用专属 Token Plan（推荐）
export MIMO_API_KEY="tp-xxxxxxxx"
export MIMO_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"

export MIMO_MODEL="mimo-v2.5"
```

### 与豆包对比

| 特性 | 豆包 (Doubao) | MiMo-V2.5 |
|------|-------------|-----------|
| 响应速度 | 2-5秒/batch | 1-3秒/batch（专属Key更快） |
| 限流 | 17批后触发429 | 更宽松（专属Key几乎不限） |
| 准确率 | 良好 | 良好（对服装分类表现稳定） |

如果遇到 HTTP 429 `SetLimitExceeded` 错误：

1. 进入 [火山引擎控制台 > 模型开通](https://console.volcengine.com/ark/region:ark+cn-beijing/open)
2. 找到使用的模型
3. 关闭「安全体验模式」(Safe Experience Mode)
4. 重启程序

## 费用说明 / Pricing

豆包视觉模型按 token 计费。分类一条 3 分钟视频大约消耗 2000~4000 输入 token + 200~500 输出 token。
具体价格请参考 [火山引擎定价页面](https://www.volcengine.com/pricing)。

## 替换为其他 API / Using Other APIs

如果你不想用豆包，可以修改 `src/clip_remix/classifier.py` 中的 `classify_frames_batch` 方法，
替换成其他视觉 API（如 GPT-4V、Gemini、Claude Vision 等）。

接口规范：接收帧列表，返回 `[{timestamp, label, confidence}]` 格式。
