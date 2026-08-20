---
name: kaola-setup
description: 引导用户注册并配置 Kaola 所需的 MiniMax、阿里云 OSS 和 Grsai GPT Image Two 账号与 API 凭据。用户说第一次配置、缺少 API Key 或 OSS、不知道去哪里注册，或输入 /kaola-setup、$kaola-setup 时使用。
---

# Kaola 首次配置

读取 [provider-setup.md](references/provider-setup.md)，根据用户缺少的服务给出对应入口。

## 执行规则

- MiniMax 和 GPT Image Two 只给注册或后台网址，告诉用户登录后创建 API Key，不展开长篇教程。
- GPT Image Two 统一引导到 Grsai 后台，对应 `gpt-image-2-vip` 兼容能力。
- 阿里云 OSS 需要引导用户完成账号、OSS 开通、Bucket、RAM 用户、AccessKey 和最小权限配置。
- 不要让用户把密钥粘贴到对话或 GitHub；只让用户在自己的本地环境中保存。
- 不代替用户充值、购买、实名认证或授予高权限。
