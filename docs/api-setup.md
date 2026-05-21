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

## 安全体验模式 / Safe Experience Mode

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
