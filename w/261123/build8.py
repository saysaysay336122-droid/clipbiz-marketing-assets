"""홍책사 8화 17:59 탈출 작전 편집. 프레임 단위로 바탕 영상, 색보정, 효과, HUD, 자막을 한 번에 합성한다.
사용: python3 build8.py [출력.mp4] [--from 초 --to 초]
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import animatic as AN  # noqa: E402

W, H, FPS = 1080, 1920, 30
D = "/home/claude/ep8"
ST = f"{D}/gen/stills"
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_FC = {}


def F(path, size):
    k = (path, size)
    if k not in _FC:
        if path.endswith(".ttc"):
            for i in range(10):
                f = ImageFont.truetype(path, size, index=i)
                if "KR" in f.getname()[0]:
                    break
        else:
            f = ImageFont.truetype(path, size)
        _FC[k] = f
    return _FC[k]


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- 소스
class Clip:
    def __init__(self, path, t0=0.0, t1=None):
        info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", path],
                                         capture_output=True, text=True).stdout)
        s = info["streams"][0]
        self.w, self.h = s["width"], s["height"]
        a, b = s["r_frame_rate"].split("/")
        self.fps = float(a) / float(b)
        dur = float(info["format"]["duration"])
        t1 = dur if t1 is None else min(dur, t1)
        self.t0 = t0
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", path,
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        n = len(raw) // (self.w * self.h * 3)
        self.frames = np.frombuffer(raw[: n * self.w * self.h * 3], np.uint8).reshape(n, self.h, self.w, 3)

    def at(self, st):
        i = int(round((st - self.t0) * self.fps))
        i = min(len(self.frames) - 1, max(0, i))
        return Image.fromarray(self.frames[i])


_STILL = {}


def still(name):
    if name not in _STILL:
        _STILL[name] = Image.open(f"{ST}/{name}.png").convert("RGB")
    return _STILL[name]


def view(img, z=1.0, cx=0.5, cy=0.5, dx=0.0, dy=0.0):
    """img에서 9:16 창을 잘라 1080x1920으로. z는 확대, cx cy는 중심(0~1), dx dy는 화면 흔들림(px, 출력 기준)."""
    iw, ih = img.size
    cw, ch = iw / z, ih / z
    x0 = cx * iw - cw / 2 - dx * iw / W / z
    y0 = cy * ih - ch / 2 - dy * ih / H / z
    x0 = min(iw - cw, max(0, x0))
    y0 = min(ih - ch, max(0, y0))
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


def shake(t, amp=14, f=37):
    return amp * math.sin(t * f * 2.1), amp * 0.7 * math.cos(t * f * 1.7)


# ---------------------------------------------------------------- 색과 효과(numpy)
def arr(img):
    return np.asarray(img, dtype=np.float32)


def grade(a, kind, k=1.0):
    if kind is None or k <= 0:
        return a
    if kind == "frozen":
        lum = a.mean(axis=2, keepdims=True)
        b = a * 0.42 + lum * 0.58
        b = b * np.array([0.88, 0.97, 1.10], np.float32) * 0.96 + np.array([0, 4, 10], np.float32)
    elif kind == "warm":
        b = a * np.array([1.07, 1.01, 0.90], np.float32) + np.array([6, 2, 0], np.float32)
    elif kind == "evening":
        b = a * np.array([1.0, 0.96, 0.94], np.float32) * 0.96
    elif kind == "desat":
        lum = a.mean(axis=2, keepdims=True)
        b = a * 0.7 + lum * 0.3
    elif kind == "rewind":
        lum = a.mean(axis=2, keepdims=True)
        b = (a * 0.45 + lum * 0.55) * np.array([1.0, 0.98, 1.08], np.float32) + 8
    else:
        return a
    return a * (1 - k) + b * k


def hblur(a, amount):
    """가로 방향 흐림(휩 팬)."""
    if amount < 2:
        return a
    n = 7
    acc = np.zeros_like(a)
    for i in range(n):
        acc += np.roll(a, int((i - n // 2) * amount / n), axis=1)
    return acc / n


def chroma(a, px):
    b = a.copy()
    b[..., 0] = np.roll(a[..., 0], px, axis=1)
    b[..., 2] = np.roll(a[..., 2], -px, axis=1)
    return b


def scanlines(a, strength=0.18):
    m = np.ones((H, 1, 1), np.float32)
    m[::6] = 1 - strength
    m[1::6] = 1 - strength * 0.5
    return a * m


def darken_top(a, k, edge=0.45):
    """형광등이 꺼지는 느낌: 위쪽부터 어둡게."""
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    m = 1 - k * np.clip((edge + 0.25 - y) / 0.5 + 0.5, 0.35, 1.0)
    return a * m


# ---------------------------------------------------------------- 겹치는 그림(RGBA)
_OV = {}


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def cached(key, fn):
    if key not in _OV:
        _OV[key] = fn()
    return _OV[key]


def text_center(d, y, s, f, fill=(255, 255, 255, 255), stroke=6, sfill=(0, 0, 0, 255)):
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)


def ov_ai():
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        t = "AI로 만든 가상인물"
        f = F(FR, 26)
        w = d.textlength(t, font=f)
        d.rounded_rectangle((26, 40, 26 + w + 28, 84), 12, fill=(0, 0, 0, 120))
        d.text((40, 46), t, font=f, fill=(255, 255, 255, 215))
        return im
    return cached("ai", mk)


def ov_caption(s, y=250):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        lines = s.split("\n") if "\n" in s else AN.wrap(s, 13).split("\n")
        for i, l in enumerate(lines):
            text_center(d, y + i * 90, l, F(FB, 66), stroke=6)
        return im
    return cached(("cap", s, y), mk)


def ov_sub(s, size=60):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        lines = AN.wrap(s, 14).split("\n")
        y = 1150 - (len(lines) - 1) * 42
        for i, l in enumerate(lines):
            text_center(d, y + i * 84, l, F(FB, size), stroke=5)
        return im
    return cached(("sub", s, size), mk)


def ov_small_sub(s):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        text_center(d, 1180, s, F(FB, 46), fill=(240, 240, 240, 255), stroke=4)
        return im
    return cached(("ssub", s), mk)


def ov_tag(s):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, 46)
        w = d.textlength(s, font=f)
        x1 = 1040
        x0 = x1 - w - 48
        d.rounded_rectangle((x0, 990, x1, 1064), 18, fill=(20, 20, 20, 200))
        d.text((x0 + 24, 997), s, font=f, fill=(255, 214, 80, 255))
        return im
    return cached(("tag", s), mk)


def ov_clock(s, mode="normal", sub=None, big=False):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FM, 92 if big else 62)
        w = d.textlength(s, font=f)
        x = (W - w) / 2
        y = 110
        col = {"normal": (255, 255, 255, 240), "frozen": (150, 220, 255, 240), "red": (255, 90, 80, 250),
               "gold": (255, 210, 90, 255)}[mode]
        d.rounded_rectangle((x - 26, y - 10, x + w + 26, y + (108 if big else 78)), 16, fill=(0, 0, 0, 130))
        d.text((x, y), s, font=f, fill=col)
        if sub:
            fs = F(FB, 26)
            ws = d.textlength(sub, font=fs)
            d.rounded_rectangle((W / 2 - ws / 2 - 14, y + (112 if big else 82), W / 2 + ws / 2 + 14, y + (150 if big else 120)), 10, fill=(255, 214, 80, 220))
            d.text((W / 2 - ws / 2, y + (114 if big else 84)), sub, font=fs, fill=(20, 20, 20, 255))
        return im
    return cached(("clock", s, mode, sub, big), mk)


def ov_big(s, size=210, color=(255, 255, 255, 255), y=None, font=FM):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(font, size)
        bb = d.textbbox((0, 0), s, font=f)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        yy = (H - h) / 2 - bb[1] if y is None else y
        d.text(((W - w) / 2 - bb[0], yy), s, font=f, fill=color, stroke_width=8, stroke_fill=(0, 0, 0, 255))
        return im
    return cached(("big", s, size, color, y, font), mk)


def ov_reticle(cx, cy, label, red=False, r=78, lab_size=40):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        c = (255, 70, 60, 240) if red else (120, 255, 190, 230)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=6)
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=c)
        for a in range(4):
            ang = a * math.pi / 2
            x1, y1 = cx + math.cos(ang) * (r - 26), cy + math.sin(ang) * (r - 26)
            x2, y2 = cx + math.cos(ang) * (r + 26), cy + math.sin(ang) * (r + 26)
            d.line((x1, y1, x2, y2), fill=c, width=6)
        if label:
            f = F(FB, lab_size)
            w = d.textlength(label, font=f)
            d.rounded_rectangle((cx - w / 2 - 18, cy + r + 34, cx + w / 2 + 18, cy + r + 44 + lab_size + 18), 12, fill=(0, 0, 0, 160))
            d.text((cx - w / 2, cy + r + 40), label, font=f, fill=c)
        return im
    return cached(("ret", cx, cy, label, red, r, lab_size), mk)


def ov_gauge(pct, red=False):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        x, y, w, h = 60, 400, 380, 34
        c = (255, 80, 70, 240) if red else (120, 255, 190, 235)
        f = F(FB, 34)
        d.rounded_rectangle((x - 14, y - 58, x + w + 14, y + h + 16), 14, fill=(0, 0, 0, 140))
        d.text((x, y - 50), f"은신 {pct}%", font=f, fill=c)
        d.rounded_rectangle((x, y, x + w, y + h), 10, outline=c, width=4)
        d.rounded_rectangle((x + 6, y + 6, x + 6 + (w - 12) * pct / 100, y + h - 6), 6, fill=c)
        return im
    return cached(("gauge", pct, red), mk)


def ov_stamp(s, color=(220, 40, 40), cy=900, rot=-9):
    def mk():
        f = F(FB, 104)
        tmp = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        w = d.textlength(s, font=f)
        x0 = (900 - w) / 2 - 40
        d.rounded_rectangle((x0, 50, x0 + w + 80, 250), 26, outline=color + (235,), width=14)
        d.text((x0 + 40, 70), s, font=f, fill=color + (240,))
        tmp = tmp.rotate(rot, resample=Image.BICUBIC, expand=True)
        im = layer()
        im.alpha_composite(tmp, ((W - tmp.width) // 2, cy - tmp.height // 2))
        return im
    return cached(("stamp", s, color, cy, rot), mk)


def scaled(im, s, cx=W / 2, cy=H / 2):
    if abs(s - 1) < 0.01:
        return im
    w, h = int(W * s), int(H * s)
    big = im.resize((w, h), Image.BICUBIC)
    out = layer()
    out.alpha_composite(big.crop((int(w / 2 - cx), int(h / 2 - cy), int(w / 2 - cx) + W, int(h / 2 - cy) + H)) if s > 1 else big,
                        (0, 0) if s > 1 else (int(cx - w / 2), int(cy - h / 2)))
    return out


def ov_namecard(num_from, num_to=None, roll=0.0, green=False):
    """이름 카드. roll 0~1이면 숫자가 아래에서 위로 굴러 바뀐다."""
    key = ("card", num_from, num_to, round(roll, 2), green)

    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = 60, 1300, 640, 1580
        border = (80, 220, 120, 255) if green else (255, 214, 80, 255)
        d.rounded_rectangle((x0, y0, x1, y1), 22, fill=(10, 10, 14, 200), outline=border, width=6)
        d.text((x0 + 34, y0 + 20), "도윤", font=F(FB, 74), fill=(255, 214, 80, 255))
        d.text((x0 + 230, y0 + 50), "3년 차", font=F(FR, 44), fill=(235, 235, 235, 255))
        f = F(FB, 58)
        pre = "정시 퇴근 "
        d.text((x0 + 34, y0 + 140), pre, font=f, fill=(255, 255, 255, 255))
        nx = x0 + 34 + d.textlength(pre, font=f)
        nw = d.textlength("0번", font=f)
        # 숫자 창
        box = Image.new("RGBA", (int(nw) + 10, 90), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        if num_to is None or roll <= 0:
            bd.text((0, 4), f"{num_from}번", font=f, fill=(255, 255, 255, 255))
        else:
            off = int(86 * ease(roll))
            bd.text((0, 4 - off), f"{num_from}번", font=f, fill=(255, 255, 255, 255))
            bd.text((0, 90 - off), f"{num_to}번", font=f, fill=(120, 255, 160, 255))
        im.alpha_composite(box, (int(nx), y0 + 136))
        return im
    return cached(key, mk)


def ov_ring(cx, cy, r, alpha, color=(255, 255, 255), width=12):
    im = layer()
    if r > 2 and alpha > 0.01:
        d = ImageDraw.Draw(im)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (int(255 * alpha),), width=width)
        d.ellipse((cx - r * 0.93, cy - r * 0.93, cx + r * 0.93, cy + r * 0.93), outline=color + (int(110 * alpha),), width=max(2, width // 2))
    return im


def ov_flash(alpha, color=(255, 255, 255)):
    return Image.new("RGBA", (W, H), color + (int(255 * min(1, max(0, alpha))),))


def with_alpha(im, a):
    if a >= 0.999:
        return im
    if a <= 0.001:
        return None
    r, g, b, al = im.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def fade(lt, s, e, fin=0.12, fout=0.12, first=False):
    if lt < s or lt >= e:
        return 0.0
    a = 1.0
    if not first and fin > 0:
        a = min(a, (lt - s) / fin)
    if fout > 0:
        a = min(a, (e - lt) / fout)
    return max(0.0, min(1.0, a))


# ---------------------------------------------------------------- 시계
def clock_at(T):
    """절대 시간 T에서 HUD 시계 글자와 모드. None이면 숨김."""
    if T < 1.2:
        return None
    if T < 14.6:
        s = int(45 * (T - 1.2) / (14.6 - 1.2))
        return f"17:59:{s:02d}", "normal", "빨리 감기"
    if T < 15.4:
        return "17:59:45", "normal", None
    if T < 17.0:
        s = 45 + int(2 * (T - 15.4) / 1.6)
        return f"17:59:{s:02d}", "normal", None
    if T < 17.9:
        return "17:59:47", "normal", None
    if T < 26.85:
        return "17:59:47", "frozen", "정지"
    if T < 29.4:
        return None
    if T < 31.3:
        s = 47 + int(9 * (T - 29.4) / 1.9)
        return f"17:59:{min(56, s):02d}", "normal", None
    return None


# ---------------------------------------------------------------- 샷 정의
SPEC = json.load(open(f"{D}/ep08_spec_v6.json", encoding="utf-8"))
T = {s["id"]: tuple(s["t"]) for s in SPEC["shots"]}
ORDER = [s["id"] for s in SPEC["shots"]]
TOTAL = SPEC["shots"][-1]["t"][1]
ASR = json.load(open(f"{D}/asr.json", encoding="utf-8"))

# 사용 구간(원본 시각)
USE = {"S3": 0.5, "S4": 0.3, "S5": 0.2, "S7": 0.3, "S8": 0.6, "S10": 0.8, "S11": 0.6, "S12": 0.4,
       "S13": 0.5, "S14": 0.0, "S15": 0.6, "S16": 0.3}
# 대사 자막 구간(샷 안 시각)
SUBS = {
    "S3": ("작전 개시.", 1.24, 1.95),
    "S5": ("도윤 씨, 잠깐만.", 0.45, 1.6),
    "S8": ("종이 좀 넣어 줄래?", 0.52, 1.7),
    "S12": ("뭐야, 이거.", 0.12, 1.0),
    "S14": ("다 했는데, 왜 숨어요?", 0.12, 1.9),
    "S16": ("먼저 들어가 보겠습니다.", 0.98, 2.2),
    "S20": ("홍책사 한 수면, 됐지?", 0.0, 2.9),
}
CLIPS = {}


def clip(name, path=None):
    if name not in CLIPS:
        CLIPS[name] = Clip(path or f"{D}/clips/{name}.mp4")
    return CLIPS[name]


def base_frame(sid, lt, dur):
    """바탕 그림(PIL RGB 1080x1920)과 numpy 후처리 정보."""
    post = {"grade": None, "k": 1.0, "hblur": 0, "chroma": 0, "scan": 0, "dark": 0}
    if sid == "S0":
        c = clip("S11")
        if lt < 0.7:
            st = 0.6 + lt * 0.7
            img = view(c.at(st), 1.75, 0.53, 0.40)
        else:
            k = (lt - 0.7) / 0.5
            st = 1.1 - k * 1.0
            img = view(c.at(st), 1.25 + 0.2 * k, 0.5, 0.45, *shake(lt, 10))
            post.update(scan=0.22, hblur=40 * k + 10)
        post["grade"] = "frozen"
        return img, post
    if sid == "S1":
        z = 1.25 - 0.25 * ease(lt / 0.12) if lt < 0.12 else 1.0 + 0.06 * (lt - 0.12) / (dur - 0.12)
        return view(still("S1"), z, 0.5, 0.45), post
    if sid == "S2":
        z = 1.0 + 0.8 * ease(lt / 0.1)
        img = view(still("S3"), z, 0.43, 0.47)
        post.update(grade="desat")
        return img, post
    if sid == "S3":
        c = clip("S3")
        st = USE["S3"] + lt
        z = 1.0
        if 0.62 <= lt < 0.8:
            z = 1.0 + 0.12 * (1 - (lt - 0.62) / 0.18)
        img = view(c.at(st), z, 0.5, 0.45)
        if lt > dur - 0.22:
            post["hblur"] = 160 * (lt - (dur - 0.22)) / 0.22
        return img, post
    if sid == "S4":
        c = clip("S4")
        st = USE["S4"] + lt * 1.25
        z = 1.04 + (0.08 * ease((lt - (dur - 0.3)) / 0.12) if lt > dur - 0.3 else 0)
        img = view(c.at(st), z, 0.5, 0.5)
        post["hblur"] = 14 if lt < 1.5 else 0
        return img, post
    if sid == "S5":
        c = clip("S5")
        z = 1.12 - 0.12 * ease(lt / 0.12)
        return view(c.at(USE["S5"] + lt), z, 0.45, 0.62), post
    if sid == "S6":
        c = clip("S4")
        end = USE["S4"] + T["S4"][1] * 0 + (T["S4"][1] - T["S4"][0]) * 1.25
        if lt < 0.45:
            img = view(c.at(end), 1.12, 0.5, 0.45, *shake(lt, 16 * (1 - lt / 0.45)))
        else:
            k = (lt - 0.45) / 0.45
            img = view(c.at(end - k * 1.35), 1.06, 0.5, 0.5, *shake(lt, 6))
            post.update(grade="rewind", scan=0.2, hblur=26)
        return img, post
    if sid == "S7":
        c = clip("S7")
        return view(c.at(USE["S7"] + lt), 1.0, 0.5, 0.5), post
    if sid == "S8":
        c = clip("S8")
        return view(c.at(USE["S8"] + lt), 1.0, 0.5, 0.5), post
    if sid == "S9":
        c = clip("S7")
        img = view(c.at(2.85), 1.35, 0.55, 0.47, *shake(lt, 14 * max(0.2, 1 - lt / 0.4)))
        return img, post
    if sid == "S10":
        c = clip("S10")
        return view(c.at(USE["S10"] + lt), 1.0, 0.5, 0.5), post
    if sid == "S11":
        c = clip("S11")
        st = USE["S11"] + lt * 1.2
        img = view(c.at(st), 1.04, 0.5, 0.5)
        post["grade"] = "frozen"
        if lt < 0.12:
            post["chroma"] = int(16 * (1 - lt / 0.12)) + 4
            post["k"] = 0.6
        return img, post
    if sid == "S12":
        c = clip("S12")
        img = view(c.at(USE["S12"] + lt), 1.45, 0.66, 0.47)
        post["grade"] = "frozen"
        return img, post
    if sid == "S13":
        c = clip("S13")
        img = view(c.at(USE["S13"] + lt), 1.0, 0.5, 0.5)
        post["grade"] = "frozen"
        if lt > dur - 0.3:
            post["hblur"] = 180 * (lt - (dur - 0.3)) / 0.3
        return img, post
    if sid in ("S13a", "S13b"):
        img = view(still(sid), 1.0 + 0.08 * lt / dur, 0.5, 0.48)
        post.update(grade="frozen", hblur=max(0, 120 * (1 - lt / 0.2)))
        return img, post
    if sid == "S14":
        c = clip("S14")
        img = view(c.at(USE["S14"] + lt), 1.0 + 0.03 * lt / dur, 0.5, 0.5)
        if lt < 2.75:
            post["grade"] = "frozen"
        else:
            post["grade"] = "warm"
            post["k"] = min(1.0, (lt - 2.75) / 0.3)
            if lt < 2.85:
                post["chroma"] = 10
        return img, post
    if sid == "S14b":
        z = 1.0 + 0.12 * ease(lt / 0.8)
        post["grade"] = "warm"
        return view(still("S14b"), z, 0.5, 0.42), post
    if sid == "S15":
        c = clip("S15")
        st = USE["S15"] + (lt * 0.6 if lt < 0.5 else 0.3 + (lt - 0.5) * (2.6 - 0.3) / 2.1)
        post["grade"] = "warm"
        post["k"] = 0.8
        return view(c.at(st), 1.0, 0.5, 0.5), post
    if sid == "S15c":
        if lt < 0.3:
            img = view(still("S3"), 4.4 - 0.5 * ease(lt / 0.08), 0.534, 0.598, *shake(lt, 8))
        elif lt < 0.6:
            img = view(still("S17"), 2.5 - 0.3 * ease((lt - 0.3) / 0.08), 0.32, 0.48, *shake(lt, 10))
        else:
            img = view(still("S16"), 1.1, 0.5, 0.5, *shake(lt, 12)).filter(ImageFilter.GaussianBlur(14))
            post["dark"] = 0.45
        post["grade"] = "warm"
        post["k"] = 0.6
        return img, post
    if sid == "S16":
        c = clip("S16")
        z = 1.08 - 0.08 * ease(lt / 0.25)
        img = view(c.at(USE["S16"] + lt), z, 0.5, 0.48, *(shake(lt, 12 * (1 - lt / 0.3)) if lt < 0.3 else (0, 0)))
        post["grade"] = "warm"
        post["k"] = 0.8
        return img, post
    if sid == "S17":
        c = clip("S17")
        if lt < 1.2:
            img = view(c.at(0.1 + lt), 1.0, 0.5, 0.5)
        else:
            img = view(c.at(1.9 + (lt - 1.2)), 1.18, 0.38, 0.62)
        return img, post
    if sid == "S18":
        c = clip("S17")
        st = 4.3 + lt * 1.25
        frames = [arr(view(c.at(st - j * 0.04), 1.1, 0.5, 0.55, *shake(lt, 12))) for j in range(4)]
        post["avg"] = frames
        return None, post
    if sid == "S18v":
        c = clip("S18v")
        if lt < 1.1:
            img = view(c.at(0.1 + lt), 1.0, 0.5, 0.5, *(shake(lt, 14) if lt < 0.25 else (0, 0)))
        elif lt < 1.7:
            img = view(c.at(2.4 + (lt - 1.1)), 1.12, 0.42, 0.36)
        else:
            z = 1.0 + 1.3 * ease((lt - 1.7) / 0.12)
            img = view(c.at(3.0 + (lt - 1.7)), z, 0.63, 0.64)
        post["grade"] = "warm"
        post["k"] = 0.5
        return img, post
    if sid == "S19":
        img = view(still("S19"), 1.0 + 0.05 * lt / dur, 0.5, 0.55)
        steps = sum(1 for x in (0.2, 0.5, 0.8) if lt >= x)
        post["dark"] = [0, 0.18, 0.34, 0.48][steps]
        return img, post
    if sid == "S20":
        c = clip("S20", "/home/claude/ep7/v/clips/S16.mp4")
        post["grade"] = "evening"
        return view(c.at(1.8 + lt), 1.0, 0.5, 0.5), post
    if sid == "S21":
        return endcard(lt), post
    raise KeyError(sid)


# ---------------------------------------------------------------- 끝 화면
_END = {}


def endcard(lt):
    if "full" not in _END:
        bg = AN.cover(still("S20coin") if os.path.exists(f"{ST}/S20coin.png") else Image.open(f"{D}/gen/coin.png")).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.42))
        labels = ["축사", "회식", "소개팅", "빼빼로", "택시", "다녀와", "무르기", "퇴근"]
        full = AN.coin_string(bg.copy(), labels)
        d = ImageDraw.Draw(full)

        def c(t, f, y, fill):
            w = d.textlength(t, font=f)
            d.text(((W - w) / 2, y), t, font=f, fill=fill)
        c("8닢째", F(FB, 52), 1080, (255, 200, 60))
        c("2027년 칼퇴 운이 궁금할 땐", F(FB, 60), 1190, (255, 255, 255))
        f2 = F(FB, 42)
        w = d.textlength("hongchaksa.kr", font=f2)
        d.rounded_rectangle((540 - w / 2 - 32, 1310, 540 + w / 2 + 32, 1386), 38, outline=(215, 215, 215), width=2)
        c("hongchaksa.kr", f2, 1318, (245, 245, 245))
        # 여덟 번째 엽전 자리를 지운 판
        pre = full.copy()
        cx, cy = 615, 890
        pre.paste(bg.crop((cx - 120, cy - 135, cx + 120, cy + 150)), (cx - 120, cy - 135))
        dd = ImageDraw.Draw(pre)
        dd.line((cx - 120, cy, cx + 60, cy), fill=(170, 40, 40), width=6)
        # 날아오는 엽전
        coin = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        AN.coin(ImageDraw.Draw(coin), 90, 90, 74, True)
        _END.update(full=full, pre=pre, coin=coin)
    if lt >= 0.5:
        return _END["full"]
    k = ease(lt / 0.45)
    img = _END["pre"].copy()
    x = int(1100 + (615 - 1100) * k) - 90
    y = int(200 + (890 - 200) * k) - 90
    img.paste(_END["coin"], (x, y), _END["coin"])
    return img


# ---------------------------------------------------------------- 겹침 목록
def overlays(sid, lt, dur, T0):
    out = []  # (RGBA, alpha)
    Tabs = T0 + lt
    # 시계
    ck = clock_at(Tabs)
    if ck and sid not in ("S15c", "S16"):
        s, mode, sub = ck
        im = ov_clock(s, mode, sub)
        if sid == "S10" and 1.85 <= lt < 2.05:
            im2 = layer()
            im2.alpha_composite(im, (int(10 * math.sin(lt * 90)), 0))
            out.append((im2, 1.0))
        else:
            out.append((im, 1.0))
    if sid == "S0":
        out.append((ov_caption("퇴근 1분 전,\n회사 시간이 멈췄다"), 1.0))
    if sid == "S1":
        out.append((ov_caption("잠시 전,\n퇴근 탈출 작전"), fade(lt, 0.05, dur, 0.1, 0.1)))
        if lt < 0.12:
            out.append((ov_flash(1 - lt / 0.12), 1.0))
    if sid == "S2":
        out.append((ov_namecard(0), fade(lt, 0.08, dur + 1, 0.08, 0)))
        if lt < 0.06:
            out.append((ov_flash(0.7 * (1 - lt / 0.06)), 1.0))
    if sid in SUBS:
        s, a, b = SUBS[sid]
        out.append((ov_sub(s), fade(lt, a, min(b, dur), 0.08, 0.1, first=(a == 0))))
    if sid == "S4":
        out.append((ov_caption("1차 작전, 의자 활주"), fade(lt, 0.0, 0.95, 0.08, 0.12)))
        if lt >= 0.6:
            m = 12 - int(5 * (lt - 0.6) / (dur - 0.6))
            out.append((ov_reticle(540, 640, f"출구까지 {m}m"), fade(lt, 0.6, dur + 1, 0.1, 0)))
    if sid == "S5":
        if lt < 0.45 and int(lt * 12) % 2 == 0:
            out.append((ov_reticle(540, 640, "발각", red=True), 1.0))
    if sid == "S6":
        k = ease(min(1, (lt - 0.03) / 0.08)) if lt >= 0.03 else 0
        if k > 0:
            out.append((scaled(ov_stamp("작전 실패 1", cy=1300), 1.6 - 0.6 * k, 540, 1300), min(1, k * 1.5) * fade(lt, 0, dur, 0, 0.12)))
    if sid == "S7":
        out.append((ov_caption("2차 작전, 낮은 포복"), fade(lt, 0.0, 0.95, 0.08, 0.12)))
        if lt >= 0.6:
            red = lt >= 1.5 and int(lt * 10) % 2 == 0
            out.append((ov_gauge(100 if lt < 1.5 else 40, red), 1.0))
    if sid == "S9":
        k = ease(min(1, (lt - 0.03) / 0.08)) if lt >= 0.03 else 0
        if k > 0:
            out.append((scaled(ov_stamp("작전 실패 2", cy=1300), 1.6 - 0.6 * k, 540, 1300), min(1, k * 1.5)))
    if sid == "S10":
        out.append((ov_tag("홍책사"), fade(lt, 0.3, dur, 0.15, 0.1)))
        out.append((ov_caption("커피 배달 온 카페 사장"), fade(lt, 0.3, 1.9, 0.12, 0.15)))
        if lt > dur - 0.3:
            out.append((ov_flash((lt - (dur - 0.3)) / 0.3), 1.0))
    if sid == "S11":
        if lt < 0.15:
            out.append((ov_flash(1 - lt / 0.15), 1.0))
        r = 1500 * ease(lt / 0.55)
        out.append((ov_ring(540, 760, r, max(0, 1 - lt / 0.55), (200, 235, 255), 14), 1.0))
        out.append((ov_caption("시간이 멈췄다"), fade(lt, 0.25, dur, 0.15, 0.1)))
    if sid == "S13":
        out.append((ov_caption("홍책사는 산책 중"), fade(lt, 0.1, dur - 0.25, 0.12, 0.1)))
    if sid in ("S13a", "S13b") and lt < 2 / FPS:
        out.append((ov_flash(0.55), 1.0))
    if sid == "S14":
        if 2.75 <= lt < 2.75 + 2 / FPS:
            out.append((ov_flash(0.9, (255, 240, 210)), 1.0))
        if 2.75 <= lt < 3.15:
            k = (lt - 2.75) / 0.4
            out.append((ov_ring(560, 900, 1500 * (1 - ease(k)), 1 - k, (255, 215, 140), 14), 1.0))
    if sid == "S15":
        out.append((ov_caption("3차 작전, 정면으로"), fade(lt, 0.0, 0.7, 0.08, 0.12)))
    if sid == "S15c":
        beat = 0 if lt < 0.3 else 1 if lt < 0.6 else 2
        s = ["17:59:57", "17:59:58", "17:59:59"][beat]
        if beat < 2:
            out.append((ov_clock(s, "red", None, big=True), 1.0))
        else:
            sc = 1.25 - 0.25 * ease((lt - 0.6) / 0.08)
            out.append((scaled(ov_big(s, 190, (255, 90, 80, 255)), sc), 1.0))
    if sid == "S16":
        if lt < 0.3:
            sc = 1.3 - 0.3 * ease(lt / 0.08)
            out.append((scaled(ov_big("18:00:00", 200, (255, 210, 90, 255)), sc), 1.0))
            if lt < 0.08:
                out.append((ov_flash(0.6 * (1 - lt / 0.08), (255, 230, 170)), 1.0))
        elif lt < 0.55:
            k = ease((lt - 0.3) / 0.25)
            big = ov_big("18:00:00", 200, (255, 210, 90, 255))
            s = 1 - 0.68 * k
            moved = layer()
            sm = big.resize((int(W * s), int(H * s)), Image.BICUBIC)
            cy = 960 + (150 - 960) * k
            moved.alpha_composite(sm, (int(W / 2 - sm.width / 2), int(cy - sm.height / 2)))
            out.append((moved, 1.0))
        else:
            out.append((ov_clock("18:00:00", "gold", None), 1.0))
        r = 1500 * ease(lt / 0.6)
        out.append((ov_ring(540, 960, r, max(0, 1 - lt / 0.6), (255, 205, 100), 16), 1.0))
    if sid == "S17":
        if 0.1 <= lt < 0.95:
            if int(lt * 10) % 2 == 0:
                out.append((ov_reticle(540, 640, "발각", red=True), 1.0))
        elif 0.95 <= lt < 1.1:
            g = layer()
            g.alpha_composite(ov_reticle(540, 640, "발각", red=True), (int(30 * math.sin(lt * 200)), 0))
            out.append((g, 0.6))
        if lt >= 1.2:
            out.append((ov_sub("나도 그 말 기다렸어."), fade(lt, 2.0, 3.4, 0.08, 0.1)))
        else:
            out.append((ov_sub("도윤 씨,"), fade(lt, 0.12, 0.9, 0.08, 0.1)))
    if sid == "S18":
        if lt < 0.2:
            out.append((ov_reticle(600, 1000, "출구까지 12m"), 1.0))
        elif lt < 0.4:
            out.append((ov_reticle(600, 1000, "출구까지 0m", red=True), 1.0))
        else:
            out.append((scaled(ov_big("퇴근 신기록 0.4초", 92, (255, 214, 80, 255), font=FB), 1.2 - 0.2 * ease((lt - 0.4) / 0.08)), 1.0))
    if sid == "S18v":
        if lt < 1.1:
            out.append((ov_big("퇴근 신기록 0.4초", 92, (255, 214, 80, 255), font=FB), fade(lt, 0, 1.1, 0, 0.12)))
        if lt >= 1.7:
            out.append((ov_small_sub("코트는 두고 갔다"), fade(lt, 1.78, dur, 0.06, 0.08)))
    if sid == "S19":
        if lt >= 1.1:
            k = ease(min(1, (lt - 1.1) / 0.1))
            card = ov_namecard(0, 1, roll=min(1, max(0, (lt - 1.2) / 0.18)), green=True)
            out.append((scaled(card, 1.4 - 0.4 * k, 350, 1440), min(1, k * 1.4)))
    return out


# ---------------------------------------------------------------- 렌더
def composite(base, ovs):
    if not ovs:
        return base
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    for o, a in ovs:
        o2 = with_alpha(o, a)
        if o2 is not None:
            im.alpha_composite(o2)
    return im.convert("RGB")


def render(out, t_from=0.0, t_to=None):
    t_to = TOTAL if t_to is None else t_to
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-vf", "unsharp=5:5:0.35", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out],
                         stdin=subprocess.PIPE)
    for fi in range(n0, n1):
        Tabs = (fi + 0.5) / FPS
        sid = next(s for s in ORDER if T[s][0] <= Tabs < T[s][1]) if Tabs < TOTAL else ORDER[-1]
        a0, a1 = T[sid]
        lt, dur = Tabs - a0, a1 - a0
        img, post = base_frame(sid, lt, dur)
        if "avg" in post:
            a = sum(post["avg"]) / len(post["avg"])
        else:
            a = arr(img)
        if post.get("chroma"):
            a = chroma(a, post["chroma"])
        if post.get("grade"):
            a = grade(a, post["grade"], post.get("k", 1.0))
        if post.get("hblur"):
            a = hblur(a, post["hblur"])
        if post.get("scan"):
            a = scanlines(a, post["scan"])
        if post.get("dark"):
            a = darken_top(a, post["dark"]) if sid == "S19" else a * (1 - post["dark"])
        ovs = overlays(sid, lt, dur, a0)
        ovs.append((ov_ai(), 1.0))
        fr = composite(a, ovs)
        p.stdin.write(np.asarray(fr, np.uint8).tobytes())
        if fi % 60 == 0:
            print(f"{Tabs:5.1f}s {sid}", flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else f"{D}/out/ep08_video.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tf = float(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0.0
    tt = float(sys.argv[sys.argv.index("--to") + 1]) if "--to" in sys.argv else None
    render(out, tf, tt)
