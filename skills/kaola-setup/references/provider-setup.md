# 服务注册入口

## MiniMax

把 [MiniMax 开放平台](https://platform.minimaxi.com/) 发给用户，说明注册或登录后，进入“接口密钥”创建 API Key 即可。

## GPT Image Two

把 [Grsai API 后台](https://grsai.com/zh/dashboard) 发给用户，说明注册或登录后创建 API Key 即可。

## 阿里云 OSS

1. 打开 [阿里云 OSS](https://www.aliyun.com/product/oss)，注册或登录阿里云，按平台要求完成必要的认证。
2. 开通 OSS 服务。
3. 在 [OSS 控制台](https://oss.console.aliyun.com/bucket) 创建 Bucket，记住 Bucket 名、地域和 Endpoint。
4. 在 [RAM 用户](https://ram.console.aliyun.com/users) 创建专用子用户，不要直接使用主账号 AccessKey。
5. 为 RAM 用户创建 AccessKey ID 和 AccessKey Secret，只授予目标 Bucket 所需的最小权限。
6. 告诉用户只在本机保存 AccessKey，不要发到对话或 GitHub。

如需对照官方步骤，打开 [OSS 控制台快速入门](https://help.aliyun.com/zh/oss/user-guide/console-quick-start/) 和 [RAM AccessKey 访问 OSS](https://help.aliyun.com/en/oss/developer-reference/use-the-accesskey-pair-of-a-ram-user-to-initiate-a-request)。

> 阿里云 OSS 与大秘 OSS 不是同一个服务。只有当前执行工具支持阿里云 OSS 时，上述凭据才能直接使用。
