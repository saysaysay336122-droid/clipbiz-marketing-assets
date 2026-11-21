"""홍책사 10화 송년회 건배사 v22 공포 스릴러판(1080x1920, 30fps, 약 37초).
'잠깐 시간 돼?'를 공포 영화의 주문처럼: 정전, 붉은 빛, 깜빡임, 속삭임, 갑툭튀 도장, 흑백 정지, 급줌.
장면마다 위쪽 상황 자막으로 이야기 순서를 짚는다.
사용: python3 build_v22.py [출력.mp4] [--from 초 --to 초] [--frames 0,24.3]
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



# ---------------------------------------------------------------- 편집 목록 v22
SHOTS = [
    ("O1", 1.2, dict(tagshot=(0.35, 1.0, 1.15))),
    ("H1", 1.6, dict(src="H1", a=1.9, zz=(1.0, 1.06), c=(0.5, 0.40))),
    ("H2", 1.3, dict(src="H2", a=0.0, speed=0.5, zz=(1.0, 1.16), c=(0.5, 0.42), crash=0.22)),
    ("RW", 0.5, dict(rew=(4.0, 0.3))),
    ("S6", 1.8, dict(still="S6", z=(1.0, 1.20), c0=(0.62, 0.6), c1=(0.50, 0.58))),
    ("S10", 2.4, dict(src="S10", a=1.45, zz=(1.0, 1.08), c=(0.5, 0.42))),
    ("F1", 1.2, dict(still="F1", snap=(1.0, 1.10), c=(0.5, 0.58), step2=(0.55, 1.22))),
    ("F2", 1.2, dict(still="F2", snap=(1.06, 1.18), c=(0.5, 0.58), step2=(0.55, 1.32))),
    ("H3", 1.8, dict(src="H3", a=0.1, zz=(1.0, 1.10), c=(0.5, 0.52), insert=(0.5, 0.8))),
    ("S12", 2.6, dict(src="S12", a=0.20, zz=(1.05, 1.15), c=(0.5, 0.45))),
    ("S13", 1.1, dict(src="S13", a=0.75, zz=(1.08, 1.20), c=(0.5, 0.42), crash=0.12)),
    ("S14", 0.7, dict(still="S14", snap=(1.0, 1.20), c=(0.64, 0.52))),
    ("S15", 1.6, dict(src="S15", a=1.40, zz=(1.0, 1.06), c=(0.5, 0.42))),
    ("S16", 1.1, dict(src="S16", a=0.9, speed=0.5)),
    ("O2", 0.7, dict(tagshot=(-1.0, 1.12, 1.24))),
    ("S17", 1.5, dict(src="S17", a=0.10, zz=(1.05, 1.05), c=(0.5, 0.5), steps=(0.0, 0.5, 1.0))),
    ("H2b", 0.6, dict(src="H2", a=0.1, speed=0.8, zz=(1.25, 1.42), c=(0.5, 0.36), crash=0.12)),
    ("S18", 1.4, dict(src="S18", a=0.20, zz=(1.08, 1.08), c=(0.5, 0.4), tail=0.6)),
    ("S19", 1.85, dict(src="S19", a=0.75, zz=(1.0, 1.05), c=(0.5, 0.45))),
    ("FZ2", 0.9, dict(freeze=("S18", 3.0), z=1.12, c=(0.55, 0.34))),
    ("N5a", 1.5, dict(chat="boss")),
    ("N5", 1.6, dict(src="N5", a=0.75, stopat=0.8, snapz=1.10, c=(0.5, 0.4))),
    ("N3", 1.6, dict(src="N3", a=1.70)),
    ("N4", 1.1, dict(still="N4", z=(1.0, 1.06), c=(0.5, 0.45))),
    ("E7a", 1.22, dict(src="E7", a=2.20, zz=(1.0, 1.03))),
    ("E7b", 0.58, dict(src="E7", a=4.02, zz=(1.06, 1.07))),
    ("END", 3.0, dict(end=True)),
]

EDL = []
_t = 0.0
for _sid, _d, _o in SHOTS:
    EDL.append((_sid, round(_t, 3), round(_t + _d, 3), _o))
    _t += _d
TOTAL = EDL[-1][2]
ORDER = [e[0] for e in EDL]
T = {e[0]: (e[1], e[2]) for e in EDL}
OPT = {e[0]: e[3] for e in EDL}


def at(sid, rel):
    """샷 안의 상대 시각을 전체 시각으로. rel이 음수면 샷 끝에서 거꾸로."""
    a0, a1 = T[sid]
    return round((a1 + rel) if rel < 0 else (a0 + rel), 3)


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
    elif kind == "warm":
        b = a * np.array([1.05, 1.0, 0.92], np.float32) + 5
    elif kind == "bw":
        lum = a.mean(axis=2, keepdims=True)
        b = np.repeat((lum - 128) * 1.25 + 128, 3, axis=2)
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




# ---------------------------------------------------------------- 첫 장면: 봉투 꼬리표
TAG_C = (650, 1500)
_TAGB = {}


def tag_base():
    if "img" not in _TAGB:
        _TAGB["img"] = view(grab("S17", 0.0))
    return _TAGB["img"]


def tagged(u):
    """S17 첫 프레임에 '연말 격려금 100만 원' 종이 꼬리표를 붙인다. u는 붉은 밑줄 진행(0~1)."""
    u = round(min(1.0, max(0.0, u)), 1)
    key = ("tagged", u)
    if key in _TAGB:
        return _TAGB[key]
    base = tag_base().convert("RGBA")
    tw, th = 400, 200
    tg = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(tg)
    d.rounded_rectangle((20, 20, 20 + tw, 20 + th), 16, fill=(246, 242, 232, 255), outline=(200, 192, 176, 255), width=2)
    d.ellipse((38, 38 + th / 2 - 22, 62, 38 + th / 2 + 2), fill=(170, 160, 140, 255))
    f1, f2 = F(FB, 42), F(FB, 72)
    d.text((88, 38), "연말 격려금", font=f1, fill=(40, 46, 70, 255))
    d.text((88, 88), "100만 원", font=f2, fill=(30, 34, 58, 255))
    if u > 0:
        w2 = d.textlength("100만 원", font=f2)
        d.line((86, 184, 86 + (w2 + 6) * u, 180), fill=(206, 34, 34, 255), width=9)
    tg = tg.rotate(-7, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", tg.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 90), (0, 0), tg.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    x, y = TAG_C[0] - tg.width // 2, TAG_C[1] - tg.height // 2
    d2 = ImageDraw.Draw(base)
    d2.line((688, 1330, x + 54, y + tg.height // 2 - 22), fill=(150, 120, 80, 255), width=4)
    base.alpha_composite(sh, (x + 8, y + 10))
    base.alpha_composite(tg, (x, y))
    out = base.convert("RGB")
    _TAGB[key] = out
    return out


def opening(lt, dur=1.6, u0=0.6, z0=1.0, z1=1.2):
    z = z0 + (z1 - z0) * ease(lt / dur)
    return view(tagged((lt - u0) / 0.16), z, TAG_C[0] / W, TAG_C[1] / H)


# ---------------------------------------------------------------- 겹침(v20)
def ov_clock(s):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FM, 100)
        d.text((62, 1268), s, font=f, fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))
        return im
    return cached(("clock", s), mk)


def stamp_img(s, size):
    def mk():
        f = F(FB, size)
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        tw = tmp.textlength(s, font=f)
        pad = int(size * 0.45)
        w, h = int(tw + pad * 2), int(size * 1.55)
        im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        red = (214, 38, 38, 255)
        d.rounded_rectangle((10, 10, 10 + w, 10 + h), int(size * 0.28), outline=red, width=max(5, size // 12))
        d.rounded_rectangle((10 + size // 7, 10 + size // 7, 10 + w - size // 7, 10 + h - size // 7), int(size * 0.2),
                            outline=(214, 38, 38, 150), width=max(2, size // 30))
        d.text((10 + pad, 10 + (h - size * 1.2) / 2), s, font=f, fill=red)
        g = np.random.default_rng(len(s) + size)
        a = np.asarray(im).copy()
        holes = g.random(a.shape[:2]) < 0.06
        a[..., 3] = np.where(holes, (a[..., 3] * 0.35).astype(np.uint8), a[..., 3])
        im = Image.fromarray(a).rotate(8, resample=Image.BICUBIC, expand=True)
        return im
    return cached(("stampimg", s, size), mk)


def ov_stamp(s, size, cx, cy, lt):
    """도장 쾅: 0.08초에 크게서 제 크기로 떨어진다."""
    if lt < 0:
        return None
    k = ease(lt / 0.08)
    sc = 1.7 - 0.7 * k
    st = stamp_img(s, size)
    w, h = int(st.width * sc), int(st.height * sc)
    im = layer()
    im.alpha_composite(st.resize((w, h), Image.BICUBIC), (int(cx - w / 2), int(cy - h / 2)))
    return with_alpha(im, min(1.0, 0.25 + k))


def ov_board(n):
    """건배사 안내판: 제목과 선창, 후창."""
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        fl, ft, fs, fh = F(FB, 40), F(FB, 60), F(FB, 36), F(FB, 44)
        rows = [("선창", "잠깐 시간 돼?", ""), ("후창", "내년에", "(올해 일은 끝)")][:n]
        x0, x1, y0 = 120, 960, 196
        d.rounded_rectangle((x0, y0, x1, y0 + 96 + 2 * 98), 26, fill=(10, 10, 12, 190))
        tw = d.textlength("건배사", font=fh)
        d.text(((W - tw) / 2, y0 + 18), "건배사", font=fh, fill=YEL)
        for i, (lab, t, small) in enumerate(rows):
            y = y0 + 92 + i * 98
            d.rounded_rectangle((x0 + 30, y + 12, x0 + 130, y + 64), 14, fill=YEL)
            lw = d.textlength(lab, font=fl)
            d.text((x0 + 80 - lw / 2, y + 12), lab, font=fl, fill=(20, 20, 20, 255))
            d.text((x0 + 156, y - 2), t, font=ft, fill=(255, 255, 255, 255))
            if small:
                tx = x0 + 156 + d.textlength(t, font=ft) + 16
                d.text((tx, y + 18), small, font=fs, fill=(210, 210, 210, 255))
        return im
    return cached(("board", n), mk)


def ov_sub_hl(parts, size=60):
    """부분 강조 자막: [(글, 노랑 여부)]"""
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, size)
        tw = sum(d.textlength(t, font=f) for t, _ in parts)
        x = (W - tw) / 2
        for t, hl in parts:
            d.text((x, 1150), t, font=f, fill=YEL if hl else (255, 255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0, 255))
            x += d.textlength(t, font=f)
        return im
    return cached(("subhl", tuple(parts), size), mk)


def ov_suby(s, size=64):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        text_center(d, 1150, s, F(FB, size), fill=YEL, stroke=6)
        return im
    return cached(("suby", s, size), mk)


# ---------------------------------------------------------------- 메신저 합성(F3, N5a)
_CHAT = {}


def chat_frame(kind, lt):
    if kind not in _CHAT:
        if kind == "doyun":
            bg = view(still("F2"), 1.05, 0.5, 0.55)
            head, body, size, who = "최 팀장", "도윤 씨, 잠깐 시간 돼?", 46, None
        else:
            bg = view(Image.open(f"{ST}/N5bg.png").convert("RGB"), 1.05, 0.5, 0.45)
            head, body, size, who = "본부장", "최 팀장, 잠깐 시간 돼?", 54, "본부장"
        bg = bg.filter(ImageFilter.GaussianBlur(14))
        bg = Image.fromarray((arr(bg) * np.array([0.30, 0.32, 0.42], np.float32)).astype(np.uint8))
        ph = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ph)
        x0, y0, x1, y1 = 150, 400, 930, 1230
        d.rounded_rectangle((x0 - 14, y0 - 14, x1 + 14, y1 + 14), 70, fill=(18, 18, 20, 255))
        d.rounded_rectangle((x0, y0, x1, y1), 58, fill=(236, 238, 242, 255))
        d.rounded_rectangle((x0, y0, x1, y0 + 150), 58, fill=(250, 250, 252, 255))
        d.rectangle((x0, y0 + 90, x1, y0 + 150), fill=(250, 250, 252, 255))
        d.line((x0, y0 + 150, x1, y0 + 150), fill=(215, 218, 224, 255), width=2)
        d.text((x0 + 120, y0 + 52), head, font=F(FB, 44), fill=(30, 30, 34, 255))
        d.ellipse((x0 + 36, y0 + 48, x0 + 96, y0 + 108), fill=(190, 196, 206, 255))
        bub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        db = ImageDraw.Draw(bub)
        ft = F(FB, size)
        tw = db.textlength(body, font=ft)
        bx, by = x0 + 34, y0 + 300
        if who:
            db.text((bx + 8, by - 56), who, font=F(FR, 34), fill=(90, 94, 102, 255))
        db.rounded_rectangle((bx, by, bx + tw + 64, by + int(size * 2.2)), 36, fill=(255, 255, 255, 255))
        db.text((bx + 32, by + int(size * 0.42)), body, font=ft, fill=(25, 25, 28, 255))
        _CHAT[kind] = (bg, ph, bub)
    bg, ph, bub = _CHAT[kind]
    img = bg.convert("RGBA")
    img.alpha_composite(ph)
    t0 = 0.08 if kind == "doyun" else 0.2
    if lt >= t0:
        k = ease((lt - t0) / 0.18)
        b = with_alpha(bub, k)
        if b is not None:
            img.alpha_composite(b, (0, int(30 * (1 - k))))
    return img.convert("RGB")


# ---------------------------------------------------------------- 끝 화면과 엽전 구멍 줌 스루
_END = {}
CX10, CY10 = 765, 890
HOLE = 74 * 0.32


def endcard_full():
    if "full" not in _END:
        s1 = view(grab("S1", 0.4))
        bg = s1.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.42))
        labels = ["축사", "회식", "소개팅", "빼빼로", "택시", "다녀와", "무르기", "퇴근", "월요일", "건배사"]
        full = AN.coin_string(bg.copy(), labels)
        d = ImageDraw.Draw(full)

        def c(t, f, y, fill):
            w = d.textlength(t, font=f)
            d.text(((W - w) / 2, y), t, font=f, fill=fill)
        c("입버릇이 복을 부르기도,", F(FB, 60), 300, (255, 255, 255))
        c("쫓기도 해요", F(FB, 60), 384, (255, 255, 255))
        c("10닢째", F(FB, 52), 1080, (255, 200, 60))
        c("2027 한 수", F(FB, 60), 1190, (255, 255, 255))
        f2 = F(FB, 42)
        w = d.textlength("hongchaksa.kr", font=f2)
        d.rounded_rectangle((540 - w / 2 - 32, 1310, 540 + w / 2 + 32, 1386), 38, outline=(215, 215, 215), width=2)
        c("hongchaksa.kr", f2, 1318, (245, 245, 245))
        pre = full.copy()
        pre.paste(bg.crop((CX10 - 120, CY10 - 135, CX10 + 120, CY10 + 150)), (CX10 - 120, CY10 - 135))
        ImageDraw.Draw(pre).line((CX10 - 120, CY10, CX10 + 60, CY10), fill=(170, 40, 40), width=6)
        coin = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        AN.coin(ImageDraw.Draw(coin), 90, 90, 74, True)
        pad = Image.new("RGB", (W + 1200, H + 1200), (12, 10, 9))
        pad.paste(full, (600, 600))
        _END.update(full=full, pre=pre, coin=coin, pad=pad)
    return _END


def endcard(lt):
    E = endcard_full()
    dur = TOTAL - T["END"][0]
    zt = 0.6
    if lt >= dur - zt:
        p = (lt - (dur - zt)) / (zt - 0.06)
        p = min(1.0, p)
        q = p ** 2.2
        s = math.exp(math.log(46.0) * q)
        m = smooth(min(1.0, p * 2.5))
        cx = 540 + (CX10 - 540) * m
        cy = 960 + (CY10 - 960) * m
        bw, bh = W / s, H / s
        box = (cx - bw / 2 + 600, cy - bh / 2 + 600, cx + bw / 2 + 600, cy + bh / 2 + 600)
        img = E["pad"].resize((W, H), Image.BICUBIC, box=box)
        side = 2 * HOLE * s
        sx = (CX10 - cx) * s + 540
        sy = (CY10 - cy) * s + 960
        hs = min(H, side)
        sc = hs / H
        op = opening(0.0)
        if sc > 0.01:
            ow, oh = max(1, int(W * sc)), max(1, int(H * sc))
            small = op.resize((ow, oh), Image.BICUBIC)
            l, t = int(sx - ow / 2), int(sy - oh / 2)
            mk = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mk).rectangle((sx - side / 2, sy - side / 2, sx + side / 2, sy + side / 2), fill=255)
            canvas = img.copy()
            canvas.paste(small, (l, t))
            img = Image.composite(canvas, img, mk)
        if p >= 1.0:
            img = op
        return img
    if lt >= 0.5:
        return E["full"]
    k = ease(lt / 0.45)
    img = E["pre"].copy()
    x = int(1100 + (CX10 - 1100) * k) - 90
    y = int(200 + (CY10 - 200) * k) - 90
    img.paste(E["coin"], (x, y), E["coin"])
    return img



OPT["RW"]["rew"] = (T["H2"][1] - 0.05, 0.3)

# ---------------------------------------------------------------- 공포 스릴러 효과(11화에서 가져옴)
_RNG = np.random.default_rng(10)


def thriller(a, k=1.0):
    lum = a.mean(axis=2, keepdims=True) / 255.0
    sh = np.array([-10, 4, 14], np.float32) * (1 - lum)
    hi = np.array([14, 4, -12], np.float32) * lum
    b = (a - 128) * 1.18 + 128 + sh + hi
    gray = b.mean(axis=2, keepdims=True)
    b = gray + (b - gray) * 0.84
    return a * (1 - k) + b * k


def horror(a, k=1.0):
    """붉은 그림자와 눌린 밝기: 공포 구간."""
    b = thriller(a, 1.0) * np.array([1.04, 0.86, 0.84], np.float32) * 0.82
    return a * (1 - k) + b * k


def night(a, k=1.0):
    b = thriller(a, 1.0) * np.array([0.80, 0.92, 1.12], np.float32) * 0.9
    return a * (1 - k) + b * k


def golden(a, k=1.0):
    b = a * np.array([1.08, 1.0, 0.86], np.float32) + np.array([14, 8, 0], np.float32)
    return a * (1 - k) + b * k


def grain(a, s=7.0):
    n = _RNG.normal(0, s, (H // 2, W // 2, 1)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, axis=0), 2, axis=1)
    return a + n


def red_wash(a, k):
    """붉은 조명: 밝기는 살리고 초록과 파랑을 눌러 핏빛 어둠으로."""
    k = min(1.0, k * 2.4)
    b = a * np.array([1.10, 0.40, 0.42], np.float32)
    return a * (1 - k) + b * k


def letterbox(img):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 104), fill=(0, 0, 0))
    d.rectangle((0, H - 104, W, H), fill=(0, 0, 0))
    return img


def flash_k(lt, t0, dur=0.18):
    if t0 <= lt < t0 + dur:
        return 1 - (lt - t0) / dur
    return 0.0


_FL = np.random.default_rng(7).random(4000)


def flicker(Tabs, depth=0.6):
    """고장 난 조명처럼 불규칙하게 어두워졌다 돌아온다."""
    i = int(Tabs * 22)
    v = _FL[i % len(_FL)]
    if v < 0.22:
        return 1 - depth
    if v < 0.34:
        return 1 - depth * 0.45
    return 1.0


def ov_big(s, color, size=460, cx=540, cy=900, stroke=14):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, size)
        w = d.textlength(s, font=f)
        d.text((cx - w / 2, cy - size * 0.62), s, font=f, fill=color, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        return im
    return cached(("big", s, color, size, cx, cy), mk)


def ov_whisper(s):
    """속삭임 자막: 붉은 글자와 번지는 그림자."""
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, 96)
        w = d.textlength(s, font=f)
        d.text(((W - w) / 2, 1110), s, font=f, fill=(255, 40, 40, 255), stroke_width=8, stroke_fill=(0, 0, 0, 255))
        glow = im.filter(ImageFilter.GaussianBlur(16))
        out = layer()
        out.alpha_composite(glow)
        out.alpha_composite(im)
        return out
    return cached(("whisper", s), mk)


def ov_capband(s, y=190, size=60):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        lines = s.split("\n")
        f = F(FB, size)
        w = max(d.textlength(l, font=f) for l in lines)
        lh = int(size * 1.36)
        d.rounded_rectangle((540 - w / 2 - 36, y - 18, 540 + w / 2 + 36, y + lh * len(lines) + 4), 22, fill=(8, 8, 10, 215))
        for i, l in enumerate(lines):
            text_center(d, y + i * lh, l, f, stroke=4)
        return im
    return cached(("capband", s, y, size), mk)


def stamp2_img(lines, size, color=(214, 38, 38, 255)):
    def mk():
        f = F(FB, size)
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        tw = max(tmp.textlength(s, font=f) for s in lines)
        pad = int(size * 0.45)
        lh = int(size * 1.25)
        w, h = int(tw + pad * 2), int(lh * len(lines) + size * 0.5)
        im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((10, 10, 10 + w, 10 + h), int(size * 0.28), fill=(255, 250, 244, 225), outline=color, width=max(6, size // 10))
        for i, s in enumerate(lines):
            sw = d.textlength(s, font=f)
            d.text((10 + (w - sw) / 2, 10 + size * 0.2 + i * lh), s, font=f, fill=color)
        g = np.random.default_rng(len(lines[0]) + size)
        a = np.asarray(im).copy()
        holes = g.random(a.shape[:2]) < 0.05
        a[holes, 3] = (a[holes, 3] * 0.35).astype(np.uint8)
        return Image.fromarray(a).rotate(-6, resample=Image.BICUBIC, expand=True)
    return cached(("stamp2", tuple(lines), size, color), mk)


def ov_stamp2(lines, size, cx, cy, lt, color=(214, 38, 38, 255)):
    if lt < 0:
        return None
    im = stamp2_img(lines, size, color)
    k = ease(lt / 0.1)
    s = 1.9 - 0.9 * k
    big = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    out = layer()
    out.alpha_composite(big, (int(cx - big.width / 2), int(cy - big.height / 2)))
    return with_alpha(out, min(1.0, 0.3 + k))


_RAYS = {}


def ov_rays(k):
    if "r" not in _RAYS:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        ox, oy = 980, -120
        for i in range(9):
            ang = math.radians(112 + i * 7.5)
            w = 26 + (i % 3) * 18
            x1, y1 = ox + math.cos(ang) * 2600, oy + math.sin(ang) * 2600
            nx, ny = -math.sin(ang) * w, math.cos(ang) * w
            d.polygon([(ox, oy), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny)], fill=(255, 214, 140, 46))
        _RAYS["r"] = im.filter(ImageFilter.GaussianBlur(18))
    return with_alpha(_RAYS["r"], k)


def ov_sparks(lt, seed=3):
    """잔이 부딪는 순간의 금빛 불꽃."""
    g = np.random.default_rng(seed)
    im = layer()
    d = ImageDraw.Draw(im)
    for _ in range(46):
        ang = g.random() * math.tau
        sp = 300 + g.random() * 900
        x = 540 + math.cos(ang) * sp * lt
        y = 900 + math.sin(ang) * sp * lt + 420 * lt * lt
        r = 4 + g.random() * 6
        a = int(255 * max(0.0, 1 - lt / 1.0))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 220, 120, a))
    return im.filter(ImageFilter.GaussianBlur(1.5))


# ---------------------------------------------------------------- 바탕 화면
LOOK = {"O1": "horror", "H1": "horror", "H2": "horror", "S6": "horror", "F1": "memory", "F2": "memory", "H3": "night",
        "S10": "gold", "S12": "gold_in", "S13": "gold", "S14": "gold", "S15": "gold", "S16": "gold", "O2": "horror",
        "S17": "horror_in", "H2b": "horror", "S18": "horror", "S19": "horror", "N5": "horror", "N3": "gold", "N4": "gold",
        "E7a": "gold", "E7b": "gold"}
BOX = {"H1", "H2", "S6", "S10", "F1", "F2", "H3", "S12", "S13", "S14", "S15", "S16", "S17", "H2b", "S18", "S19", "N5", "N3", "N4"}


def shot_at(Tabs):
    for sid in ORDER:
        if T[sid][0] <= Tabs < T[sid][1]:
            return sid
    return ORDER[-1]


def base_frame(sid, lt, dur, light=False):
    o = OPT[sid]
    post = {}
    if o.get("tagshot"):
        u0, z0, z1 = o["tagshot"]
        return opening(lt, dur, u0, z0, z1), post
    if o.get("insert") and o["insert"][0] <= lt < o["insert"][1] and not light:
        i0 = o["insert"][0]
        img = view(chat_frame("doyun", 0.1 + (lt - i0)), 1.18, 0.5, 0.42)
        post.update(red=0.18, chroma=6, flash=flash_k(lt, i0, 0.12) * 0.8, look="none")
        return img, post
    if "src" in o:
        stop = o.get("stopat")
        tail = o.get("tail")
        lt2 = lt
        if stop is not None and lt >= stop:
            lt2 = stop
        if tail is not None and lt >= dur - tail:
            lt2 = dur - tail
        st = o["a"] + lt2 * o.get("speed", 1.0)
        if light:
            im = grab(o["src"], st)
        elif o.get("speed", 1.0) != 1.0:
            im = clip(sid).blend(st)
        else:
            im = clip(sid).at(st)
        cx, cy = o.get("c", (0.5, 0.5))
        z = 1.0
        if "zz" in o:
            z0, z1 = o["zz"]
            z = z0 + (z1 - z0) * (ease(min(1.0, lt / o["crash"])) if o.get("crash") else smooth(lt / dur))
        if o.get("steps"):
            n = sum(1 for s in o["steps"] if lt >= s)
            z = (1.0, 1.12, 1.28, 1.48)[min(3, n)] * (1.0 + 0.05 * (1 - ease((lt - o["steps"][n - 1]) / 0.07)))
            post["flash"] = flash_k(lt, o["steps"][n - 1], 0.07) * 0.35
        if stop is not None and lt >= stop:
            z = z * (1.0 + (o["snapz"] - 1.0) * ease((lt - stop) / 0.08))
            post.update(grade="bw", gk=0.85, vign=0.5)
        if tail is not None and lt >= dur - tail:
            z = z * (1.0 + 0.12 * ease((lt - (dur - tail)) / 0.08))
            post.update(grade="bw", gk=1.0, vign=0.5)
        img = view(im, z, cx, cy)
        return img, post
    if "still" in o:
        if "snap" in o:
            z0, z1 = o["snap"]
            z = z0 + (z1 - z0) * ease(lt / 0.09)
            if o.get("step2") and lt >= o["step2"][0]:
                z = z1 + (o["step2"][1] - z1) * ease((lt - o["step2"][0]) / 0.07)
        else:
            z0, z1 = o["z"]
            z = z0 + (z1 - z0) * smooth(lt / dur)
        if "c0" in o:
            k = smooth(lt / dur)
            cx = o["c0"][0] + (o["c1"][0] - o["c0"][0]) * k
            cy = o["c0"][1] + (o["c1"][1] - o["c0"][1]) * k
        else:
            cx, cy = o["c"]
        img = view(still(o["still"]), z, cx, cy)
        return img, post
    if "freeze" in o:
        name, t = o["freeze"]
        cx, cy = o["c"]
        z = 1.0 + (o["z"] - 1.0) * ease(lt / 0.1)
        img = view(grab(name, t), z, cx, cy)
        post.update(grade="bw", gk=1.0, vign=0.5, red=0.12 * (1 - ease(lt / 0.3)))
        return img, post
    if o.get("chat"):
        img = chat_frame(o["chat"], lt)
        z = 1.0 + 0.1 * ease(max(0.0, lt - 0.2) / 0.1)
        img = view(img, z, 0.5, 0.45)
        post.update(red=0.10 + 0.08 * (0.5 + 0.5 * math.sin(lt * 20)), flash=flash_k(lt, 0.2, 0.12) * 0.6, look="none")
        return img, post
    if "rew" in o:
        T0, T1 = o["rew"]
        p = smooth(lt / dur)
        Ts = max(0.0, T0 - (T0 - T1) * p - 0.001)
        sid2 = shot_at(Ts)
        img, _ = base_frame(sid2, Ts - T[sid2][0], T[sid2][1] - T[sid2][0], light=True)
        speed = math.sin(math.pi * min(1.0, lt / dur))
        post.update(grade="rewind", hblur=10 + 30 * speed, chroma=int(4 + 8 * speed), scan=0.25, vign=0.4, look="none")
        return img, post
    if o.get("end"):
        return endcard(lt), post
    raise ValueError(sid)


# ---------------------------------------------------------------- 자막과 표시
SUBS = [  # (시작, 끝, 글, 방식)
    (at("H1", 0.30), at("H1", -0.02), "잠깐 시간 돼?", "whisper"),
    (at("S10", 0.15), at("S10", -0.05), "제일 많이 들은 말, 뭐예요?", "sub"),
    (at("F1", 0.08), at("F1", -0.02), "잠깐 시간 돼?", "voice"),
    (at("F2", 0.08), at("F2", -0.02), "잠깐 시간 돼?", "voice"),
    (at("S12", 0.3), at("S12", -0.03), "잠깐 시간 돼, 하면 내년에.", "sub"),
    (at("S13", 0.1), at("S13", -0.01), "잠깐 시간 돼?", "pop_white"),
    (at("S15", 0.55), at("S15", -0.01), "내년에.", "pop_yellow"),
    (at("S17", 0.08), at("S17", -0.01), "도윤 씨, 잠깐 시간 돼?", "sub"),
    (at("S18", 0.05), at("S18", 0.78), "내년에.", "suby"),
    (at("S19", 0.1), at("S19", -0.02), "그래, 이건 내년에.", "sub"),
    (at("N5", 0.27), at("N5", 0.8), "내년에.", "suby"),
    (at("N3", 0.5), at("N3", -0.02), "이건 올해 받아.", "hl"),
    (at("E7a", 0.03), at("E7b", -0.02), "홍책사 한 수면, 됐지?", "sub"),
]
CAPS = [  # 위쪽 상황 자막(시작, 끝, 글, 크기)
    (0.0, T["H1"][1] - 0.0001, "송년회, 팀장님이\n100만 원 봉투를 꺼냈다", 64),
    (T["H2"][0], T["H2"][1] - 0.0001, "올해만 413번째 들은 그 말", 62),
    (at("S6", 0.05), T["S6"][1] - 0.0001, "막내 도윤의 건배사 차례,\n머릿속이 하얘졌다", 60),
    (T["S10"][0], T["S10"][1] - 0.0001, "그때, 고깃집 직원 홍책사", 62),
    (T["F1"][0], T["H3"][1] - 0.0001, "도윤이 올해 제일 많이 들은 말", 60),
    (at("S15", 0.55), T["S15"][1] - 0.0001, "팀장님이 제일 크게", 66),
    (T["S16"][0], T["S16"][1] - 0.0001, "분위기 살렸다", 70),
    (T["O2"][0], T["S17"][1] - 0.0001, "봉투를 건네려는 순간", 64),
    (at("S18", 0.8), T["S18"][1] - 0.0001, "몸이 먼저 대답했다", 66),
    (T["N5a"][0], T["N5a"][1] - 0.0001, "그 시각 팀장님 휴대폰", 62),
    (at("N4", 0.05), T["N4"][1] - 0.0001, "이번엔 반사 안 함", 66),
]
STAMPS2 = [  # (등장, 끝, 줄, 크기, x, y)
    (at("F1", 0.35), T["F1"][1], ["410번째", "보고서 추가"], 58, 760, 1330),
    (at("F2", 0.35), T["F2"][1], ["411번째", "야근"], 70, 780, 1320),
    (at("H3", 0.85), T["H3"][1], ["올해 412번째", "내일 아침까지"], 84, 540, 1090),
    (at("H2b", 0.12), T["H2b"][1], ["413번째"], 112, 540, 1260),
    (at("N5a", 0.6), T["N5a"][1], ["팀장님도", "올해 389번째"], 70, 540, 1420),
]
SHAKE = [(at("H2", 0.0), 0.22, 0.016), (at("F2", 0.35), 0.16, 0.012), (at("H3", 0.5), 0.3, 0.022),
         (at("H3", 0.85), 0.25, 0.018), (at("H2b", 0.12), 0.2, 0.016), (at("FZ2", 0.0), 0.3, 0.02),
         (at("N5a", 0.6), 0.16, 0.012), (at("S15", 0.55), 0.16, 0.01)]
CLOCKS = [("F1", "09:00"), ("F2", "17:59"), ("H3", "23:40")]


def overlays(sid, lt, dur, Tabs):
    out = []
    for s0, s1, t, size in CAPS:
        a = win(Tabs, s0, s1, 0.0 if s0 < 0.01 else 0.05, 0.06)
        if a:
            out.append((ov_capband(t, 190, size), a))
    a = win(Tabs, at("S6", 0.2), at("S6", -0.1), 0.12, 0.12)
    if a:
        out.append((ov_hook("도윤과 최 팀장, 8화 그 팀"), a))
    a = win(Tabs, at("S10", 0.15), at("S10", -0.1), 0.1, 0.12)
    if a:
        k = ease((Tabs - at("S10", 0.15)) / 0.12)
        out.append((scaled(ov_tag("홍책사"), 1.3 - 0.3 * k, 960, 1027), a))
    if sid in ("S10", "S15"):
        out.append((ov_rays(0.8 if sid == "S10" else min(1.0, max(0.0, (lt - 0.5) / 0.2))), 1.0))
    if sid == "RW":
        k = ease(lt / 0.1)
        out.append((scaled(ov_big("10분 전", (255, 255, 255, 255), 150, 540, 960, 10), 1.25 - 0.25 * k, 540, 960), 1.0))
    for s, t in CLOCKS:
        s0, s1 = T[s]
        if s0 <= Tabs < s1 and not (s == "H3" and OPT["H3"]["insert"][0] <= lt < OPT["H3"]["insert"][1]):
            k = ease((Tabs - s0) / 0.1)
            out.append((scaled(ov_clock(t), 1.0 + 0.1 * (1 - k), 200, 1330), 1.0))
    b0, b1 = at("S12", 0.3), at("S12", -0.02)
    if b0 <= Tabs < b1:
        out.append((ov_board(2 if Tabs >= at("S12", 1.9) else 1), win(Tabs, b0, b1, 0.1, 0.1)))
    for s0, s1, lines, size, cx, cy in STAMPS2:
        if s0 <= Tabs < s1:
            st = ov_stamp2(lines, size, cx, cy, Tabs - s0)
            if st is not None:
                out.append((st, 1.0))
    if sid == "S16":
        out.append((ov_sparks(lt / 1.1 * 0.9), 1.0))
    if sid == "FZ2":
        k = ease(lt / 0.1)
        out.append((scaled(ov_big("100만 원,", (255, 50, 50, 255), 120, 540, 1080, 10), 1.3 - 0.3 * k, 540, 1080), 1.0))
        out.append((scaled(ov_big("내년으로", (255, 255, 255, 255), 120, 540, 1240, 10), 1.3 - 0.3 * k, 540, 1240), 1.0))
    if sid == "N5" and lt >= OPT["N5"]["stopat"]:
        lt2 = lt - OPT["N5"]["stopat"]
        k = ease(lt2 / 0.1)
        out.append((scaled(ov_pop("팀장님도 반사", YEL, 300, 104), 1.15 - 0.15 * k, 540, 300), 1.0))
    for s0, s1, t, kind in SUBS:
        if s0 <= Tabs < s1:
            a = win(Tabs, s0, s1, 0.05, 0.07)
            if kind == "sub":
                out.append((ov_sub(t), a))
            elif kind == "suby":
                out.append((ov_suby(t), a))
            elif kind == "voice":
                out.append((ov_whisper(t), a))
            elif kind == "whisper":
                k = ease((Tabs - s0) / 0.25)
                out.append((scaled(ov_whisper(t), 1.12 - 0.12 * k, 540, 1170), a))
            elif kind == "hl":
                out.append((ov_sub_hl((("이건 ", False), ("올해", True), (" 받아.", False))), a))
            else:
                col = (255, 255, 255, 255) if kind == "pop_white" else YEL
                k = ease((Tabs - s0) / 0.12)
                out.append((scaled(ov_pop(t, col), 1.1 - 0.1 * k, 540, 1010), a))
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
    for t0, d0, amp in SHAKE:
        if t0 <= Tabs < t0 + d0:
            k = 1 - (Tabs - t0) / d0
            img = view(img, 1.0 + 2.5 * amp, 0.5 + amp * k * math.sin((Tabs - t0) * 90),
                       0.5 + amp * k * math.cos((Tabs - t0) * 70))
    a = arr(img)
    look = post.get("look", LOOK.get(sid))
    if look == "horror":
        a = horror(a)
    elif look == "horror_in":
        a = horror(a, 0.4 + 0.6 * smooth(lt / dur))
    elif look == "night":
        a = night(a)
    elif look == "memory":
        a = grade(a, "memory", 1.0)
        a = horror(a, 0.5)
    elif look == "gold":
        a = golden(thriller(a, 0.6), 0.6)
    elif look == "gold_in":
        k = smooth(lt / 0.8)
        a = horror(a, 1 - k) * 1.0
        a = golden(a, 0.6 * k)
    if post.get("grade"):
        a = grade(a, post["grade"], post.get("gk", 1.0))
    # 조명 깜빡임: 공포 구간
    if sid in ("O1", "S6", "O2", "S17") or (sid == "F1"):
        a = a * flicker(Tabs, 0.55 if sid != "S17" else 0.45)
    if sid == "H1" and 0.05 <= lt < 0.2:
        post["flash"] = 0.55 * (1 - (lt - 0.05) / 0.15)
    if sid in ("O1", "H2"):
        post["red"] = max(post.get("red", 0.0), 0.10 + 0.12 * max(0.0, math.sin(lt * 9)))
    if sid == "S17":
        post["red"] = max(post.get("red", 0.0), 0.22 * smooth(lt / dur))
    if sid == "F2":
        post["red"] = 0.14
    if sid == "H3" and post.get("look") is None and lt >= 0.8:
        post["flash"] = flash_k(lt, 0.8, 0.12) * 0.7
    if sid == "S15" and lt >= 0.55:
        post["flash"] = flash_k(lt, 0.55, 0.22) * 0.75
        post["gold"] = True
    if sid == "S16":
        post["flash"] = flash_k(lt, 0.25, 0.25) * 0.6
        post["gold"] = True
    if sid == "N3":
        post["flash"] = flash_k(lt, 0.0, 0.3) * 0.8
        post["gold"] = True
    if sid == "N5" and lt >= OPT["N5"]["stopat"]:
        post["flash"] = flash_k(lt, OPT["N5"]["stopat"], 0.14) * 0.9
    if sid == "H2b":
        post["flash"] = flash_k(lt, 0.12, 0.1) * 0.6
        post["red"] = 0.16
    if post.get("red"):
        a = red_wash(a, post["red"])
    if post.get("hblur"):
        a = hblur(a, post["hblur"])
    if post.get("chroma"):
        a = chroma(a, post["chroma"])
    if post.get("scan"):
        a = scanlines(a, post["scan"])
    if post.get("vign"):
        a = vignette(a, post["vign"])
    if sid in BOX:
        a = vignette(a, 0.45)
        a = grain(a, 6.0)
    if post.get("flash"):
        f = post["flash"]
        col = np.array([255, 236, 200] if post.get("gold") else [255, 255, 255], np.float32)
        a = a * (1 - f) + col * f
    base = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if sid in BOX and post.get("look") is None:
        base = letterbox(base)
    ovs = overlays(sid, lt, dur, Tabs)
    if sid != "END" or lt < 2.3:
        ovs.append((ov_ai(), 1.0))
    return sid, composite(arr(base), ovs)


def render(out, t_from=0.0, t_to=None):
    t_to = TOTAL if t_to is None else t_to
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-vf", "unsharp=5:5:0.3", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
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
        os.makedirs(f"{D}/out/v22f", exist_ok=True)
        for t in ts:
            sid, fr = frame_at(min(TOTAL - 1e-3, t))
            fr.save(f"{D}/out/v22f/f_{t:05.2f}_{sid}.jpg", quality=88)
            print(t, sid)
        sys.exit(0)
    out = args[0] if args and not args[0].startswith("--") else f"{D}/out/ep10_v22_video.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tf = float(args[args.index("--from") + 1]) if "--from" in args else 0.0
    tt = float(args[args.index("--to") + 1]) if "--to" in args else None
    render(out, tf, tt)
