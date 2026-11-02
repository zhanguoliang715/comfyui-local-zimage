---
name: comfyui-local-zimage
description: 在 Windows 本机用 ComfyUI 做本地免费 AI 出图（文生图/图生图），含多镜头故事板的角色/风格一致性方案（设定稿 + img2img 锁脸），以及「剧本→分镜图→MP4 成片」流水线。面向 RTX 50 系 Blackwell 显卡 + 8GB 显存，覆盖代理分段下载、NVFP4 量化模型选型、Z-Image-Turbo 工作流与 API 批量出图。触发词：ComfyUI、本地出图、文生图、图生图、角色一致性、锁脸、Z-Image、AI 绘画、节点式工作流、部署 Stable Diffusion、剧本转视频。
---

# ComfyUI 本地出图（Z-Image-Turbo · Blackwell 8GB）

## 何时用这个 skill

用户想**在本机免费跑 AI 出图**、不想用云端付费（如即梦/Midjourney API）、或
已有 ComfyUI 但被"装不上/下不动/显存爆"卡住时。本 skill 沉淀了在
一台 RTX 5060 Laptop 8GB 机器上实测跑通的完整路径。

## 参考部署（作者机器实测，仅供对照）

> **换机器时下表每一项都要重写**：盘符、venv 位置、工作流文件名、模型目录都不同。这张表的价值是告诉你「需要确认哪些项」，不是让你照抄路径。

| 项 | 值 |
|---|---|
| ComfyUI 目录 | `D:\ComfyUI`（源码运行，非安装版，无注册表/无桌面快捷方式） |
| 版本 | **0.41.0**（2026-10-17 全量重装；来源 `git clone --depth 1 github.com/comfyanonymous/ComfyUI`，需 `GIT_SSL_NO_VERIFY=1`） |
| Python 环境 | `D:\ComfyUI\venv`（系统 Python 3.12.10 建；torch 2.10.0+cu128 用本地 wheels 装） |
| 启动入口 | `D:\ComfyUI\main.py` |
| 一键启动 | `<ComfyUI 目录>\start_comfyui.bat`（出图模式）/ `start_video_wan22.bat`（Wan2.2 低显存模式）；桌面快捷方式放哪都行，**关键是 bat 里的启动参数**。两个 bat 均**等端口就绪再自动开浏览器**，地址写死 `http://127.0.0.1:8188`（不用 localhost——localhost 可能解析到 IPv6 ::1 或被代理拦截，是「打不开」的高发原因） |
| 访问地址 | http://127.0.0.1:8188 |
| 工作流 | `D:\ComfyUI\z_image_turbo_workflow.json`（10 节点，API 格式）、`z_image_img2img.json`（锁脸）、`wan22_ti2v_api.json`（视频） |
| 出图目录 | `D:\ComfyUI\output\` |
| 模型重下 | `D:\ComfyUI\dl_models.sh`（16 段并行 dl-seg，26.5GB 约 11 分钟；日志 `download_jiubang.log`） |
| 完整备份 | `D:\ComfyUI_backup_20261017`（重装前全量 40.34GB，含旧 0.39.0 venv 与全部旧模型） |

### 模型清单（Z-Image-Turbo FP4，总 ~8.3GB）

| 文件 | 位置 | 大小(字节) |
|---|---|---|
| 扩散模型 | `models/diffusion_models/z_image_turbo_nvfp4.safetensors` | 4509509600 |
| 文本编码器 | `models/text_encoders/qwen_3_4b_fp4_mixed.safetensors` | 3479416193 |
| VAE | `models/vae/ae.safetensors` | 335304388 |

> ComfyUI 的 `folder_paths` 把 `unet` 旧名同时映射到 `models/unet` 与
> `models/diffusion_models`，所以扩散模型放哪个都能被 UNETLoader 扫到。
> 模型来源：hf-mirror.com 的 `Comfy-Org/z_image_turbo`（fp4 版专为显存紧张设计）。

### Wan2.2 TI2V-5B 视频三件套（总 ~18.2GB，2026-10-17 重装时重下）

| 文件 | 位置 | 大小(字节) |
|---|---|---|
| 视频扩散模型 | `models/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors` | 9999658848 |
| 文本编码器 | `models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6735906897 |
| VAE | `models/vae/wan2.2_vae.safetensors` | 1409400960 |

> 来源 `Comfy-Org/Wan_2.2_ComfyUI_repackaged`（hf-mirror 会 307 到 `Wan_2.2_ComfyUI_Repackaged` 大写形式，URL 照写即可）。
> **注意 hf-mirror API 对大小写敏感**：直接列仓库文件用 API 可能 401，用 resolve URL 跟重定向最稳。

## 启动与出图

### 1. 启动服务

```bash
cd /d/ComfyUI && ./venv/Scripts/python.exe main.py --listen 0.0.0.0 --port 8188
```

看到 `To see the GUI go to: http://0.0.0.0:8188` 即成功；浏览器开 `127.0.0.1:8188`。
启动日志里出现 `Native ops: mxfp8, nvfp4, ...` = **NVFP4 原生支持已生效**（8GB 能跑的关键）。
`IMPORT FAILED: nodes_upscale_model / nodes_canny / nodes_morphology / nodes_glsl` 等是
缺 kornia/spandrel 的可选节点，**与文生图无关，可忽略**。

### 2. 用 API 出图（比模拟点击稳，脚本见 `scripts/gen.py`）

```bash
cd /d/ComfyUI && ./venv/Scripts/python.exe gen_first.py
# POST http://127.0.0.1:8188/prompt  {"prompt": <工作流>, "client_id": "..."}
# 轮询 GET /history/<prompt_id> 拿输出文件名，图落在 output/
```

## Z-Image-Turbo 正确节点结构（照抄，别自创）

```
UNETLoader(z_image_turbo_nvfp4.safetensors, weight_dtype=default)
  → ModelSamplingAuraFlow(shift=3.0)
  → KSampler(steps=8, cfg=1.0, sampler=res_multistep, scheduler=simple)
CLIPLoader(qwen_3_4b_fp4_mixed.safetensors, type=lumina2) → CLIPTextEncode(正向)
CLIPTextEncode(正向) → ConditioningZeroOut = 负向（CFG=1 时负向零化）
VAELoader(ae.safetensors) → VAEDecode → SaveImage(filename_prefix 必填!)
EmptySD3LatentImage(1024x1024) → KSampler.latent_image
```

**五个必守点**（错一个就报错或出黑图）：

1. `cfg` 必须 **1.0**（蒸馏模型固定 CFG，调高会糊/爆）。
2. `steps` = **8**，`sampler_name` = **res_multistep**，`scheduler` = **simple**（官方推荐）。
3. 必须经 **ModelSamplingAuraFlow(shift=3.0)**，缺它画质会崩。
4. 潜变量用 **EmptySD3LatentImage**（不是 EmptyLatentImage）。
5. 负向用 **ConditioningZeroOut**；`SaveImage` 的 `filename_prefix` **必填**（漏了报 400 `Required input is missing: filename_prefix`）。

## 文生图备选：SDXL / Animagine 九宫格分镜（教程 p17 替代）

Z-Image-Turbo 出单张质量高、速度快；但若要**一套风格统一的九宫格分镜**（教程 p17
用 SDXL 1.0 演示），本机已下好 **Animagine XL 3.1**（6.45GB checkpoint，SDXL 架构），
走标准 SDXL 链路，无需蒸馏专属节点。

### 工作流（标准 SDXL，照抄 `references/workflow-animagine-ninegrid.json`）

```
CheckpointLoaderSimple(animagine-xl-3.1.safetensors)
  → CLIPTextEncode(正/负)        # 负向直接用英文负向词即可，不必 ZeroOut
  → EmptyLatentImage(768x768)
  → KSampler(steps=28, cfg=7.0, sampler=dpmpp_2m, scheduler=karras)
  → VAEDecode → SaveImage(filename_prefix 必填)
```

与 Z-Image-Turbo 的区别：**CFG=7、steps=28、用 EmptyLatentImage（非 SD3）、负向走普通
负向词**。这是标准 SDXL 参数，别把蒸馏那套（CFG=1/steps=8/SD3 潜变量）套过来。

### 一键出九宫格

`scripts/gen_grid.py` 内置 9 条赛博朋克银发少女英文提示词，逐张提交工作流（深拷贝改
seed/提示词/前缀），用 PIL 拼成 `output/zimage-9grid.png`。**必须放在 ComfyUI 根目录运行**
（脚本里 `WF/OUT` 基于自身路径定位 `z_image_ninegrid.json` 与 `output/`）。

```bash
cd /d/ComfyUI && ./venv/Scripts/python.exe gen_grid.py
```

> 8GB 显存跑 SDXL 768² 单张约 20-30s，9 张约 3-5 分钟，全程在显存内，不会爆。

## 两个本机环境硬坑（换个网络/机器要重新验证）

### 坑 1：MITM 代理单连接尾段卡死
本机所有外网走代理，单个长连接下到 95% 会掉到几 KB/s 卡死。**解法**：
用 `scripts/dl-seg.sh <url> <outfile> [段数]` 分段并行下载 + 按序拼接 + 校验大小。
大文件（torch 轮子 2.87GB）建议拆 **16 段**（每段 ~180MB，单连接足够短不易被掐）。
段内用 `curl -k -L -r START-END`；hf-mirror 每次重签 S3 URL（Expires 1h），段内 <1h 安全。

### 坑 2：pip 默认源在代理下挂起
一律加 aliyun 镜像：`pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com ...`
**大依赖务必加 `--no-cache-dir`**（transformers 5.x 等大包在缓存写入时会被 MITM 掐断，报 `Connection broken: IncompleteRead`，且残缺缓存文件会触发 safe-delete 钩子报错）。

### 坑 3：Windows 上删大目录树（2026-10-17 重装实测）
- `rm -rf`（Git Bash）删 11 万文件 10 分钟几乎无进度——**别用**。
- PowerShell `Remove-Item -Recurse` 删到 venv site-packages 深层 `.pyc` 时**静默失败**（.NET 5.1 MAX_PATH 限制），多跑几遍也删不掉同一批。
- **解法：robocopy 镜像删除**——`robocopy D:\zzz_empty <目标目录> /MIR`（空目录同步过去＝清空），快且无长路径问题；之后 `Remove-Item` 删根目录即可。
- 0 字节的 `nul` 保留设备名文件删不掉（.NET/PowerShell/del 全部访问被拒）：把所在目录**改名让位**，留待重启后清理。

## 环境事实（Blackwell 专用）

- 显卡 RTX 5060 Laptop，**sm_120**，必须 **CUDA 12.8**。
- torch 用 **2.10.0+cu128** + torchvision **0.25.0+cu128**（轮子自带 CUDA 库，**无 nvidia-* 依赖**）。
  轮子在 `D:\ComfyUI\wheels\`，本地 `pip install <whl>` 即可。
- 依赖精简清单在 `D:\ComfyUI\req_core.txt`（剔除 torch/torchvision + GUI 包，含 transformers/safetensors 等）。

## 8GB 显存边界

- ✅ 能跑：Z-Image-Turbo FP4 文生图 1024×1024（约 25s/张）。
- ✅ **能跑（慢）**：Wan2.2 TI2V-5B 图生图视频——`start_video_wan22.bat` 启动（`--fp8_e4m3fn-unet --fp8_e4m3fn-text-enc --lowvram --reserve-vram 1.5`），1152×640×81 帧@16fps（≈5 秒）**单条约 11 分钟**，面部稳定。fp16 原模型 10GB 装不进 8G，必须 fp8 量化 + lowvram 内存 offload（32G 内存是关键前提）。
- ⚠️ 吃紧：fp4 模型 + fp4 文本编码器已在 8GB 边缘，别再叠 ControlNet/多 LoRA。
- ❌ 别碰：LTX2.3 及 14B 级视频模型（如 Wan2.2 S2V 口型驱动），8GB/32G 组合跑不动，需云端或换卡。**真人级口型同步在本机不可行**，替代方案＝旁白配音＋固定中近景。
- ❌ **MiniMax H3 R2V 实测不可行**（2026-10-17）：5 个模型共 39.1GB 已下齐（见下节），但 8G 卡 + dynamic VRAM loading 模式下 20GB int8 主模型分 208 patches 流式换入，32G 内存被 Qwen3VL 编码器（15G）+ staged 权重（20G）挤爆（空闲 <1G），权重页被换出页面文件，第三次 39 帧微型探针仍 10 分钟进不了第 1 步。**三规模实测（192/124/39 帧）证实为架构性瓶颈，非调参可解。**

## MiniMax H3 R2V 部署记录（2026-10-17，模型已下齐待 24G+ 卡）

### 模型（Comfy-Org/MiniMax-H3，共 39.1GB，已在本机）

| 文件 | 位置 | 大小(字节) |
|---|---|---|
| R2V 主模型 int8 | `models/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 20970379616 |
| Qwen3VL 32B nvfp4 文本编码器 | `models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15687142551 |
| 视频 VAE int8 | `models/vae/minimax_h3_video_vae_int8_convrot.safetensors` | 2811065184 |
| 音频 VAE fp32 | `models/vae/minimax_h3_audio_vae_fp32.safetensors` | 605254808 |
| 4 步 Turbo LoRA | `models/loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | 1956193000 |

**下载源**：`hf-mirror.com/Comfy-Org/MiniMax-H3` 16 段并行下 4/5 成功；视频 VAE 反复失败（hf-mirror 已 308 跳原站、原站 range 被代理挡），**最终用 ModelScope 成功**：
```bash
URL=$(curl -sk "https://modelscope.cn/api/v1/models/Comfy-Org/MiniMax-H3/repo?FilePath=vae/minimax_h3_video_vae_int8_convrot.safetensors" -o /dev/null -w "%{redirect_url}")
curl -skL -C - "$URL" -o models/vae/minimax_h3_video_vae_int8_convrot.safetensors   # CDN 直连带 auth_key 有时效
```
（ModelScope 是 Comfy-Org 仓库的可用镜像，大文件单流稳定 ~15MB/s。）

### 工作流与入口

- 官方模板：`user/default/workflows/MiniMax H3 参考生视频 R2V.json`（另存 I2V/T2V 版）；ComfyUI 0.41.0 原生含 `MiniMaxH3ReferenceToVideo` 节点
- 预填生成：`make_jiubang_r2v.py`（LoadImage 参考图/提示词/参数）→ 产出 `MiniMax H3 R2V - 九棒 s01.json`
- 模板→API 转换器：`wf_to_api.py`（处理 ResolutionSelector 求值、ComfyMathExpression、ComfySwitchNode 分支、autogrow 参考图列表归并）
- 批量生成：`jiubang_h3.py s01 s02...`（每镜提示词+时长覆盖、轮询、复制输出）
- 启动：`start_comfyui_h3.bat`（**不带 fp8 参数**——H3 是 int8 convrot 权重，再 fp8 会冲突）

### 关键经验

1. **widgets_values 含全部 widget 值（含被链接的），按声明顺序**——转换器不要排除 linked，否则值错位（曾因此把提示词写进 ref_image_size）。
2. **`132.value`（秒数）的 override 穿不过 ComfyMathExpression**（resolve_link 从 JSON 原始值求值）——必须直接覆盖 `136.length`（帧数），公式 `n=max(5,round(sec*24)); frames=n+(5-(n%17))%17`。
3. **`ref_image_size` 用 `match` 不用 `max`**：max 保留 2048px 短边，参考 token 每步重算，模板明示慢；8G 下还必须 `CLIPLoader device=cpu`（14.6G 编码器放 CPU）。
4. **R2V 提示词必须按连接顺序引用 `<Picture 1>`/`<Picture 2>` 并说明各自驱动什么**（模板原话：ref2va 对措辞极敏感）；H3 原生联合生成音频，台词写进 prompt 即自动口型同步。
5. R2V 输出最高 2K/24fps/约 15 秒；采样 res_multistep + 4 步 turbo LoRA；视频 VAE/音频 VAE 分别 decode 后由 CreateVideo 合成带声音的 MP4。

## Wan2.2 图生图（i2v）正确接线（2026-10-17 实测）

`wan22_ti2v_api.json`（API 格式）原样没有图片输入。接图生图**必须加 LoadImage 节点**：

```python
wf["11"] = {"class_type": "LoadImage", "inputs": {"image": "你的关键帧.png"}}
wf["7"]["inputs"]["start_image"] = ["11", 0]   # 必须是节点链接！
```

**直接给 `start_image` 传文件名字符串会报 `'str' object has no attribute 'movedim'`**（节点拿到 str 当成 tensor 用）。
关键帧先复制进 `ComfyUI/input/`。其余参数：`Wan22ImageToVideoLatent(width=1152, height=640, length=81)`、
`ModelSamplingSD3(shift=8.0)`、`KSampler(20步, uni_pc, simple, cfg=5.0)`、`SaveAnimatedWEBP(fps=16)`。
成品脚本：`jiubang_wan.py`（每镜一条 5 秒运动片段）。

## 故障速查

见 `references/troubleshooting.md`。

## Agent 可调用入口（剧本 → 视频 流水线）

用户不需要懂节点；agent 直接调下面两个脚本即可。已实测跑通。

### 1) 出图：`scripts/comfy_gen.py`（给提示词 → 返回图片绝对路径）
```bash
cd /d/ComfyUI && ./venv/Scripts/python.exe comfy_gen.py --prompt "一个银发少女，赛博朋克都市，电影感，杰作"
# 可选: --model animagine --width 768 --height 768 --seed 12345 --out scene01
# 图生图锁角色: --ref refs/ref_yech.png --denoise 0.80
# 成功唯一输出：图片绝对路径（供下一步合成视频）
```
- `zimage`（默认）：FP4 蒸馏，1024²，~25s/张，CFG=1。
- `animagine`：SDXL，768²，~20–30s/张，可换风格。
- `--ref`：走图生图（锁角色，见下节），参考图自动复制进 `ComfyUI/input/`。

### 2) 合成视频：`scripts/make_video.py`（分镜图 → MP4）
先写 `scenes.json`（数组，每项一镜头）：
```json
[{"image":"D:/ComfyUI/output/scene01.png","duration":4,"caption":"镜1字幕"},
 {"image":"D:/ComfyUI/output/scene02.png","duration":3,"audio":"旁白.mp3"}]
```
```bash
cd /d/ComfyUI && ./venv/Scripts/python.exe make_video.py --manifest scenes.json --out story.mp4
# 可选: --bgm music.mp3 --fps 25 --width 1920 --height 1080
```
- 每镜头做 Ken Burns 推拉（zoompan 1.0→1.08）；`caption` 经微软雅黑烧入中文字幕；
  `audio` 为镜头专属旁白，缺则静音；`--bgm` 全局背景乐循环铺底（音量 0.25）。
- 所有片段统一 1920×1080 / 25fps / libx264+aac，concat demuxer 拼接。

### 8GB 显存下的"视频"边界（务必先告知用户）
本机 RTX 5060 仅 8GB，**跑不动真正的 AI 视频大模型**（Wan2.2 / LTX2.3 需 ≥12–16GB）。
所以"根据剧本生成视频"在本机落地为：**剧本 → 每镜头出一张分镜图（comfy_gen）→
ffmpeg 合成带镜头运动/字幕/旁白的 MP4**。这是本地免费、确定可跑的"视频"。
若要"真·人物运动"的 AI 视频，需云端付费 API（如即梦/Runway 等，需账号/Key）或换 ≥16GB 显卡。

## 角色/风格一致性（多镜头故事板必用 · 实测）

**问题**：同一角色跨多镜生成会"变脸"、风格在动漫/卡通间漂移。根因：Z-Image-Turbo
是**通用**模型，且每镜**独立随机种子**——纯 txt2img 没有任何"角色记忆"。

**修复四步**（本机已实测，出图见 `D:\ComfyUI\output\wuling\`）：

1. **统一风格串**：全片用同一段风格后缀，且**别混入"电影感/写实"**这类会拉向半写实的词。
   示例：`，统一日式赛璐璐动漫风格，线条清晰干净，古风玄幻，蒸汽朋克机关元素，杰作，高细节`。
2. **先出角色设定稿**：用 txt2img + **固定种子**出半身正面胸像（如 `refs/ref_yech.png`），
   与后续同一模型（同域才利于 img2img）。
3. **img2img 锁脸**：`z_image_img2img.json` = `LoadImage → VAEEncode → KSampler(latent=VAEEncode)`
   （与文生图唯一区别：latent 来自 VAEEncode 而非 EmptySD3LatentImage；参考图须在 `ComfyUI/input/`）。
   调 `comfy_gen.py --ref refs/ref_yech.png --denoise 0.80`。
   **denoise 是关键旋钮**（实测）：`0.62` 脸最像但场景换不动；`0.75` 脸好场景中等；
   `0.85` 场景最活脸略漂；**`0.80` 为平衡点**。
4. **文字兜底 + 路由**：每镜附**同一段角色描述**（如"叶尘：黑发黑瞳剑眉星目清瘦少年束发灰布破旧交领长衫"）；
   按关键词路由（含"秦昭月/红裙"→她的 ref；含"叶尘/少年"→叶尘 ref；否则纯空镜走 txt2img）。

**残留局限（须透明告知用户）**：img2img 只能"高度相似"，非像素级一致，且低去噪会锁构图；
100% 锁脸需训练角色 LoRA（见下）。**相同场景**一致性目前只靠统一风格 + 一致场景描述，未做场景参考图。

> ⚠️ **IP-Adapter 在 Z-Image-Turbo 上走不通（已实测否定，别再试）**：
> Z-Image-Turbo 是 **Flux/AuraFlow 架构**（模型里有 `context_refiner` 块、融合 `qkv.weight`、
> 隐藏维度 **3840**），不是 SDXL 那种有独立 `to_k/to_v` 交叉注意力的结构。标准
> `ComfyUI_IPAdapter_plus` 节点改的是 SDXL 交叉注意力（维度 2048），**对不上 Z-Image 的模块结构和维度**，
> 装上去要么报错要么出乱码；公开仓库也**没有 Z-Image 专用 IP-Adapter 权重**。所以本项目锁脸只能用
> img2img（本节能用）或训练 LoRA（下条）。
>
> **真·像素级锁脸的正确路径 = 训练角色 LoRA**：Z-Image-Turbo 支持 LoRA（`LoraLoaderModelOnly`，
> 社区已验证）。用几张角色设定稿训练一个"叶尘"LoRA（低 rank、少量图），注入后角色一致且连画风一起锁。
> 代价：8GB 上训 6B DiT 的 LoRA 较慢、需要训练脚本与显存权衡；属"最强但最重"方案。

## 交付与可见性约定（用户偏好）

用户要求**操作可见**，不要只甩代码日志。做法：
- 把 Web 界面用预览面板开到 `http://127.0.0.1:8188` 让用户亲眼看节点图；
- 进度用**口语化 + 图表**汇报，别贴大段命令输出；
- 需要长时间下载/安装时，**去掉 `| tail` 缓冲**（否则进度被全缓冲，用户以为死机）。

## 短剧四一致工艺（2026-10-17《完美犯罪》EP01 实测，可复用）

用户对短剧系列的硬要求＝**角色一致/场景一致/人物细节一致/场景细节一致**。落地五件套：

1. **基准图制**：角色（正脸半身像）与场景各先生成定锚图，固定种子 + 固定提示词块**逐字复用**，全系列不变。
2. **场景派生**：同场景所有镜头只改裁剪不改内容，i2i denoise ≤ 0.62 派生；细节锚点物件（茶缸/警戒带/KB线/屏幕排布）写进每张提示词。
3. **贴脸引导**：脸区从定锚图裁剪，椭圆羽化（GaussianBlur ~26px）贴入场景引导图，接缝由 i2i 重绘弥合。**正脸证件照式贴图仍有"贴纸边缘"**——边缘/背景人物改侧影背身由提示词生成，不贴正脸。
4. **UI 后处理**：系统弹窗/红框/小字一律 ffmpeg drawbox/drawtext 叠加，不进生成模型（Wan 会把画面文字重绘成乱码）。
5. **种子体系**：角色固定种子（齐封 2001…），构图种子＝角色种子+镜号偏移，同镜重跑可复现。

配套脚本模式（`D:/ComfyUI/drama_*.py`）：kit（基准）→ guides（贴脸引导）→ shots（i2i 关键帧）→ wan（运动段）→ tts（旁白）→ build（合成）。

## 2026-10-17 新踩坑（短剧制作）

- **comfy_gen.py 被 MITM 代理劫本地请求**：urllib 默认读 HTTP_PROXY，127.0.0.1 提交也被代理拒绝（os error 10061，报"upstream connect failed"）。已在 comfy_gen.py 加 `OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))`，所有本地请求走 OPENER。新写脚本同样默认无代理 opener。
- **ComfyUI 后台服务会被 sandbox 回收**：表现为 HTTP 000（连 `curl --noproxy` 都不通），日志无 traceback。重启即可，不是模型/环境问题。
- **txt2img 场景会自行塞人物**：场景提示词不加约束时模型自己加人（办公室场景出了个外国警员）。场景块必须写 `empty and unoccupied, no people`，人物用贴脸/侧影单独加。
- **i2i 会增删细节锚点**：`exactly one green tea mug` 也可能生成两个。对策：提示词加 exactly 限定；仍出现则 PIL 局部 patch（取周边同纹理块覆盖）。
