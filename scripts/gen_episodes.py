#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_episodes.py —— 按《五灵混沌》前5集镜头方案，批量出分镜图并合成成片。
流程：
  1) 每个镜头用 comfy_gen.py 出图（AI 镜头）或 PIL 生成结尾金句卡；
  2) 逐集写 scenes.json，调 make_video.py 出每集 MP4；
  3) ffmpeg concat 把 5 集合成完整成片 wuling_chengpian.mp4。
仅用本地 ComfyUI（Z-Image-Turbo）+ ffmpeg，零花费、零云端。
"""
import os, sys, subprocess, json, time, shutil, tempfile

ROOT = "D:/ComfyUI"
OUT = os.path.join(ROOT, "output", "wuling")
os.makedirs(OUT, exist_ok=True)
COMFY_GEN = os.path.join(ROOT, "comfy_gen.py")
MAKE_VIDEO = os.path.join(ROOT, "make_video.py")
VENV_PY = os.path.join(ROOT, "venv", "Scripts", "python.exe")
URL = "http://127.0.0.1:8188"

STYLE = "，统一日式赛璐璐动漫风格，线条清晰干净，古风玄幻，蒸汽朋克机关元素，杰作，高细节"

# 角色外貌锁定：每镜都附带同一段描述，配合参考图 img2img，保证人脸/服饰一致
DESC_YECHEN = "主角叶尘：黑发黑瞳、剑眉星目、清瘦少年、身高颀长、束发、穿灰布破旧交领长衫。"
DESC_QIN = "秦昭月：红裙少女、眉目凌厉、高马尾。"
REF_YECHEN = os.path.join(ROOT, "refs", "ref_yech.png")
REF_QIN = os.path.join(ROOT, "refs", "ref_qin.png")
I2I_DENOISE = 0.80  # 图生图去噪：过低场景换不动，过高脸会漂，0.80 为实测平衡点


def route_shot(prompt):
    """按提示词判定该镜用哪张角色参考图。返回 (ref_path 或 None, 附加描述, denoise)。"""
    if ("秦昭月" in prompt) or ("红裙" in prompt):
        return REF_QIN, DESC_QIN, I2I_DENOISE
    if ("叶尘" in prompt) or ("少年" in prompt):
        return REF_YECHEN, DESC_YECHEN, I2I_DENOISE
    return None, "", 0.0  # 纯空镜：文生图，无面部需求

# 镜头数据：(集, 镜号, 类型 ai/card, 提示词或金句文本, 时长s, 字幕)
# 字幕尽量简短，便于烧入视频
SHOTS = [
    # ===== 第1集：五灵根废物 =====
    (1, 1, "ai", "天工宗灵测台广场，成千上万弟子围观，天空一艘机关飞舟飘过，中央高台发光灵晶，白天宏大场面", 5, "灵测台·千人围观"),
    (1, 2, "ai", "高台上的考官挥手向广场喊话，台下人群仰望，庄严肃穆", 3, "考官点名"),
    (1, 3, "ai", "一名黑袍破旧但身形挺直的少年从人群中走出，古风玄幻", 3, "叶尘出场"),
    (1, 4, "ai", "特写少年将手按在发光灵晶上，灵晶透出金木水火土五色微光，暗淡微弱", 4, "测灵·五色暗淡"),
    (1, 5, "ai", "围观弟子哄笑嘲讽的群像，多人面孔，轻蔑表情，古代宗门广场", 3, "全场哄笑"),
    (1, 6, "ai", "红裙少女从贵宾席起身穿过人群走到少年面前取出婚书，压迫感，古风", 4, "秦昭月退婚"),
    (1, 7, "ai", "特写红裙少女当众撕毁一张婚书，碎纸片飘落，古风", 3, "撕毁婚书"),
    (1, 8, "ai", "少年低着头碎纸片被风吹起，表情难辨，孤独", 3, "低头不语"),
    (1, 9, "ai", "深夜破旧杂役院小屋，月光从破窗洒入，冷色调，孤寂氛围", 3, "深夜破屋"),
    (1, 10, "ai", "少年躺在布满灰尘草席上，月光照脸，眼神空洞如枯井", 4, "孤绝"),
    (1, 11, "ai", "特写少年胸口丹田亮起五道彩色光芒旋转编织成环，玄幻内视光芒", 5, "五色同调"),
    (1, 12, "ai", "特写少年猛然睁开的眼睛瞳孔收缩，震惊表情", 2, "惊觉"),
    (1, 13, "card", "五色同调，是废还是序？", 3, ""),
    # ===== 第2集：机关残骸里的秘密 =====
    (2, 1, "ai", "巨大露天废料场堆满报废机关兽残骸齿轮与锈铁，蒸汽余烟袅袅，白天", 4, "废料场全景"),
    (2, 2, "ai", "山羊胡中年管事把一把锈铲扔给少年并讥笑，傲慢神情，古风", 3, "林管事刁难"),
    (2, 3, "ai", "少年独自在废料场铲废铁汗珠滴落，俯拍，古风", 3, "独自劳作"),
    (2, 4, "ai", "特写一块刻满古文铭文的甲片泛出淡蓝光芒，机关残骸，玄幻", 4, "古铭文共振"),
    (2, 5, "ai", "少年侧脸低声自语专注神情，古风", 3, "低声自语"),
    (2, 6, "ai", "少年催动体内光芒对准残骸金色光芒暴涨铁精熔化流淌，玄幻光效", 5, "金系熔铁"),
    (2, 7, "ai", "特写少年的手掌毫发无伤金色微光，古风", 3, "手掌无伤"),
    (2, 8, "ai", "少年近景自信自语坚定表情，古风玄幻", 3, "五行轮转"),
    (2, 9, "card", "规则在手，废物二字不过是无知者的标签。", 3, ""),
    # ===== 第3集：夜袭 =====
    (3, 1, "ai", "雨夜破屋外景雨刚停地面反射月光潮湿阴暗，古风", 3, "雨夜破屋"),
    (3, 2, "ai", "少年躺在草席上攥着碎灵石屋内昏暗警觉，古风", 3, "攥灵石"),
    (3, 3, "ai", "木门被一脚踹开三个醉汉冲入手持凶器，古风", 3, "夜袭闯入"),
    (3, 4, "ai", "近景三人围住少年抢夺灵石嘲讽，古风", 3, "夺灵石"),
    (3, 5, "ai", "少年低声说放下被一脚踢中腹部痛苦表情，古风", 3, "挨踢"),
    (3, 6, "ai", "少年被补踢滚到墙角撞翻水盆泥水四溅，古风", 3, "滚落墙角"),
    (3, 7, "ai", "特写少年右臂皮肤硬化浮出暗金色金属光泽一拳击飞敌人，慢动作玄幻", 5, "金系铁臂爆发"),
    (3, 8, "ai", "另外两人惊慌后退少年低头看自己恢复正常的右手，古风", 3, "敌人惊慌"),
    (3, 9, "ai", "少年近景瞳孔震动震惊于自己的力量，古风", 3, "确认觉醒"),
    (3, 10, "card", "金系觉醒——铁臂。", 3, ""),
    # ===== 第4集：禁闭室 =====
    (4, 1, "ai", "半埋在地下的铁笼禁闭室建筑阴沉压抑仰拍，古风", 3, "禁闭室门外"),
    (4, 2, "ai", "少年被铁链绑着拖到禁闭室门前阴冷管事宣布惩罚，古风", 4, "押入禁闭"),
    (4, 3, "ai", "铁门打开漆黑一片管事一脚把少年踹入门轰然关闭，阴暗，古风", 4, "踹入黑门"),
    (4, 4, "ai", "纯黑场景中十对红色眼睛依次亮起如同饿兽，玄幻暗黑", 4, "十傀儡红眼"),
    (4, 5, "ai", "中景少年以金色硬化右臂格挡四面袭来钢刃铁拳血溅铁壁混战，玄幻", 6, "绝境混战"),
    (4, 6, "ai", "少年全身覆盖岩石铠甲一拳击碎机关傀儡岩石碎片飞溅，玄幻", 5, "岩甲觉醒"),
    (4, 7, "card", "濒死时刻，第二属性觉醒——岩甲。", 3, ""),
    # ===== 第5集：铁笼塌了 =====
    (5, 1, "ai", "禁闭室内少年靠墙角全身岩石铠甲满地破碎傀儡浑身是血但眼神明亮，玄幻", 4, "战果满地"),
    (5, 2, "ai", "少年近景喘气却嘴角上扬自信，古风玄幻", 3, "沉静自信"),
    (5, 3, "ai", "室外白天阴天管事与十余杂役围观群像，古风", 3, "门外围观"),
    (5, 4, "ai", "大全景铁门被岩石拳头从内部轰开撕裂飞出少年走出碎片慢动作，玄幻爆发", 5, "铁笼塌了"),
    (5, 5, "ai", "中景杂役们后退三步管事笑容僵住碎块滚动，古风", 4, "群像震慑"),
    (5, 6, "ai", "特写暗金色拳头停在管事鼻尖前一寸未落下张力，古风玄幻", 3, "拳停鼻尖"),
    (5, 7, "ai", "少年近景对管事说规矩改一下压迫，古风", 3, "规矩改一下"),
    (5, 8, "ai", "全景少年穿过自动让路的人群走向废料场背影，古风", 4, "转身离场"),
    (5, 9, "card", "七十二小时，规矩换了人。", 3, ""),
]

CARD_FONT = r"C:/Windows/Fonts/msyh.ttc"


def gen_ai(ep, shot, prompt):
    prefix = "wuling_e%d_s%d" % (ep, shot)
    # 去重：若 wuling 目录已存在该前缀的图片，直接复用
    import glob
    existing = glob.glob(os.path.join(OUT, prefix + "_*.png"))
    if existing:
        return existing[0]
    ref, desc, denoise = route_shot(prompt)
    full = prompt + desc + STYLE
    for attempt in range(2):
        try:
            cmd = [VENV_PY, COMFY_GEN, "--prompt", full, "--model", "zimage",
                   "--out", prefix, "--url", URL, "--seed", str(1000 * ep + 10 * shot)]
            if ref:
                # 角色镜：以设定稿为底图生图，锁定人脸/服饰
                cmd += ["--ref", ref, "--denoise", str(denoise)]
            else:
                cmd += ["--width", "1152", "--height", "648"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            for line in r.stdout.splitlines():
                line = line.strip()
                if line.endswith(".png") and os.path.exists(line):
                    # 真实落点（comfy_gen 打印绝对路径），移入 wuling/ 保持原文件名
                    dest = os.path.join(OUT, os.path.basename(line))
                    if os.path.abspath(line) != os.path.abspath(dest):
                        shutil.move(line, dest)
                    return dest
        except Exception as e:
            sys.stderr.write("AI 出图异常 ep%d s%d: %s\n" % (ep, shot, e))
        time.sleep(2)
    return None


def gen_card(text):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1920, 1080), (10, 10, 14))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(CARD_FONT, 84)
    except Exception:
        font = ImageFont.load_default()
    # 简单按标点/字数折行，最多 3 行
    max_chars = 14
    lines = []
    for i in range(0, len(text), max_chars):
        lines.append(text[i:i + max_chars])
    lines = lines[:3]
    lh = 110
    total_h = lh * len(lines)
    y = (1080 - total_h) // 2
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((1920 - w) // 2, y), ln, font=font, fill=(224, 184, 74))
        y += lh
    return img


def main():
    # 清理旧产物（换风格/换角色方案后必须重跑，否则去重会跳过）
    import glob as _glob
    for pat in ("wuling_*.png", "wuling_*.mp4", "scenes_e*.json"):
        for f in _glob.glob(os.path.join(OUT, pat)):
            try:
                os.remove(f)
            except Exception:
                pass
    log = open(os.path.join(OUT, "gen_episodes.log"), "w", encoding="utf-8")
    # 1) 出图
    results = {}  # (ep, shot) -> image path
    cards = {}    # (ep, shot) -> card path
    for ep, shot, kind, content, dur, cap in SHOTS:
        if kind == "ai":
            p = gen_ai(ep, shot, content)
            if p:
                results[(ep, shot)] = p
                log.write("OK ai e%d s%d -> %s\n" % (ep, shot, p))
            else:
                log.write("FAIL ai e%d s%d\n" % (ep, shot))
        else:
            path = os.path.join(OUT, "wuling_card_e%d_s%d.png" % (ep, shot))
            gen_card(content).save(path)
            cards[(ep, shot)] = path
            log.write("OK card e%d s%d -> %s\n" % (ep, shot, path))
        log.flush()

    # 2) 逐集合成
    episode_mp4s = []
    for ep in range(1, 6):
        scenes = []
        for s in SHOTS:
            if s[0] != ep:
                continue
            key = (s[0], s[1])
            if s[2] == "ai":
                img = results.get(key)
            else:
                img = cards.get(key)
            if not img:
                log.write("skip e%d s%d (no image)\n" % key)
                continue
            scenes.append({"image": img, "duration": s[4], "caption": s[5]})
        if not scenes:
            log.write("episode %d 无镜头，跳过\n" % ep)
            continue
        mani = os.path.join(OUT, "scenes_e%d.json" % ep)
        with open(mani, "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
        mp4 = os.path.join(OUT, "wuling_ep%d.mp4" % ep)
        r = subprocess.run([VENV_PY, MAKE_VIDEO, "--manifest", mani, "--out", mp4],
                           capture_output=True, text=True, timeout=600)
        if r.returncode == 0 and os.path.exists(mp4):
            episode_mp4s.append(mp4)
            log.write("OK episode %d -> %s\n" % (ep, mp4))
        else:
            log.write("FAIL episode %d: %s\n" % (ep, r.stderr[-500:]))
        log.flush()

    # 3) 拼接成片
    if len(episode_mp4s) >= 2:
        final = os.path.join(OUT, "wuling_chengpian.mp4")
        lst = os.path.join(OUT, "concat_list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for m in episode_mp4s:
                f.write("file '%s'\n" % os.path.abspath(m).replace("\\", "/"))
        r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                           "-c", "copy", final], capture_output=True, text=True, timeout=600)
        if r.returncode == 0 and os.path.exists(final):
            log.write("OK 成片 -> %s\n" % final)
        else:
            log.write("FAIL 成片: %s\n" % r.stderr[-500:])
    else:
        log.write("集数不足，未拼接成片\n")
    log.close()
    print("完成。成片目录:", OUT)


if __name__ == "__main__":
    main()
