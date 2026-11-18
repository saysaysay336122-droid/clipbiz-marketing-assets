"""홍책사 9화 v6 편집(월요일 9시, 회의실이 터졌다).
사용: python3 build_ep9.py 출력.mp4 [--from 초 --to 초]
생성 클립(gen9/clips), 시작 사진(gen9/stills), 7화 고정 멘트 클립을 설계서 ep09_spec_v6.json 시간표대로 잇고
충격 레이어(tools/vfx_impact.py), HUD, 시간 정지 색, 금빛 격자, 자막, 끝 화면을 얹는다.
"""
import json
import math
import os
import random
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import animatic as AN  # noqa: E402
import vfx_impact as VX  # noqa: E402

W, H, FPS = 1080, 1920, 30
D = "/home/claude/clipbiz-marketing-assets/w/261130"
G = f"{D}/gen9"
EP7 = "/home/claude/ep7/v/clips/S16.mp4"
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SPEC = json.load(open(f"{D}/ep09_spec_v6.json", encoding="utf-8"))
TOTAL = SPEC["target_sec"]
T = {s["id"]: tuple(s["t"]) for s in SPEC["shots"]}
ORDER = [s["id"] for s in SPEC["shots"]]
GOLD = (255, 205, 110)
_FC = {}


def F(path, size):
    k = (path, size)
    if k not in _FC:
        f = None
        for i in range(10):
            f = ImageFont.truetype(path, size, index=i)
            if "KR" in f.getname()[0]:
                break
        _FC[k] = f
    return _FC[k]


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- 소스
class Clip:
    def __init__(self, path, mirror=False):
        cap = cv2.VideoCapture(path)
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 24
        fr = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            fr.append(f[:, ::-1].copy() if mirror else f)
        self.frames = fr

    def at(self, t):
        x = t * self.fps
        i = int(math.floor(x))
        a = x - i
        i0 = min(len(self.frames) - 1, max(0, i))
        i1 = min(len(self.frames) - 1, max(0, i + 1))
        if a < 0.08 or i0 == i1:
            return Image.fromarray(self.frames[i0])
        return Image.fromarray(cv2.addWeighted(self.frames[i0], 1 - a, self.frames[i1], a, 0))


_CL = {}


def clip(name, mirror=False):
    k = (name, mirror)
    if k not in _CL:
        _CL[k] = Clip(EP7 if name == "EP7" else f"{G}/clips/{name}.mp4", mirror)
    return _CL[k]


_ST = {}


def still(name):
    if name not in _ST:
        _ST[name] = Image.open(f"{G}/stills/{name}.png").convert("RGB")
    return _ST[name]


def win(img, z=1.0, cx=0.5, cy=0.5):
    iw, ih = img.size
    cw, ch = iw / z, ih / z
    x0 = min(iw - cw, max(0, cx * iw - cw / 2))
    y0 = min(ih - ch, max(0, cy * ih - ch / 2))
    return x0, y0, cw, ch


def view(img, z=1.0, cx=0.5, cy=0.5, dx=0.0, dy=0.0):
    x0, y0, cw, ch = win(img, z, cx, cy)
    iw, ih = img.size
    x0 = min(iw - cw, max(0, x0 - dx * cw / W))
    y0 = min(ih - ch, max(0, y0 - dy * ch / H))
    return img.resize((W, H), Image.LANCZOS if img.width > W else Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def to_screen(img, px, py, z=1.0, cx=0.5, cy=0.5):
    """원본 비율 좌표(px, py)가 view 뒤 화면 어디에 오는지."""
    x0, y0, cw, ch = win(img, z, cx, cy)
    iw, ih = img.size
    return (px * iw - x0) / cw * W, (py * ih - y0) / ch * H


def shake(t, amp=14, f=37):
    return amp * math.sin(t * f * 2.1), amp * 0.7 * math.cos(t * f * 1.7)


def arr(img):
    return np.asarray(img, dtype=np.float32)


# ---------------------------------------------------------------- 색
def grade(a, kind, k=1.0):
    if kind is None or k <= 0:
        return a
    if kind == "frozen":
        lum = a.mean(axis=2, keepdims=True)
        b = a * 0.40 + lum * 0.60
        b = b * np.array([0.86, 0.96, 1.10], np.float32) * 0.95 + np.array([0, 5, 12], np.float32)
    elif kind == "action":
        lum = a.mean(axis=2, keepdims=True) / 255.0
        hi = np.clip((lum - 0.45) / 0.55, 0, 1)
        lo = 1 - np.clip(lum / 0.45, 0, 1)
        b = a + hi * np.array([14, 5, -10], np.float32) + lo * np.array([-8, 4, 10], np.float32)
        b = (b - 128) * 1.07 + 128
    elif kind == "neutral":
        lum = a.mean(axis=2, keepdims=True)
        b = (a * 0.9 + lum * 0.1) * np.array([0.99, 1.0, 1.01], np.float32)
    elif kind == "warm":
        b = a * np.array([1.06, 1.01, 0.92], np.float32) + np.array([5, 2, 0], np.float32)
    else:
        return a
    return a * (1 - k) + b * k


def chroma(a, px):
    if px <= 0:
        return a
    b = a.copy()
    b[..., 0] = np.roll(a[..., 0], px, axis=1)
    b[..., 2] = np.roll(a[..., 2], -px, axis=1)
    return b


def hblur(a, amount):
    if amount < 2:
        return a
    n = 7
    acc = np.zeros_like(a)
    for i in range(n):
        acc += np.roll(a, int((i - n // 2) * amount / n), axis=1)
    return acc / n


def vign(a, k=0.25):
    yy, xx = np.mgrid[0:H, 0:W]
    vm = 1 - k * np.clip((np.hypot(xx - 540, (yy - 960) * 0.7) - 360) / 560, 0, 1)
    return a * vm.astype(np.float32)[..., None]


# ---------------------------------------------------------------- 충격 레이어(vfx_impact, BGR 기준)
_PARTS = {}


def impact(a, t, px, py, material="carpet", seed=7, strong=True, ox_amp=1.0, flash_k=0.82):
    """a: RGB float 화면. t: 접촉 기준 시각. 일곱 층을 겹친다."""
    b = a[..., ::-1].copy()
    cx, cy = px * W, py * H
    key = (px, py, material, seed)
    if key not in _PARTS:
        _PARTS[key] = VX.Particles(cx, cy, W, H, seed=seed, material=material)
    parts = _PARTS[key]
    if -0.5 <= t < 0.05:  # 위에서 내려오는 거대한 그림자(주먹이 보이게 옅게)
        k = (t + 0.5) / 0.5
        m = np.zeros((H, W), np.float32)
        cv2.ellipse(m, (int(W * 0.52), int(-H * 0.25 + H * 0.95 * k)), (int(W * 0.55), int(H * 0.22)), 0, 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), 60) * 0.38 * k + 0.1 * k
        b = b * (1 - np.clip(m, 0, 0.5)[..., None])
    b = VX.vblur(b, t)
    b = parts.draw(b, t, "bg")
    if material == "carpet":
        b = VX.dust(b, cx, cy, t, seed=seed)
    b = VX.shockwave(b, cx, cy, t, amp=26 if strong else 14)
    b = parts.draw(b, t, "fg")
    if strong:
        b = b * (1 - flash_k) + VX.flash(b, t) * flash_k
        b = VX.flicker(b, t)
    b = VX.chroma(np.clip(b, 0, 255), t)
    ox, oy = VX.shake_offset(t, seed)
    out = np.ascontiguousarray(b[..., ::-1])
    if ox or oy:
        M = np.float32([[1.06, 0, ox * ox_amp - W * 0.03], [0, 1.06, oy * ox_amp - H * 0.03]])
        out = cv2.warpAffine(out, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return out


# ---------------------------------------------------------------- 겹치는 그림(RGBA)
_OV = {}


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def cached(key, fn):
    if key not in _OV:
        _OV[key] = fn()
    return _OV[key]


def with_alpha(im, a):
    if im is None or a <= 0.001:
        return None
    if a >= 0.999:
        return im
    r, g, b, al = im.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))


def fade(lt, s, e, fin=0.1, fout=0.1, first=False):
    if lt < s or lt >= e:
        return 0.0
    a = 1.0
    if not first and fin > 0:
        a = min(a, (lt - s) / fin)
    if fout > 0:
        a = min(a, (e - lt) / fout)
    return max(0.0, min(1.0, a))


def text_center(d, y, s, f, fill=(255, 255, 255, 255), stroke=6, sfill=(0, 0, 0, 255), x=None):
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2 if x is None else x - w / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)


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
        lines = s.split("\n")
        y = 1150 - (len(lines) - 1) * 42
        for i, l in enumerate(lines):
            text_center(d, y + i * 84, l, F(FB, size), stroke=5)
        return im
    return cached(("sub", s, size), mk)


def ov_tag(s, y=990):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, 46)
        w = d.textlength(s, font=f)
        x1 = 1040
        x0 = x1 - w - 48
        d.rounded_rectangle((x0, y, x1, y + 74), 18, fill=(20, 20, 20, 200))
        d.text((x0 + 24, y + 7), s, font=f, fill=(255, 214, 80, 255))
        return im
    return cached(("tag", s, y), mk)


def ov_flash(alpha, color=(255, 255, 255)):
    return Image.new("RGBA", (W, H), color + (int(255 * min(1, max(0, alpha))),))


def ov_ring(cx, cy, r, alpha, color=(255, 255, 255), width=12):
    im = layer()
    if r > 2 and alpha > 0.01:
        d = ImageDraw.Draw(im)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (int(255 * alpha),), width=width)
        d.ellipse((cx - r * 0.93, cy - r * 0.93, cx + r * 0.93, cy + r * 0.93), outline=color + (int(110 * alpha),), width=max(2, width // 2))
    return im


def glow_layer(im, radius=10, gain=1.0):
    """RGBA 그림에 같은 색 번짐을 더한다."""
    g = im.filter(ImageFilter.GaussianBlur(radius))
    out = layer()
    out.alpha_composite(with_alpha(g, min(1.0, gain)))
    out.alpha_composite(im)
    return out


def flare(cx, cy, length=900, alpha=1.0, color=(255, 214, 140)):
    """아나모픽 렌즈 플레어 한 줄."""
    key = ("flare", int(cx) // 4, int(cy) // 4, length, color)

    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        for i, (w, a) in enumerate(((18, 30), (8, 80), (3, 200))):
            d.line((cx - length / 2, cy, cx + length / 2, cy), fill=color + (a,), width=w)
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=(255, 245, 225, 210))
        return im.filter(ImageFilter.GaussianBlur(3))
    return with_alpha(cached(key, mk), alpha)


_PT = None


def particles(t_abs, alpha=1.0, warm=True):
    """공기 속에 떠 있는 먼지."""
    global _PT
    if _PT is None:
        g = np.random.default_rng(8)
        n = 70
        _PT = dict(x=g.uniform(0, W, n), y=g.uniform(0, H, n), vx=g.uniform(-5, 5, n), vy=g.uniform(-7, 2, n),
                   r=g.uniform(1.6, 4.6, n), a=g.uniform(0.25, 0.75, n), ph=g.uniform(0, 6.28, n), f=g.uniform(0.6, 1.6, n))
    im = layer()
    d = ImageDraw.Draw(im)
    p = _PT
    c1, c2 = ((255, 236, 200), (255, 246, 225)) if warm else ((200, 225, 255), (235, 245, 255))
    for i in range(len(p["x"])):
        x = (p["x"][i] + p["vx"][i] * t_abs) % W
        y = (p["y"][i] + p["vy"][i] * t_abs) % H
        a = p["a"][i] * (0.65 + 0.35 * math.sin(p["ph"][i] + t_abs * p["f"][i] * 3)) * alpha
        r = p["r"][i]
        d.ellipse((x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2), fill=c1 + (int(40 * a),))
        d.ellipse((x - r, y - r, x + r, y + r), fill=c2 + (int(200 * a),))
    return im


# ---------------------------------------------------------------- HUD
def ov_hud(num, pop_t, big=False, mail=None, mail_t=0.0, blink_t=0.0):
    """금빛 선 HUD: 오른쪽 위 남은 안건, 왼쪽 위 배터리, 아래 시계와 메일. 큰 숫자만 또렷하게."""
    im = layer()
    d = ImageDraw.Draw(im)
    g = GOLD + (235,)
    gs = GOLD + (85,)
    m = 36
    L = 70
    for (x, y, sx, sy) in ((m, 130, 1, 1), (W - m, 130, -1, 1), (m, H - 130, 1, -1), (W - m, H - 130, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=g, width=3)
        d.line([(x, y), (x, y + sy * L)], fill=g, width=3)
    pop = 1.0 + 0.35 * math.exp(-pop_t / 0.08) if pop_t >= 0 else 1.0
    size = int(H / 5 * 0.62 * pop * (1.5 if big else 1.0))
    fb = F(FB, size)
    fs = F(FR, 30)
    x0, y0 = int(W * 0.50), int(H * 0.115)
    bw = W - m - 10 - x0
    bh = int(H * 0.2 * (1.35 if big else 1.0))
    d.rectangle([x0, y0, x0 + bw, y0 + bh], outline=gs, width=2)
    d.text((x0 + 18, y0 + 10), "남은 안건", font=fs, fill=g)
    s = str(num)
    tw = d.textlength(s, font=fb)
    jx = int(10 * math.sin(pop_t * 90)) if 0 <= pop_t < 0.12 else 0
    d.text((x0 + bw / 2 - tw / 2 + jx, y0 + 34 - (size - int(H / 5 * 0.62)) * 0.18), s, font=fb, fill=g)
    blink = int(blink_t * 8) % 2 == 0
    col = (255, 80, 70, 240) if blink else (255, 80, 70, 90)
    bx, by = m + 10, int(H * 0.13)
    d.rectangle([bx, by, bx + 120, by + 44], outline=col, width=3)
    d.rectangle([bx + 6, by + 6, bx + 20, by + 38], fill=col)
    d.text((bx, by + 52), "배터리 12%", font=fs, fill=col)
    d.text((m + 10, int(H * 0.86)), "09:00", font=F(FR, 34), fill=gs)
    mx, my = W - m - 90, int(H * 0.86)
    mc = g if mail else gs
    d.rectangle([mx, my, mx + 70, my + 46], outline=mc, width=3 if mail else 2)
    d.line([(mx, my), (mx + 35, my + 26), (mx + 70, my)], fill=mc, width=3 if mail else 2)
    if mail:
        k = ease(mail_t / 0.1)
        r = int(26 + 10 * (1 - k))
        cxm, cym = mx + 70, my - 4
        d.ellipse([cxm - r, cym - r, cxm + r, cym + r], fill=(235, 70, 60, 245))
        f2 = F(FB, 30)
        w2 = d.textlength(str(mail), font=f2)
        d.text((cxm - w2 / 2, cym - 21), str(mail), font=f2, fill=(255, 255, 255, 255))
    cx, cy = W // 2, int(H * 0.45)
    r = 150
    for a0 in (200, 290, 20, 110):
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a0 + 50, fill=gs, width=2)
    return glow_layer(im, 6, 0.8)


def ov_battery(s, red=True, y=140):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        col = (255, 80, 70, 250) if red else GOLD + (240,)
        bx, by = 46, y
        d.rectangle([bx, by, bx + 120, by + 44], outline=col, width=4)
        d.rectangle([bx + 120, by + 14, bx + 128, by + 30], fill=col)
        d.rectangle([bx + 6, by + 6, bx + 20, by + 38], fill=col)
        d.text((bx + 142, by - 4), s, font=F(FB, 40), fill=col)
        return glow_layer(im, 8, 0.9)
    return cached(("bat", s, red, y), mk)


def ov_hud_frame(alpha):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        g = GOLD + (220,)
        m, L = 36, 90
        for (x, y, sx, sy) in ((m, 130, 1, 1), (W - m, 130, -1, 1), (m, H - 130, 1, -1), (W - m, H - 130, -1, -1)):
            d.line([(x, y), (x + sx * L, y)], fill=g, width=4)
            d.line([(x, y), (x, y + sy * L)], fill=g, width=4)
        return glow_layer(im, 6, 0.8)
    return with_alpha(cached("hudframe", mk), alpha)


# ---------------------------------------------------------------- 사진 위 합성(원본 해상도)
def monitor_text(img, box, lines, color=(235, 245, 255), glow=True):
    """사진 속 모니터 상자(비율 좌표) 안에 글자를 켠다. lines: [(글자, 크기 비율, 색)]"""
    im = img.copy().convert("RGBA")
    iw, ih = im.size
    x0, y0, x1, y1 = box[0] * iw, box[1] * ih, box[2] * iw, box[3] * ih
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    bh = y1 - y0
    tot = sum(s for _, s, _ in lines)
    y = y0 + bh * 0.08
    bw = x1 - x0
    d.rounded_rectangle((x0 + bw * 0.03, y0 + bh * 0.04, x1 - bw * 0.03, y1 - bh * 0.04), int(bh * 0.06), fill=(12, 18, 30, 238))
    im.alpha_composite(lay)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for txt, s, col in lines:
        sz = int(bh * 0.84 * s / tot)
        while sz > 10 and d.textlength(txt, font=F(FB, sz)) > bw * 0.84:
            sz -= 2
        f = F(FB, max(10, sz))
        w = d.textlength(txt, font=f)
        d.text(((x0 + x1) / 2 - w / 2, y), txt, font=f, fill=col + (255,))
        y += bh * 0.84 * s / tot * 1.02
    if glow:
        g = lay.filter(ImageFilter.GaussianBlur(max(3, int(bh * 0.05))))
        im.alpha_composite(g)
    im.alpha_composite(lay)
    return im.convert("RGB")


_DOTS = None


def cable_dots():
    """S17 사진의 검은 전선 위에 흰 바둑돌 빛 52개 자리."""
    global _DOTS
    if _DOTS is None:
        im = np.asarray(still("S17").convert("L"), np.float32)
        ih, iw = im.shape
        m = (im < 42).astype(np.uint8)
        m = cv2.erode(m, np.ones((15, 15), np.uint8))
        m[: int(ih * 0.44)] = 0
        ys, xs = np.nonzero(m)
        rnd = random.Random(5)
        idx = list(range(len(xs)))
        rnd.shuffle(idx)
        pts = []
        for i in idx:
            x, y = xs[i], ys[i]
            if all((x - a) ** 2 + (y - b) ** 2 > 105 ** 2 for a, b in pts):
                pts.append((x, y))
            if len(pts) >= 52:
                break
        _DOTS = [(x / iw, y / ih) for x, y in pts]
    return _DOTS


def dots_layer(img, levels, gold_idx=None):
    """levels: 점마다 밝기(1 흰빛, 0.25 대기 회색)."""
    im = img.copy().convert("RGBA")
    iw, ih = im.size
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, (x, y) in enumerate(cable_dots()):
        lv = levels[i]
        cx, cy = x * iw, y * ih
        if gold_idx is not None and i == gold_idx:
            col = (255, 205, 110)
        elif lv > 0.6:
            col = (245, 250, 255)
        else:
            col = (120, 150, 185)
        r = 13
        d.ellipse((cx - r * 2.6, cy - r * 2.6, cx + r * 2.6, cy + r * 2.6), fill=col + (int(70 * lv),))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (int(255 * max(0.35, lv)),))
    g = lay.filter(ImageFilter.GaussianBlur(9))
    im.alpha_composite(g)
    im.alpha_composite(lay)
    return im.convert("RGB")


S17_MON = (0.37, 0.27, 0.67, 0.42)
_CACHE = {}


def s17_img(state, wave=3):
    key = ("s17", state, wave)
    if key not in _CACHE:
        base = still("S17")
        n = len(cable_dots())
        if state == "52":
            img = dots_layer(base, [1.0] * n)
            img = monitor_text(img, S17_MON, [("52", 1.0, (235, 245, 255))])
        else:
            lv = [1.0] * n
            for i in range(1, n):
                if i % 3 < wave:
                    lv[i] = 0.45
            img = dots_layer(base, lv, gold_idx=0)
            if state == "two":
                img = monitor_text(img, S17_MON, [("오늘 1", 1.0, GOLD), ("대기 51", 0.9, (170, 176, 186))])
            else:
                img = monitor_text(img, S17_MON, [("52", 1.0, (235, 245, 255))])
        _CACHE[key] = img
    return _CACHE[key]


def gold_wire(img, k, yank=0.0):
    """S21: 손이 쥔 전선 한 가닥만 금빛으로 번진다. k 0~1 번진 정도."""
    iw, ih = img.size
    path = [(0.62, 0.27), (0.56, 0.35), (0.51, 0.43), (0.48, 0.50), (0.44, 0.57), (0.38, 0.63), (0.29, 0.68), (0.18, 0.73)]
    hand = 3
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(x * iw, y * ih - yank * ih * 0.04) for x, y in path]
    for i in range(len(pts) - 1):
        mid = (i + 0.5)
        dist = abs(mid - hand) / (len(pts) - 1)
        if dist > k * 0.75:
            continue
        d.line((pts[i], pts[i + 1]), fill=GOLD + (255,), width=22)
    im = img.copy().convert("RGBA")
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(26)))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))
    return im.convert("RGB")


def giant_power(img, k_eye, k_body):
    """S22b: 거인 눈빛과 몸통 모니터를 끈다. k_body 0~1 위에서 아래로 어두워진 정도."""
    a = arr(img)
    ih, iw = a.shape[:2]
    m = np.zeros((ih, iw), np.float32)
    polys = [[(0.42, 0.26), (0.53, 0.26), (0.53, 0.345), (0.42, 0.345)],
             [(0.35, 0.34), (0.63, 0.34), (0.62, 0.57), (0.37, 0.57)],
             [(0.60, 0.30), (0.72, 0.15), (0.84, 0.10), (0.86, 0.16), (0.72, 0.30), (0.64, 0.40)],
             [(0.30, 0.38), (0.37, 0.38), (0.35, 0.58), (0.28, 0.58)]]
    for p in polys:
        cv2.fillPoly(m, [np.array([(x * iw, y * ih) for x, y in p], np.int32)], 1.0)
    yy = np.linspace(0, 1, ih, dtype=np.float32)[:, None]
    front = 0.08 + 0.55 * k_body
    sweep = np.clip((front - yy) / 0.05, 0, 1)
    bright = np.clip((a.mean(axis=2) - 110) / 80, 0, 1)
    mon = np.zeros((ih, iw), np.float32)
    mon[int(0.365 * ih):int(0.425 * ih), int(0.425 * iw):int(0.52 * iw)] = 1.0
    dark = cv2.GaussianBlur(m, (0, 0), 6) * sweep * bright * (1 - mon) * 0.62
    a = a * (1 - dark[..., None])
    if k_eye > 0:
        e = np.zeros((ih, iw), np.float32)
        cv2.rectangle(e, (int(0.43 * iw), int(0.285 * ih)), (int(0.52 * iw), int(0.33 * ih)), 1.0, -1)
        e = cv2.GaussianBlur(e, (0, 0), 14) * k_eye
        a = a + e[..., None] * np.array([150, 200, 255], np.float32)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return monitor_text(out, (0.425, 0.365, 0.52, 0.425), [("오늘 1", 1.0, GOLD), ("대기 51", 0.9, (170, 176, 186))])


def postit_note(img):
    """S23 손바닥 포스트잇에 손글씨: 오늘 1, 대기 51."""
    if "s23" in _CACHE:
        return _CACHE["s23"]
    im = img.copy().convert("RGBA")
    iw, ih = im.size
    lay = Image.new("RGBA", (int(iw * 0.2), int(ih * 0.11)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lw, lh = lay.size
    f1 = F(FB, int(lh * 0.30))
    f2 = F(FR, int(lh * 0.24))
    d.text((lw * 0.09, lh * 0.10), "오늘 1", font=f1, fill=(40, 52, 110, 235))
    d.text((lw * 0.10, lh * 0.56), "대기 51", font=f2, fill=(70, 74, 92, 210))
    lay = lay.rotate(8, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(lay, (int(iw * 0.505 - lay.width / 2), int(ih * 0.640 - lay.height / 2)))
    _CACHE["s23"] = im.convert("RGB")
    return _CACHE["s23"]


# ---------------------------------------------------------------- 물보라와 젖은 포스트잇
_SPRAY = None


def spray(a, t, px=0.58, py=0.92):
    global _SPRAY
    if t < 0:
        return a
    if _SPRAY is None:
        g = np.random.default_rng(21)
        n = 260
        ang = g.uniform(-math.pi * 0.62, -math.pi * 0.38, n)
        sp = g.uniform(900, 2600, n)
        _SPRAY = dict(vx=np.cos(ang) * sp, vy=np.sin(ang) * sp, r=g.uniform(3, 11, n), life=g.uniform(0.35, 0.9, n))
    p = _SPRAY
    lay = np.zeros((H, W), np.float32)
    cx, cy = px * W, py * H
    for i in range(len(p["vx"])):
        if t > p["life"][i]:
            continue
        x = cx + p["vx"][i] * t
        y = cy + p["vy"][i] * t + 0.5 * 3200 * t * t
        x1 = x - p["vx"][i] * 0.02
        y1 = y - (p["vy"][i] + 3200 * t) * 0.02
        cv2.line(lay, (int(x1), int(y1)), (int(x), int(y)), 1.0 - t / p["life"][i], max(1, int(p["r"][i] * 0.6)), cv2.LINE_AA)
    col = cv2.GaussianBlur(lay, (0, 0), 1.2)
    glow = cv2.GaussianBlur(lay, (0, 0), 8)
    out = a * (1 - np.clip(col, 0, 0.85)[..., None]) + np.clip(col, 0, 0.85)[..., None] * np.array([235, 245, 255], np.float32)
    return out + glow[..., None] * np.array([60, 80, 110], np.float32)


def ov_wet_postit(t_on, slide=0.0, fall=0.0):
    """젖은 포스트잇이 화면(렌즈)에 철썩. 렌즈 가까이라 흐리고 크다."""
    key = ("wet",)
    if key not in _OV:
        tmp = Image.new("RGBA", (760, 760), (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        d.rectangle((40, 40, 720, 720), fill=(250, 218, 92, 238))
        g = np.random.default_rng(3)
        wet = Image.new("RGBA", tmp.size, (0, 0, 0, 0))
        dw = ImageDraw.Draw(wet)
        for _ in range(4):
            x, y, r = g.uniform(160, 600), g.uniform(160, 600), g.uniform(90, 170)
            dw.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=(205, 168, 55, 60))
        tmp.alpha_composite(wet.filter(ImageFilter.GaussianBlur(40)))
        d.polygon([(560, 720), (720, 560), (720, 720)], fill=(230, 196, 70, 200))
        tmp = tmp.rotate(-12, resample=Image.BICUBIC, expand=True).filter(ImageFilter.GaussianBlur(5))
        _OV[key] = tmp
    tmp = _OV[key]
    s = 1.0 + 0.3 * (1 - ease(t_on / 0.06))
    im = tmp if abs(s - 1) < 0.01 else tmp.resize((int(tmp.width * s), int(tmp.height * s)), Image.BICUBIC)
    out = layer()
    out.alpha_composite(im, (int(-170 - (im.width - tmp.width) / 2), int(-120 + slide * 60 + fall * 2300 - (im.height - tmp.height) / 2)))
    return out


# ---------------------------------------------------------------- 엽전
_COIN = {}


def coin_img(r=74, squash=1.0):
    k = (r, round(squash, 2))
    if k not in _COIN:
        im = Image.new("RGBA", (2 * r + 20, 2 * r + 20), (0, 0, 0, 0))
        AN.coin(ImageDraw.Draw(im), r + 10, r + 10, r, True)
        if squash < 0.99:
            im = im.resize((max(6, int(im.width * squash)), im.height), Image.BICUBIC)
        _COIN[k] = im
    return _COIN[k]


def grid_layer(cx, cy, radius, alpha):
    """금빛 바둑판 격자(19줄): 엽전 자리에서 물결처럼 퍼진다."""
    key = ("grid",)
    if key not in _OV:
        im = layer()
        d = ImageDraw.Draw(im)
        vx, vy = 540, 520
        for i in range(19):
            u = i / 18
            yb = vy + (H + 260 - vy) * (u ** 1.8)
            spread = (yb - vy) / (H - vy) * W * 1.6
            d.line((540 - spread / 2, yb, 540 + spread / 2, yb), fill=GOLD + (230,), width=4)
        for i in range(19):
            u = (i - 9) / 9
            d.line((vx, vy, vx + u * W * 1.5, H + 200), fill=GOLD + (230,), width=4)
        for i in range(19):
            u = (i - 9) / 9
            d.line((vx + u * W * 0.9, 0, vx, vy), fill=GOLD + (90,), width=2)
        _OV[key] = glow_layer(im, 9, 0.9)
    g = _OV[key]
    m = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(m)
    dm.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=int(255 * alpha))
    band = Image.new("L", (W, H), 0)
    db = ImageDraw.Draw(band)
    if radius > 30:
        db.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=255, width=60)
    m = m.filter(ImageFilter.GaussianBlur(30))
    out = layer()
    gg = g.copy()
    a = np.asarray(gg.split()[3], np.float32) * np.asarray(m, np.float32) / 255.0
    a = np.clip(a + np.asarray(band.filter(ImageFilter.GaussianBlur(25)), np.float32) * 0.5 * (np.asarray(gg.split()[3], np.float32) / 255.0), 0, 255)
    a = a * np.linspace(0.3, 1.0, H, dtype=np.float32)[:, None]
    gg.putalpha(Image.fromarray(a.astype(np.uint8)))
    out.alpha_composite(gg)
    return out


# ---------------------------------------------------------------- 끝 화면
_END = {}


def endcard(lt):
    if "full" not in _END:
        src = Image.open("/home/claude/ep8/gen/coin.png")
        bg = AN.cover(src).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.42))
        labels = SPEC["shots"][-1]["coins"]
        full = AN.coin_string(bg.copy(), labels)
        d = ImageDraw.Draw(full)

        def c(t, f, y, fill):
            w = d.textlength(t, font=f)
            d.text(((W - w) / 2, y), t, font=f, fill=fill)
        c("9닢째", F(FB, 52), 1110, (255, 200, 60))
        c("무엇부터 할지 망설여질 땐", F(FB, 58), 1210, (255, 255, 255))
        c("괘 하나", F(FB, 58), 1290, (255, 255, 255))
        f2 = F(FB, 42)
        w = d.textlength("hongchaksa.kr", font=f2)
        d.rounded_rectangle((540 - w / 2 - 32, 1410, 540 + w / 2 + 32, 1486), 38, outline=(215, 215, 215), width=2)
        c("hongchaksa.kr", f2, 1418, (245, 245, 245))
        pre = full.copy()
        cx, cy = 690, 890
        pre.paste(bg.crop((cx - 100, cy - 135, cx + 100, cy + 150)), (cx - 100, cy - 135))
        dd = ImageDraw.Draw(pre)
        dd.line((cx - 100, cy, cx - 60, cy), fill=(170, 40, 40), width=6)
        _END.update(full=full, pre=pre, coin=coin_img(74))
    if lt >= 0.5:
        return _END["full"]
    k = ease(lt / 0.45)
    img = _END["pre"].copy()
    c = _END["coin"]
    x = int(1150 + (690 - 1150) * k) - c.width // 2
    y = int(180 + (890 - 180) * k) - c.height // 2
    img.paste(c, (x, y), c)
    return img


# ---------------------------------------------------------------- 샷별 바탕 화면
FROZEN = {"S14": 0.55, "S15": 0.15, "S16": 0.15, "S17": 0.85, "S19": 0.2, "S20": 0.15, "S21": 0.85, "S22a": 0.85}
ACTION = {"S0a", "S1h", "S1", "S0b", "S0c", "S3", "S4a", "S4b", "S4c", "S4d", "S5", "S5h", "S6", "S7a", "S7", "S8", "S11", "S11c", "S10", "S12"}


def base(sid, lt, dur):
    """(RGB float 배열, 후처리 dict)"""
    post = {}
    if sid == "S0a":
        st = 1.41 + 0.5 * lt if lt < 0.1 else 1.46 + 1.2 * (lt - 0.1)
        a = arr(view(clip("S6", True).at(st)))
        a = impact(a, lt - 0.1, 0.47, 0.78, "carpet", seed=7)
        return a, post
    if sid == "S1h":
        img = still("S1h")
        k = ease(lt / 0.12)
        z = 1.06 + 0.04 * lt
        dx, dy = (shake(lt, 9, 55) if 0.43 <= lt < 0.6 else (0, 0))
        a = arr(view(img, z, 0.5, 0.42, dx, dy))
        if lt < 0.12:
            a = hblur(a, 120 * (1 - k))
        on_l = 0.27 <= lt and not (0.31 <= lt < 0.34)
        on_r = 0.35 <= lt
        for on, box in ((on_l, (0.28, 0.27, 0.45, 0.36)), (on_r, (0.47, 0.25, 0.67, 0.35))):
            if on:
                x0, y0 = to_screen(img, box[0], box[1], z, 0.5, 0.42)
                x1, y1 = to_screen(img, box[2], box[3], z, 0.5, 0.42)
                m = np.zeros((H, W), np.float32)
                cv2.rectangle(m, (int(x0 + 12), int(y0 + 12)), (int(x1 - 12), int(y1 - 12)), 1.0, -1)
                g = cv2.GaussianBlur(m, (0, 0), 30)
                scan = (0.82 + 0.18 * (np.arange(H) % 6 < 3)).astype(np.float32)[:, None, None]
                a = a * (1 - m[..., None] * 0.55) + m[..., None] * np.array([190, 222, 255], np.float32) * 0.55 * scan + g[..., None] * np.array([70, 120, 190], np.float32)
        post["chroma"] = 3
        return a, post
    if sid == "S1":
        a = arr(view(clip("S1").at(0.6 + lt)))
        post["chroma"] = 2
        return a, post
    if sid == "S0b":
        return arr(view(clip("S0b").at(0.3 + lt))), post
    if sid == "S0c":
        k = ease(lt / 0.15)
        z = 1.0 + 1.5 * k
        img = clip("S1").at(1.8)
        img = monitor_text(img, (0.35, 0.375, 0.51, 0.43), [("안건 37", 1.0, (235, 245, 255))]) if lt >= 0.08 else img
        a = arr(view(img, z, 0.43, 0.40))
        if 0.08 <= lt < 0.14:
            a = chroma(a, 10)
            a = a + np.random.default_rng(int(lt * 100)).normal(0, 12, a.shape[:2])[..., None].astype(np.float32)
        return a, post
    if sid == "S3":
        z = 1.02 + 0.07 * ease(lt / dur)
        a = arr(view(still("S3"), z, 0.5, 0.5))
        if lt < 0.1:
            a = hblur(a, 90 * (1 - lt / 0.1))
        return a, post
    if sid in ("S4a", "S4b", "S4c", "S4d"):
        k = ease(lt / 0.07)
        z = 1.12 - 0.12 * k
        dx, dy = shake(lt, 16 * max(0, 1 - lt / 0.12), 61) if lt < 0.12 else (0, 0)
        a = arr(view(still(sid), z, 0.5, 0.5, dx, dy))
        if lt < 0.04:
            a = a * 0.8 + 255 * 0.2
        return a, post
    if sid == "S5":
        return arr(view(clip("S5").at(0.3 + lt))), post
    if sid == "S5h":
        img = still("suit")
        k = smooth(lt / dur)
        z = 1.18 + 0.12 * k
        cy = 0.64 - 0.26 * k
        a = arr(view(img, z, 0.5, cy))
        mx, my = to_screen(img, 0.615, 0.215, z, 0.5, cy)
        post["flare"] = (mx, my, 0.55 + 0.45 * (1 if lt >= 0.8 else 0))
        post["mic"] = (mx, my, lt >= 0.8)
        post["dust"] = 0.9
        return a, post
    if sid == "S6":
        a = arr(view(clip("S6").at(0.7 + 0.9 * lt)))
        post["chroma"] = 2
        return a, post
    if sid == "S7a":
        img = clip("S7").at(0.41 + lt)
        a = arr(view(img, 1.55, 0.5, 0.26))
        a = impact(a, lt - 0.05, 0.5, 0.16, "metal", seed=13)
        return a, post
    if sid == "S7":
        dx, dy = shake(lt, 10 * max(0, 1 - lt / 0.2), 47) if lt < 0.2 else (0, 0)
        return arr(view(clip("S7").at(0.5 + lt), 1.0, 0.5, 0.5, dx, dy)), post
    if sid == "S8":
        return arr(view(clip("S5").at(0.95 + lt))), post
    if sid == "S11":
        st = 1.06 + 0.8 * lt if lt < 0.5 else 1.46 + 1.2 * (lt - 0.5)
        a = arr(view(clip("S6", True).at(st)))
        a = impact(a, lt - 0.5, 0.47, 0.78, "carpet", seed=17)
        post["chroma"] = 2
        return a, post
    if sid == "S11c":
        a = arr(view(clip("S6", True).at(1.99 + 0.9 * lt), 1.04, 0.5, 0.55))
        a = spray(a, lt - 0.02)
        return a, post
    if sid == "S10":
        return arr(view(clip("S5").at(1.6 + lt))), post
    if sid == "S12":
        return arr(view(clip("S5").at(2.8 + lt))), post
    if sid == "S13":
        st = 2.35 + 0.32 * (1 - math.exp(-lt / 0.25))
        a = arr(view(clip("S6", True).at(st), 1.04, 0.5, 0.55))
        kz = smooth((lt - 0.82) / 0.12)
        a = grade(grade(a, "action", 1 - kz), "frozen", kz)
        return a, post
    if sid == "S14":
        return arr(view(clip("S14").at(0.6 + lt))), post
    if sid == "S15":
        return arr(view(clip("S15").at(0.2 + lt))), post
    if sid == "S16":
        return arr(view(clip("S15").at(3.3 + lt))), post
    if sid == "S17":
        z = 1.0 + 0.05 * smooth(lt / dur)
        return arr(view(s17_img("52"), z, 0.5, 0.5)), post
    if sid == "S18":
        a = arr(view(clip("S20").at(0.1 + lt)))
        fz = grade(a, "frozen", 0.85)
        s = smooth((lt - 0.3) / 0.6)
        line_y = H * (1.05 - 1.15 * s)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        below = np.clip((yy - line_y) / 80, 0, 1)
        person = np.clip(1 - np.hypot((xx - 560) / (W * 0.42), (yy - 1050) / (H * 0.55)), 0, 1) ** 0.5
        wgt = (below * np.clip(person * 1.6, 0, 1))[..., None]
        a = fz * (1 - wgt) + a * wgt
        if 0.3 <= lt < 0.95:
            band = np.exp(-((yy - line_y) ** 2) / (2 * 18.0 ** 2))[..., None]
            a = a + band * np.array([255, 200, 110], np.float32) * 0.9
        return a, post
    if sid == "S19":
        return arr(view(clip("S19").at(0.2 + lt))), post
    if sid == "S20":
        return arr(view(clip("S20").at(1.9 + lt))), post
    if sid == "S21":
        k = smooth((lt - 0.2) / 0.3)
        yank = ease((lt - 0.55) / 0.12) if lt >= 0.55 else 0.0
        img = gold_wire(still("S21"), k, yank)
        z = 1.04 + 0.03 * lt + 0.08 * yank
        dx, dy = shake(lt, 18 * max(0, 1 - (lt - 0.55) / 0.15), 59) if 0.55 <= lt < 0.7 else (0, 0)
        a = arr(view(img, z, 0.48, 0.5, dx, dy))
        fz = grade(a, "frozen", 0.85)
        gold = np.clip((a[..., 0] - a[..., 2] - 40) / 60, 0, 1)[..., None]
        a = fz * (1 - gold) + a * gold
        post["no_grade"] = True
        return a, post
    if sid == "S22a":
        wave = 0 if lt < 0.05 else 1 if lt < 0.18 else 2 if lt < 0.3 else 3
        state = "two" if lt >= 0.4 else "dim"
        z = 1.05 + 0.06 * smooth(lt / dur)
        img = s17_img(state, wave) if (state == "two" or wave > 0) else s17_img("52")
        return arr(view(img, z, 0.5, 0.5)), post
    if sid == "S22b":
        k_eye = 0.0
        if lt < 0.4:
            k_eye = 1.0 if int(lt * 20) % 3 != 1 else 0.3
            k_eye *= max(0, 1 - lt / 0.4)
        k_body = smooth((lt - 0.4) / 0.4)
        img = giant_power(still("S6"), k_eye, k_body)
        sink = 0.03 * ease((lt - 0.8) / 0.15) if lt >= 0.8 else 0.0
        dx, dy = (shake(lt, 7, 13) if 0.8 <= lt < 1.05 else (0, 0))
        a = arr(view(img, 1.06, 0.5, 0.5 - sink * 0.5, dx, dy))
        kw = smooth((lt - 0.8) / 0.5)
        a = grade(a, "frozen", 0.85 * (1 - kw))
        a = grade(a, "warm", 0.25 * kw)
        if lt >= 0.8:
            fx, fy = to_screen(still("S6"), 0.5, 0.66, 1.06, 0.5, 0.5)
            a = VX.dust(a[..., ::-1].copy(), fx, fy, (lt - 0.8) * 0.9, seed=4)[..., ::-1]
        post["no_grade"] = True
        return np.ascontiguousarray(a), post
    if sid == "S23":
        z = 1.03 + 0.04 * smooth(lt / dur)
        return arr(view(postit_note(still("S23")), z, 0.5, 0.55)), post
    if sid == "S24":
        return arr(view(clip("S24").at(0.1 + lt))), post
    if sid == "S25":
        return arr(view(clip("S25").at(0.2 + lt))), post
    if sid == "S26":
        z = 1.04 + 0.07 * smooth(lt / dur)
        return arr(view(still("S26"), z, 0.5, 0.45)), post
    if sid == "S27":
        return arr(view(clip("EP7").at(1.9 + lt))), post
    if sid == "S28":
        return arr(endcard(lt)), post
    raise KeyError(sid)


# ---------------------------------------------------------------- 겹침
SUBS = {  # 샷: (자막, 시작, 끝)
    "S0b": ("또 월요일이네.", 0.42, 1.55),
    "S19": ("이거, 오늘 다 해야 해요?", 0.05, 2.0),
    "S20": ("아뇨. 하나면 돼요.", 0.65, 2.45),
    "S24": ("하나만 하겠습니다.", 0.55, 2.45),
    "S25": ("좋아.", 0.06, 0.75),
    "S27": ("홍책사 한 수면, 됐지?", 0.0, 2.9),
}


def overlays(sid, lt, dur, a0, post):
    out = []
    Tabs = a0 + lt
    if Tabs < 1.6:
        out.append((ov_caption("월요일 9시,\n회의실이 터졌다"), fade(Tabs, 0.05, 1.6, 0.0, 0.12, first=True)))
    if sid in SUBS:
        s, a, b = SUBS[sid]
        out.append((ov_sub(s), fade(lt, a, min(b, dur), 0.06, 0.1)))
    if sid in ("S8", "S10", "S12"):
        if sid == "S8":
            num, pt = (37, -1) if lt < 0.1 else (38, lt - 0.1)
            out.append((ov_hud(num, pt, blink_t=lt), 1.0))
        elif sid == "S10":
            num, pt = (38, -1) if lt < 0.15 else (39, lt - 0.15)
            out.append((ov_wet_postit(lt - 0.03, slide=lt / 1.6), 1.0 if lt >= 0.03 else 0.0))
            out.append((ov_hud(num, pt, blink_t=lt), 1.0))
        else:
            mail = 13 if lt >= 0.1 else None
            num, pt, big = (39, -1, False) if lt < 0.4 else (52, lt - 0.4, True)
            fall = ease((lt - 0.75) / 0.3) if lt >= 0.75 else 0.0
            out.append((ov_wet_postit(1.0, slide=(0.55 + lt) / 1.6, fall=fall), 1.0))
            out.append((ov_hud(num, pt, big=big, mail=mail, mail_t=lt - 0.1, blink_t=lt), 1.0))
    if sid == "S5h":
        mx, my, lit = post["mic"]
        fx, fy, fa = post["flare"]
        out.append((flare(fx, fy, 1000, 1.0), fa * 0.75))
        if lit:
            out.append((ov_ring(mx, my, 18, 1.0, GOLD, 10), 1.0))
            out.append((flare(mx, my, 420, 1.0, GOLD), 0.8))
        if 1.0 <= lt < 1.12 or 1.2 <= lt < 1.32:
            out.append((ov_battery("배터리 12%"), 1.0))
    if sid == "S13":
        if lt < 0.9:
            k = 1 - math.exp(-max(0, lt - 0.05) / 0.12)
            x = 1180 + (540 - 1180) * k
            y = 900 + 40 * math.sin(lt * 3)
            spin = abs(math.cos(10 * math.pi * k))
        else:
            x, y, spin = 540, 900 + 40 * math.sin(0.9 * 3), 1.0
        c = coin_img(92, max(0.12, spin))
        im = layer()
        if lt >= 0.05:
            if lt < 0.6:
                for j, w in enumerate((0.25, 0.12)):
                    im.alpha_composite(with_alpha(c, w), (int(x + (j + 1) * 60 * (1 - min(1, lt / 0.5)) - c.width / 2), int(y - c.height / 2)))
            im.alpha_composite(c, (int(x - c.width / 2), int(y - c.height / 2)))
            out.append((glow_layer(im, 14, 0.7), 1.0))
        if lt >= 0.82:
            kk = (lt - 0.82) / 0.18
            out.append((flare(540, y, 1400, 1.0), 1 - 0.4 * kk))
            out.append((ov_ring(540, y, 1500 * ease(kk), max(0, 1 - kk), (210, 235, 255), 14), 1.0))
    if sid == "S15":
        out.append((ov_tag("홍책사"), fade(lt, 0.45, 2.3, 0.15, 0.12)))
    if sid == "S16":
        cx, cy = 0.39 * W, 0.92 * H
        if lt >= 0.68:
            k = (lt - 0.68) / 0.62
            out.append((grid_layer(cx, cy, 2600 * ease(k), 0.55 + 0.45 * (1 - k)), 1.0))
            out.append((flare(cx, cy, 900, 1.0, GOLD), max(0, 1 - k * 1.2)))
            if lt < 0.75:
                out.append((ov_flash(0.35 * (1 - (lt - 0.68) / 0.07), (255, 230, 170)), 1.0))
    if sid == "S17":
        out.append((ov_caption("전선 하나가\n안건 하나", y=230), fade(lt, 0.1, dur, 0.1, 0.1)))
    if sid == "S18" and lt < 0.3:
        out.append((grid_layer(540, 1900, 2600, 0.45), 1.0))
    if sid == "S21" and 0.55 <= lt < 0.62:
        out.append((ov_flash(0.85 * (1 - (lt - 0.55) / 0.07), (255, 240, 210)), 1.0))
    if sid == "S25" and lt >= 1.45:
        out.append((ov_sub("근데 그건 뭐야?"), fade(lt, 1.45, dur, 0.06, 0.1)))
    if sid == "S24":
        out.append((ov_caption("현실, 월요일 9시 1분", y=250, size=58), fade(lt, 0.0, 1.5, 0.0, 0.15, first=True)))
    if sid == "S26" and 0.6 <= lt < 0.78:
        a = 1.0 if int((lt - 0.6) * 30) % 3 != 1 else 0.4
        out.append((ov_hud_frame(a), 1.0))
        out.append((ov_battery("배터리 11%", red=False, y=150), a))
    return out


# ---------------------------------------------------------------- 렌더
def composite(a, ovs):
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    for o, al in ovs:
        o2 = with_alpha(o, al)
        if o2 is not None:
            im.alpha_composite(o2)
    return im.convert("RGB")


def frame_at(Tabs):
    sid = next((s for s in ORDER if T[s][0] <= Tabs < T[s][1]), ORDER[-1])
    a0, a1 = T[sid]
    lt, dur = Tabs - a0, a1 - a0
    a, post = base(sid, lt, dur)
    if post.get("chroma"):
        a = chroma(a, post["chroma"])
    if not post.get("no_grade"):
        if sid in ACTION:
            a = grade(a, "action", 0.8)
        elif sid in FROZEN:
            a = grade(a, "frozen", FROZEN[sid])
        elif sid in ("S24", "S25", "S26"):
            a = grade(a, "neutral", 1.0)
        elif sid == "S27":
            a = grade(a, "warm", 0.35)
    if sid not in ("S28",):
        a = vign(a, 0.18)
    ovs = []
    if sid in ("S13",) and lt >= 0.9 or sid in ("S14", "S15", "S16", "S17", "S19", "S21", "S22a"):
        ovs.append((particles(Tabs, warm=sid in ("S15", "S16", "S19")), 0.85))
    if post.get("dust"):
        ovs.append((particles(Tabs, warm=True), post["dust"]))
    ovs += overlays(sid, lt, dur, a0, post)
    ovs.append((ov_ai(), 1.0))
    return composite(a, ovs), sid


def render(out, t_from=0.0, t_to=None):
    t_to = TOTAL if t_to is None else t_to
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-vf", "unsharp=5:5:0.3", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out],
                         stdin=subprocess.PIPE)
    last = None
    for fi in range(n0, n1):
        Tabs = (fi + 0.5) / FPS
        fr, sid = frame_at(Tabs)
        if sid != last:
            keep = {k for k in _CL if k[0] in {"S0a": ("S6",), "S11": ("S6",), "S11c": ("S6",), "S13": ("S6",)}.get(sid, ())}
            last = sid
            if len(_CL) > 3:
                for k in list(_CL):
                    if k not in keep and len(_CL) > 3:
                        del _CL[k]
        p.stdin.write(np.asarray(fr, np.uint8).tobytes())
        if fi % 60 == 0:
            print(f"{Tabs:5.1f}s {sid}", flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    if "--still" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--still") + 1].split(",")]:
            fr, sid = frame_at(t)
            fr.save(f"/tmp/f9_{t:.2f}.jpg", quality=85)
            print(t, sid)
        sys.exit(0)
    out = sys.argv[1]
    tf = float(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0.0
    tt = float(sys.argv[sys.argv.index("--to") + 1]) if "--to" in sys.argv else None
    render(out, tf, tt)
