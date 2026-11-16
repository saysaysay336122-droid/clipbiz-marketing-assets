"""회차 설계서(JSON)와 시작 사진으로 사진 콘티 영상(애니매틱)을 만든다. 영상 생성 전에 구성과 길이를 확인하는 용도.

사용: python3 animatic.py 설계서.json 사진폴더 음악.wav 출력.mp4 [끝화면.png]
사진폴더에는 샷 id 이름의 png(S1.png 등). 재사용 샷은 원본 샷 사진을 쓴다.
comp 샷: chat(메신저), rewind(되감기), endcard(끝 화면). 대사는 화자 이름을 붙인 자막으로 보여 준다(완성본에는 이름 없음).
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import sfx  # noqa: E402

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
W, H = 1080, 1920


def font(sz, bold=True):
    return ImageFont.truetype(FONT if bold else FONT_R, sz)


def cover(im):
    im = im.convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s + 0.5), int(im.height * s + 0.5)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def text_c(d, y, txt, sz, fill=(255, 255, 255), stroke=5):
    f = font(sz)
    for k, line in enumerate(txt.split("\n")):
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y + k * int(sz * 1.3)), line, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def wrap(txt, n=14):
    out, cur = [], ""
    for wd in txt.split(" "):
        if len(cur) + len(wd) + 1 > n and cur:
            out.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    out.append(cur)
    return "\n".join(out[:2])


def base_overlay(caption=None, tag=None, small=None, note=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.text((28, 26), "AI로 만든 가상인물", font=font(30, False), fill=(255, 255, 255, 200))
    d.text((W - 300, 26), "사진 콘티(생성 전)", font=font(30, False), fill=(255, 230, 120, 230))
    if caption:
        text_c(d, 150, wrap(caption, 13), 64)
    if tag:
        f = font(46)
        w = d.textlength(tag, font=f)
        d.rounded_rectangle((60, 1330, 60 + w + 50, 1410), 14, fill=(20, 20, 20, 210))
        d.text((85, 1340), tag, font=f, fill=(255, 214, 64))
    if small:
        d.text((W - 230, 90), small, font=font(40), fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    if note:
        f = font(38, False)
        w = d.textlength(note, font=f)
        d.rounded_rectangle((40, 300, 40 + w + 40, 360), 12, fill=(0, 0, 0, 150))
        d.text((60, 306), note, font=f, fill=(255, 255, 255, 235))
    return ov


def sub_overlay(speaker, line):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    text_c(d, 1120, wrap(f"{speaker}: {line}", 15), 60)
    return ov


def chat_frames(msgs, bg, title="준", me="은서"):
    frames = []
    back = bg.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.55))
    meas = ImageDraw.Draw(back.copy())
    total = 0
    for m in msgs:
        body = m.split(":", 1)[1].strip()
        n, cur = 1, ""
        for wd in body.split(" "):
            cand = (cur + " " + wd).strip()
            if meas.textlength(cand, font=font(54, False)) > 600 and cur:
                n += 1
                cur = wd
            else:
                cur = cand
        total += 34 + 68 * n + 34
    for k in range(1, len(msgs) + 1):
        im = back.copy()
        d = ImageDraw.Draw(im)
        x0, y0, x1 = 70, 330, 1010
        y1 = min(1640, max(y0 + 760, y0 + 180 + total + 50))
        d.rounded_rectangle((x0, y0, x1, y1), 50, fill=(246, 246, 248))
        d.rectangle((x0, y0 + 40, x1, y0 + 130), fill=(236, 236, 240))
        d.text((x0 + 40, y0 + 62), title, font=font(44), fill=(30, 30, 30))
        y = y0 + 180
        for m in msgs[:k]:
            who, body = m.split(":", 1)
            body = body.strip()
            draft = who.strip() == "지움"
            mine = who.strip() == me or draft
            f = font(54, False)
            lines = []
            cur = ""
            for wd in body.split(" "):
                cand = (cur + " " + wd).strip()
                if d.textlength(cand, font=f) > 600 and cur:
                    lines.append(cur)
                    cur = wd
                else:
                    cur = cand
            lines.append(cur)
            bh = 34 + 68 * len(lines)
            bw = max(d.textlength(l, font=f) for l in lines) + 50
            bx = x1 - 40 - bw if mine else x0 + 40
            fill = (232, 232, 236) if draft else ((196, 226, 255) if mine else (255, 255, 255))
            d.rounded_rectangle((bx, y, bx + bw, y + bh), 26, fill=fill, outline=(205, 205, 212) if draft else (220, 220, 225))
            for i, l in enumerate(lines):
                d.text((bx + 26, y + 15 + i * 68), l, font=f, fill=(80, 80, 88) if draft else (25, 25, 25))
                if draft:
                    lw = d.textlength(l, font=f)
                    d.line((bx + 22, y + 15 + i * 68 + 40, bx + 30 + lw, y + 15 + i * 68 + 40), fill=(215, 70, 70), width=3)
            if draft:
                d.text((bx - 100, y + bh / 2 - 22), "지움", font=font(34), fill=(215, 70, 70))
            y += bh + 34
        frames.append(im)
    return frames


def coin(d, cx, cy, r, lit):
    rim, face, hole = ((214, 170, 80), (186, 140, 58), (28, 22, 16)) if lit else ((96, 84, 64), (74, 66, 52), (20, 18, 16))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rim)
    d.ellipse((cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8), fill=face)
    h = r * 0.32
    d.rectangle((cx - h, cy - h, cx + h, cy + h), fill=hole)


def coin_string(img, labels):
    """끝 화면 엽전 꾸러미: 지난 닢은 어둡게 이름과 함께, 이번 닢만 밝게."""
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)
    n = len(labels)
    per_row = 6 if n > 7 else n
    rows = [labels[i:i + per_row] for i in range(0, n, per_row)]
    k = 0
    for ri, row in enumerate(rows):
        cy = 640 + ri * 250
        gap = min(150, (W - 120) // max(1, len(row)))
        x0 = (W - gap * (len(row) - 1)) // 2
        d.line((x0 - 60, cy, x0 + gap * (len(row) - 1) + 60, cy), fill=(170, 40, 40), width=6)
        for j, lab in enumerate(row):
            k += 1
            lit = k == n
            cx = x0 + j * gap
            coin(d, cx, cy, 74 if lit else 58, lit)
            f = font(38 if lit else 32, lit)
            w = d.textlength(lab, font=f)
            d.text((cx - w / 2, cy + (92 if lit else 74)), lab, font=f, fill=(255, 226, 150) if lit else (170, 165, 155))
            num = f"{k}"
            fn = font(26, False)
            d.text((cx - d.textlength(num, font=fn) / 2, cy - (120 if lit else 100)), num, font=fn, fill=(200, 195, 185))
    return img


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    sdir, music, out = sys.argv[2], sys.argv[3], sys.argv[4]
    endcard = sys.argv[5] if len(sys.argv) > 5 else None
    ch = spec["characters"]
    tmp = tempfile.mkdtemp()
    segs = []
    shots = {s["id"]: s for s in spec["shots"]}
    prev_img = None
    events = []
    for i, sh in enumerate(spec["shots"]):
        a, b = sh["t"]
        dur = round(b - a, 3)
        events += [tuple(e) for e in sh.get("sfx", [])]
        seg = os.path.join(tmp, f"seg{i:02d}.mp4")
        ov = base_overlay(sh.get("caption") if sh["kind"] == "video" else None,
                          sh.get("tag"), sh.get("caption") if sh.get("comp") == "rewind" else None, sh.get("note"))
        if sh["kind"] == "video":
            src = sh.get("reuse") or sh["id"]
            img = cover(Image.open(os.path.join(sdir, f"{src}.png")))
            prev_img = img
            if sh.get("line"):
                sub = sub_overlay(ch[sh["speaker"]]["name"], sh["line"])
                ov = Image.alpha_composite(ov, sub)
            ip, op = os.path.join(tmp, f"i{i}.png"), os.path.join(tmp, f"o{i}.png")
            img.save(ip)
            ov.save(op)
            n = int(dur * 30)
            run(["ffmpeg", "-y", "-loop", "1", "-i", ip, "-i", op, "-filter_complex",
                 f"[0]zoompan=z='min(1+on*0.0015,1.08)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:s={W}x{H}:fps=30[v];[v][1]overlay,format=yuv420p",
                 "-frames:v", str(n), "-r", "30", seg])
        elif sh.get("comp") == "chat":
            frames = chat_frames(sh["chat"], prev_img or Image.new("RGB", (W, H), (40, 40, 40)),
                                 sh.get("chat_title", "준"), sh.get("chat_me", "은서"))
            cov = base_overlay(sh.get("caption"))
            lst = os.path.join(tmp, f"l{i}.txt")
            with open(lst, "w") as fh:
                for k, fr in enumerate(frames):
                    p = os.path.join(tmp, f"c{i}_{k}.png")
                    Image.alpha_composite(fr.convert("RGBA"), cov).convert("RGB").save(p)
                    fh.write(f"file '{p}'\nduration {dur / len(frames):.3f}\n")
                fh.write(f"file '{p}'\n")
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", "fps=30,format=yuv420p", "-t", str(dur), seg])
        elif sh.get("comp") == "rewind":
            img = prev_img or Image.new("RGB", (W, H), (40, 40, 40))
            frames = []
            for k in range(6):
                fr = img.copy().filter(ImageFilter.GaussianBlur(2 + k))
                d = ImageDraw.Draw(fr)
                for y in range(0, H, 24):
                    d.line((0, y + (k * 7) % 24, W, y + (k * 7) % 24), fill=(255, 255, 255), width=2)
                frames.append(Image.alpha_composite(fr.convert("RGBA"), ov).convert("RGB"))
            lst = os.path.join(tmp, f"l{i}.txt")
            with open(lst, "w") as fh:
                for k, fr in enumerate(frames):
                    p = os.path.join(tmp, f"r{i}_{k}.png")
                    fr.save(p)
                    fh.write(f"file '{p}'\nduration {dur / 6:.3f}\n")
                fh.write(f"file '{p}'\n")
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", "fps=30,format=yuv420p", "-t", str(dur), seg])
        else:
            img = cover(Image.open(endcard)) if endcard else Image.new("RGB", (W, H), (20, 18, 16))
            if sh.get("coins"):
                img = coin_string(img.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45)), sh["coins"])
            d = ImageDraw.Draw(img)
            text_c(d, 1240, sh.get("caption", "").replace(", ", "\n"), 64)
            p = os.path.join(tmp, f"e{i}.png")
            Image.alpha_composite(img.convert("RGBA"), base_overlay()).convert("RGB").save(p)
            run(["ffmpeg", "-y", "-loop", "1", "-i", p, "-vf", "fps=30,format=yuv420p", "-t", str(dur), seg])
        segs.append(seg)
    lst = os.path.join(tmp, "all.txt")
    with open(lst, "w") as fh:
        for s in segs:
            fh.write(f"file '{s}'\n")
    vid = os.path.join(tmp, "v.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid])
    total = spec["shots"][-1]["t"][1]
    fxw = os.path.join(tmp, "fx.wav")
    sfx.mix(total, fxw, events=events)
    mixw = os.path.join(tmp, "mix.wav")
    run(["ffmpeg", "-y", "-i", music, "-i", fxw, "-filter_complex",
         "[0]volume=0.45[m];[1]aresample=48000,pan=stereo|c0=c0|c1=c0[f];[m][f]amix=inputs=2:normalize=0,alimiter=limit=0.5:attack=1:release=50:level=disabled[a]",
         "-map", "[a]", "-ar", "48000", "-t", str(total), mixw])
    meas = subprocess.run(["ffmpeg", "-i", mixw, "-af", "loudnorm=I=-14:TP=-2:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-y", "-i", vid, "-i", mixw, "-filter_complex", f"[1]{ln},alimiter=limit=0.70:attack=1:release=50:level=disabled,aresample=48000[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "160k",
         "-t", str(total), "-movflags", "+faststart", out])
    print(out)


if __name__ == "__main__":
    main()
