#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""通过 ComfyUI API 提交 Z-Image-Turbo 工作流并等待出图。
用法:
    python gen.py "提示词" [宽] [高] [种子] [工作流json路径] [服务器URL]
    默认 1024x1024, seed=42, 工作流=同目录 ../references/workflow-z-image-turbo.json
出图落在 ComfyUI 的 output/ 目录。
"""
import json, os, sys, time, urllib.request

BASE = sys.argv[6] if len(sys.argv) > 6 else "http://127.0.0.1:8188"
WF = sys.argv[5] if len(sys.argv) > 5 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "references", "workflow-z-image-turbo.json")
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "a silver-haired girl, cyberpunk city, neon lights, cinematic"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
H = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 42

with open(WF, encoding="utf-8") as f:
    wf = json.load(f)

# 定位节点：CLIPTextEncode(正向) / EmptySD3LatentImage / KSampler
for nid, node in wf.items():
    ct = node.get("class_type", "")
    if ct == "CLIPTextEncode":
        node["inputs"]["text"] = PROMPT
    elif ct == "EmptySD3LatentImage":
        node["inputs"]["width"] = W
        node["inputs"]["height"] = H
    elif ct == "KSampler":
        node["inputs"]["seed"] = SEED

payload = json.dumps({"prompt": wf, "client_id": "comfyui-local-zimage"}).encode()
req = urllib.request.Request(BASE + "/prompt", data=payload,
                             headers={"Content-Type": "application/json"})
try:
    pid = json.loads(urllib.request.urlopen(req, timeout=60).read())["prompt_id"]
    print("已提交 prompt_id:", pid, flush=True)
except urllib.error.HTTPError as e:
    print("提交被拒:", e.read().decode("utf-8", "replace"), flush=True)
    sys.exit(1)

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
                print("出图:", img.get("filename"), "子目录:", img.get("subfolder", ""), flush=True)
        print("完成", flush=True)
        break
    time.sleep(5)
