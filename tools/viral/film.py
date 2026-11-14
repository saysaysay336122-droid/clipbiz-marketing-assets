"""실사 소재(Pexels)로 만드는 짝퉁 장르 영상: 재난 블록버스터 예고편, 자연 다큐, 허세 vs 현실.

spec(json)
  style  : trailer | doc
  seed, bpm
  bug    : 화면 왼쪽 위 작은 프로그램 이름(다큐)
  shots  : [{clip, from, dur, zoom:[시작,끝], grade, speed, flash, sfx:[[초, 이름, 크기]], captions:[{at, dur, text, style, sub}]}
            또는 {card: true, dur, captions:[...]}]
    caption style: trailer(가운데 명조), card(검은 화면 명조), title(큰 제목), punch(노란 큰 글씨), doc(아래 자막), real(현실 딱지)
  mute   : [[시작, 끝]] 음악 끄는 구간(허무한 정적)
  end    : {t, hold, lines:[[글, 크기, 색]], cta, tiny}
python3 film.py spec.json out.mp4 --tmp DIR
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx  # noqa: E402
import sound  # noqa: E402
import skia  # noqa: E402

STOCK = Path(__file__).resolve().parents[2] / "stock"
W, H, FPS = fx.W, fx.H, fx.FPS
GRADE = {
    "night": "eq=contrast=1.18:brightness=-0.05:saturation=0.75,colorbalance=bs=0.10:bm=0.04:rs=-0.05",
    "warm": "eq=contrast=1.06:saturation=1.12,colorbalance=rh=0.06:rm=0.03:bh=-0.05",
    "cold": "eq=contrast=1.1:saturation=0.8,colorbalance=bs=0.1:bm=0.05:rs=-0.06",
    "doc": "eq=contrast=1.05:saturation=1.08",
    "bw": "hue=s=0,eq=contrast=1.15",
    "none": "null",
    "cold_blur": "gblur=sigma=14,eq=contrast=1.1:saturation=0.8,colorbalance=bs=0.1:bm=0.05:rs=-0.06",
}


def clip_frames(clip, start, dur, speed=1.0, grade="none"):
    src = STOCK / f"pexels_{clip}.mp4"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts=PTS/{speed},fps={FPS},"
          f"{GRADE.get(grade, 'null')},format=rgba")
    n = int(round(dur * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start}", "-t", f"{dur * speed + 0.5}", "-i", str(src),
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
    size = W * H * 4
    last = None
    for _ in range(n):
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        last = np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 4)
        yield last
    else:
        p.stdout.close()
        p.wait()
        return
    # 소재가 짧으면 마지막 장면을 붙든다
    p.stdout.close()
    p.wait()
    produced = 0 if last is None else 1
    while last is not None and produced < n:
        yield last
        produced += 1


def spaced(c, s, x, y, f, color, a, gap=0.08, stroke=0):
    """글자 사이를 벌린 가운데 정렬 글씨(예고편 느낌)."""
    ws = [f.measureText(ch) for ch in s]
    sp = f.getSize() * gap
    total = sum(ws) + sp * (len(s) - 1)
    cx = x - total / 2
    for ch, w in zip(s, ws):
        if ch != " ":
            fx.text(c, ch, cx, y, f, color, a, align="left", stroke=stroke, shadow=10)
        cx += w + sp


def draw_caption(c, cap, t, style_kind):
    dt = t - cap["at"]
    dur = cap["dur"]
    if not (0 <= dt < dur):
        return
    st = cap.get("style", style_kind)
    a_in = min(1, dt / 0.22)
    a_out = min(1, (dur - dt) / 0.22)
    a = min(a_in, a_out)
    text = cap["text"]
    if st in ("trailer", "card"):
        f = fx.font("serif", cap.get("size", 72))
        lines = text.split("\n")
        scl = 1.0 + 0.04 * (dt / dur)
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(scl, scl)
        for i, ln in enumerate(lines):
            spaced(c, ln, 0, (i - (len(lines) - 1) / 2) * f.getSize() * 1.35 + f.getSize() * 0.35, f, "#F4F1EA", a)
        if cap.get("sub"):
            spaced(c, cap["sub"], 0, len(lines) * f.getSize() * 0.75 + 70, fx.font("serif", 40), "#C8C2B4", a)
        c.restore()
    elif st == "title":
        k = fx.ease_out_back(min(1, dt / 0.3))
        c.save()
        c.translate(W / 2, H / 2 - 40)
        c.scale(0.7 + 0.3 * k, 0.7 + 0.3 * k)
        f = fx.font("serif", cap.get("size", 170))
        c.drawTextBlob(skia.TextBlob.MakeFromString(text, f), -f.measureText(text) / 2, 0,
                       fx.paint("#FFB648", 0.7 * a, blur=26))
        spaced(c, text, 0, 0, f, "#FFF6E0", a, gap=0.04)
        if cap.get("sub"):
            spaced(c, cap["sub"], 0, 120, fx.font("serif", 52), "#E8DCC2", a, gap=0.2)
        c.restore()
    elif st == "punch":
        k = min(1, dt / 0.12)
        scl = 1.9 - 0.9 * fx.ease_out(k)
        c.save()
        c.translate(W / 2, cap.get("y", 1240))
        c.rotate(cap.get("rot", -4))
        c.scale(scl, scl)
        f = fx.font("black", cap.get("size", 110))
        for i, ln in enumerate(text.split("\n")):
            fx.text(c, ln, 0, i * f.getSize() * 1.15, f, cap.get("color", "#FFD54A"), a, stroke=16, stroke_color="#111111")
        c.restore()
    elif st == "doc":
        f = fx.font("bold", cap.get("size", 58))
        lines = []
        for part in text.split("\n"):
            lines += fx.wrap(part, f, 940)
        y0 = cap.get("y", 1380) - (len(lines) - 1) * f.getSize() * 1.3
        for i, ln in enumerate(lines):
            fx.text(c, ln, W / 2, y0 + i * f.getSize() * 1.3, f, "#FFFFFF", a, stroke=7, stroke_color="#000000", shadow=12)
    elif st == "label":
        # 이름표(다큐의 '종 이름' 자막)
        f = fx.font("serif", cap.get("size", 76))
        x0 = 70
        y = cap.get("y", 1160)
        fx.text(c, text, x0, y, f, "#FFFFFF", a, align="left", stroke=6, stroke_color="#000000", shadow=12)
        if cap.get("sub"):
            fx.text(c, cap["sub"], x0, y + 58, fx.font("regular", 34), "#EDEDED", a, align="left", stroke=5,
                    stroke_color="#000000")
        c.drawRect(skia.Rect.MakeXYWH(x0, y + 18 + (70 if cap.get("sub") else 0), 220 * min(1, dt / 0.4), 5),
                   fx.paint("#FFD54A", a))
    elif st == "real":
        # '현실' 딱지
        k = fx.ease_out_back(min(1, dt / 0.18))
        c.save()
        c.translate(W / 2, cap.get("y", 520))
        c.rotate(-7)
        c.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k)
        f = fx.font("black", cap.get("size", 120))
        w = f.measureText(text) + 80
        fx.rrect(c, -w / 2, -f.getSize() * 0.95, w, f.getSize() * 1.3, 18, "#E3342F", 0.95 * a)
        fx.text(c, text, 0, 0, f, "#FFFFFF", a)
        c.restore()


def render(spec, out, tmp):
    style = spec.get("style", "trailer")
    seed = spec.get("seed", 1)
    rng = np.random.default_rng(seed)
    cam = fx.Camera(seed)
    # 시간표
    t = 0.0
    shots = []
    for s in spec["shots"]:
        s = dict(s)
        s["t0"] = t
        shots.append(s)
        t += s["dur"]
    end = spec["end"]
    end_t = t
    total = end_t + end.get("hold", 3.0)
    # 소리
    ev = []
    for s in shots:
        if s.get("flash"):
            cam.flash(s["t0"], 0.12)
            ev.append((s["t0"], "whoosh", 0.5))
        for at, name, g in s.get("sfx", []):
            ev.append((s["t0"] + at, name, g))
            if name in ("braam", "boom", "dun"):
                cam.shake(s["t0"] + at, 0.5, 14)
                cam.punch(s["t0"] + at, 0.05, 0.5)
            if name in ("hit",):
                cam.punch(s["t0"] + at, 0.06, 0.3)
    kind = spec.get("music", "trailer" if style == "trailer" else "doc")
    if kind == "trailer":
        mus = sound.trailer_music(total + 1, seed=seed, bpm=spec.get("bpm", 96))
    elif kind == "phonk":
        mus = sound.phonk(total + 1, seed=seed, bpm=spec.get("bpm", 140))
    else:
        mus = sound.doc_music(total + 1, seed=seed, bpm=spec.get("bpm", 72))
    mute = [tuple(m) for m in spec.get("mute", [])]
    ev.append((end_t, end.get("sfx", "sting"), 0.9))
    audio = Path(tmp) / (Path(out).stem + ".wav")
    sound.mix(total, audio, music=mus, events=ev, mute=mute, music_gain=spec.get("music_gain", 0.6))
    # 그림
    vid = Path(tmp) / (Path(out).stem + "_v.mp4")
    wr = fx.Writer(vid)
    surf = fx.surface()
    grains = [(rng.standard_normal((H // 4, W // 4)) * spec.get("grain", 9)).clip(-30, 30) for _ in range(4)]
    vign = None
    fi = 0
    for s in shots:
        n = int(round(s["dur"] * FPS))
        if s.get("card"):
            frames = (None for _ in range(n))
        else:
            frames = clip_frames(s["clip"], s.get("from", 0), s["dur"], s.get("speed", 1.0), s.get("grade", "none"))
        z0, z1 = s.get("zoom", [1.0, 1.08])
        for k, arr in enumerate(frames):
            t = fi / FPS
            lt = k / FPS
            c = surf.getCanvas()
            c.clear(fx.col("#000000"))
            c.save()
            cam.apply(c, t)
            if arr is not None:
                img = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)
                z = z0 + (z1 - z0) * (k / max(1, n - 1))
                c.save()
                c.translate(W / 2, H / 2)
                c.scale(z, z)
                c.translate(-W / 2, -H / 2)
                c.drawImage(img, 0, 0)
                c.restore()
                if s.get("dim"):
                    c.drawRect(skia.Rect.MakeWH(W, H), fx.paint("#000000", s["dim"]))
            c.restore()
            if style == "trailer":
                c.drawRect(skia.Rect.MakeXYWH(0, 0, W, 250), fx.paint("#000000"))
                c.drawRect(skia.Rect.MakeXYWH(0, H - 250, W, 250), fx.paint("#000000"))
            else:
                fx.vignette(c, 0.45)
                if spec.get("bug"):
                    fx.text(c, spec["bug"], 60, 225, fx.font("serif", 36), "#FFFFFF", 0.85, align="left", stroke=4,
                            stroke_color="#000000")
            for cap in s.get("captions", []):
                draw_caption(c, cap, lt, "trailer" if style == "trailer" else "doc")
            cam.overlay(c, t)
            frame = fx.snapshot(surf)
            # 필름 알갱이
            g = grains[fi % 4]
            g = np.repeat(np.repeat(g, 4, axis=0), 4, axis=1)[:H, :W]
            frame = frame.astype(np.int16)
            frame[..., :3] += g[..., None].astype(np.int16)
            frame = frame.clip(0, 255).astype(np.uint8)
            wr.put(frame)
            fi += 1
        # 소재 프레임이 모자라면 검은 화면으로 채운다
        while fi < int(round((s["t0"] + s["dur"]) * FPS)):
            wr.put(np.zeros((H, W, 4), np.uint8) + np.array([0, 0, 0, 255], np.uint8))
            fi += 1
    # 끝 화면
    for k in range(int(round((total - end_t) * FPS))):
        t = end_t + k / FPS
        dt = t - end_t
        c = surf.getCanvas()
        c.clear(fx.col("#000000"))
        a = min(1, dt / 0.3)
        y = end.get("y", 820)
        for text, size, color in end["lines"]:
            f = fx.font("serif" if size >= 60 else "bold", size)
            for ln in text.split("\n"):
                spaced(c, ln, W / 2, y, f, color, a, gap=0.05)
                y += size * 1.35
            y += 16
        fx.text(c, end["cta"], W / 2, 1640, fx.font("medium", 34), "#C9D3CE", 0.85 * a)
        fx.text(c, end["tiny"], W / 2, 1700, fx.font("regular", 17), "#8C9791", 0.6 * a)
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
    spec = json.loads(Path(a.spec).read_text())
    print(render(spec, a.out, a.tmp))


if __name__ == "__main__":
    main()
