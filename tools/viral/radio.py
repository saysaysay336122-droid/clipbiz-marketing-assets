"""보이는 라디오 사연 낭독 화면. 사연 문장이 한 줄씩 타자처럼 나오고, 아래 청취자 채팅이 실시간으로 달린다.

spec(json)
  show, title, seed, bpm
  lines : [{t, text, quote?, punch?: hit|boom, flood?: [채팅 문구...], dj?: 'DJ 자막'}]
  chat  : [[t, 닉네임, 글]]
  mute  : [[시작, 끝]]
  end   : {t, hold, big, sub, cta, tiny}
python3 radio.py spec.json out.mp4 --tmp DIR
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

W, H, FPS = fx.W, fx.H, fx.FPS
NICK_COL = ["#FFB648", "#7FD1FF", "#B7F28A", "#FF8FB1", "#C9A8FF", "#FFE07A", "#8AF2D8"]
FLOOD_NICK = ["출근러", "2호선민", "운세중독", "퇴근각", "익명의대리", "칸막이", "역무원아님", "지각러", "사연러버", "새벽형인간"]


def render(spec, out, tmp):
    seed = spec.get("seed", 1)
    rng = np.random.default_rng(seed)
    cam = fx.Camera(seed)
    lines = spec["lines"]
    end = spec["end"]
    total = end["t"] + end.get("hold", 3.0)
    chat = [tuple(c) for c in spec.get("chat", [])]
    ev = []
    djs = []
    for ln in lines:
        ev.append((ln["t"], "tick", 0.25))
        p = ln.get("punch")
        if p == "boom":
            ev.append((ln["t"], "boom", 0.9))
            cam.shake(ln["t"], 0.5, 24)
            cam.punch(ln["t"], 0.08, 0.45)
            cam.flash(ln["t"], 0.14)
        elif p == "hit":
            ev.append((ln["t"], "hit", 0.7))
            cam.punch(ln["t"], 0.05, 0.3)
        for s in ln.get("sfx", []):
            ev.append((ln["t"] + s[0], s[1], s[2]))
        if ln.get("flood"):
            for k in range(14):
                tt = ln["t"] + 0.25 + k * 0.11
                chat.append((tt, FLOOD_NICK[int(rng.integers(0, len(FLOOD_NICK)))], ln["flood"][k % len(ln["flood"])]))
        if ln.get("dj"):
            djs.append((ln["t"] + 0.4, ln["dj"]))
    chat.sort()
    ev.append((end["t"], "sting", 0.8))
    mus = sound.radio_music(total + 1, seed=seed, bpm=spec.get("bpm", 84))
    audio = Path(tmp) / (Path(out).stem + ".wav")
    sound.mix(total, audio, music=mus, events=ev, mute=[tuple(m) for m in spec.get("mute", [])], music_gain=0.5)

    vid = Path(tmp) / (Path(out).stem + "_v.mp4")
    wr = fx.Writer(vid)
    surf = fx.surface()
    f_line = fx.font("bold", 62)
    f_old = fx.font("medium", 42)
    nick_col = {}
    for fi in range(int(total * FPS)):
        t = fi / FPS
        c = surf.getCanvas()
        fx.radial_bg(c, "#2A1F45", "#0D0A18", 540, 700, 1300)
        c.save()
        cam.apply(c, t)
        # 이퀄라이저
        for k in range(28):
            hgt = 20 + 60 * abs(math.sin(t * (2.1 + k * 0.37) + k)) * (0.6 + 0.4 * math.sin(t * 1.3 + k * 0.5))
            c.drawRoundRect(skia.Rect.MakeXYWH(70 + k * 34, 380 - hgt, 20, hgt), 6, 6, fx.paint("#7B5CFF", 0.45))
        # 위 띠
        on = 0.6 + 0.4 * (math.sin(t * 5) > 0)
        fx.rrect(c, 60, 150, 170, 62, 31, "#E3342F", on)
        fx.text(c, "ON AIR", 145, 195, fx.font("black", 34), "#FFFFFF")
        fx.text(c, spec["show"], 250, 195, fx.font("bold", 34), "#D9D2FF", 0.95, align="left")
        ft = fx.font("black", 60)
        tl = fx.wrap(spec["title"], ft, 960)
        for i, s in enumerate(tl):
            fx.text(c, s, 540, 290 + i * 74, ft, "#FFFFFF", 1, stroke=10, stroke_color="#0D0A18")
        # 사연 문장
        shown = [ln for ln in lines if ln["t"] <= t]
        y = 1060
        for k, ln in enumerate(reversed(shown)):
            if k == 0:
                n = len(ln["text"])
                nch = min(n, int((t - ln["t"]) / 0.045) + 1)
                txt = ln["text"][:nch]
                col = "#FFE07A" if ln.get("quote") else "#FFFFFF"
                fl = f_line
                if ln.get("punch"):
                    fl = fx.font("black", 92 if ln["punch"] == "boom" else 78)
                    col = "#FFD54A"
                    txt = ln["text"]
                wl = fx.wrap(txt, fl, 940)
                lh = fl.getSize() * 1.3
                y -= (len(wl) - 1) * lh
                c.save()
                if ln.get("punch"):
                    kk = min(1, (t - ln["t"]) / 0.14)
                    scl = 1.6 - 0.6 * fx.ease_out(kk)
                    c.translate(70, y)
                    c.scale(scl, scl)
                    c.translate(-70, -y)
                for i, s in enumerate(wl):
                    fx.text(c, s, 70, y + i * lh, fl, col, 1, align="left", stroke=10, stroke_color="#0D0A18")
                c.restore()
                y -= 120
            else:
                a = max(0.0, 0.55 - 0.12 * k)
                if a <= 0:
                    break
                wl = fx.wrap(ln["text"], f_old, 940)
                y -= (len(wl) - 1) * 54
                for i, s in enumerate(wl):
                    fx.text(c, s, 70, y + i * 54, f_old, "#CFC8F0", a, align="left")
                y -= 78
                if y < 470:
                    break
        c.restore()
        # 채팅 창
        fx.rrect(c, 50, 1260, 980, 330, 26, "#000000", 0.45)
        fx.text(c, "청취자 채팅", 80, 1305, fx.font("bold", 28), "#B9B2E0", 0.9, align="left")
        vis = [m for m in chat if m[0] <= t][-6:]
        for i, (mt, nick, msg) in enumerate(vis):
            yy = 1350 + i * 40
            if nick not in nick_col:
                nick_col[nick] = NICK_COL[len(nick_col) % len(NICK_COL)]
            a = min(1, (t - mt) / 0.15)
            fx.text(c, nick, 80, yy + 12, fx.font("bold", 30), nick_col[nick], a, align="left")
            nw = fx.font("bold", 30).measureText(nick)
            fx.text(c, msg, 80 + nw + 18, yy + 12, fx.font("medium", 30), "#FFFFFF", a, align="left")
        # DJ 자막
        for dt0, s in djs:
            dt = t - dt0
            if 0 <= dt < 1.5:
                k = min(1, dt / 0.12)
                scl = 1.8 - 0.8 * fx.ease_out(k)
                a = min(1, (1.5 - dt) / 0.25)
                c.save()
                c.translate(540, 560)
                c.rotate(-5)
                c.scale(scl, scl)
                fx.text(c, s, 0, 0, fx.font("black", 82), "#FFD54A", a, stroke=14, stroke_color="#111111")
                c.restore()
        if t >= end["t"]:
            dt = t - end["t"]
            k = fx.ease_out(dt / 0.3)
            c.drawRect(skia.Rect.MakeWH(W, H), fx.paint("#0D0A18", 0.985 * k))
            fx.text(c, end["dj"], 540, 700, fx.font("bold", 40), "#B9B2E0", k)
            for i, s in enumerate(end["big"].split("\n")):
                fx.text(c, s, 540, 880 + i * 100, fx.font("black", 84), "#FFFFFF", k, stroke=10, stroke_color="#0D0A18")
            fx.text(c, end["sub"], 540, 1110, fx.font("bold", 44), "#D9D2FF", k)
            fx.text(c, end["cta"], 540, 1640, fx.font("medium", 34), "#C9C2E8", 0.85 * k)
            fx.text(c, end["tiny"], 540, 1700, fx.font("regular", 17), "#8C86A8", 0.6 * k)
        cam.overlay(c, t)
        wr.put(fx.snapshot(surf))
    wr.close()
    fx.mux(vid, audio, out)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--tmp", default=".")
    a = ap.parse_args()
    print(render(json.loads(Path(a.spec).read_text()), a.out, a.tmp))


if __name__ == "__main__":
    main()
