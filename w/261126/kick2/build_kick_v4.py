"""홍책사 짤 '엽전이 병뚜껑 격파' v4: 원본(seo__bam) 구도를 따라 옆에서 본 화면, 왼쪽 소반과 병, 오른쪽 엽전이.
구글 플로우에서 열쇠 장면 4장(자세 KA, 발차기 KB, 공중 비명 KC, 착지 KD)을 만들고
Omni 1.2 Flash 프레임 방식으로 네 샷(KA-KB, KB-KC, KC-KD, KD-KA)을 이어 끝없이 반복되게 했다.
원본 영상 파일은 생성에 쓰지 않았다.
"""
import os
import subprocess
import sys
import wave

import cv2
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/w/261126/kick")
import hcs_music  # noqa: E402
import sfx  # noqa: E402
from build_kick import ai_png  # noqa: E402
from build_kick_v2 import tag_png  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FL = os.path.join(HERE, "flow")
W, H, FPS, SR = 1080, 1920, 30, 44100
# (이름, 클립, 시작, 끝, 출력 길이)
SEGS = [
    ("stance", "s1b", 0.00, 2.50, 2.08),
    ("windup", "s1b", 2.50, 3.50, 1.00),
    ("kick", "s1b", 3.50, 5.00, 1.67),
    ("scream1", "s2a", 0.00, 3.00, 2.61),
    ("scream2", "s3a", 0.00, 1.80, 1.50),
    ("land", "s3a", 1.80, 3.00, 1.20),
    ("back", "s4", 1.30, 3.00, 1.21),
]
DISSOLVE = {"back": 4}


def seg_frames(k, name, clip, a, b, d):
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
    return fr[np.clip(np.arange(n), 0, len(fr) - 1)]


def timeline():
    t, marks = 0.0, {}
    for name, clip, a, b, d in SEGS:
        t -= DISSOLVE.get(name, 0) / FPS
        marks[name] = t
        t += d
    return marks, t


BLUR_MASK = None


def blur_text(fr):
    """벽 족자와 종이의 붓글씨 모양을 흐리게(720x1280 좌표)."""
    global BLUR_MASK
    x1, y1 = 300, 600
    if BLUR_MASK is None:
        m = np.zeros((y1, x1), np.float32)
        cv2.rectangle(m, (0, 0), (x1 - 40, y1 - 40), 1, -1)
        BLUR_MASK = cv2.GaussianBlur(m, (0, 0), 16)[..., None]
    roi = fr[:y1, :x1]
    b = cv2.GaussianBlur(roi, (0, 0), 6)
    fr[:y1, :x1] = (roi * (1 - BLUR_MASK) + b * BLUR_MASK).astype(np.uint8)
    return fr


def render(out):
    frames = []
    for k, (name, clip, a, b, d) in enumerate(SEGS):
        f = seg_frames(k, name, clip, a, b, d)
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
        img = np.clip(img + rng.normal(0, 1.8, img.shape[:2])[..., None], 0, 255)
        for o in ovs:
            al = o[..., 3:4].astype(np.float32) / 255
            img = img * (1 - al) + o[..., [2, 1, 0]].astype(np.float32) * al
        enc.stdin.write(img.astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    return len(frames) / FPS


def clip_audio(path, a, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a}", "-t", f"{dur}", "-i", path,
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def stretch(x, rate):
    """재생 속도를 rate배로(1보다 작으면 길고 낮게)."""
    n = int(len(x) / rate)
    src = np.arange(n) * rate
    return np.stack([np.interp(src, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)


def env(n, fi=0.04, fo=0.3):
    e = np.ones(n)
    a, b = int(fi * SR), int(fo * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-b:] = np.linspace(1, 0, b)
    return e[:, None]


def put(buf, at, s, g=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    m = min(len(s), len(buf) - i)
    if s.ndim == 1:
        s = np.stack([s, s], axis=1)
    buf[i:i + m] += s[:m] * g


def norm(x):
    return x / (np.abs(x).max() or 1)


def audio(out, total, marks):
    n = int(total * SR)
    buf = np.zeros((n, 2))
    rng = np.random.default_rng(9)
    t_kick, t_hit, t_land = marks["kick"], marks["scream1"], marks["land"]
    # 음악: 비장한 행진이 발차기까지 커지다 발이 소반에 닿기 0.45초 전에 끊김
    mus = os.path.join(HERE, "music_v4.wav")
    hcs_music.make(total, [(0, t_hit - 0.45, "anthem", "Cm"), (t_hit - 0.45, total, "stop", "Cm")], mus, bpm=72, room=0.22)
    with wave.open(mus) as w:
        ch = w.getnchannels()
        mu = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767
    mu = mu.reshape(-1, ch) if ch > 1 else np.stack([mu, mu], axis=1)
    k = min(n, len(mu))
    ramp = np.clip(np.arange(k) / (SR * 2.2), 0.75, 1.0)[:, None]
    buf[:k] += mu[:k] * 0.95 * ramp
    # 날아 차는 바람 소리, 기합(클립 소리 그대로), 소반 모서리에 쾅
    put(buf, t_kick + 0.25, sfx.FX["whoosh"](rng), 0.8)
    kiai = clip_audio(os.path.join(FL, "s1b.mp4"), 3.55, 1.40)
    kiai = stretch(kiai, 0.9)
    put(buf, t_kick + 0.05, norm(kiai) * env(len(kiai)), 0.45)
    put(buf, t_hit - 0.02, sfx.FX["thunk"](rng), 1.0)
    put(buf, t_hit - 0.02, sfx.FX["boom"](rng), 0.5)
    # 공중 비명: 클립의 비명을 느리고 낮게 늘려 하이라이트 내내
    sc1 = clip_audio(os.path.join(FL, "s2a.mp4"), 1.0, 2.0)
    sc2 = clip_audio(os.path.join(FL, "s3a.mp4"), 0.0, 1.6)
    xf = int(0.08 * SR)
    sc = np.concatenate([sc1[:-xf], sc1[-xf:] * np.linspace(1, 0, xf)[:, None] + sc2[:xf] * np.linspace(0, 1, xf)[:, None], sc2[xf:]])
    scream = stretch(sc, 0.8)
    scream = norm(scream) * env(len(scream), 0.05, 0.5)
    put(buf, t_hit + 0.15, scream, 0.7)
    # 착지 쿵과 낑
    put(buf, t_land + 0.25, sfx.FX["thunk"](rng), 0.8)
    whim = clip_audio(os.path.join(FL, "s3a.mp4"), 2.6, 0.6)
    put(buf, t_land + 0.45, norm(whim) * env(len(whim), 0.02, 0.2), 0.3)
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
    real = render(os.path.join(HERE, "v4.mp4"))
    print("video", round(real, 2))
    audio(os.path.join(HERE, "a4.wav"), real, marks)
    print("ok")
