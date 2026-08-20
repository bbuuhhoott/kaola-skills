# 服务注册入口

## MiniMax

把 [MiniMax 开放平台](https://platform.minimaxi.com/) 发给用户，说明注册或登录后，进入“接口密钥”创建 API Key 即可。

## GPT Image Two（可选建议）

只在用户需要生成新的人脸参考图时，建议使用 GPT Image Two。把 [Grsai API 后台](https://grsai.com/zh/dashboard) 发给用户，说明注册或登录后创建 API Key 即可。用户不配置时，直接使用系统内置图片生成能力。

## 阿里云 OSS 半自动配置

1. 把 [阿里云 OSS](https://www.aliyun.com/product/oss) 发给用户。用户自行完成注册、登录、实名认证与需要的付费确认，然后回复“已登录”。
2. 用户已登录后，直接操作 [OSS 控制台](https://oss.console.aliyun.com/bucket)；不再让用户自己点完后续页面。
3. OSS 未开通时，可完成免费开通步骤；如出现付费、资源包或合同确认，停下交给用户。
4. 创建 Bucket：
   - 名称：`kaola-video-assets-唯一后缀`；
   - 地域：华东 1（杭州）；
   - 存储类型：标准存储；
   - 读写权限：私有；
   - 其他选项保持安全默认值。
5. 进入 [RAM 用户](https://ram.console.aliyun.com/users)，创建不启用控制台登录的专用用户 `kaola-oss-uploader`。
6. 为该 RAM 用户建立只作用于目标 Bucket 的最小权限策略，仅包含上传、读取、列出必要对象的权限；不授予 `AliyunOSSFullAccess`。
7. 打开该 RAM 用户的 AccessKey 创建页面，停在最终“创建 AccessKey”操作前，即时请求用户确认。
8. 用户确认后才创建 AccessKey。不在对话中显示完整 AccessKey ID 或 Secret；如要将凭据保存到本地配置，在写入前再说明具体文件位置并征得用户确认。
9. 完成后只回报 Bucket 名、地域、Endpoint、RAM 用户名和权限范围，不回报凭据值。

如需对照官方步骤，打开 [OSS 控制台快速入门](https://help.aliyun.com/zh/oss/user-guide/console-quick-start/) 和 [RAM AccessKey 访问 OSS](https://help.aliyun.com/en/oss/developer-reference/use-the-accesskey-pair-of-a-ram-user-to-initiate-a-request)。

> 阿里云 OSS 与大秘 OSS 不是同一个服务。创建阿里云凭据不代表现有大秘 OSS 上传器会自动改用阿里云；必须有对应的阿里云 OSS 适配器。
