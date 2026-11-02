#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_video.py —— 把分镜图合成视频（Agent 调用，本地免费，ffmpeg 实现）

设计目的：配合 comfy_gen.py 使用。comfy_gen 按剧本每个镜头出一张图，本脚本
把这些图合成一段 MP4（Ken Burns 推拉 + 可选字幕 + 可选旁白/背景音乐）。
无需云端、无需大显存，纯 CPU + ffmpeg。

用法:
  python make_video.py --manifest scenes.json --out story.mp4
  python make_video.py --manifest scenes.json --out story.mp4 --bgm music.mp3 --fps 25

scenes.json 结构（数组，每项是一镜头）:
  [
    {"image": "D:/ComfyUI/output/scene01.png", "duration": 4, "caption": "可选字幕"},
    {"image": "...", "duration": 3, "audio": "可选旁白.mp3"},
    ...
  ]
  - image:    必填，分镜图绝对路径（由 comfy_gen.py 产出）
  - duration: 该镜头秒数（默认 4）
  - caption:  可选，烧入字幕（中文需系统有 CJK 字体，见下）
  - audio:    可选，该镜头专属旁白/音效；不填则静音

可选全局参数:
  --bgm      全局背景音乐（循环铺满整段）
  --fps      帧率（默认 25）
  --width/--height  画布尺寸（默认 1920x1080）
  --caption-font  指定字幕字体文件（默认自动找 Windows 微软雅黑）

输出: 打印最终 MP4 绝对路径并退出 0；失败打印错误退出 1。
"""
import argparse, json, os, sys, subprocess, tempfile, shutil

FFMPEG = "ffmpeg"


def find_cjk_font():
    candidates = [
        r"C:/Windows/Fonts/msyh.ttc",
        r"C:/Windows/Fonts/msyhbd.ttc",
        r"C:/Windows/Fonts/simhei.ttf",
        r"C:/Windows/Fonts/simsun.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def ff(args, log):
    p = subprocess.run([FFMPEG, "-y"] + args, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.write("FFCMD: ffmpeg -y " + " ".join(args) + "\n")
        sys.stderr.write("FFERR: " + p.stderr.decode("utf-8", "replace")[-2000:] + "\n")
        log.write("ffmpeg 失败(rc=%d):\n%s\n" % (p.returncode, p.stderr.decode("utf-8", "replace")))
        return False
    return True


def esc_drawtext(s):
    # ffmpeg drawtext 文本需转义 : 与 ' 等
    return s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")


def esc_fontfile(path):
    # 滤镜里 fontfile 路径的冒号（C:/...）必须转义；统一用正斜杠
    return path.replace("\\", "/").replace(":", "\\:")


def build_scene_clip(scene, idx, fps, w, h, font, tmpdir, log):
    img = scene["image"]
    dur = float(scene.get("duration", 4))
    frames = max(1, int(round(dur * fps)))
    audio = scene.get("audio")
    out = os.path.join(tmpdir, "scene_%02d.mp4" % idx)

    filt = ("[0:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
            "zoompan=z='min(1.08,1.0+0.08*on/%d)':d=%d:s=%dx%d:fps=%d:"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',format=yuv420p"
            % (w, h, w, h, frames, frames, w, h, fps))
    if scene.get("caption") and font:
        cap = esc_drawtext(scene["caption"])
        filt += (",drawtext=fontfile='%s':text='%s':fontcolor=white:fontsize=48:"
                 "box=1:boxcolor=black@0.5:boxborderw=12:x=(w-tw)/2:y=h-th-80"
                 % (esc_fontfile(font), cap))
    filt += "[v]"

    args = ["-loop", "1", "-i", img, "-t", str(dur)]
    if audio and os.path.exists(audio):
        args += ["-i", audio]
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    args += ["-filter_complex", filt, "-map", "[v]", "-map", "1:a",
             "-t", str(dur), "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-ar", "44100", "-b:a", "128k", out]
    if not ff(args, log):
        return None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bgm", default=None)
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--caption-font", default=None)
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        scenes = json.load(f)
    if not isinstance(scenes, list) or not scenes:
        sys.stderr.write("manifest 必须是非空数组\n")
        sys.exit(1)

    font = args.caption_font or find_cjk_font()
    if not font:
        sys.stderr.write("警告: 未找到 CJK 字体，字幕将跳过（caption 不烧入）\n")

    tmpdir = tempfile.mkdtemp(prefix="makevideo_")
    log = open(os.path.join(tmpdir, "log.txt"), "w", encoding="utf-8")
    try:
        clips = []
        for i, sc in enumerate(scenes):
            if not os.path.exists(sc.get("image", "")):
                sys.stderr.write("跳过镜头 %d: 图片不存在 %s\n" % (i, sc.get("image")))
                continue
            clip = build_scene_clip(sc, i, args.fps, args.width, args.height, font, tmpdir, log)
            if not clip:
                sys.stderr.write("镜头 %d 合成失败\n" % i)
                sys.exit(1)
            clips.append(clip)
        if not clips:
            sys.stderr.write("没有任何成功合成的镜头\n")
            sys.exit(1)

        # 拼接（concat demuxer，所有片段已统一参数）
        list_path = os.path.join(tmpdir, "list.txt")
        with open(list_path, "w", encoding="utf-8") as lf:
            for c in clips:
                lf.write("file '%s'\n" % os.path.abspath(c).replace("\\", "/"))

        out_args = ["-f", "concat", "-safe", "0", "-i", list_path]
        if args.bgm and os.path.exists(args.bgm):
            out_args += ["-i", args.bgm, "-filter_complex",
                         "[0:v]concat=n=%d:v=1:a=1[v];[1:a]volume=0.25[a]" % len(clips),
                         "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                         "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", args.out]
        else:
            out_args += ["-c", "copy", args.out]
        if not ff(out_args, log):
            sys.stderr.write("最终拼接失败，详见日志 %s\n" % log.name)
            sys.exit(1)
    finally:
        log.close()
    print(os.path.abspath(args.out))
    shutil.rmtree(tmpdir, ignore_errors=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
