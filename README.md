# Kaola Skills

Kaola 是一组面向短视频分析、复刻、电商带货分镜和产品卖点可视化的 Codex Skills。

## 包含内容

- `kaola`：根据当前视频任务路由到合适的子 Skill。
- `kaola-lapian`：对用户有权分析的视频进行抽帧、转写和结构化拉片。
- `kaola-daihuo`：把商品素材和已确认卖点整理为电商短视频分镜与提示词。
- `kaola-fuke`：保留原视频结构，仅替换指定人物、服装、商品或 Logo。
- `kaola-maidian`：把产品功能转化为可见的发布会式卖点演示。

## 安装

下载本仓库的 `kaola-skills.zip` 并解压，将其中 `skills/` 内各目录复制到你的 Codex 项目 `.agents/skills/` 目录；随后可在对话中使用 `$kaola` 或对应子 Skill 名称。

`kaola-lapian` 的本地处理脚本需要 FFmpeg、FFprobe 和 Pillow。若要使用 SenseVoice 转写，请在你自己的 Python 环境中安装 `funasr`、`torch` 与 `torchaudio`，并按服务自身要求准备模型。

## 凭据与隐私

本仓库不包含、不会要求提交、也不读取任何作者密钥。涉及图像或视频生成的能力，均由使用者自行在其环境中配置账户和凭据。请不要提交 `.env`、密钥文件、模型缓存、生成素材、转写结果或受版权保护的视频。

## 使用边界

只分析、下载、复刻或发布你拥有相应权利的视频、人物肖像、品牌和商品素材。第三方平台内容的分析不等于获得复刻、商业使用或再发布授权。

## 开源许可

本项目采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans)（署名—非商业性使用 4.0 国际）许可。

- 非商业使用、学习、研究和修改均可；
- 公开分享原作或衍生作品时，请保留来源、许可证链接，并标注修改；
- 商业使用需先取得版权所有者的单独授权。
