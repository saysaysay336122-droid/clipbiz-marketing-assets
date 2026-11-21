"""홍책사 짤 '엽전이 병뚜껑 격파' v3: Veo 3.1 Quality 클립(구글 플로우)으로 원본 릴스 박자를 그대로 따른다.
진지한 자세 2.6초, 준비 1.3초, 발차기 0.9초(빗나감), 공중 비명 슬로 2.7초, 착지 0.9초, 원위치 0.5초, 끝없이 반복.
flow/a3.mp4 = 시작 k1에서 끝 k2(공중 비명), flow/b1.mp4 = 시작 k2에서 끝 k1(착지와 원위치).
"""
import os
import subprocess
import sys
import wave

import cv2
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music  # noqa: E402
import sfx  # noqa: E402
from build_kick import ai_png, blur_text  # noqa: E402
from build_kick_v2 import tag_png  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FL = os.path.join(HERE, "flow")
W, H, FPS, SR = 1080, 1920, 30, 44100
# (이름, 클립, 시작, 끝, 출력 길이)
SEGS = [
    ("stance", "a3", 0.00, 2.60, 2.60),
    ("windup", "a3", 2.60, 3.55, 1.30),
    ("kick", "a3", 3.55, 3.97, 0.90),
    ("scream1", "a3", 7.35, 7.92, 1.60),
    ("scream2", "b1", 0.04, 0.45, 1.10),
    ("land", "b1", 0.45, 1.40, 0.90),
    ("back", "b1", 5.60, 6.40, 0.50),
    ("seam", "a3", 0.00, 0.125, 0.27),
]
DISSOLVE = {"back": 4, "seam": 6}  # 앞 구간과 몇 프레임 겹쳐 녹일지


def seg_file(k, name, clip, a, b, d):
    out = os.path.join(FL, f"seg{k}_{name}.mp4")
    sp = d / (b - a)
    vf = f"setpts={sp:.5f}*(PTS-STARTPTS)"
    if sp > 0.95:
        vf += ",minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    vf += ",fps=30"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", os.path.join(FL, clip + ".mp4"),
                    "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", out], check=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 1280, 720, 3)
    n = int(round(d * FPS))
    idx = np.clip(np.arange(n), 0, len(fr) - 1)
    return fr[idx]


def timeline():
    t, marks = 0.0, {}
    for name, clip, a, b, d in SEGS:
        marks[name] = t
        t += d - DISSOLVE.get(name, 0) / FPS
    return marks, t


def render(out):
    frames = []
    for k, (name, clip, a, b, d) in enumerate(SEGS):
        f = seg_file(k, name, clip, a, b, d)
        nd = DISSOLVE.get(name, 0)
        if nd and frames:
            for j in range(nd):
                al = (j + 1) / (nd + 1)
                frames[-nd + j] = (frames[-nd + j] * (1 - al) + f[j] * al).astype(np.uint8)
            f = f[nd:]
        frames.extend(list(f))
    ovs = [ai_png(), tag_png()]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(5)
    for f in frames:
        f = blur_text(f.copy())
        img = cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        img = np.clip(img + rng.normal(0, 2.0, img.shape[:2])[..., None], 0, 255)
        for o in ovs:
            al = o[..., 3:4].astype(np.float32) / 255
            img = img * (1 - al) + o[..., [2, 1, 0]].astype(np.float32) * al
        enc.stdin.write(img.astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    return len(frames) / FPS


def clip_audio(clip, a, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a}", "-t", f"{dur}", "-i", os.path.join(FL, clip + ".mp4"),
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def slowmo_voice(x, rate):
    """느린 화면 속 목소리: 재생 속도를 낮춰 길고 낮게 늘인다."""
    n = int(len(x) / rate)
    src = np.arange(n) * rate
    out = np.stack([np.interp(src, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)
    return out


def put(buf, at, s, g=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    m = min(len(s), len(buf) - i)
    if s.ndim == 1:
        s = np.stack([s, s], axis=1)
    buf[i:i + m] += s[:m] * g


def audio(out, total, marks):
    n = int(total * SR)
    buf = np.zeros((n, 2))
    rng = np.random.default_rng(9)
    t_kick = marks["kick"]
    t_scr = marks["scream1"]
    t_land = marks["land"]
    # 음악: 비장한 행진이 발차기 직전까지, 비명 0.45초 전에 끊고 정적
    mus = os.path.join(HERE, "music_v3.wav")
    hcs_music.make(total, [(0, t_scr - 0.45, "anthem", "Cm"), (t_scr - 0.45, total, "stop", "Cm")], mus, bpm=72, room=0.22)
    with wave.open(mus) as w:
        ch, msr = w.getnchannels(), w.getframerate()
        mu = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767
    mu = mu.reshape(-1, ch) if ch > 1 else np.stack([mu, mu], axis=1)
    k = min(n, len(mu))
    ramp = np.clip(np.arange(k) / (SR * 2.6), 0.75, 1.0)[:, None]
    buf[:k] += mu[:k] * 0.95 * ramp
    # 발차기 바람 소리
    put(buf, t_kick + 0.05, sfx.FX["whoosh"](rng), 0.75)
    # 공중 비명: 클립의 비명 소리를 절반 속도로 늘려 길고 낮게
    v = clip_audio("a3", 4.70, 1.40)
    v = slowmo_voice(v, 0.52)
    v /= (np.abs(v).max() or 1)
    e = np.ones(len(v))
    fi, fo = int(0.06 * SR), int(0.5 * SR)
    e[:fi] = np.linspace(0, 1, fi)
    e[-fo:] = np.linspace(1, 0, fo)
    put(buf, t_scr + 0.02, v * e[:, None], 0.6)
    # 착지 쿵, 짧은 낑
    put(buf, t_land + 0.18, sfx.FX["thunk"](rng), 0.9)
    w2 = clip_audio("b1", 1.0, 0.5)
    w2 /= (np.abs(w2).max() or 1)
    put(buf, t_land + 0.35, w2, 0.35)
    fade = int(0.03 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    buf = np.tanh(buf / 0.95) * 0.95
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    marks, total = timeline()
    print({k: round(v, 2) for k, v in marks.items()}, "total", round(total, 2))
    real = render(os.path.join(HERE, "v3.mp4"))
    print("video", round(real, 2))
    audio(os.path.join(HERE, "a3.wav"), real, marks)
    print("ok")
