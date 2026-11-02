"""키네틱 타이포 두 가지.

ranking : 10위부터 1위까지 박자에 맞춰 한 줄씩 꽂히는 순위표(일간별 등)
alerts  : 머릿속 시스템 알림 카드가 쌓이고 게이지가 떨어지다 마지막에 뒤집히는 형식

python3 kinetic.py spec.json out.mp4 --tmp DIR
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx  # noqa: E402
import sound  # noqa: E402
import skia  # noqa: E402

EL_COLOR = {"목": "#2FB36B", "화": "#F0503F", "토": "#F2C14E", "금": "#F4F5F7", "수": "#3A7BEA"}
EL_TEXT = {"목": "#FFFFFF", "화": "#FFFFFF", "토": "#2A2112", "금": "#1C2128", "수": "#FFFFFF"}


def ranking(spec, out, tmp):
    bpm = spec.get("bpm", 150)
    beat = 60 / bpm
    step = beat * 4
    items = spec["items"]          # 10위부터 순서대로
    n = len(items)
    t0 = 0.35
    reveal = [t0 + k * step for k in range(n)]
    t_one = reveal[-1]
    t_end = t_one + step * 1.25
    total = t_end + 2.4
    cam = fx.Camera(3)
    sfx_ev = []
    for k, rt in enumerate(reveal):
        if k < n - 1:
            sfx_ev.append((rt, "whoosh", 0.45))
            sfx_ev.append((rt + 0.05, "hit", 0.45))
            cam.punch(rt, 0.025, 0.25)
    sfx_ev += [(t_one - 1.0, "riser", 0.6), (t_one, "boom", 0.95), (t_one, "orch", 0.7), (t_end, "whoosh", 0.5)]
    cam.flash(t_one, 0.2)
    cam.shake(t_one, 0.45, 22)
    cam.punch(t_one, 0.08, 0.45)
    mus = sound.phonk(total + 1, seed=spec.get("seed", 4), bpm=bpm)
    audio = Path(tmp) / (Path(out).stem + ".wav")
    sound.mix(total, audio, music=mus, events=sfx_ev, drop=[t_one], music_gain=0.6)
    vid = Path(tmp) / (Path(out).stem + "_v.mp4")
    wr = fx.Writer(vid)
    surf = fx.surface()
    top, row_h = 430, 104
    for fi in range(int(total * fx.FPS)):
        t = fi / fx.FPS
        c = surf.getCanvas()
        c.clear(fx.col("#0E1412"))
        fx.radial_bg(c, "#1F2C27", "#0B0F0E", 540, 900, 1100)
        c.save()
        cam.apply(c, t)
        fx.text(c, spec["kicker"], 540, 200, fx.font("bold", 38), "#FFD54A")
        hs = 1 + 0.05 * max(0, 1 - t / 0.25)
        fx.text(c, spec["title"], 540, 300, fx.font("black", int(70 * hs)), "#FFFFFF", stroke=10)
        fx.text(c, spec.get("sub", ""), 540, 365, fx.font("bold", 32), "#C9D3CE", 0.9)
        for k, it in enumerate(items):
            rank = n - k
            rt = reveal[k]
            y = top + (rank - 1) * row_h
            # 빈 칸
            fx.rrect(c, 60, y, 960, row_h - 14, 22, "#FFFFFF", 0.05)
            if t < rt:
                fx.text(c, f"{rank}", 112, y + 64, fx.font("black", 46), "#FFFFFF", 0.25)
                continue
            dt = t - rt
            kx = fx.ease_out_back(min(1, dt / 0.22))
            off = (1 - kx) * 600
            a_ = min(1, dt / 0.12)
            c.save()
            c.translate(off, 0)
            gold = rank == 1
            if gold:
                pulse = 0.5 + 0.5 * math.sin(t * 7)
                c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(150, y - 6, 870, row_h + 2), 24, 24),
                            fx.paint("#FFD54A", 0.35 + 0.25 * pulse, blur=18))
            fx.rrect(c, 150, y, 870, row_h - 14, 22, "#FFD54A" if gold else "#1E2A26", a_)
            el = it["el"]
            c.drawCircle(205, y + 45, 34, fx.paint(EL_COLOR[el], a_))
            fx.text(c, it["stem"], 205, y + 60, fx.font("black", 40), EL_TEXT[el], a_)
            fx.text(c, it["name"], 258, y + 60, fx.font("black", 40), "#141A21" if gold else "#FFFFFF", a_, align="left")
            nw = fx.font("black", 40).measureText(it["name"])
            f_d = fx.font("bold", 34)
            desc = it["desc"]
            while f_d.measureText(desc) > 990 - (278 + nw) and len(desc) > 4:
                f_d = fx.font("bold", f_d.getSize() - 2)
            fx.text(c, desc, 278 + nw, y + 58, f_d, "#141A21" if gold else "#DDE5E1", a_, align="left")
            c.restore()
            if dt < 0.25:
                c.drawRect(skia.Rect.MakeXYWH(150, y, 870, row_h - 14), fx.paint("#FFFFFF", 0.5 * (1 - dt / 0.25)))
            fx.text(c, f"{rank}", 112, y + 64, fx.font("black", 46), "#FFD54A" if gold else "#FFFFFF", 1.0)
        c.restore()
        if t >= t_end:
            k = fx.ease_out((t - t_end) / 0.3)
            c.drawRect(skia.Rect.MakeWH(1080, 1920), fx.paint("#0B0F0E", 0.95 * k))
            fx.text(c, spec["end_big"], 540, 900, fx.font("black", 96), "#FFFFFF", k, stroke=10)
            fx.text(c, spec["end_sub"], 540, 1010, fx.font("bold", 46), "#C9D3CE", k)
            fx.text(c, spec["cta"], 540, 1640, fx.font("medium", 34), "#C9D3CE", 0.85 * k)
            fx.text(c, spec["tiny"], 540, 1700, fx.font("regular", 17), "#8C9791", 0.6 * k)
        cam.overlay(c, t)
        wr.put(fx.snapshot(surf))
    wr.close()
    fx.mux(vid, audio, out)
    return total


def alerts(spec, out, tmp):
    th = spec.get("theme", {})
    bg1, bg2 = th.get("bg1", "#17222E"), th.get("bg2", "#0B1118")
    beats = spec["beats"]           # [{t, level, text, gauge}]
    last = beats[-1]
    t_end = spec["end"]["t"]
    total = t_end + spec["end"].get("hold", 2.6)
    cam = fx.Camera(5)
    rng = np.random.default_rng(5)
    sfx_ev = []
    for b in beats[:-1]:
        sfx_ev.append((b["t"], "ding" if b["level"] == "ok" else "buzz", 0.55))
        sfx_ev.append((b["t"], "pop", 0.6))
        cam.punch(b["t"], 0.03, 0.25)
        if b.get("vibrate"):
            sfx_ev.append((b["t"] + 0.1, "vibrate", 0.8))
            cam.shake(b["t"], 1.0, 8)
    sfx_ev += [(last["t"] - 1.2, "riser", 0.6), (last["t"], "boom", 0.95), (last["t"] + 0.05, "cash", 0.5)]
    cam.flash(last["t"], 0.2)
    cam.shake(last["t"], 0.45, 24)
    cam.punch(last["t"], 0.1, 0.5)
    cam.glitch(beats[-2]["t"], 0.25)
    sk = sound.sneaky(total + 1, seed=spec.get("seed", 6))
    ph = sound.phonk(total + 1, seed=spec.get("seed", 6) + 1, bpm=spec.get("bpm", 140))
    music = sound.bed(total + 0.1, [(0, last["t"] - 0.45, sk, 1.0), (last["t"], total, ph, 1.0)])
    audio = Path(tmp) / (Path(out).stem + ".wav")
    sound.mix(total, audio, music=music, events=sfx_ev, muffle=[(beats[-2]["t"], last["t"] - 0.45)], music_gain=0.55)
    vid = Path(tmp) / (Path(out).stem + "_v.mp4")
    wr = fx.Writer(vid)
    surf = fx.surface()
    LV = {"ok": ("#2FB36B", "확인"), "warn": ("#F2C14E", "주의"), "bad": ("#FF8A3D", "경고"), "red": ("#FF3B30", "위험"),
          "win": ("#FFD54A", "해결")}

    def gauge_at(t):
        g = beats[0]["gauge"]
        for k, b in enumerate(beats):
            if t >= b["t"]:
                prev = beats[k - 1]["gauge"] if k else b["gauge"]
                kk = fx.ease_out(min(1, (t - b["t"]) / 0.45))
                g = prev + (b["gauge"] - prev) * kk
        return g

    for fi in range(int(total * fx.FPS)):
        t = fi / fx.FPS
        c = surf.getCanvas()
        fx.radial_bg(c, bg1, bg2, 540, 900, 1200)
        c.save()
        cam.apply(c, t)
        fx.text(c, spec["kicker"], 540, 200, fx.font("bold", 38), th.get("accent", "#FF8A3D"))
        hs = 1 + 0.05 * max(0, 1 - t / 0.25)
        for li, ln in enumerate(spec["title"]):
            fx.text(c, ln, 540, 292 + li * 82, fx.font("black", int(66 * hs)), "#FFFFFF", stroke=10)
        # 게이지
        g = gauge_at(t)
        gy = 300 + len(spec["title"]) * 82
        fx.text(c, spec.get("gauge_label", "자신감"), 70, gy + 40, fx.font("black", 40), "#FFFFFF", align="left")
        fx.rrect(c, 260, gy, 620, 52, 26, "#FFFFFF", 0.12)
        gc = "#2FB36B" if g >= 60 else ("#F2C14E" if g >= 30 else "#FF3B30")
        fx.rrect(c, 260, gy, max(52, 620 * g / 100), 52, 26, gc)
        fx.text(c, f"{int(round(g))}%", 1010, gy + 42, fx.font("black", 44), gc, align="right")
        # 알림 카드: 최근 것이 위로, 오래된 것은 아래로 밀리며 흐려진다
        shown = [b for b in beats if b["t"] <= t]
        y0 = gy + 120
        for k, b in enumerate(reversed(shown)):
            dt = t - b["t"]
            big = b is last
            kk = fx.ease_out_back(min(1, dt / 0.22))
            colr, tag = LV[b["level"]]
            h = 250 if big else 170
            y = y0 + sum((250 if bb is last else 170) + 22 for bb in list(reversed(shown))[:k])
            if y > 1560:
                continue
            a_ = (1.0 if k == 0 else max(0.35, 0.8 - 0.15 * k)) * min(1, dt / 0.1)
            c.save()
            c.translate(540, y + h / 2)
            sc_ = (0.75 + 0.25 * kk) * (1.0 if k == 0 else 0.96)
            c.scale(sc_, sc_)
            fx.rrect(c, -480, -h / 2, 960, h, 28, "#0B0F14", 0.9 * a_)
            fx.rrect(c, -480, -h / 2, 960, h, 28, colr, a_, stroke=5 if not big else 8)
            fx.rrect(c, -450, -h / 2 + 26, 120, 50, 14, colr, a_)
            fx.text(c, tag, -390, -h / 2 + 64, fx.font("black", 32), "#0B0F14", a_)
            f_ = fx.font("black", 52 if not big else 62)
            lines = [ln for part in b["text"].split("\n") for ln in fx.wrap(part, f_, 880)]
            for li, ln in enumerate(lines[:2]):
                fx.text(c, ln, -450, -h / 2 + 130 + li * (62 if big else 56), f_, "#FFFFFF", a_, align="left")
            if b.get("note"):
                fx.text(c, b["note"], 450, -h / 2 + 64, fx.font("bold", 30), "#C9D3CE", a_, align="right")
            c.restore()
        c.restore()
        if t >= t_end:
            e = spec["end"]
            k = fx.ease_out((t - t_end) / 0.3)
            c.drawRect(skia.Rect.MakeWH(1080, 1920), fx.paint(bg2, 0.96 * k))
            fx.text(c, e["series"], 540, 760, fx.font("bold", 46), th.get("accent", "#FF8A3D"), k)
            for li, ln in enumerate(e["big"]):
                fx.text(c, ln, 540, 890 + li * 100, fx.font("black", 80), "#FFFFFF", k, stroke=10)
            fx.text(c, e["ask"], 540, 890 + len(e["big"]) * 100 + 40, fx.font("bold", 44), "#C9D3CE", k)
            fx.text(c, e["cta"], 540, 1640, fx.font("medium", 34), "#C9D3CE", 0.85 * k)
            fx.text(c, e["tiny"], 540, 1700, fx.font("regular", 17), "#8C9791", 0.6 * k)
        cam.overlay(c, t)
        arr = fx.snapshot(surf)
        gl = cam.glitch_amt(t)
        if gl > 0:
            arr = fx.rgb_split(arr, gl, rng)
        wr.put(arr)
    wr.close()
    fx.mux(vid, audio, out)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--tmp", default=".")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    fn = ranking if spec["mode"] == "ranking" else alerts
    print(fn(spec, a.out, a.tmp))


if __name__ == "__main__":
    main()
