# comfyui-local-zimage

[简体中文](README.md) | **English**

**Free local image generation on Windows with ComfyUI. Built for the three things that stop people: can't install it, can't finish the download, can't fit it in VRAM.**

![License](https://img.shields.io/badge/license-MIT-yellow)
![Platform](https://img.shields.io/badge/platform-Windows%20%2B%20NVIDIA-3776AB)
![VRAM](https://img.shields.io/badge/VRAM-8GB-2E7D32)
![spec](https://img.shields.io/badge/agentskills.io-spec%20valid-2E7D32)

## Install

```bash
npx skills add zhanguoliang715/comfyui-local-zimage
```

Or as a Claude Code plugin:

```bash
claude plugin marketplace add zhanguoliang715/comfyui-local-zimage
claude plugin install comfyui-local-zimage@comfyui-local-zimage
```

## The problems it actually addresses

| Symptom | Cause | What the skill does |
|---|---|---|
| Download dies at 60% | 20GB+ single-stream download | segmented parallel download (`scripts/dl-seg.sh`) with resume |
| OOM halfway through | full-precision model on 8GB | NVFP4 quantized model + low-VRAM launch flags |
| Browser spins forever | `localhost` resolving to IPv6 `::1` or hitting a proxy | use `http://127.0.0.1:8188` |
| Every face different | no reference conditioning | generate a character sheet first, then img2img for consistency |
| One image at a time | clicking nodes by hand | workflows stored as API JSON, driven by scripts |

## What is inside

| Path | Content |
|---|---|
| `scripts/comfy_gen.py` | batch generation over the ComfyUI API |
| `scripts/gen.py` / `gen_episodes.py` / `gen_grid.py` | single / per-episode / nine-grid |
| `scripts/make_video.py` | storyboard images to MP4 |
| `references/workflow-*.json` | three importable workflows (txt2img, img2img face-lock, nine-grid) |

## Boundaries

- **Windows + NVIDIA only.** macOS, AMD and CPU-only paths are unverified.
- **8GB VRAM is a hard constraint.** The skill gives downscale-then-upscale fallbacks, not "4K on 8GB".
- **No quality guarantee.** It makes the pipeline reproducible; it does not make the images good.
- **Model licenses vary.** Check them before commercial use; this repo does not decide that for you.

## Docs

- [Beginner handbook](docs/新手手册.md)
- [Technical doc](docs/技术文档.md)
- [SKILL.md](SKILL.md) — full procedure and troubleshooting order

## License

MIT. Workflow JSON files are configuration only and contain no model weights.
