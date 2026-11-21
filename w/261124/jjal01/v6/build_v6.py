"""홍책사 짤 1 v6 '복채가 파 놓은 함정' 편집(1080x1920, 30fps).
v5 편집기(build_v5.py)에 두 가지를 더했다.
1. grade: 컷마다 다른 색과 대비를 grade.py로 맞춰 화면이 한 장소, 한 시간대로 이어지게 한다.
2. music: tools/hcs_music.py 자체 제작 곡을 구간대로 깐다.
사용: python3 build_v6.py cfg_v6.json
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "v5"))
sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import build_v5 as B  # noqa: E402
import hcs_music  # noqa: E402
from grade import grade  # noqa: E402

W, H, FPS, SR = B.W, B.H, B.FPS, B.SR


def graded_clip(s, out, rng):
    a, b = s["use"]
    vf = f"scale={W}:{H}:flags=lanczos,fps={FPS},format=bgr24"
    if s.get("crop"):
        cx, cy, cw, ch = s["crop"]
        vf = f"crop={cw}:{ch}:{cx}:{cy}," + vf
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", s["path"], "-an", "-vf", vf,
                            "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    enc_cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if B.has_audio(s["path"]):
        enc_cmd += ["-ss", str(a), "-t", str(b - a), "-i", s["path"], "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k"]
    enc_cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p", out]
    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)
    n = W * H * 3
    last = None
    while True:
        raw = dec.stdout.read(n)
        if len(raw) < n:
            break
        img = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        g = grade(img, s["grade"], rng)
        enc.stdin.write(g.tobytes())
        last = g
    enc.stdin.close()
    enc.wait()
    dec.wait()
    return last


def main():
    cfg = json.load(open(sys.argv[1]))
    tmp = os.path.join(HERE, "tmp")
    os.makedirs(tmp, exist_ok=True)
    rng = np.random.default_rng(7)
    segs = []
    last_frames = {}
    for i, s in enumerate(cfg["segments"]):
        if s.get("still_from"):
            png = os.path.join(tmp, f"still{i}.png")
            cv2.imwrite(png, last_frames[s["still_from"]])
            segs.append({"still": png, "dur": s["dur"], "zoom": s.get("zoom", 0.03)})
            continue
        out = os.path.join(tmp, f"g{i}.mp4")
        last = graded_clip(s, out, rng)
        last_frames[s.get("id", str(i))] = last
        segs.append({"path": out, "use": [0.0, s["use"][1] - s["use"][0]], "gain": s.get("gain", 1.0), "mute": s.get("mute", False)})
    total = sum(B.seg_len(s) for s in segs)
    run_cfg = {"segments": segs, "overlays": cfg["overlays"], "blur": cfg.get("blur", []), "sfx": cfg["sfx"], "out": cfg["out"]}
    base = B.video(run_cfg, tmp)
    # 음악을 효과음 목록에 넣기 위해 곡을 먼저 만든다
    mus = os.path.join(tmp, "music.wav")
    hcs_music.make(total, [tuple(x) for x in cfg["music"]["sections"]], mus, bpm=cfg["music"].get("bpm"))
    wav = audio_with_music(run_cfg, tmp, total, mus, cfg["music"].get("gain", 0.35))
    cmd = ["ffmpeg", "-y", "-i", base, "-i", wav]
    for o in run_cfg["overlays"]:
        cmd += ["-loop", "1", "-t", str(total), "-i", o["png"]]
    fc, last = [], "0:v"
    for k, (x, y, w, h, a, b) in enumerate(run_cfg.get("blur", [])):
        fc.append(f"[{last}]split[bb{k}][bs{k}];[bs{k}]crop={w}:{h}:{x}:{y},gblur=sigma=7,format=rgba[bc{k}];"
                  f"movie={HERE}/ov/blurmask.png,format=gray,scale={w}:{h}[bm{k}];[bc{k}][bm{k}]alphamerge[ba{k}];"
                  f"[bb{k}][ba{k}]overlay={x}:{y}:enable='between(t,{a},{b})'[bl{k}]")
        last = f"bl{k}"
    for k, o in enumerate(run_cfg["overlays"]):
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
    B.run(cmd)
    print("ok", cfg["out"], round(total, 2))


def audio_with_music(cfg, tmp, total, mus, mgain):
    """build_v5.audio와 같은 순서로 섞되, 정규화 전에 자체 제작 곡을 더한다."""
    import wave
    n = int(total * SR) + SR
    buf = np.zeros((n, 2))
    pos = 0.0
    for s in cfg["segments"]:
        d = B.seg_len(s)
        if not s.get("still") and not s.get("mute"):
            x = B.read_audio(s["path"], 0.0, d) * s.get("gain", 1.0)
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
            s = B.squish(rng)
        elif name == "room":
            s = B.room(rng, ev[3])
        else:
            s = B.sfx.FX[name](rng)
        s = s * g
        i = int(at * SR)
        m = min(len(s), n - i)
        buf[i:i + m, 0] += s[:m]
        buf[i:i + m, 1] += s[:m]
    with wave.open(mus) as w:
        ch, sr_m = w.getnchannels(), w.getframerate()
        m = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767
    m = m.reshape(-1, ch) if ch > 1 else np.stack([m, m], axis=1)
    if sr_m != SR:
        idx = (np.arange(int(len(m) * SR / sr_m)) * sr_m / SR).astype(int)
        m = m[np.clip(idx, 0, len(m) - 1)]
    k = min(len(buf), len(m))
    buf[:k] += m[:k] * mgain
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
    B.run(["ffmpeg", "-y", "-i", raw, "-af",
           f"loudnorm=I=-13.4:TP=-2.6:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
           f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,lowpass=f=16000,volume=0.3dB,alimiter=limit=0.6:attack=1:release=40:level=disabled", "-ar", str(SR), out])
    return out


if __name__ == "__main__":
    main()
