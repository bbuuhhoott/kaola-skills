---
name: kaola-setup
description: 引导用户注册并配置 Kaola 所需的 MiniMax、阿里云 OSS，以及可选的 Grsai GPT Image Two 账号与 API 凭据。用户说第一次配置、缺少 API Key 或 OSS、不知道去哪里注册，或输入 /kaola-setup、$kaola-setup 时使用。
---

# Kaola 首次配置

读取 [provider-setup.md](references/provider-setup.md)，根据用户缺少的服务给出对应入口。

## 执行规则

- MiniMax 和 GPT Image Two 只给注册或后台网址，告诉用户登录后创建 API Key，不展开长篇教程。
- GPT Image Two 是用于生成新人脸参考图的可选建议，统一引导到 Grsai 后台。用户未配置时使用系统内置图片生成能力，不暂停任务。
- 阿里云 OSS 采用半自动流程：用户只负责注册、登录、实名认证和必要的付费确认；登录完成后，使用当前可用的浏览器操作能力创建私有 Bucket、RAM 专用用户和最小权限策略。
- 默认 Bucket 使用华东 1（杭州）、标准存储、私有读写，名称使用 `kaola-video-assets-唯一后缀`；RAM 用户使用 `kaola-oss-uploader`。用户已指定名称或地域时优先服从用户。
- 在最终点击创建 AccessKey 前必须即时说明“即将为 kaola-oss-uploader 创建长期访问凭据”并取得用户确认。未确认时停在最后一步，不创建凭据。
- 不要让用户把密钥粘贴到对话或 GitHub；只让用户在自己的本地环境中保存。
- 不代替用户充值、购买、实名认证或授予高权限。
