#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""p17 九宫格分镜：用 Animagine/SDXL 生成 9 张图，合成为 3x3 网格。
用法: python gen_grid.py
依赖：已下载 models/checkpoints/animagine-xl-3.1.safetensors，ComfyUI 服务在 127.0.0.1:8188。
"""
import json, os, sys, time, urllib.request, urllib.error
from PIL import Image
from io import BytesIO

BASE = "http://127.0.0.1:8188"
ROOT = os.path.dirname(os.path.abspath(__file__))
# 注意：本脚本默认放在 ComfyUI 根目录运行；若放进 skill/scripts 需改成 ComfyUI 根。
WF = os.path.join(ROOT, "z_image_ninegrid.json")
OUT = os.path.join(ROOT, "output")
GRID = os.path.join(OUT, "zimage-9grid.png")

NEG = "low quality, worst quality, blurry, jpeg artifacts, text, watermark, extra digits, signature"

PROMPTS = [
    "silver-haired girl, neon alley, looking up at rainy night sky, cyberpunk, cinematic, masterpiece",
    "silver-haired girl, walking into a retro arcade, glowing machines, cyberpunk, anime style",
    "silver-haired girl, wearing holographic headset, data streams reflected in eyes, cyberpunk",
    "silver-haired girl on city rooftop, unfolding glowing mechanical wings, sunset, cinematic",
    "silver-haired girl, beside a floating robot cat, rooftop garden, cyberpunk, anime style",
    "silver-haired girl, underground lab, city map on screens, blue lighting, cyberpunk",
    "silver-haired girl, holding a light blade, ready for battle, dynamic pose, cyberpunk",
    "silver-haired girl, shielding the robot cat amid explosion fire, dramatic, cinematic",
    "silver-haired girl, dawn, smiling at rebuilt city, hopeful, cyberpunk, masterpiece",
]


def submit(workflow):
    payload = json.dumps({"prompt": workflow, "client_id": "comfyui-grid"}).encode()
    req = urllib.request.Request(BASE + "/prompt", data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        pid = json.loads(urllib.request.urlopen(req, timeout=60).read())["prompt_id"]
        return pid
    except urllib.error.HTTPError as e:
        print("提交被拒:", e.read().decode("utf-8", "replace"), flush=True)
        return None


def wait_image(pid):
    for _ in range(360):
        try:
            h = json.loads(urllib.request.urlopen(BASE + "/history/" + pid, timeout=60).read())
        except Exception:
            h = {}
        if pid in h:
            item = h[pid]
            for m in item.get("status", {}).get("messages", []):
                if m[0] in ("execution_error", "error"):
                    print("执行报错:", json.dumps(m[1], ensure_ascii=False), flush=True)
            for nid, o in item.get("outputs", {}).items():
                for img in o.get("images", []):
                    return img.get("filename"), img.get("subfolder", "")
        time.sleep(5)
    return None, None


def main():
    with open(WF, encoding="utf-8") as f:
        template = json.load(f)
    cells = []
    for i, p in enumerate(PROMPTS):
        wf = json.loads(json.dumps(template))  # 深拷贝
        wf["2"]["inputs"]["text"] = p
        wf["3"]["inputs"]["text"] = NEG
        wf["5"]["inputs"]["seed"] = 12345 + i * 17
        wf["7"]["inputs"]["filename_prefix"] = "grid-%02d" % i
        pid = submit(wf)
        if not pid:
            print("第 %d 张提交失败，跳过" % i)
            continue
        fn, sub = wait_image(pid)
        if fn:
            path = os.path.join(OUT, sub, fn) if sub else os.path.join(OUT, fn)
            try:
                cells.append(Image.open(path).convert("RGB"))
                print("第 %d 张完成: %s" % (i + 1, fn), flush=True)
            except Exception as e:
                print("读图失败 %s: %s" % (path, e), flush=True)
        else:
            print("第 %d 张无输出" % i, flush=True)

    if len(cells) != 9:
        print("只生成了 %d 张，不足 9 张，放弃合成网格" % len(cells))
        return
    cell = 768
    grid = Image.new("RGB", (cell * 3, cell * 3), (255, 255, 255))
    for idx, im in enumerate(cells):
        im = im.resize((cell, cell), Image.LANCZOS)
        r, c = divmod(idx, 3)
        grid.paste(im, (c * cell, r * cell))
    grid.save(GRID)
    print("九宫格已合成: %s" % GRID, flush=True)


if __name__ == "__main__":
    main()
