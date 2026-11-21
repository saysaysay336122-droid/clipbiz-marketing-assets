"""홍책사 짤 1 '쉿' 편집(1080x1920, 30fps, 약 15초).
사용: python3 build_jjal01.py config.json
config: clips(S1, S2 경로와 사용 구간), line(대사 자막 시작과 끝), sfx 시각, 출력 경로.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import sfx  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
YEL = (255, 214, 80, 255)
HERE = os.path.dirname(os.path.abspath(__file__))


def font(path, size):
    for i in range(10):
        f = ImageFont.truetype(path, size, index=i)
        if "KR" in f.getname()[0]:
            return f
    return ImageFont.truetype(path, size)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def center(d, y, s, f, fill=(255, 255, 255, 255), stroke=6):
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))


def png(name, draw):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw(ImageDraw.Draw(im))
    p = os.path.join(HERE, "ov", name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p)
    return p


def overlays(cfg):
    out = []

    def ai(d):
        t = "AI로 만든 가상 캐릭터"
        f = font(FR, 26)
        w = d.textlength(t, font=f)
        d.rounded_rectangle((26, 40, 26 + w + 28, 84), 12, fill=(0, 0, 0, 120))
        d.text((40, 46), t, font=f, fill=(255, 255, 255, 215))
    out.append((png("ai.png", ai), 0, 99))

    def cap(d):
        f = font(FB, 70)
        for i, l in enumerate(cfg["caption"].split("\n")):
            center(d, 210 + i * 96, l, f, stroke=7)
    a, b = cfg["caption_t"]
    out.append((png("cap.png", cap), a, b))

    def line(d):
        center(d, 1150, cfg["line"]["text"], font(FB, 62), stroke=6)
    a, b = cfg["line"]["t"]
    out.append((png("line.png", line), a, b))

    def tag(d):
        f1, f2 = font(FB, 60), font(FB, 46)
        y = 1360
        w = max(d.textlength("2027 한 수", font=f1), d.textlength("hongchaksa.kr", font=f2))
        x0, x1 = (W - w) / 2 - 40, (W + w) / 2 + 40
        d.rounded_rectangle((x0, y - 18, x1, y + 168), 26, fill=(15, 15, 20, 190))
        center(d, y, "2027 한 수", f1, fill=YEL, stroke=0)
        center(d, y + 86, "hongchaksa.kr", f2, stroke=0)
    a, b = cfg["tag_t"]
    out.append((png("tag.png", tag), a, b))

    if cfg.get("nametag"):
        nt = cfg["nametag"]

        def name(d):
            f = font(FB, 44)
            x, y = nt["xy"]
            w = d.textlength(nt["text"], font=f)
            d.rounded_rectangle((x, y, x + w + 36, y + 66), 14, fill=(15, 15, 20, 200))
            d.text((x + 18, y + 6), nt["text"], font=f, fill=YEL)
        a, b = nt["t"]
        out.append((png("name.png", name), a, b))
    return out


def video(cfg, tmp):
    parts = []
    for i, c in enumerate(cfg["clips"]):
        p = os.path.join(tmp, f"v{i}.mp4")
        a, b = c["use"]
        run(["ffmpeg", "-y", "-ss", str(a), "-t", str(b - a), "-i", c["path"], "-an",
             "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS},setsar=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             "-pix_fmt", "yuv420p", p])
        parts.append(p)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    base = os.path.join(tmp, "base.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])
    return base


def read_audio(path, a, b):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def squish(rng):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    lp = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += 0.08 * (noise[i] - acc)
        lp[i] = acc
    wob = np.sin(2 * math.pi * (90 + 60 * np.exp(-t * 9)) * t) * 0.6
    env = np.minimum(1, t / 0.01) * np.exp(-t * 7)
    return (lp * 3.5 + wob) * env * 0.5


def audio(cfg, tmp, total):
    n = int(total * SR)
    buf = np.zeros((n, 2))
    pos = 0.0
    for c in cfg["clips"]:
        a, b = c["use"]
        x = read_audio(c["path"], a, b) * c.get("gain", 1.0)
        if c.get("semitones"):
            import librosa
            x = np.stack([librosa.effects.pitch_shift(x[:, k].astype(np.float32), sr=SR, n_steps=c["semitones"]) for k in range(2)], axis=1)
        i = int(pos * SR)
        m = min(len(x), n - i)
        buf[i:i + m] += x[:m]
        pos += b - a
    for a, b in cfg.get("quiet", []):
        i, j = int(a * SR), int(b * SR)
        buf[i:j] *= 0.15
    rng = np.random.default_rng(7)
    for at, name, g in cfg["sfx"]:
        s = squish(rng) if name == "squish" else sfx.FX[name](rng)
        s = s * g
        i = int(at * SR)
        m = min(len(s), n - i)
        buf[i:i + m, 0] += s[:m]
        buf[i:i + m, 1] += s[:m]
    buf = np.tanh(buf / 0.95) * 0.95
    raw = os.path.join(tmp, "mix.wav")
    import wave
    with wave.open(raw, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    # 2패스 loudnorm -14 LUFS, 최고 -2 dBTP
    r = subprocess.run(["ffmpeg", "-i", raw, "-af", "loudnorm=I=-14:TP=-2.6:LRA=11:print_format=json", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True).stderr
    j = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    out = os.path.join(tmp, "mix_norm.wav")
    run(["ffmpeg", "-y", "-i", raw, "-af",
         f"loudnorm=I=-14:TP=-2.6:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
         f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,alimiter=limit=0.72:level=disabled", "-ar", str(SR), out])
    return out


def main():
    cfg = json.load(open(sys.argv[1]))
    tmp = os.path.join(HERE, "tmp")
    os.makedirs(tmp, exist_ok=True)
    total = sum(c["use"][1] - c["use"][0] for c in cfg["clips"])
    base = video(cfg, tmp)
    ovs = overlays(cfg)
    wav = audio(cfg, tmp, total)
    cmd = ["ffmpeg", "-y", "-i", base, "-i", wav]
    for p, a, b in ovs:
        cmd += ["-loop", "1", "-t", str(total), "-i", p]
    fc = []
    last = "0:v"
    for k, (x, y, w, h, a, b) in enumerate(cfg.get("blur", [])):
        fc.append(f"[{last}]split[bb{k}][bs{k}];[bs{k}]crop={w}:{h}:{x}:{y},gblur=sigma=7,format=rgba[bc{k}];"
                  f"movie={HERE}/ov/blurmask.png,format=gray,scale={w}:{h}[bm{k}];[bc{k}][bm{k}]alphamerge[ba{k}];"
                  f"[bb{k}][ba{k}]overlay={x}:{y}:enable='between(t,{a},{b})'[bl{k}]")
        last = f"bl{k}"
    for k, (p, a, b) in enumerate(ovs):
        nxt = f"v{k}"
        fc.append(f"[{last}][{k + 2}:v]overlay=0:0:enable='between(t,{a},{b})'[{nxt}]")
        last = nxt
    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", str(total), "-movflags", "+faststart", cfg["out"]]
    run(cmd)
    print("ok", cfg["out"], total)


if __name__ == "__main__":
    main()
