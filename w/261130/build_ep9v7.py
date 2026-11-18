"""홍책사 9화 v7(액션 재구성) 편집. build_ep9.py의 도구를 그대로 쓰고 시간표와 샷 구성만 새로 짠다.
사용: python3 build_ep9v7.py 출력.mp4 [--from 초 --to 초]  또는  --still 초,초
"""
import json
import math
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import build_ep9 as B

W, H, FPS = B.W, B.H, B.FPS
SPEC = json.load(open(f"{B.D}/ep09_spec_v7.json", encoding="utf-8"))
TOTAL = SPEC["target_sec"]
T = {s["id"]: tuple(s["t"]) for s in SPEC["shots"]}
ORDER = [s["id"] for s in SPEC["shots"]]
GOLD = B.GOLD
arr, view, ease, smooth, fade = B.arr, B.view, B.ease, B.smooth, B.fade


def fr(name, st, speed=1.0, mirror=False):
    """클립 프레임. 빨리 돌리는 구간은 두 프레임을 겹쳐 움직임 잔상을 준다."""
    c = B.clip(name, mirror)
    if speed >= 1.6:
        a = np.asarray(c.at(st), np.float32)
        b = np.asarray(c.at(st + 0.5 * speed / FPS), np.float32)
        return Image.fromarray(((a + b) / 2).astype(np.uint8))
    return c.at(st)


def warm_keep(a, k):
    """시간 정지 색: 금빛과 살색처럼 따뜻한 곳만 원래 색을 남기고 나머지는 청회색."""
    fz = B.grade(a, "frozen", k)
    m = np.clip((a[..., 0] - a[..., 2] - 26) / 46, 0, 1)[..., None]
    return fz * (1 - m) + a * m


# ---------------------------------------------------------------- 겹치는 그림
def ov_count(num, pop_t, y=150):
    """오른쪽 위 작은 카운터: 남은 안건 N."""
    im = B.layer()
    d = ImageDraw.Draw(im)
    pop = 1.0 + 0.4 * math.exp(-pop_t / 0.07) if pop_t >= 0 else 1.0
    fb = B.F(B.FB, int(128 * pop))
    fs = B.F(B.FR, 30)
    x1 = W - 46
    x0 = x1 - 330
    d.rounded_rectangle((x0, y, x1, y + 210), 14, fill=(8, 10, 14, 150), outline=GOLD + (200,), width=3)
    d.text((x0 + 20, y + 12), "남은 안건", font=fs, fill=GOLD + (235,))
    s = str(num)
    tw = d.textlength(s, font=fb)
    jx = int(10 * math.sin(pop_t * 90)) if 0 <= pop_t < 0.12 else 0
    d.text((x0 + 165 - tw / 2 + jx, y + 40 - (int(128 * pop) - 128) * 0.5), s, font=fb, fill=GOLD + (255,))
    return B.glow_layer(im, 6, 0.8)


def ov_hud_label(s):
    def mk():
        im = B.layer()
        d = ImageDraw.Draw(im)
        f = B.F(B.FB, 46)
        w = d.textlength(s, font=f)
        x = (W - w) / 2
        d.line((x - 60, 1490, x - 16, 1490), fill=GOLD + (220,), width=3)
        d.line((x + w + 16, 1490, x + w + 60, 1490), fill=GOLD + (220,), width=3)
        d.text((x, 1458), s, font=f, fill=GOLD + (245,))
        return B.glow_layer(im, 6, 0.8)
    return B.cached(("hudlabel", s), mk)


def ov_scan(y, alpha=0.8):
    im = B.layer()
    d = ImageDraw.Draw(im)
    d.rectangle((0, y - 3, W, y + 3), fill=GOLD + (int(255 * alpha),))
    d.rectangle((0, y - 40, W, y + 40), fill=GOLD + (int(40 * alpha),))
    return im


def ov_red(alpha):
    key = "redvig"
    if key not in B._OV:
        yy, xx = np.mgrid[0:H, 0:W]
        m = np.clip((np.hypot(xx - W / 2, (yy - H / 2) * 0.6) - 380) / 420, 0, 1)
        im = np.zeros((H, W, 4), np.uint8)
        im[..., 0] = 255
        im[..., 1] = 40
        im[..., 2] = 30
        im[..., 3] = (m * 200).astype(np.uint8)
        B._OV[key] = Image.fromarray(im, "RGBA")
    return B.with_alpha(B._OV[key], alpha)


# ---------------------------------------------------------------- 바둑돌 52개(S17)
_S17 = {}
LAND = (0.52, 0.345)


def s17_stage(step):
    """step 0: 돌 없음. 1~8: 엽전이 닿은 곳에서 가까운 돌부터 켜진다."""
    if step not in _S17:
        base = B.still("S17")
        dots = B.cable_dots()
        iw, ih = base.size
        order = sorted(range(len(dots)), key=lambda i: (dots[i][0] - LAND[0]) ** 2 + ((dots[i][1] - LAND[1]) * ih / iw) ** 2)
        n = int(len(dots) * step / 8)
        im = base.copy().convert("RGBA")
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for rank, i in enumerate(order[:n]):
            cx, cy = dots[i][0] * iw, dots[i][1] * ih
            new = rank >= int(len(dots) * (step - 1) / 8)
            r = 16 if new else 13
            d.ellipse((cx - r * 2.6, cy - r * 2.6, cx + r * 2.6, cy + r * 2.6), fill=(245, 250, 255, 90 if new else 70))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(245, 250, 255, 255))
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(9)))
        im.alpha_composite(lay)
        _S17[step] = B.monitor_text(im.convert("RGB"), B.S17_MON, [("52", 1.0, (235, 245, 255))])
    return _S17[step]


# ---------------------------------------------------------------- 샷별 바탕
F5_HITS = (0.05, 0.25, 0.45, 0.65, 0.85)
REUSE = {"S0b", "S0c", "S19", "S22a", "S23", "S24", "S25", "S26", "S27", "S28"}
ACTION = {"C0", "F1", "S0b", "S0c", "U1", "U2a", "U4", "U3", "U2b", "S5a", "U6", "S6", "F2", "F2r", "F3", "S5b", "F5", "F6", "S5c",
          "F4a", "F4b", "F4c", "F7"}


def base(sid, lt, dur):
    post = {}
    if sid in REUSE:
        a, p = B.base(sid, lt, dur)
        post.update(p)
        return a, post
    if sid == "C0":
        a = arr(view(fr("F2", 1.50 + lt), 1.25, 0.42, 0.40))
        return B.impact(a, lt - 0.08, 0.425, 0.45, "metal", seed=13, flash_k=0.42), post
    if sid == "F1":
        dx, dy = B.shake(lt, 16, 43) if 0.1 <= lt < 0.85 else (0, 0)
        a = arr(view(fr("F1", 0.95 + lt), 1.06 + 0.05 * lt, 0.5, 0.42, dx, dy))
        post["chroma"] = 4 if 0.1 <= lt < 0.85 else 2
        return a, post
    if sid == "U1":
        a = arr(view(fr("U1", 0.10 + lt * 2.0, 2.0), 1.0 + 0.08 * ease(lt / 0.3), 0.5, 0.5))
        if lt < 0.07:
            a = a * 0.75 + 255 * 0.25
        return a, post
    if sid == "U2a":
        st = lt * 2.0
        kick = 14 * max(0, 1 - abs(st - 1.75) / 0.2) if st >= 1.6 else 0
        dx, dy = B.shake(lt, kick, 53)
        return arr(view(fr("U2", st, 2.0), 1.02 + 0.05 * smooth(lt / dur), 0.5, 0.5, dx, dy)), post
    if sid == "U4":  # 가슴 장갑 두 쪽이 맞물려 잠기고 화면이 켜진다
        if lt < 0.2:
            st, sp = 0.05 + lt * 1.6, 1.6
            z, cy = 1.16 - 0.06 * ease(lt / 0.2), 0.40
            dx, dy = B.shake(lt, 16 * max(0, 1 - abs(lt - 0.12) / 0.08), 61)
        else:
            u = lt - 0.2
            st, sp = 1.05 + u * 2.64, 2.64
            z, cy = 1.04 + 0.06 * smooth(u / 0.55), 0.50
            dx, dy = B.shake(lt, 10 * max(0, 1 - abs(u - 0.17) / 0.1), 67)
        return arr(view(fr("U4b", st, sp), z, 0.5, cy, dx, dy)), post
    if sid == "U3":
        k = ease(lt / 0.08)
        dx, dy = B.shake(lt, 12 * max(0, 1 - lt / 0.15), 61)
        return arr(view(fr("U3", lt * 2.0, 2.0), 1.2 - 0.1 * k, 0.5, 0.5, dx, dy)), post
    if sid == "U2b":
        st = min(5.95, 2.4 + lt * 3.0)
        return arr(view(fr("U2", st, 3.0), 1.07 + 0.09 * smooth(lt / dur), 0.5, 0.47)), post
    if sid == "S5a":
        return arr(view(B.clip("S5").at(0.3 + lt))), post
    if sid == "U6":
        a = arr(view(fr("U6", lt * 1.81, 1.81), 1.0 + 0.1 * smooth((lt - 0.4) / 1.2), 0.5, 0.46))
        return B.impact(a, lt - 0.05, 0.5, 0.74, "carpet", seed=23, strong=False), post
    if sid == "S6":
        post["chroma"] = 2
        return arr(view(fr("S6", 0.8 + lt))), post
    if sid == "F2":
        a = arr(view(fr("F2", 1.2 + lt * 1.5), 1.0 + 0.06 * smooth(lt / dur), 0.45, 0.45))
        return B.impact(a, lt - 0.17, 0.37, 0.39, "metal", seed=31, strong=False), post
    if sid == "F2r":
        return arr(view(fr("F2", 2.9 + lt), 1.1 + 0.1 * smooth(lt / dur), 0.5, 0.42)), post
    if sid == "F3":
        a = arr(view(fr("F3", lt * 1.2)))
        post["chroma"] = 2
        return B.impact(a, lt - 0.1, 0.47, 0.2, "metal", seed=37, strong=False), post
    if sid == "S5b":
        return arr(view(B.clip("S5").at(0.95 + lt))), post
    if sid == "S5c":
        return arr(view(B.clip("S5").at(2.8 + lt))), post
    if sid == "F5":
        amp = max([12 * max(0, 1 - abs(lt - h) / 0.08) for h in F5_HITS])
        dx, dy = B.shake(lt, amp, 67)
        return arr(view(fr("F5", 0.3 + lt * 2.0, 2.0), 1.04, 0.5, 0.5, dx, dy)), post
    if sid == "F6":
        dx, dy = B.shake(lt, 6, 11)
        post["chroma"] = 2
        return arr(view(fr("F6", 0.3 + lt * 2.3, 2.3), 1.03, 0.5, 0.5, dx, dy)), post
    if sid == "F4a":
        a = arr(view(fr("F4", lt * 1.25)))
        return B.impact(a, lt - 0.05, 0.3, 0.72, "carpet", seed=41, strong=False), post
    if sid == "F4b":
        a = arr(view(fr("F4", 1.33 + lt * 1.37)))
        return B.impact(a, lt - 0.5, 0.45, 0.62, "carpet", seed=43, strong=False), post
    if sid == "F4c":
        return arr(view(fr("F4", 3.1 + lt), 1.25 + 0.08 * smooth(lt / dur), 0.52, 0.62)), post
    if sid == "F7":
        dx, dy = B.shake(lt, 8, 9)
        a = arr(view(fr("F7", 2.55 + lt * 1.17), 1.0, 0.5, 0.5, dx, dy))
        post["chroma"] = 3
        return a, post
    if sid == "H1":
        a = arr(view(fr("H1", lt)))
        if lt < 0.12:
            a = a * (1 - (0.12 - lt) / 0.12 * 0.6) + np.array([255, 235, 190], np.float32) * (0.12 - lt) / 0.12 * 0.6
        k = smooth((lt - 1.35) / 0.3)
        if k > 0:
            a = warm_keep(a, 0.8 * k)
        post["no_grade"] = True
        return a, post
    if sid == "H2":
        post["no_grade"] = True
        return warm_keep(arr(view(fr("H2", 0.2 + lt), 1.0 + 0.04 * smooth(lt / dur), 0.5, 0.5)), 0.8), post
    if sid == "S17":
        land = 0.42
        step = 0 if lt < land else min(8, int((lt - land) / 0.45 * 8) + 1)
        return arr(view(s17_stage(step), 1.0 + 0.05 * smooth(lt / dur), 0.5, 0.5)), post
    if sid == "S20n":
        post["no_grade"] = True
        return arr(view(fr("S20n", 1.0 + lt))), post
    if sid == "K1":
        st = lt * 1.25 if lt < 1.2 else 1.5 + (lt - 1.2) * 1.58
        a = arr(view(fr("K1", st)))
        a = B.impact(a, lt - 1.52, 0.5, 0.42, "metal", seed=47, flash_k=0.5)
        post["no_grade"] = True
        return a, post
    if sid == "K2":
        dx, dy = B.shake(lt, 14 * max(0, 1 - abs(lt - 0.35) / 0.3), 41)
        post["no_grade"] = True
        return arr(view(fr("K2", lt * 1.5, 1.5), 1.02, 0.5, 0.5, dx, dy)), post
    raise KeyError(sid)


# ---------------------------------------------------------------- 겹침
SUBS = {
    "S0b": ("또 월요일이네.", 0.42, 1.55),
    "S19": ("이거, 오늘 다 해야 해요?", 0.05, 2.0),
    "S20n": ("아뇨. 하나면 돼요.", 0.58, 2.55),
    "S24": ("하나만 하겠습니다.", 0.55, 2.45),
    "S25": ("좋아.", 0.06, 0.75),
    "S27": ("홍책사 한 수면, 됐지?", 0.0, 2.9),
}


def overlays(sid, lt, dur, a0, post):
    out = []
    Tabs = a0 + lt
    if Tabs < 1.5:
        out.append((B.ov_caption("월요일 9시,\n회의실이 터졌다"), fade(Tabs, 0.05, 1.5, 0.0, 0.12, first=True)))
    if sid in SUBS:
        s, a, b = SUBS[sid]
        out.append((B.ov_sub(s), fade(lt, a, min(b, dur), 0.06, 0.1)))
    if sid == "S25" and lt >= 1.45:
        out.append((B.ov_sub("근데 그건 뭐야?"), fade(lt, 1.45, dur, 0.06, 0.1)))
    if sid == "U4" and 0.36 <= lt < 0.46:
        out.append((B.ov_flash(0.35 * (1 - (lt - 0.36) / 0.1), (215, 235, 255)), 1.0))
    if sid == "S0b":
        out.append((B.ov_caption("1분 전", y=250, size=58), fade(lt, 0.0, 1.3, 0.0, 0.15, first=True)))
    if sid == "S5a" and lt >= 0.22:
        k = (lt - 0.22) / 0.25
        flick = 1.0 if (k >= 1 or int(lt * 40) % 3 != 1) else 0.3
        out.append((B.ov_hud(37, -1, blink_t=lt), min(1.0, k * 1.5) * flick))
        if k < 1:
            out.append((ov_scan(130 + (H - 260) * k), 1.0))
        out.append((ov_hud_label("월요일 슈트 가동"), fade(lt, 0.34, dur, 0.06, 0.06)))
    if sid == "U6" and (1.18 <= lt < 1.3 or 1.38 <= lt < 1.5):
        out.append((B.ov_battery("배터리 12%"), 1.0))
    if sid == "U6" and 0.05 <= lt < 0.17:
        out.append((B.ov_flash(0.5 * (1 - (lt - 0.05) / 0.12), (255, 240, 215)), 1.0))
    if sid == "F3" and 0.1 <= lt < 0.2:
        out.append((B.ov_flash(0.55 * (1 - (lt - 0.1) / 0.1), (255, 240, 215)), 1.0))
    if sid == "S5b":
        num, pt = (37, -1) if lt < 0.1 else (38, lt - 0.1)
        out.append((B.ov_hud(num, pt, blink_t=lt), 1.0))
    if sid == "F5":
        num, pt = 38, -1
        for h, n in zip(F5_HITS, (39, 42, 45, 48, 52)):
            if lt >= h:
                num, pt = n, lt - h
        out.append((ov_count(num, pt), 1.0))
        for h in F5_HITS:
            if h <= lt < h + 0.05:
                out.append((B.ov_flash(0.3 * (1 - (lt - h) / 0.05)), 1.0))
    if sid == "F6":
        out.append((ov_count(52, -1), fade(lt, 0.0, dur, 0.0, 0.1, first=True)))
        out.append((B.ov_caption("칠수록 일이 늘어난다", y=1130, size=64), fade(lt, 0.12, dur, 0.1, 0.1)))
    if sid == "S5c":
        out.append((B.ov_hud(52, lt, big=True, blink_t=lt * 2), 1.0))
    if sid == "F4c":
        out.append((ov_red(1.0), 0.75 if int(lt * 6.7) % 2 == 0 else 0.25))
    if sid == "F7" and lt > dur - 0.1:
        out.append((B.ov_flash((lt - (dur - 0.1)) / 0.1 * 0.9, (255, 235, 190)), 1.0))
    if sid == "H1":
        if 0.22 <= lt < 0.9:
            k = (lt - 0.22) / 0.68
            out.append((B.flare(W * 0.5, H * 0.33, 1500, 1.0, GOLD), max(0, 1 - k)))
            out.append((B.ov_ring(W * 0.5, H * 0.33, 1700 * ease(k), max(0, 1 - k), GOLD, 16), 1.0))
        out.append((B.ov_tag("홍책사"), fade(lt, 0.7, dur, 0.15, 0.12)))
        if 1.33 <= lt < 1.6:
            k = (lt - 1.33) / 0.27
            out.append((B.ov_ring(W * 0.5, H * 0.5, 1600 * ease(k), max(0, 1 - k), (210, 235, 255), 14), 1.0))
    if sid == "S17":
        land = 0.42
        if lt < land:
            k = ease(lt / land)
            x = -120 + (LAND[0] * W + 120) * k
            y = 1500 + (LAND[1] * H - 1500) * k - 260 * math.sin(math.pi * k)
            r = int(120 - 70 * k)
            c = B.coin_img(r, max(0.15, abs(math.cos(lt * 30))))
            im = B.layer()
            for j, w in enumerate((0.3, 0.15)):
                kk = max(0, k - 0.06 * (j + 1))
                xx = -120 + (LAND[0] * W + 120) * kk
                yy = 1500 + (LAND[1] * H - 1500) * kk - 260 * math.sin(math.pi * kk)
                im.alpha_composite(B.with_alpha(c, w), (int(xx - c.width / 2), int(yy - c.height / 2)))
            im.alpha_composite(c, (int(x - c.width / 2), int(y - c.height / 2)))
            out.append((B.glow_layer(im, 14, 0.7), 1.0))
        else:
            k = (lt - land) / 0.5
            if k < 1:
                out.append((B.flare(LAND[0] * W, LAND[1] * H, 1200, 1.0, GOLD), 1 - k))
                out.append((B.ov_ring(LAND[0] * W, LAND[1] * H, 1500 * ease(k), 1 - k, GOLD, 14), 1.0))
            if lt < land + 0.06:
                out.append((B.ov_flash(0.5 * (1 - (lt - land) / 0.06), (255, 230, 170)), 1.0))
        out.append((B.ov_caption("돌 하나에 일 하나", y=230, size=62), fade(lt, 0.55, dur, 0.1, 0.1)))
    if sid == "K1":
        if 1.5 <= lt < 1.8:
            k = (lt - 1.5) / 0.3
            out.append((B.ov_ring(W * 0.5, H * 0.42, 1700 * ease(k), max(0, 1 - k), GOLD, 18), 1.0))
    if sid == "K2" and 0.25 <= lt < 0.5:
        out.append((B.ov_flash(0.7 * (1 - (lt - 0.25) / 0.25), (255, 240, 205)), 1.0))
    if sid == "S24":
        out.append((B.ov_caption("현실, 월요일 9시 1분", y=250, size=58), fade(lt, 0.0, 1.5, 0.0, 0.15, first=True)))
    if sid == "S26" and 0.6 <= lt < 0.78:
        a = 1.0 if int((lt - 0.6) * 30) % 3 != 1 else 0.4
        out.append((B.ov_hud_frame(a), 1.0))
        out.append((B.ov_battery("배터리 11%", red=False, y=150), a))
    return out


def frame_at(Tabs):
    sid = next((s for s in ORDER if T[s][0] <= Tabs < T[s][1]), ORDER[-1])
    a0, a1 = T[sid]
    lt, dur = Tabs - a0, a1 - a0
    a, post = base(sid, lt, dur)
    if post.get("chroma"):
        a = B.chroma(a, post["chroma"])
    if not post.get("no_grade"):
        if sid in ACTION:
            a = B.grade(a, "action", 0.8)
        elif sid == "S19":
            a = B.grade(a, "frozen", 0.2)
        elif sid in ("S17", "S22a"):
            a = B.grade(a, "frozen", 0.85)
        elif sid in ("S24", "S25", "S26"):
            a = B.grade(a, "neutral", 1.0)
        elif sid == "S27":
            a = B.grade(a, "warm", 0.35)
    if sid != "S28":
        a = B.vign(a, 0.18)
    ovs = []
    if sid in ("H2", "S17", "S19", "S22a") or (sid == "H1" and lt >= 1.5):
        ovs.append((B.particles(Tabs, warm=sid in ("H1", "H2", "S19")), 0.85))
    ovs += overlays(sid, lt, dur, a0, post)
    ovs.append((B.ov_ai(), 1.0))
    return B.composite(a, ovs), sid


def render(out, t_from=0.0, t_to=None):
    t_to = TOTAL if t_to is None else t_to
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-vf", "unsharp=5:5:0.3", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out],
                         stdin=subprocess.PIPE)
    last = None
    src = {s["id"]: s.get("src") for s in SPEC["shots"]}
    for fi in range(n0, n1):
        Tabs = (fi + 0.5) / FPS
        frm, sid = frame_at(Tabs)
        if sid != last:
            last = sid
            keep = {src.get(sid), "S5"}
            for k in list(B._CL):
                if k[0] not in keep and len(B._CL) > 3:
                    del B._CL[k]
        p.stdin.write(np.asarray(frm, np.uint8).tobytes())
        if fi % 60 == 0:
            print(f"{Tabs:5.1f}s {sid}", flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    if "--still" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--still") + 1].split(",")]:
            frm, sid = frame_at(t)
            frm.save(f"/tmp/g9_{t:.2f}.jpg", quality=85)
            print(t, sid)
        sys.exit(0)
    out = sys.argv[1]
    tf = float(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0.0
    tt = float(sys.argv[sys.argv.index("--to") + 1]) if "--to" in sys.argv else None
    render(out, tf, tt)
