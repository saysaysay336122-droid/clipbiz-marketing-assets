"""홍책사 10화 송년회 건배사 편집(1080x1920, 30fps). 생성 클립 13개와 사진 5장, 합성 장면(되감기, 메신저, 정지 화면, 끝 화면).
사용: python3 build10.py [출력.mp4] [--from 초 --to 초] [--frames 0,24.3,42.3]
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import animatic as AN  # noqa: E402

W, H, FPS = 1080, 1920, 30
D = "/home/claude/ep10"
CL = f"{D}/clips"
ST = f"{D}/gen/stills"
E7 = "/home/claude/ep7/v/clips/S16.mp4"
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
YEL = (255, 214, 80, 255)
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


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- 편집 목록(타임라인 초, 원본 시작 초)
EDL = [
    ("S1", 0.0, 2.4, dict(src="S1", a=0.4)),
    ("S3", 2.4, 3.0, dict(src="S3", a=2.8)),
    ("R1", 3.0, 3.6, dict(rew=(3.0, 0.0))),
    ("S4", 3.6, 6.0, dict(src="S4", a=0.8)),
    ("S5", 6.0, 7.5, dict(src="S5", a=0.95)),
    ("S6", 7.5, 8.3, dict(still="S6", z=(1.0, 1.12), c=(0.58, 0.6))),
    ("S7", 8.3, 10.7, dict(src="S7", a=0.2)),
    ("S8", 10.7, 11.3, dict(src="S3", a=3.2)),
    ("R2", 11.3, 11.9, dict(rew=(11.3, 3.6))),
    ("S9", 11.9, 12.8, dict(src="S4", a=0.95)),
    ("S10", 12.8, 15.5, dict(src="S10", a=1.16)),
    ("F1", 15.5, 16.3, dict(still="F1", z=(1.0, 1.05), c=(0.5, 0.58))),
    ("F2", 16.3, 17.4, dict(still="F2", z=(1.0, 1.05), c=(0.5, 0.58))),
    ("F3", 17.4, 18.7, dict(chat=True)),
    ("S12", 18.7, 21.9, dict(src="S12", a=0.4)),
    ("S13", 21.9, 23.8, dict(src="S13", a=0.75)),
    ("S14", 23.8, 24.2, dict(still="S14", snap=1.18, c=(0.64, 0.52))),
    ("FZ", 24.2, 24.8, dict(freeze=("S15", 0.9), z=1.08, c=(0.45, 0.36))),
    ("S15", 24.8, 26.9, dict(src="S15", a=0.9)),
    ("S16", 26.9, 28.7, dict(src="S16", a=0.0, speed=0.8)),
    ("S17", 28.7, 30.8, dict(src="S17", a=0.1)),
    ("S18", 30.8, 33.0, dict(src="S18", a=0.2)),
    ("S19", 33.0, 35.8, dict(src="S19", a=0.4)),
    ("S20", 35.8, 36.5, dict(src="S18", a=3.0, hold=0.2, punch=1.10, c=(0.55, 0.34))),
    ("S21", 36.5, 39.4, dict(src="E7", a=1.8, grade="evening")),
    ("S22", 39.4, 42.4, dict(end=True)),
]
TOTAL = EDL[-1][2]
ORDER = [e[0] for e in EDL]
T = {e[0]: (e[1], e[2]) for e in EDL}
OPT = {e[0]: e[3] for e in EDL}


def src_path(name):
    return E7 if name == "E7" else f"{CL}/{name}.mp4"


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

    def blend(self, st):
        x = (st - self.t0) * self.fps
        i = int(math.floor(x))
        i = min(len(self.frames) - 1, max(0, i))
        j = min(len(self.frames) - 1, i + 1)
        k = min(1.0, max(0.0, x - i))
        if k < 0.05 or i == j:
            return Image.fromarray(self.frames[i])
        a = self.frames[i].astype(np.float32) * (1 - k) + self.frames[j].astype(np.float32) * k
        return Image.fromarray(a.astype(np.uint8))


CLIPS = {}


def clip(sid):
    if sid not in CLIPS:
        o = OPT[sid]
        a0, a1 = T[sid]
        span = (a1 - a0) * o.get("speed", 1.0)
        CLIPS[sid] = Clip(src_path(o["src"]), max(0.0, o["a"] - 0.1), o["a"] + span + 0.15)
    return CLIPS[sid]


_GRAB = {}


def grab(name, t):
    k = (name, round(t, 2))
    if k not in _GRAB:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", src_path(name), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        import io
        _GRAB[k] = Image.open(io.BytesIO(raw)).convert("RGB")
    return _GRAB[k]


_STILL = {}


def still(name):
    if name not in _STILL:
        _STILL[name] = Image.open(f"{ST}/{name}.png").convert("RGB")
    return _STILL[name]


def view(img, z=1.0, cx=0.5, cy=0.5):
    iw, ih = img.size
    cw, ch = iw / z, ih / z
    x0 = min(iw - cw, max(0, cx * iw - cw / 2))
    y0 = min(ih - ch, max(0, cy * ih - ch / 2))
    return img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


# ---------------------------------------------------------------- 색과 효과
def arr(img):
    return np.asarray(img, dtype=np.float32)


def grade(a, kind, k=1.0):
    if kind is None or k <= 0:
        return a
    if kind == "evening":
        b = a * np.array([1.0, 0.96, 0.94], np.float32) * 0.96
    elif kind == "desat":
        lum = a.mean(axis=2, keepdims=True)
        b = (a * 0.35 + lum * 0.65) * np.array([0.95, 0.98, 1.05], np.float32) * 0.9
    elif kind == "rewind":
        lum = a.mean(axis=2, keepdims=True)
        b = (a * 0.45 + lum * 0.55) * np.array([1.0, 0.98, 1.08], np.float32) + 8
    elif kind == "memory":
        lum = a.mean(axis=2, keepdims=True)
        b = (a * 0.75 + lum * 0.25) * np.array([1.03, 1.0, 0.95], np.float32) + 6
    else:
        return a
    return a * (1 - k) + b * k


def hblur(a, amount):
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


_VIG = {}


def vignette(a, k):
    if k not in _VIG:
        yy, xx = np.mgrid[0:H, 0:W]
        _VIG[k] = (1 - k * np.clip((np.hypot(xx - 540, yy - 960) - 300) / 560, 0, 1)).astype(np.float32)[..., None]
    return a * _VIG[k]


# ---------------------------------------------------------------- 겹침
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


def ov_caption(s, y=250, size=66):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        for i, l in enumerate(s.split("\n")):
            text_center(d, y + i * int(size * 1.36), l, F(FB, size), stroke=6)
        return im
    return cached(("cap", s, y, size), mk)


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


def ov_voice(s):
    """회상 속 팀장 목소리: 작은 기울지 않은 회색 자막."""
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        text_center(d, 1170, s, F(FB, 50), fill=(235, 235, 235, 255), stroke=4)
        return im
    return cached(("voice", s), mk)


def ov_tag(s, y=990):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, 46)
        w = d.textlength(s, font=f)
        x1 = 1040
        x0 = x1 - w - 48
        d.rounded_rectangle((x0, y, x1, y + 74), 18, fill=(20, 20, 20, 200))
        d.text((x0 + 24, y + 7), s, font=f, fill=YEL)
        return im
    return cached(("tag", s, y), mk)


def ov_hook(s):
    """앞편 고리: 왼쪽 아래 작은 회색 자막."""
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, 34)
        w = d.textlength(s, font=f)
        d.rounded_rectangle((44, 1318, 44 + w + 36, 1372), 14, fill=(0, 0, 0, 150))
        d.text((62, 1322), s, font=f, fill=(225, 225, 225, 240))
        return im
    return cached(("hook", s), mk)


def ov_time(s):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FM, 132)
        w = d.textlength(s, font=f)
        d.text(((W - w) / 2, 196), s, font=f, fill=(255, 255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0, 255))
        return im
    return cached(("time", s), mk)


def ov_pop(s, color=(255, 255, 255, 255), cy=1010, size=104):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        text_center(d, cy - size * 0.62, s, F(FB, size), fill=color, stroke=8)
        return im
    return cached(("pop", s, color, cy, size), mk)


def ov_rule(show2):
    """선창과 후창 안내판."""
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        fl, ft = F(FB, 40), F(FB, 62)
        rows = [("선창", "잠깐 시간 돼?"), ("후창", "내년에")][: 2 if show2 else 1]
        w = max(d.textlength(t, font=ft) for _, t in [("선창", "잠깐 시간 돼?"), ("후창", "내년에")]) + 150
        x0 = (W - w - 60) / 2
        y0 = 214
        d.rounded_rectangle((x0, y0, x0 + w + 60, y0 + 40 + len(rows) * 100), 26, fill=(10, 10, 12, 185))
        for i, (lab, t) in enumerate(rows):
            y = y0 + 26 + i * 100
            d.rounded_rectangle((x0 + 28, y + 12, x0 + 128, y + 64), 14, fill=YEL)
            lw = d.textlength(lab, font=fl)
            d.text((x0 + 78 - lw / 2, y + 12), lab, font=fl, fill=(20, 20, 20, 255))
            d.text((x0 + 152, y - 2), t, font=ft, fill=(255, 255, 255, 255))
        return im
    return cached(("rule", show2), mk)


def ov_hud(a, b=None, k=0.0, big=False):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, 70 if big else 54)
        h = 108 if big else 88
        w = int(max(d.textlength(a, font=f), d.textlength(b or a, font=f)) + (64 if big else 52))
        x1, y0 = 1040, 36
        x0 = x1 - w
        d.rounded_rectangle((x0, y0, x1, y0 + h), 20, fill=(12, 12, 14, 205), outline=(255, 214, 80, 235), width=3)
        strip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ds = ImageDraw.Draw(strip)
        if b is None:
            ds.text((w / 2, h / 2), a, font=f, fill=YEL, anchor="mm")
        else:
            ds.text((w / 2, h / 2 - k * h), a, font=f, fill=YEL, anchor="mm")
            ds.text((w / 2, h / 2 + (1 - k) * h), b, font=f, fill=YEL, anchor="mm")
        im.alpha_composite(strip, (x0, y0))
        return im
    if b is None:
        return cached(("hud", a, big), mk)
    return mk()


def scaled(im, s, cx=W / 2, cy=H / 2):
    if abs(s - 1) < 0.005:
        return im
    w, h = int(W * s), int(H * s)
    big = im.resize((w, h), Image.BICUBIC)
    out = layer()
    ox, oy = int(cx - cx * s), int(cy - cy * s)
    out.alpha_composite(big.crop((max(0, -ox), max(0, -oy), max(0, -ox) + min(W, w), max(0, -oy) + min(H, h))),
                        (max(0, ox), max(0, oy)))
    return out


def ov_flash(alpha, color=(255, 255, 255)):
    return Image.new("RGBA", (W, H), color + (int(255 * alpha),))


def with_alpha(im, a):
    if a >= 0.999:
        return im
    if a <= 0.001:
        return None
    r, g, b, al = im.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def win(T0, s, e, fin=0.1, fout=0.1):
    if T0 < s or T0 >= e:
        return 0.0
    a = 1.0
    if fin > 0:
        a = min(a, (T0 - s) / fin)
    if fout > 0:
        a = min(a, (e - T0) / fout)
    return max(0.0, min(1.0, a))


# ---------------------------------------------------------------- 메신저 합성(F3)
_CHAT = {}


def chat_frame(lt):
    if "bg" not in _CHAT:
        bg = view(still("F2"), 1.05, 0.5, 0.55).filter(ImageFilter.GaussianBlur(14))
        bg = Image.fromarray((arr(bg) * np.array([0.30, 0.32, 0.42], np.float32)).astype(np.uint8))
        ph = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ph)
        x0, y0, x1, y1 = 170, 430, 910, 1560
        d.rounded_rectangle((x0 - 14, y0 - 14, x1 + 14, y1 + 14), 70, fill=(18, 18, 20, 255))
        d.rounded_rectangle((x0, y0, x1, y1), 58, fill=(236, 238, 242, 255))
        d.rounded_rectangle((x0, y0, x1, y0 + 150), 58, fill=(250, 250, 252, 255))
        d.rectangle((x0, y0 + 90, x1, y0 + 150), fill=(250, 250, 252, 255))
        d.line((x0, y0 + 150, x1, y0 + 150), fill=(215, 218, 224, 255), width=2)
        f = F(FB, 44)
        d.text((x0 + 120, y0 + 52), "최 팀장", font=f, fill=(30, 30, 34, 255))
        d.ellipse((x0 + 36, y0 + 48, x0 + 96, y0 + 108), fill=(190, 196, 206, 255))
        fs = F(FR, 30)
        d.text((x0 + 300, y0 + 230), "오후 11:40", font=fs, fill=(130, 134, 142, 255))
        bub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        db = ImageDraw.Draw(bub)
        ft = F(FB, 46)
        t = "도윤 씨, 잠깐 시간 돼?"
        tw = db.textlength(t, font=ft)
        bx, by = x0 + 40, y0 + 300
        db.rounded_rectangle((bx, by, bx + tw + 64, by + 104), 36, fill=(255, 255, 255, 255))
        db.text((bx + 32, by + 20), t, font=ft, fill=(25, 25, 28, 255))
        _CHAT.update(bg=bg, ph=ph, bub=bub)
    img = _CHAT["bg"].convert("RGBA")
    img.alpha_composite(_CHAT["ph"])
    if lt >= 0.1:
        k = ease((lt - 0.1) / 0.18)
        b = with_alpha(_CHAT["bub"], k)
        if b is not None:
            img.alpha_composite(b, (0, int(30 * (1 - k))))
    return img.convert("RGB")


# ---------------------------------------------------------------- 끝 화면
_END = {}
CX10, CY10 = 765, 890


def endcard(lt):
    if "full" not in _END:
        s1 = view(grab("S1", 0.4))
        bg = s1.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.42))
        labels = ["축사", "회식", "소개팅", "빼빼로", "택시", "다녀와", "무르기", "퇴근", "월요일", "건배사"]
        full = AN.coin_string(bg.copy(), labels)
        d = ImageDraw.Draw(full)

        def c(t, f, y, fill):
            w = d.textlength(t, font=f)
            d.text(((W - w) / 2, y), t, font=f, fill=fill)
        c("10닢째", F(FB, 52), 1080, (255, 200, 60))
        c("2027 한 수가 궁금할 땐", F(FB, 60), 1190, (255, 255, 255))
        f2 = F(FB, 42)
        w = d.textlength("hongchaksa.kr", font=f2)
        d.rounded_rectangle((540 - w / 2 - 32, 1310, 540 + w / 2 + 32, 1386), 38, outline=(215, 215, 215), width=2)
        c("hongchaksa.kr", f2, 1318, (245, 245, 245))
        pre = full.copy()
        pre.paste(bg.crop((CX10 - 120, CY10 - 135, CX10 + 120, CY10 + 150)), (CX10 - 120, CY10 - 135))
        ImageDraw.Draw(pre).line((CX10 - 120, CY10, CX10 + 60, CY10), fill=(170, 40, 40), width=6)
        coin = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        AN.coin(ImageDraw.Draw(coin), 90, 90, 74, True)
        _END.update(full=full, pre=pre, coin=coin, s1=s1)
    dur = TOTAL - T["S22"][0]
    if lt >= dur - 0.4:
        k = smooth((lt - (dur - 0.4)) / 0.4)
        return Image.blend(_END["full"], _END["s1"], k)
    if lt >= 0.5:
        return _END["full"]
    k = ease(lt / 0.45)
    img = _END["pre"].copy()
    x = int(1100 + (CX10 - 1100) * k) - 90
    y = int(200 + (CY10 - 200) * k) - 90
    img.paste(_END["coin"], (x, y), _END["coin"])
    return img


# ---------------------------------------------------------------- 바탕 화면
def shot_at(Tabs):
    for sid in ORDER:
        if T[sid][0] <= Tabs < T[sid][1]:
            return sid
    return ORDER[-1]


def base_frame(sid, lt, dur, light=False):
    """(PIL 이미지, 후처리 dict)"""
    o = OPT[sid]
    post = {}
    if "src" in o:
        if "hold" in o:
            st = o["a"] + max(0.0, lt - o["hold"])
        else:
            st = o["a"] + lt * o.get("speed", 1.0)
        if light:
            im = grab(o["src"], st)
        elif o.get("speed", 1.0) != 1.0:
            im = clip(sid).blend(st)
        else:
            im = clip(sid).at(st)
        if "punch" in o:
            z = 1.0 + (o["punch"] - 1.0) * ease(lt / 0.1)
            cx, cy = o["c"]
            img = view(im, z, cx, cy)
        else:
            img = view(im)
        if o.get("grade"):
            post["grade"] = o["grade"]
        if sid == "S20" and lt < o["hold"]:
            post["vign"] = 0.35
        return img, post
    if "still" in o:
        cx, cy = o["c"]
        if "snap" in o:
            z = 1.0 + (o["snap"] - 1.0) * ease(lt / 0.09)
        else:
            z0, z1 = o["z"]
            z = z0 + (z1 - z0) * smooth(lt / dur)
        img = view(still(o["still"]), z, cx, cy)
        if sid in ("F1", "F2"):
            post["grade"] = "memory"
            post["vign"] = 0.45
        return img, post
    if "freeze" in o:
        name, t = o["freeze"]
        cx, cy = o["c"]
        z = 1.0 + (o["z"] - 1.0) * ease(lt / 0.12)
        img = view(grab(name, t), z, cx, cy)
        post["grade"] = "desat"
        post["vign"] = 0.5
        return img, post
    if o.get("chat"):
        return chat_frame(lt), post
    if "rew" in o:
        T0, T1 = o["rew"]
        p = smooth(lt / dur)
        Ts = T0 - (T0 - T1) * p - 0.001
        Ts = max(0.0, Ts)
        sid2 = shot_at(Ts)
        img, _ = base_frame(sid2, Ts - T[sid2][0], T[sid2][1] - T[sid2][0], light=True)
        speed = math.sin(math.pi * min(1.0, lt / dur))
        post.update(grade="rewind", hblur=8 + 26 * speed, chroma=int(3 + 6 * speed), scan=0.2, vign=0.4)
        return img, post
    if o.get("end"):
        return endcard(lt), post
    raise ValueError(sid)


# ---------------------------------------------------------------- 자막과 표시
SUBS = [  # (시작, 끝, 글, 방식)
    (0.10, 2.40, "그리고 이월에는,", "sub"),
    (3.85, 5.95, "마무리는 도윤 씨.", "sub"),
    (6.12, 7.50, "청바지.", "sub"),
    (8.38, 10.65, "청춘은 바로 지금.", "sub"),
    (11.98, 12.80, "마무리는", "sub"),
    (13.30, 15.45, "제일 많이 들은 말, 뭐예요?", "sub"),
    (15.60, 16.30, "잠깐 시간 돼?", "voice"),
    (16.40, 17.40, "도윤 씨, 잠깐 시간 돼?", "voice"),
    (19.15, 21.85, "잠깐 시간 돼, 하면 내년에.", "sub"),
    (22.05, 23.80, "잠깐 시간 돼?", "pop_white"),
    (25.90, 26.90, "내년에.", "pop_yellow"),
    (28.85, 30.80, "도윤 씨, 잠깐 시간 돼?", "sub"),
    (30.88, 32.10, "내년에.", "pop_yellow"),
    (33.50, 35.75, "그래, 이건 내년에.", "sub"),
    (36.95, 39.35, "홍책사 한 수면, 됐지?", "sub"),
]


def overlays(sid, lt, dur, Tabs):
    out = []
    # 0초 사건 자막
    a = win(Tabs, 0.0, 2.4, fin=0.0, fout=0.12)
    if a:
        out.append((ov_caption("송년회 건배사 4분째\n아직 2월"), a))
    # 회차 표시
    if Tabs < 11.9:
        if 3.0 <= Tabs < 3.6:
            k = smooth((Tabs - 3.25) / 0.25)
            out.append((ov_hud("1트", "2트", k), 1.0))
        elif 11.3 <= Tabs < 11.9:
            k = smooth((Tabs - 11.55) / 0.25)
            out.append((ov_hud("2트", "3트", k), 1.0))
        else:
            out.append((ov_hud("1트" if Tabs < 3.0 else "2트"), 1.0))
    elif Tabs < 12.8:
        out.append((ov_hud("3트"), 1.0))
    if sid == "S20":
        s = 1.0 + 0.18 * (1 - ease(lt / 0.14))
        out.append((scaled(ov_hud("4트?", big=True), s, 980, 90), 1.0))
    # 되감기 글
    if sid in ("R1", "R2"):
        out.append((ov_caption("다시", y=860, size=120), win(lt, 0.0, dur, 0.06, 0.08)))
    # 앞편 고리, 이름표, 상
    a = win(Tabs, 3.75, 5.95, 0.12, 0.12)
    if a:
        out.append((ov_hook("도윤과 최 팀장, 8화 17:59 그 팀"), a))
    a = win(Tabs, 12.95, 15.4, 0.1, 0.12)
    if a:
        out.append((ov_tag("홍책사"), a))
    a = win(Tabs, 28.8, 30.75, 0.1, 0.12)
    if a:
        out.append((ov_tag("올해의 팀원 상", y=880), a))
    # 회상 시각
    for s0, s1, t in ((15.5, 16.3, "09:00"), (16.3, 17.4, "17:59"), (17.4, 18.7, "23:40")):
        if s0 <= Tabs < s1:
            k = ease((Tabs - s0) / 0.12)
            out.append((scaled(ov_time(t), 1.0 + 0.12 * (1 - k), 540, 270), 1.0))
    # 선창 후창 안내판
    if 19.2 <= Tabs < 21.85:
        out.append((ov_rule(Tabs >= 20.3), win(Tabs, 19.2, 21.85, 0.12, 0.12)))
    # 정지 화면 속마음
    if sid == "FZ":
        out.append((ov_flash(0.55 * max(0.0, 1 - lt / 0.07)), 1.0))
        out.append((ov_caption("도윤 속마음\n엽전 한 번만 더", y=1170, size=70), win(lt, 0.0, dur, 0.06, 0.06)))
    # 대사 자막
    for s0, s1, t, kind in SUBS:
        if s0 <= Tabs < s1:
            a = win(Tabs, s0, s1, 0.06, 0.08)
            if kind == "sub":
                out.append((ov_sub(t), a))
            elif kind == "voice":
                out.append((ov_voice(t), a))
            else:
                col = (255, 255, 255, 255) if kind == "pop_white" else YEL
                k = ease((Tabs - s0) / 0.12)
                out.append((scaled(ov_pop(t, col), 1.08 - 0.08 * k, 540, 1010), a))
    return out


def composite(base, ovs):
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    for o, a in ovs:
        o2 = with_alpha(o, a)
        if o2 is not None:
            im.alpha_composite(o2)
    return im.convert("RGB")


def frame_at(Tabs):
    sid = shot_at(Tabs)
    a0, a1 = T[sid]
    lt, dur = Tabs - a0, a1 - a0
    img, post = base_frame(sid, lt, dur)
    a = arr(img)
    if post.get("grade"):
        a = grade(a, post["grade"])
    if post.get("hblur"):
        a = hblur(a, post["hblur"])
    if post.get("chroma"):
        a = chroma(a, post["chroma"])
    if post.get("scan"):
        a = scanlines(a, post["scan"])
    if post.get("vign"):
        a = vignette(a, post["vign"])
    ovs = overlays(sid, lt, dur, Tabs)
    ovs.append((ov_ai(), 1.0))
    return sid, composite(a, ovs)


def render(out, t_from=0.0, t_to=None):
    t_to = TOTAL if t_to is None else t_to
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-vf", "unsharp=5:5:0.35", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    last = None
    for fi in range(n0, n1):
        Tabs = min(TOTAL - 1e-3, (fi + 0.5) / FPS)
        sid = shot_at(Tabs)
        if sid != last:
            for k in list(CLIPS):
                if k != sid:
                    del CLIPS[k]
            last = sid
        _, fr = frame_at(Tabs)
        p.stdin.write(np.asarray(fr, np.uint8).tobytes())
        if fi % 90 == 0:
            print(f"{Tabs:5.1f}s {sid}", flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--frames" in args:
        ts = [float(x) for x in args[args.index("--frames") + 1].split(",")]
        os.makedirs(f"{D}/out/frames", exist_ok=True)
        for t in ts:
            sid, fr = frame_at(min(TOTAL - 1e-3, t))
            fr.save(f"{D}/out/frames/f_{t:05.2f}_{sid}.jpg", quality=88)
            print(t, sid)
        sys.exit(0)
    out = args[0] if args and not args[0].startswith("--") else f"{D}/out/ep10_video.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tf = float(args[args.index("--from") + 1]) if "--from" in args else 0.0
    tt = float(args[args.index("--to") + 1]) if "--to" in args else None
    render(out, tf, tt)
