"""충격 레이어와 HUD를 영상에 입히는 편집 도구(크레딧 0).

사용 예:
  python3 vfx_impact.py 입력.mp4 출력.mp4 --impact 1.2 --point 0.5,0.82 [--hud 38] [--start 0 --dur 3]

충격 한 번에 일곱 층을 겹친다(9화 설계서 vfx_rules.impact):
 1) 접촉 직전 0.5배 슬로, 접촉 뒤 1.2배 속도 램프
 2) 위에서 내려오는 거대한 그림자(접촉 0.5초 전부터)
 3) 따뜻한 백색 블룸 화이트아웃 3프레임, 0.3초에 걸쳐 걷힘
 4) 접촉점에서 퍼지는 원형 왜곡 충격파 0.25초
 5) 파편 두 겹(앞쪽 크고 흐린 포스트잇과 키캡, 뒤쪽 작은 종이)과 금빛 불꽃
 6) 바닥 먼지 기둥(1초 동안 퍼지며 옅어짐)
 7) 흔들림 3프레임 뒤 감쇠, 색수차 0.12초, 세로 방향 모션 블러
"""
import argparse
import math
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
GOLD = (255, 205, 110)


def load(path, W, H):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    fr = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        fr.append(cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4))
    return fr, fps


def src_time(n_out, fps_out, ti, start):
    """출력 프레임 번호마다 원본 시각. 접촉 0.35초 전부터 0.5배, 접촉 뒤 0.4초 1.2배."""
    ts, out = start, []
    for k in range(n_out):
        t = k / fps_out  # 출력 시각(상대)
        rel = start + t
        if ti - 0.35 <= ts < ti:
            rate = 0.5
        elif ti <= ts < ti + 0.4:
            rate = 1.2
        else:
            rate = 1.0
        out.append(ts)
        ts += rate / fps_out
    return out


class Particles:
    def __init__(self, x, y, W, H, seed=7, material="carpet"):
        rnd = random.Random(seed)
        self.items = []
        kinds = {"carpet": (["postit", "paper", "fiber"], [0.35, 0.35, 0.3]), "metal": (["postit", "key", "paper"], [0.45, 0.3, 0.25]),
                 "water": (["drop", "postit", "paper"], [0.6, 0.25, 0.15])}[material]
        for i in range(46):
            kind = rnd.choices(*kinds)[0]
            fg = rnd.random() < 0.35
            size = {"postit": rnd.uniform(26, 48), "key": rnd.uniform(16, 26), "paper": rnd.uniform(8, 18), "fiber": rnd.uniform(10, 22),
                    "drop": rnd.uniform(6, 16)}[kind] * (1.9 if fg else 1.0)
            ang = rnd.uniform(-math.pi * 0.95, -math.pi * 0.05)
            sp = rnd.uniform(500, 1500) * (1.25 if fg else 1.0)
            self.items.append(dict(kind=kind, fg=fg, s=size, x=x, y=y, vx=math.cos(ang) * sp, vy=math.sin(ang) * sp,
                                   rot=rnd.uniform(0, 360), vr=rnd.uniform(-720, 720), life=rnd.uniform(0.9, 1.6)))
        self.sparks = []
        n_sp = {"carpet": 0, "metal": 120, "water": 18}[material]
        for i in range(n_sp):
            ang = rnd.uniform(-math.pi, 0)
            sp = rnd.uniform(600, 2400)
            self.sparks.append(dict(x=x, y=y, vx=math.cos(ang) * sp, vy=math.sin(ang) * sp, life=rnd.uniform(0.18, 0.5)))
        self.W, self.H = W, H

    def draw(self, img, t, layer):
        if t < 0:
            return img
        g = 2200.0
        over = np.zeros_like(img)
        alpha = np.zeros(img.shape[:2], np.float32)
        for p in self.items:
            if p["fg"] != (layer == "fg") or t > p["life"]:
                continue
            drag = math.exp(-1.2 * t)
            x = p["x"] + p["vx"] * (1 - drag) / 1.2
            y = p["y"] + p["vy"] * (1 - drag) / 1.2 + 0.5 * g * t * t * 0.55
            a = max(0.0, 1 - t / p["life"]) ** 0.6
            base = {"postit": (90, 214, 247), "key": (48, 46, 44), "paper": (235, 236, 238), "fiber": (70, 78, 88), "drop": (250, 235, 215)}[p["kind"]]
            shade = 0.82 + 0.18 * math.sin(math.radians(p["rot"] + p["vr"] * t))
            col = tuple(int(c * shade) for c in base)
            w = p["s"]
            h = w * {"paper": 0.7, "fiber": 0.12, "drop": 1.0}.get(p["kind"], 0.95)
            for k in range(4):  # 속도 방향 잔상(모션 블러)
                tt = max(0.0, t - k * 0.012)
                d2 = math.exp(-1.2 * tt)
                xk = p["x"] + p["vx"] * (1 - d2) / 1.2
                yk = p["y"] + p["vy"] * (1 - d2) / 1.2 + 0.5 * g * tt * tt * 0.55
                ak = a * (1.0, 0.45, 0.25, 0.12)[k]
                box = cv2.boxPoints(((xk, yk), (w, h * (0.35 + 0.65 * abs(shade - 0.82) / 0.18 + 0.2)), p["rot"] + p["vr"] * tt)).astype(np.int32)
                cv2.fillPoly(over, [box], col, lineType=cv2.LINE_AA)
                cv2.fillPoly(alpha, [box], ak, lineType=cv2.LINE_AA)
            if p["kind"] == "key":
                cv2.polylines(over, [box], True, (120, 118, 114), 2, cv2.LINE_AA)
        if layer == "fg":
            over = cv2.GaussianBlur(over, (0, 0), 6)
            alpha = cv2.GaussianBlur(alpha, (0, 0), 6) * 0.9
        a3 = alpha[..., None]
        img = (img * (1 - a3) + over * a3).astype(np.float32)
        if layer == "bg":
            sp = np.zeros_like(img)
            for s in self.sparks:
                if t > s["life"]:
                    continue
                x0 = s["x"] + s["vx"] * t
                y0 = s["y"] + s["vy"] * t + 0.5 * g * t * t
                x1 = x0 - s["vx"] * 0.018
                y1 = y0 - s["vy"] * 0.018
                k = 1 - t / s["life"]
                cv2.line(sp, (int(x1), int(y1)), (int(x0), int(y0)), (140 * k, 225 * k, 255 * k), 3, cv2.LINE_AA)
            glow = cv2.GaussianBlur(sp, (0, 0), 4)
            img = img + sp + glow * 1.5
        return img


def shockwave(img, cx, cy, t, dur=0.25, amp=22):
    if not (0 <= t < dur):
        return img
    H, W = img.shape[:2]
    r = (t / dur) * max(W, H) * 0.9
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    d = np.sqrt(dx * dx + dy * dy) + 1e-3
    band = np.exp(-((d - r) ** 2) / (2 * 35.0 ** 2)) * amp * (1 - t / dur)
    mx = xx - dx / d * band
    my = yy - dy / d * band
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def dust(img, cx, cy, t, seed=3):
    if not (0 <= t < 1.6):
        return img
    rnd = random.Random(seed)
    H, W = img.shape[:2]
    layer = np.zeros((H, W), np.float32)
    for i in range(18):
        ang = rnd.uniform(-math.pi, 0)
        dist = (160 + 420 * rnd.random()) * (1 - math.exp(-3 * t))
        x = cx + math.cos(ang) * dist * 1.6
        y = cy + math.sin(ang) * dist * 0.6 - 90 * t
        rad = 70 + 260 * (1 - math.exp(-2.5 * t)) * rnd.uniform(0.6, 1.2)
        cv2.circle(layer, (int(x), int(y)), int(rad), 1.0, -1)
    layer = cv2.GaussianBlur(layer, (0, 0), 38)
    nrng = np.random.default_rng(seed)
    tex = cv2.GaussianBlur(nrng.random((H // 8, W // 8)).astype(np.float32), (0, 0), 1.5)
    tex = cv2.resize(tex, (W, H), interpolation=cv2.INTER_CUBIC)
    layer = layer * (0.55 + 0.6 * tex) * 0.8 * max(0.0, 1 - t / 1.6) ** 1.1
    col = np.array([175, 190, 205], np.float32)  # 따뜻한 회색(BGR)
    a = np.clip(layer, 0, 0.85)[..., None]
    return img * (1 - a) + col * a


def shadow(img, t_rel):
    """접촉 0.5초 전부터 위에서 내려오는 거대한 주먹 그림자(타원 덩어리와 전체 어두워짐)."""
    if not (-0.5 <= t_rel < 0.05):
        return img
    H, W = img.shape[:2]
    k = (t_rel + 0.5) / 0.5
    m = np.zeros((H, W), np.float32)
    cy = int(-H * 0.25 + H * 0.95 * k)
    cv2.ellipse(m, (int(W * 0.52), cy), (int(W * 0.55), int(H * 0.22)), 0, 0, 360, 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), 60) * 0.7 * k + 0.25 * k
    return img * (1 - np.clip(m, 0, 0.85)[..., None])


def flash(img, t):
    if t < 0 or t > 0.4:
        return img
    if t < 3 / 30:
        a = 0.92
    else:
        a = 0.92 * math.exp(-(t - 0.1) / 0.09)
    bright = cv2.GaussianBlur(np.clip(img - 170, 0, 255), (0, 0), 25) * 1.6
    warm = np.array([225, 240, 255], np.float32)
    out = img + bright * min(1.0, a * 1.5)
    return out * (1 - a) + warm * a


def flicker(img, t):
    """충격 순간 형광등이 파르르 깜빡임: 화면 위쪽 35%의 밝기를 0.3초 동안 들쭉날쭉."""
    if not (0.05 <= t < 0.35):
        return img
    H = img.shape[0]
    k = [0.55, 1.25, 0.7, 1.15, 0.85, 1.05][int((t - 0.05) / 0.05) % 6]
    m = np.ones((H, 1, 1), np.float32)
    top = int(H * 0.35)
    m[:top, 0, 0] = np.linspace(k, 1.0, top) if k != 1 else 1.0
    return img * m


def shake_offset(t, seed=11):
    if t < 0 or t > 0.4:
        return 0, 0
    rnd = random.Random(int(t * 300) + seed)
    if t < 3 / 30:
        amp = 22
    else:
        amp = 22 * math.exp(-(t - 0.1) / 0.1)
    return rnd.uniform(-amp, amp), rnd.uniform(-amp, amp) * 0.7


def chroma(img, t):
    if t < 0 or t > 0.12:
        return img
    s = int(8 * (1 - t / 0.12)) + 1
    b, g, r = cv2.split(img)
    r = np.roll(r, s, axis=1)
    b = np.roll(b, -s, axis=1)
    return cv2.merge([b, g, r])


def vblur(img, t):
    if t < -0.08 or t > 0.15:
        return img
    k = 21 if abs(t) < 0.05 else 11
    ker = np.zeros((k, k), np.float32)
    ker[:, k // 2] = 1.0 / k
    return cv2.filter2D(img, -1, ker)


def hud(img, num, t, scale=1.0):
    """금빛 얇은 선 HUD(디테일 판): 남은 안건 큰 숫자, 배터리, 시계, 메일, 조준 모서리, 얼굴 반사광."""
    H, W = img.shape[:2]
    pil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(pil)
    g = GOLD + (235,)
    gs = GOLD + (85,)  # 보조 요소는 옅게, 큰 숫자만 또렷하게
    m = int(36 * scale)
    # 바깥 테두리 모서리
    L = int(70 * scale)
    for (x, y, sx, sy) in ((m, m * 3, 1, 1), (W - m, m * 3, -1, 1), (m, H - m * 3, 1, -1), (W - m, H - m * 3, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=g, width=3)
        d.line([(x, y), (x, y + sy * L)], fill=g, width=3)
    # 오른쪽 위 안건 카운터
    pop = 1.0 + 0.35 * math.exp(-t / 0.08) if t >= 0 else 1.0
    fb = ImageFont.truetype(FONT_B, int(H / 5 * 0.62 * pop))
    fs = ImageFont.truetype(FONT_R, int(30 * scale))
    x0, y0 = int(W * 0.50), int(H * 0.12)
    d.rectangle([x0, y0, W - m - 10, y0 + int(H * 0.2)], outline=gs, width=2)
    d.text((x0 + 18, y0 + 10), "남은 안건", font=fs, fill=g)
    d.text((x0 + 18, y0 + int(40 * scale)), str(num), font=fb, fill=g)
    # 배터리(빨갛게 깜빡)
    blink = int(t * 8) % 2 == 0
    col = (255, 80, 70, 240) if blink else (255, 80, 70, 90)
    bx, by = m + 10, int(H * 0.13)
    d.rectangle([bx, by, bx + int(120 * scale), by + int(44 * scale)], outline=col, width=3)
    d.rectangle([bx + 6, by + 6, bx + 6 + int(14 * scale), by + int(44 * scale) - 6], fill=col)
    d.text((bx, by + int(52 * scale)), "배터리 12%", font=fs, fill=col)
    # 시계와 메일
    d.text((m + 10, int(H * 0.86)), "09:00", font=ImageFont.truetype(FONT_R, int(34 * scale)), fill=gs)
    mx, my = W - m - int(90 * scale), int(H * 0.86)
    d.rectangle([mx, my, mx + int(70 * scale), my + int(46 * scale)], outline=gs, width=2)
    d.line([(mx, my), (mx + int(35 * scale), my + int(26 * scale)), (mx + int(70 * scale), my)], fill=gs, width=2)
    # 가운데 조준 괄호와 가는 원호
    cx, cy = W // 2, int(H * 0.45)
    r = int(150 * scale)
    for a0 in (200, 290, 20, 110):
        d.arc([cx - r, cy - r, cx + r, cy + r], a0, a0 + 50, fill=gs, width=2)
    d.text((cx - int(60 * scale), cy + r + 8), "주간 보고", font=fs, fill=gs)
    # 아주 옅은 주사선
    for yy in range(0, H, 6):
        d.line([(0, yy), (W, yy)], fill=(255, 205, 110, 10), width=1)
    lay = np.array(pil).astype(np.float32)
    rgb = lay[..., :3][..., ::-1]
    a = lay[..., 3:4] / 255.0
    glow = cv2.GaussianBlur(rgb * a, (0, 0), 6)
    out = img * (1 - a) + rgb * a + glow * 0.6
    # 얼굴에 HUD 반사광(따뜻한 금빛 한 겹)
    out = out * 0.96 + np.array([60, 140, 200], np.float32) * 0.04
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--impact", type=float, required=True, help="원본 기준 접촉 시각(초)")
    ap.add_argument("--point", default="0.5,0.82", help="접촉점(화면 비율 x,y)")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=3.0)
    ap.add_argument("--hud", type=int, default=0, help="HUD 숫자(0이면 HUD 없음)")
    ap.add_argument("--material", default="carpet", choices=["carpet", "metal", "water"],
                    help="부딪힌 재질: carpet 먼지와 섬유와 종이(불꽃 없음), metal 금빛 불꽃과 블룸, water 물방울과 작은 불꽃")
    ap.add_argument("--W", type=int, default=720)
    ap.add_argument("--H", type=int, default=1280)
    a = ap.parse_args()
    W, H = a.W, a.H
    fr, fps = load(a.src, W, H)
    px, py = [float(v) for v in a.point.split(",")]
    cx, cy = px * W, py * H
    parts = Particles(cx, cy, W, H, material=a.material)
    n = int(a.dur * 30)
    times = src_time(n, 30, a.impact, a.start)
    vw = cv2.VideoWriter(a.dst, cv2.VideoWriter_fourcc(*"mp4v"), 30, (W, H))
    for k, ts in enumerate(times):
        i = min(len(fr) - 1, int(round(ts * fps)))
        img = fr[i].astype(np.float32)
        t = ts - a.impact
        img = shadow(img, t)
        img = vblur(img, t)
        img = parts.draw(img, t, "bg")
        img = dust(img, cx, cy, t)
        img = shockwave(img, cx, cy, t)
        img = parts.draw(img, t, "fg")
        img = flash(img, t)
        img = flicker(img, t)
        img = chroma(np.clip(img, 0, 255), t)
        if a.hud:
            img = hud(img, a.hud if t < 0.5 else a.hud + 1, t - 0.5)
        ox, oy = shake_offset(t)
        M = np.float32([[1.06, 0, ox - W * 0.03], [0, 1.06, oy - H * 0.03]]) if (ox or oy) else None
        out = np.clip(img, 0, 255).astype(np.uint8)
        if M is not None:
            out = cv2.warpAffine(out, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        vw.write(out)
    vw.release()
    print("ok", a.dst, n, "frames")


if __name__ == "__main__":
    main()
