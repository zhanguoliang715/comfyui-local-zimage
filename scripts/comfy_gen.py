#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comfy_gen.py —— Agent 可调用的一键出图接口（封装 Z-Image-Turbo / Animagine）

设计目的：把"ComfyUI 出图"做成 agent 能直接调用的工具。给一段提示词，返回
生成图片的绝对路径，供后续流程（如合成视频）使用。用户无需懂节点。

用法:
  python comfy_gen.py --prompt "一个银发少女，赛博朋克都市，电影感，杰作"
  python comfy_gen.py --prompt "..." --model animagine --width 768 --height 768
  python comfy_gen.py --prompt "..." --seed 12345 --out scene01

参数:
  --prompt   正向提示词（必填）
  --model    zimage(默认, FP4 蒸馏, 1024, 快) | animagine(SDXL, 768, 可换风格)
  --negative 负向提示词（仅 animagine 用；zimage 走 ConditioningZeroOut 忽略此项）
  --width/--height  出图尺寸（zimage 默认 1024，animagine 默认 768）
  --seed     随机种子（不给则随机）
  --out      输出文件名前缀（默认 comfygen）
  --url      ComfyUI 地址（默认 http://127.0.0.1:8188）
  --timeout  最长等待秒数（默认 300）

成功：打印输出图片的绝对路径并退出 0；失败：打印错误并退出 1。
"""
import argparse, json, os, sys, time, shutil, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
ZIMAGE_WF = os.path.join(ROOT, "z_image_turbo_workflow.json")
ZIMAGE_I2I_WF = os.path.join(ROOT, "z_image_img2img.json")
ANIMAGINE_WF = os.path.join(ROOT, "z_image_ninegrid.json")
INPUT_DIR = os.path.join(ROOT, "input")
OUTPUT_DIR = os.path.join(ROOT, "output")

ANIMAGINE_NEG_DEFAULT = (
    "low quality, worst quality, blurry, jpeg artifacts, text, watermark, "
    "extra digits, signature, deformed, bad anatomy"
)


def load_wf(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def submit(wf, base):
    payload = json.dumps({"prompt": wf, "client_id": "comfy_gen"}).encode()
    req = urllib.request.Request(base + "/prompt", data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.stderr.write("提交被拒: " + e.read().decode("utf-8", "replace") + "\n")
        return None


def wait_image(pid, base, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            h = json.loads(urllib.request.urlopen(base + "/history/" + pid, timeout=60).read())
        except Exception:
            h = {}
        if pid in h:
            item = h[pid]
            for m in item.get("status", {}).get("messages", []):
                if m[0] in ("execution_error", "error"):
                    sys.stderr.write("执行报错: " + json.dumps(m[1], ensure_ascii=False) + "\n")
            for nid, o in item.get("outputs", {}).items():
                for img in o.get("images", []):
                    return img.get("filename"), img.get("subfolder", "")
        time.sleep(3)
    return None, None


def build_zimage(prompt, width, height, seed, prefix):
    wf = load_wf(ZIMAGE_WF)
    wf["27"]["inputs"]["text"] = prompt
    wf["13"]["inputs"]["width"] = width
    wf["13"]["inputs"]["height"] = height
    wf["3"]["inputs"]["seed"] = seed
    wf["9"]["inputs"]["filename_prefix"] = prefix
    return wf


def build_zimage_i2i(prompt, ref_path, denoise, seed, prefix):
    """图生图：以参考图（角色设定稿）为底，低去噪保留人脸/服饰一致性。"""
    wf = load_wf(ZIMAGE_I2I_WF)
    # 参考图必须落在 ComfyUI/input 目录，LoadImage 按文件名读取
    os.makedirs(INPUT_DIR, exist_ok=True)
    ref_name = os.path.basename(ref_path)
    dst = os.path.join(INPUT_DIR, ref_name)
    if os.path.abspath(ref_path) != os.path.abspath(dst):
        shutil.copyfile(ref_path, dst)
    wf["27"]["inputs"]["text"] = prompt
    wf["40"]["inputs"]["image"] = ref_name
    wf["3"]["inputs"]["seed"] = seed
    wf["3"]["inputs"]["denoise"] = float(denoise)
    wf["9"]["inputs"]["filename_prefix"] = prefix
    return wf


def build_animagine(prompt, negative, width, height, seed, prefix):
    wf = load_wf(ANIMAGINE_WF)
    wf["2"]["inputs"]["text"] = prompt
    wf["3"]["inputs"]["text"] = negative
    wf["4"]["inputs"]["width"] = width
    wf["4"]["inputs"]["height"] = height
    wf["5"]["inputs"]["seed"] = seed
    wf["7"]["inputs"]["filename_prefix"] = prefix
    return wf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", default="zimage", choices=["zimage", "animagine"])
    ap.add_argument("--negative", default=ANIMAGINE_NEG_DEFAULT)
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default="comfygen")
    ap.add_argument("--ref", default=None, help="参考图路径（图生图锁定角色）")
    ap.add_argument("--denoise", type=float, default=0.62, help="图生图去噪强度")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    if args.seed is None:
        args.seed = int(time.time() * 1000) % (2 ** 31)
    if args.ref:
        # 图生图锁定角色：参考图尺寸决定出图尺寸
        wf = build_zimage_i2i(args.prompt, args.ref, args.denoise, args.seed, args.out)
    elif args.model == "zimage":
        w, h = args.width or 1024, args.height or 1024
        wf = build_zimage(args.prompt, w, h, args.seed, args.out)
    else:
        w, h = args.width or 768, args.height or 768
        wf = build_animagine(args.prompt, args.negative, w, h, args.seed, args.out)

    pid = submit(wf, args.url)
    if not pid:
        sys.stderr.write("提交失败，未生成图像\n")
        sys.exit(1)
    fn, sub = wait_image(pid, args.url, args.timeout)
    if not fn:
        sys.stderr.write("等待输出超时（%ds）\n" % args.timeout)
        sys.exit(1)
    path = os.path.join(OUTPUT_DIR, sub, fn) if sub else os.path.join(OUTPUT_DIR, fn)
    if not os.path.exists(path):
        sys.stderr.write("图像未找到: %s\n" % path)
        sys.exit(1)
    print(os.path.abspath(path))  # 唯一成功输出：绝对路径，供 agent 解析
    sys.exit(0)


if __name__ == "__main__":
    main()
