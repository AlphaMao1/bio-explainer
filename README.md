# Bio Explainer

Bio Explainer 是一个本地运行的生物科普图生成工具。输入一个物种名称后，它会调用文本模型先规划内容，再调用 GPT Image 生成整页科普图，支持形态、演化、生态位等不同视角，也支持点击图片局部继续生成更细的解释页。

这个项目默认采用 BYOK（Bring Your Own Key）模式：你自己填写模型 API Key，生成结果和配置都保存在本机。

## 适合谁用

- 想快速生成生物科普图、教学草稿、内容创意图的人。
- 希望保留本地缓存，避免同一张图反复生成的人。
- 愿意对生成内容做人工核验的人。

目前更建议从现代、常见、资料充分的物种开始尝试，例如雪豹、帝企鹅、蓝鲸、蜜蜂等。冷门小众物种，尤其是古生物，可能出现事实错误、图文不一致、形态混淆等问题。

## 功能

- 本地 FastAPI 服务和浏览器界面。
- 支持填写自己的文本模型 API Key 和图片模型 API Key。
- 文本模型使用 OpenAI 兼容的 Chat Completions 接口。
- 图片页面全部由 GPT Image 生成，不用代码拼图。
- 图片接口支持可选 Base URL；留空时使用 SDK 默认地址。
- 本地缓存已生成的图片、文字说明、物种资料和点击深入页。
- 设置面板里可以修改提示词。
- 仓库内带有少量演示图片素材，方便第一次打开时查看效果。

## 依赖环境

运行项目需要：

- Python 3.11 或更高版本。
- uv：Python 依赖管理工具，安装说明见 <https://docs.astral.sh/uv/>。
- 一个可用的文本模型 API Key。
- 一个可用的 GPT Image 图片生成 API Key。
- 一个现代浏览器，例如 Chrome、Edge、Safari。

Python 依赖已经写在 [pyproject.toml](pyproject.toml) 里，并由 [uv.lock](uv.lock) 锁定。主要依赖包括：

- FastAPI：本地 Web 服务。
- Uvicorn：启动服务。
- OpenAI Python SDK：调用文本和图片模型。
- Pillow：处理图片尺寸和格式。
- pytest、httpx：测试使用。

## 推荐用法：下载 Release

如果你不熟悉 Git，建议从 Release 下载压缩包：

1. 打开项目的 Releases 页面：<https://github.com/AlphaMao1/bio-explainer/releases>
2. 下载最新版本里的 `bio-explainer-*.zip`，或者下载 GitHub 自动生成的 Source code zip。
3. 解压到一个你能找到的位置，例如桌面或 D 盘某个文件夹。
4. 确认电脑已经安装 Python 3.11+ 和 uv。
5. Windows 用户可以双击 `start_windows.bat` 启动。
6. 启动成功后，在浏览器打开：<http://127.0.0.1:8000>

如果双击后窗口一闪而过，通常是没有安装 Python 或 uv。请先安装依赖环境，再重新启动。

## 源码安装

如果你会使用命令行，也可以直接从 GitHub 克隆：

```powershell
git clone https://github.com/AlphaMao1/bio-explainer.git
cd bio-explainer
uv sync
uv run uvicorn server.main:app --host 127.0.0.1 --port 8000
```

然后打开：

```text
http://127.0.0.1:8000
```

开发时可以加上 `--reload`：

```powershell
uv run uvicorn server.main:app --reload --host 127.0.0.1 --port 8000
```

## 首次配置

打开页面后，点击右上角设置按钮，填写：

- 文本模型 API Key。
- 文本模型 Base URL。
- 文本模型名称。
- 图片模型 API Key。
- 图片模型名称。
- 图片模型 Base URL，可选。
- 图片尺寸和质量。

图片模型 Base URL 留空时，会使用 OpenAI SDK 默认地址；如果你的服务部署要求自定义兼容接口地址，再填写对应 Base URL。

API Key 会保存在本地文件：

```text
server/config.local.json
```

这个文件已经被 `.gitignore` 忽略，不会被提交到 GitHub。接口返回配置时也会隐藏 API Key。

## 基本使用

1. 输入物种名称，例如 `雪豹`。
2. 等待第一页形态图生成。
3. 切换形态、演化、生态位等标签页。
4. 点击图片中的某个区域，可以生成更细的解释页。
5. 底部缩略图会显示已经生成过的页面，后续可以直接打开缓存。
6. 如果想调整画面风格或内容结构，可以在设置里编辑提示词。

GPT Image 生成速度可能较慢，尤其是高分辨率或高质量设置下。第一次生成通常最慢；命中本地缓存后会快很多。

## 本地缓存

生成后的页面会保存为一组图片和 JSON 文件：

```text
static/generated/{page_id}.png
static/generated/{page_id}.json
```

物种资料会保存在：

```text
static/species/{profile_id}.json
```

这些缓存的作用是：

- 已生成页面可以直接复用。
- 点击深入页不会每次都重新生成。
- 演示素材可以随项目一起展示。

如果你想清空自己的生成结果，可以删除 `static/generated` 和 `static/species` 中对应的文件。删除前请确认不再需要这些图片，因为重新生成会再次消耗图片模型额度。

## 演示素材

仓库中保留了几张演示图片，放在：

```text
static/generated
static/species
```

它们用于展示项目效果，不代表权威科学资料。正式用于科普、教学或发布前，请自行核验事实。

雪豹形态示例：

![雪豹形态示例](static/generated/57efe5ff11905195.png)

雪豹生态位示例：

![雪豹生态位示例](static/generated/fb2e38514e06fb0e.png)

帝王蟹形态示例：

![帝王蟹形态示例](static/generated/b4e7e6f73c70e0db.png)

## 已知限制

- GPT Image 生成图片可能比较慢，这是当前体验里最明显的等待点。
- 事实可靠性依赖文本模型和图片模型的通识能力。
- 冷门物种、小众生物、古生物更容易出现事实错误、形态混淆或图文不一致。
- 演化树、生态位、食物链、地质年代等内容尤其需要人工核验。
- 建议优先尝试现代常见物种，并把生成图当作科普草稿，而不是最终科学依据。

## 安全注意

- 不要把自己的 API Key 提交到 GitHub。
- 不要提交 `.env`、`server/config.local.json`、日志文件、虚拟环境目录等私有文件。
- 如果你要公开自己的生成图片，请先确认其中没有隐私信息、错误标注或不适合公开的内容。

## 开发与测试

运行测试：

```powershell
uv run pytest
```

检查前端脚本语法：

```powershell
node --check static/app.js
```

项目结构：

```text
server/          FastAPI 服务、模型调用、缓存、提示词组装
static/          浏览器界面和演示素材
tests/           单元测试和接口测试
```

## 参考与致谢

这个项目参考了：

- [vthinkxie/illustrated-explainer-spec](https://github.com/vthinkxie/illustrated-explainer-spec)
- X 上 @berryxia 分享的科普图画提示词经验

