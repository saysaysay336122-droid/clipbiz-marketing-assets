# 홍책사 카드 영상 렌더(2026-11-27). 사용: python3 build.py [id ...]
# 위쪽 1100행은 홍책사 장면(천천히 확대), 아래는 먹색 판에 글. 오른쪽 150px, 아래 320px은 비운다.
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
import hcs_music  # noqa: E402
import sfx  # noqa: E402
from spec import ALL, STILLS  # noqa: E402

SRC_VIDEO = ROOT / "w/261125/today/hcs_today1125.mp4"
W, H, TOPH, FPS = 1080, 1920, 1100, 30
BG = (22, 32, 28)
FG = (242, 239, 230)
SUB = (201, 207, 201)
MUTE = (150, 160, 154)
GOLD = (222, 184, 108)
RED = (200, 64, 47)
FD = "/usr/share/fonts/opentype/noto/"
SERIF = FD + "NotoSerifCJK-Bold.ttc"
SANS_B = FD + "NotoSansCJK-Bold.ttc"
SANS = FD + "NotoSansCJK-Regular.ttc"
X0, XMAX = 80, W - 150
OUT = HERE / "out"
TMP = HERE / "tmp"
OUT.mkdir(exist_ok=True)
TMP.mkdir(exist_ok=True)


def font(path, size):
    return ImageFont.truetype(path, size, index=1)


def stills():
    d = TMP / "stills"
    d.mkdir(exist_ok=True)
    for name, t in STILLS.items():
        p = d / f"{name}.png"
        if p.exists():
            continue
        raw = d / f"{name}_raw.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(SRC_VIDEO), "-frames:v", "1", str(raw)], check=True)
        im = cv2.imread(str(raw))
        mask = np.zeros(im.shape[:2], np.uint8)
        mask[632:700, 28:312] = 255  # 장면에 박힌 AI 표기(35~303, 640~691)를 지우고 새 표기를 고정 위치에 얹는다
        im = cv2.inpaint(im, mask, 9, cv2.INPAINT_TELEA)
        cv2.imwrite(str(p), im)
    return d


def text_w(draw, s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0]


def fit(draw, lines, path, size, maxw, minsize=40):
    while size > minsize:
        f = font(path, size)
        if max(text_w(draw, s, f) for s in lines) <= maxw:
            return f
        size -= 2
    return font(path, minsize)


def coin(draw, cx, cy, r):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD)
    draw.ellipse((cx - r * 0.78, cy - r * 0.78, cx + r * 0.78, cy + r * 0.78), outline=(160, 120, 50), width=max(2, r // 10))
    h = r * 0.32
    draw.rectangle((cx - h, cy - h, cx + h, cy + h), fill=BG)


def overlay(sc, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # 사진 아래 경계를 먹색으로 녹인다
    for y in range(TOPH - 170, TOPH):
        a = int(255 * ((y - (TOPH - 170)) / 170) ** 1.6)
        d.line([(0, y), (W, y)], fill=BG + (a,))
    d.rectangle((0, TOPH, W, H), fill=BG + (255,))
    # AI 표기(처음부터 끝까지 같은 자리)
    lf = font(SANS, 30)
    lw = text_w(d, "AI로 만든 가상인물", lf)
    d.rounded_rectangle((35, 640, 35 + lw + 36, 691), radius=10, fill=(20, 18, 16, 170))
    d.text((35 + 18, 644), "AI로 만든 가상인물", font=lf, fill=(240, 236, 228))
    y = 1060 if sc.get("hook") else 1080
    # 꼬리표
    tf = font(SANS_B, 36)
    tw = text_w(d, sc["tag"], tf)
    x = X0
    if sc.get("end"):
        coin(d, X0 + 30, y + 32, 30)
        x = X0 + 76
    pill = RED if sc.get("rest") else GOLD
    d.rounded_rectangle((x, y, x + tw + 44, y + 64), radius=32, fill=pill)
    d.text((x + 22, y + 6), sc["tag"], font=tf, fill=(255, 255, 255) if sc.get("rest") else BG)
    y += 100
    big = sc["big"]
    size = 104 if sc.get("hook") else (132 if len(big) == 1 and len(big[0]) <= 5 else 92)
    bf = fit(d, big, SERIF, size, XMAX - X0)
    lh = int(bf.size * 1.22)
    for s in big:
        d.text((X0, y), s, font=bf, fill=FG)
        y += lh
    if sc.get("accent"):
        af = fit(d, [sc["accent"]], SERIF, sc.get("accent_size", 72), XMAX - X0, 44)
        y += 6
        d.text((X0, y), sc["accent"], font=af, fill=GOLD)
        y += int(af.size * 1.3)
    if sc.get("body"):
        y += 14
        lines = sc["body"].split("\n")
        f = fit(d, lines, SANS, 46, XMAX - X0, 34)
        for s in lines:
            d.text((X0, y), s, font=f, fill=SUB)
            y += int(f.size * 1.45)
    if sc.get("url"):
        y += 22
        uf = font(SANS_B, 46)
        uw = text_w(d, sc["url"], uf)
        d.rounded_rectangle((X0, y, X0 + uw + 56, y + 78), radius=39, fill=GOLD)
        d.text((X0 + 28, y + 8), sc["url"], font=uf, fill=BG)
        sf = font(SANS, 36)
        d.text((X0 + uw + 80, y + 18), sc.get("small", ""), font=sf, fill=SUB)
        y += 100
    if sc.get("foot"):
        ff = fit(d, [sc["foot"]], SANS, 34, XMAX - X0, 26)
        d.text((X0, max(y + 18, 1530)), sc["foot"], font=ff, fill=MUTE)
    if sc.get("end"):
        nf = font(SANS, 28)
        d.text((X0, 1572), "재미와 자기 성찰을 위한 풀이예요.", font=nf, fill=MUTE)
    assert y < 1600, (sc["tag"], y)
    im.save(path)


def scene_clip(sc, i, vid, sdir):
    n = int(round(sc["dur"] * FPS))
    ov = TMP / f"{vid}_s{i}.png"
    overlay(sc, ov)
    out = TMP / f"{vid}_s{i}.mp4"
    zin = i % 2 == 0
    z = f"1+0.06*on/{n}" if zin else f"1.06-0.06*on/{n}"
    fy = 0.42
    fade = "" if sc.get("hook") else ",fade=in:st=0:d=0.16:alpha=1"
    fc = (f"[0]crop=1080:{TOPH}:0:0,scale=2160:-1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih*{fy}-(ih/zoom*{fy})':"
          f"d={n}:s=1080x{TOPH}:fps={FPS},pad={W}:{H}:0:0:color=0x16201C,format=yuv420p[bg];"
          f"[1]format=rgba{fade}[ov];[bg][ov]overlay=0:0:shortest=1,format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(sdir / f"{sc['still']}.png"), "-loop", "1", "-framerate", str(FPS),
                    "-t", f"{n / FPS:.3f}", "-i", str(ov), "-filter_complex", fc, "-frames:v", str(n), "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def audio(v, total):
    style, key = v["music"]
    mw = TMP / f"{v['id']}_music.wav"
    hcs_music.make(total, [(0, total, style, key)], str(mw))
    ev = [(0.0, "coin", 0.9)]
    t = 0.0
    for i, sc in enumerate(v["scenes"]):
        if i > 0:
            ev.append((t, "thunk" if sc.get("rest") else ("whoosh" if not sc.get("end") else "coin"), 0.55))
        if sc.get("end"):
            ev.append((t + 0.5, "logo", 0.8))
        t += sc["dur"]
    aw = TMP / f"{v['id']}_mix.wav"
    sfx.mix(total, str(aw), music=str(mw), music_gain=0.55, events=ev)
    return aw


def loudnorm(src, out):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", "loudnorm=I=-14:TP=-2:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    js = r.stderr[r.stderr.rfind("{"): r.stderr.rfind("}") + 1]
    m = json.loads(js)
    af = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "libx264", "-preset", "veryfast", "-b:v", "4500k", "-maxrate", "6000k", "-bufsize", "9000k", "-pix_fmt", "yuv420p", "-af", af, "-ac", "2", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(out)], check=True)


def build(v):
    sdir = stills()
    clips = [scene_clip(sc, i, v["id"], sdir) for i, sc in enumerate(v["scenes"])]
    lst = TMP / f"{v['id']}_list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    silent = TMP / f"{v['id']}_v.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)], check=True)
    total = sum(sc["dur"] for sc in v["scenes"])
    aw = audio(v, total)
    mux = TMP / f"{v['id']}_mux.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(aw), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "pcm_s16le", "-shortest", str(mux.with_suffix(".mov"))], check=True)
    out = OUT / f"hcs_{v['id']}.mp4"
    loudnorm(mux.with_suffix(".mov"), out)
    return out


if __name__ == "__main__":
    ids = sys.argv[1:]
    for v in ALL:
        if ids and v["id"] not in ids:
            continue
        print(build(v))
