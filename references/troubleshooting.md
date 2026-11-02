# ComfyUI 本机出图 · 故障速查

## 启动类

| 现象 | 原因 | 解决 |
|---|---|---|
| 打了 `main.py` 没反应 / `ModuleNotFoundError` | 用了系统 python 而非 venv | 一律 `D:\ComfyUI\venv\Scripts\python.exe`，或跑 `start_comfyui.bat` |
| `IMPORT FAILED: nodes_canny/morphology/upscale_model/glsl` | 缺 kornia/spandrel/PyOpenGL（精简依赖剔掉了） | **无害**，这些是可选附加节点，文生图不需要；要用再单独 `pip install kornia spandrel` |
| 端口起不来 `address already in use` | 已有 ComfyUI 在跑 | `netstat -ano \| grep :8188` 找 PID，`taskkill /PID <pid> /F` |
| 浏览器打不开 `localhost:8188` | Windows 把 localhost 解析成 IPv6 `::1` | 用 `127.0.0.1:8188`；启动加 `--listen 0.0.0.0` 覆盖双栈 |

## 下载类

| 现象 | 原因 | 解决 |
|---|---|---|
| `pip install` 卡住不动、无输出 | 默认 PyPI 在 MITM 代理下单连接挂起 | 加 `-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com` |
| 大文件下到 95% 掉到几 KB/s | 代理对单长连接限速/尾段劣化 | 用 `scripts/dl-seg.sh <url> <out> 16` 分段并行下 |
| `curl` 报 schannel / 吊销检查失败 | 代理证书导致证书吊销检查失败（表现为静默挂起） | `curl -k`；git 用 `GIT_SSL_NO_VERIFY=1` |
| 连不上 huggingface.co（502） | 被墙 | 换 `hf-mirror.com`（镜像，返回 200） |

## 出图类

| 现象 | 原因 | 解决 |
|---|---|---|
| 提交返回 400 `Required input is missing: filename_prefix` | SaveImage 漏字段 | 给 SaveImage 加 `"filename_prefix": "zimage-turbo"` |
| 提交返回 400 其他 required input missing | 工作流节点缺字段 | 看返回体 `node_errors`，按提示补 |
| 出黑图 / 糊 / 噪点 | CFG 调高 或 缺 ModelSamplingAuraFlow | CFG 固定 **1.0**；KSampler 前必须接 **ModelSamplingAuraFlow(shift=3.0)** |
| 图很淡 / 像没生成 | steps 太少或采样器不对 | steps=**8**，sampler=**res_multistep**，scheduler=**simple** |
| `error: ... fp4 / nvfp4` | 版本不支持 NVFP4 | 需 CUDA 12.8 torch 2.10+；日志应出现 `Native ops: ... nvfp4 ...` |
| CUDA out of memory | 8GB 显存不够 | 降分辨率（如 768×768）；关其它占显存程序；别叠 LoRA/ControlNet |

## 判定"服务是否真的活着"

```bash
netstat -ano | grep ":8188"        # 应有一行 LISTENING
tail -5 D:/ComfyUI/comfyui.log     # 应能看到 "To see the GUI go to"
```

## 关键环境记录

- GPU：RTX 5060 Laptop，sm_120，驱动 591.86，CUDA 12.8。
- torch 2.10.0+cu128 / torchvision 0.25.0+cu128（轮子自带 CUDA 库）。
- 实测 Z-Image-Turbo FP4 1024×1024 出图约 25s（8 步）。
- 首次出图时间戳：2026-10-09，输出 `zimage-turbo_00001_.png`。

## 高清放大（ESRGAN 超分）额外坑

| 现象 | 原因 | 解决 |
|---|---|---|
| 提交超分工作流报 `Node 'UpscaleModelLoader' not found` | `nodes_upscale_model.py` 依赖 `spandrel`，缺它则整模块启动时不加载 | `pip install spandrel`（aliyun 镜像），**重启 ComfyUI 才生效**（自定义节点启动时加载） |
| `IMPORT FAILED: nodes_upscale_model.py` | 同上，缺 spandrel | 同上 |
| 重启后端口仍被旧进程占 | 旧 `main.py` 没退干净 | `netstat -ano \| grep :8188` 取 PID，`taskkill /PID <pid> /F` 再起 |

