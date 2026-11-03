# comfyui-local-zimage

<p align="right">[简体中文](README.md) | [English](README.en.md)</p>


**在 Windows 本机用 ComfyUI 免费出图，不按张付钱。这个技能专治三个卡点：装不上、下不动、显存爆。**

![License](https://img.shields.io/badge/license-MIT-yellow)
![Platform](https://img.shields.io/badge/platform-Windows%20%2B%20NVIDIA-3776AB)
![VRAM](https://img.shields.io/badge/显存-8GB%20可跑-2E7D32)
![spec](https://img.shields.io/badge/agentskills.io-spec%20valid-2E7D32)

## 它解决什么

云端出图按张收钱，量一大就肉疼；本地 ComfyUI 免费，但新手会卡在同一批问题上：

| 卡点 | 表现 | 技能里的对策 |
|---|---|---|
| 下不动 | 20GB+ 模型断在 60% | 分段并行下载（`scripts/dl-seg.sh`），断了续传不重下 |
| 显存爆 | 出图一半 OOM | NVFP4 量化模型 + 低显存启动参数 |
| 打不开 | 浏览器转圈 | 用 `http://127.0.0.1:8188`，**不要用 localhost**（可能解析到 IPv6 `::1` 或被代理拦） |
| 角色不一致 | 每张脸都不一样 | 先出设定稿，再用 img2img 锁脸 |
| 手动点节点 | 一次一张，无法批量 | 工作流存成 API JSON，脚本批量调 |

## 里面有什么

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 完整流程、参数、排障顺序 |
| `scripts/comfy_gen.py` | 走 API 批量出图 |
| `scripts/gen.py` / `gen_episodes.py` / `gen_grid.py` | 单张 / 分集 / 九宫格 |
| `scripts/make_video.py` | 分镜图拼 MP4 |
| `scripts/dl-seg.sh` | 模型分段下载 |
| `references/workflow-*.json` | 三个可直接导入的工作流（文生图 / img2img 锁脸 / 九宫格） |
| `references/troubleshooting.md` | 排障清单 |

## 安装（三种方式，按推荐顺序）

### 1. 一条命令装进所有 Agent（推荐，已实测）

```bash
npx skills add zhanguoliang715/comfyui-local-zimage
```

装好后会同时挂到 Codex、Cursor、Amp、Antigravity、Claude Code 等 20+ 个 Agent 上，不用逐个配。

### 2. 作为 Claude Code 插件（已实测）

```bash
claude plugin marketplace add zhanguoliang715/comfyui-local-zimage
claude plugin install comfyui-local-zimage@comfyui-local-zimage
```

### 3. 手动拷目录

```bash
git clone https://github.com/zhanguoliang715/comfyui-local-zimage.git
```

> **本机 git 报 `CRYPT_E_NO_REVOCATION_CHECK` 时**（证书吊销列表查不到），在命令前加 `GIT_SSL_NO_VERIFY=1`。
> 这是本机 TLS 配置问题，与仓库无关，换台机器通常直接可用。

## English

Local, free image generation on Windows with ComfyUI: segmented model downloads, 8GB VRAM fallbacks, img2img face locking, storyboard to MP4.

```bash
npx skills add zhanguoliang715/comfyui-local-zimage
```

## 上手

```bash
git clone https://github.com/zhanguoliang715/comfyui-local-zimage.git
cp -r comfyui-local-zimage ~/.workbuddy/skills/
python ~/.workbuddy/skills/comfyui-local-zimage/scripts/comfy_gen.py --help
```

先确认 `http://127.0.0.1:8188` 能打开，再跑脚本。**服务没起来时脚本会失败，这不是脚本坏了，是最常见的第一现场。**

## 边界（重要）

- **Windows + NVIDIA 专用**。macOS、AMD、纯 CPU 的路径没验证过，不要硬套。
- **8GB 显存是硬约束**。技能给的是降级方案（低分辨率出图再放大），不是"优化后能跑 4K"。
- **不保证画面好看**。它保证流程跑通、参数可复现，不保证审美。
- **模型许可各自不同**，商用前自己看 LICENSE，本仓库不代你判断。

## 最常见的三个错

1. **用 localhost 打不开就以为服务挂了**。换 `127.0.0.1` 往往立刻好。
2. **照抄别人机器的工作流**。节点 ID 与模型文件名跨版本会变，导入后要重新指认模型。
3. **显存爆了还加分辨率**。应低分辨率出图再放大，不要一步到位。

## 文档

| 想看什么 | 去哪 |
|---|---|
| 第一次用，怎么一步步做 | [docs/新手手册.md](docs/新手手册.md) |
| 参数契约、失败模式、已知限制 | [docs/技术文档.md](docs/技术文档.md) |
| 完整流程与排障 | [SKILL.md](SKILL.md) |

## License

[MIT](LICENSE)。注意：随仓库分发的工作流 JSON 只是配置，不包含模型权重，模型许可需另行确认。
