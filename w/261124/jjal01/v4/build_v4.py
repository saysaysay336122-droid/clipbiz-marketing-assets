"""홍책사 짤 1 v4 '오늘의 운수' 편집(1080x1920, 30fps).
사용: python3 build_v4.py cfg.json
segments: 클립 구간을 차례로 잇는다(path, use, gain, semitones, mute). still 항목은 그림 한 장을 dur초 동안 천천히 확대해 쓴다.
overlays: 미리 만든 PNG(1080x1920)를 t 구간에 얹는다. sfx: [(초, 이름, 크기)], 이름은 tools/sfx.py 또는 squish, room.
"""
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import sfx  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       stdout=subprocess.PIPE, text=True).stdout.strip()
    return bool(r)


def read_audio(path, a, b):
    if not has_audio(path):
        return np.zeros((int((b - a) * SR), 2))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    x = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    need = int((b - a) * SR)
    if len(x) < need:
        x = np.concatenate([x, np.zeros((need - len(x), 2))])
    return x[:need]


def squish(rng):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    lp = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += 0.07 * (noise[i] - acc)
        lp[i] = acc
    wob = np.sin(2 * math.pi * (85 + 70 * np.exp(-t * 8)) * t) * 0.55
    env = np.minimum(1, t / 0.012) * np.exp(-t * 6.5)
    return (lp * 3.5 + wob) * env * 0.55


def room(rng, sec):
    n = int(sec * SR)
    noise = rng.standard_normal(n)
    lp = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += 0.02 * (noise[i] - acc)
        lp[i] = acc
    fade = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (0.15 * SR))
    return lp * 0.9 * fade


def video(cfg, tmp):
    parts = []
    for i, s in enumerate(cfg["segments"]):
        p = os.path.join(tmp, f"v{i}.mp4")
        if s.get("still"):
            d = s["dur"]
            z = s.get("zoom", 0.04)
            frames = int(round(d * FPS))
            run(["ffmpeg", "-y", "-loop", "1", "-i", s["still"], "-t", str(d),
                 "-vf", f"scale={W * 2}:{H * 2}:flags=lanczos,zoompan=z='1+{z}*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},setsar=1",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", p])
        else:
            a, b = s["use"]
            vf = f"scale={W}:{H}:flags=lanczos,fps={FPS},setsar=1"
            if s.get("speed"):
                vf = f"setpts=PTS/{s['speed']}," + vf
            run(["ffmpeg", "-y", "-ss", str(a), "-t", str((b - a)), "-i", s["path"], "-an", "-vf", vf,
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", p])
        parts.append(p)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    base = os.path.join(tmp, "base.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])
    return base


def seg_len(s):
    return s["dur"] if s.get("still") else s["use"][1] - s["use"][0]


def audio(cfg, tmp, total):
    n = int(total * SR) + SR
    buf = np.zeros((n, 2))
    pos = 0.0
    for s in cfg["segments"]:
        d = seg_len(s)
        if not s.get("still") and not s.get("mute"):
            a, b = s["use"]
            x = read_audio(s["path"], a, b) * s.get("gain", 1.0)
            if s.get("semitones"):
                import librosa
                x = np.stack([librosa.effects.pitch_shift(x[:, k].astype(np.float32), sr=SR, n_steps=s["semitones"]) for k in range(2)], axis=1)
            fade = int(0.02 * SR)
            x[:fade] *= np.linspace(0, 1, fade)[:, None]
            x[-fade:] *= np.linspace(1, 0, fade)[:, None]
            i = int(pos * SR)
            buf[i:i + len(x)] += x
        pos += d
    rng = np.random.default_rng(11)
    for ev in cfg["sfx"]:
        at, name, g = ev[0], ev[1], ev[2]
        if name == "squish":
            s = squish(rng)
        elif name == "room":
            s = room(rng, ev[3])
        else:
            s = sfx.FX[name](rng)
        s = s * g
        i = int(at * SR)
        m = min(len(s), n - i)
        buf[i:i + m, 0] += s[:m]
        buf[i:i + m, 1] += s[:m]
    buf = buf[: int(total * SR)]
    buf = np.tanh(buf / 0.95) * 0.95
    raw = os.path.join(tmp, "mix.wav")
    with wave.open(raw, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    r = subprocess.run(["ffmpeg", "-i", raw, "-af", "loudnorm=I=-13.4:TP=-2.6:LRA=11:print_format=json", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True).stderr
    j = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    out = os.path.join(tmp, "mix_norm.wav")
    run(["ffmpeg", "-y", "-i", raw, "-af",
         f"loudnorm=I=-13.4:TP=-2.6:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
         f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,alimiter=limit=0.76:level=disabled", "-ar", str(SR), out])
    return out


def main():
    cfg = json.load(open(sys.argv[1]))
    tmp = os.path.join(HERE, "tmp")
    os.makedirs(tmp, exist_ok=True)
    total = sum(seg_len(s) for s in cfg["segments"])
    base = video(cfg, tmp)
    wav = audio(cfg, tmp, total)
    cmd = ["ffmpeg", "-y", "-i", base, "-i", wav]
    for o in cfg["overlays"]:
        cmd += ["-loop", "1", "-t", str(total), "-i", o["png"]]
    fc, last = [], "0:v"
    for k, (x, y, w, h, a, b) in enumerate(cfg.get("blur", [])):
        fc.append(f"[{last}]split[bb{k}][bs{k}];[bs{k}]crop={w}:{h}:{x}:{y},gblur=sigma=7,format=rgba[bc{k}];"
                  f"movie={HERE}/ov/blurmask.png,format=gray,scale={w}:{h}[bm{k}];[bc{k}][bm{k}]alphamerge[ba{k}];"
                  f"[bb{k}][ba{k}]overlay={x}:{y}:enable='between(t,{a},{b})'[bl{k}]")
        last = f"bl{k}"
    for k, o in enumerate(cfg["overlays"]):
        a, b = o["t"]
        nxt = f"v{k}"
        if o.get("fade"):
            f = o["fade"]
            fc.append(f"[{k + 2}:v]format=rgba,fade=t=in:st={a}:d={f}:alpha=1[f{k}]")
            fc.append(f"[{last}][f{k}]overlay=0:0:enable='between(t,{a},{b})'[{nxt}]")
        else:
            fc.append(f"[{last}][{k + 2}:v]overlay=0:0:enable='between(t,{a},{b})'[{nxt}]")
        last = nxt
    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", cfg["out"]]
    run(cmd)
    print("ok", cfg["out"], round(total, 2))


if __name__ == "__main__":
    main()
