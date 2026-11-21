"""홍책사 짤 '엽전이 병뚜껑 격파' v5: 소반 대신 화강암 돌덩이. 진지한 자세, 웅장한 음악으로 병뚜껑 격파를 기대하게 만든 뒤
발이 돌덩이 옆면에 쾅, 음악이 끊기고 화면이 멈칫, 공중에서 긴 비명, 바닥에 떨어져 뒹굴며 아파하다 아무 일 없던 듯 다시 자세.
구글 플로우: 열쇠 장면 4장(나노 바나나 2.1 이미지 수정, 2K)과 Omni 1.2 Flash 프레임 방식 네 샷(1080p 업스케일).
"""
import math
import os
import subprocess
import sys
import wave

import cv2
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/w/261126/kick")
import hcs_music as hm  # noqa: E402
import sfx  # noqa: E402
from build_kick import ai_png  # noqa: E402
from build_kick_v2 import tag_png  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FL = os.path.join(HERE, "flow")
W, H, FPS = 1080, 1920, 30
SR = hm.SR  # 48000
# (이름, 클립, 시작, 끝, 출력 길이). freeze는 클립의 한 프레임을 멈춰 보여 준다.
SEGS = [
    ("stance", "s1", 0.00, 1.45, 2.20),
    ("windup", "s1", 1.45, 2.45, 1.25),
    ("kick", "s1", 2.45, 2.70, 0.45),
    ("freeze", "s1", 2.70, 2.70, 0.40),
    ("shock", "s1", 2.70, 4.95, 1.50),
    ("scream", "s2", 0.00, 3.00, 3.00),
    ("roll", "s3", 0.00, 3.92, 3.92),
    ("recover", "s4", 0.00, 3.00, 1.80),
]
SEAM = 5  # 끝 프레임을 첫 프레임으로 녹이는 수


def seg_frames(k, name, clip, a, b, d):
    src = os.path.join(FL, clip + ".mp4")
    n = int(round(d * FPS))
    if b <= a:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-i", src, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                             capture_output=True, check=True).stdout
        f = np.frombuffer(raw, np.uint8).reshape(1, H, W, 3)
        return np.repeat(f, n, axis=0)
    sp = d / (b - a)
    vf = f"setpts={sp:.5f}*(PTS-STARTPTS)"
    if sp > 1.05:
        vf += ",minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    vf += ",fps=30"
    out = os.path.join(FL, f"seg{k}_{name}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", src, "-vf", vf, "-an",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", out], check=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return fr[np.clip(np.arange(n), 0, len(fr) - 1)]


def timeline():
    t, marks = 0.0, {}
    for name, clip, a, b, d in SEGS:
        marks[name] = t
        t += d
    return marks, t


MARKS, TOTAL = timeline()


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def camera(t):
    """확대 배율과 흔들림. 자세에서 발차기까지 천천히 다가가고, 부딪히는 순간 살짝 당겨 흔든 뒤 원래대로."""
    ti = MARKS["freeze"]
    if t < ti:
        z = 1.0 + 0.06 * ease(t / ti)
        sh = 0.0
    elif t < MARKS["shock"] + 0.6:
        u = t - ti
        z = 1.06 + 0.04 * math.exp(-u * 6)
        sh = 16 * math.exp(-u * 9)
    else:
        u = (t - (MARKS["shock"] + 0.6)) / 1.2
        z = 1.06 - 0.06 * ease(u) + 0.04 * math.exp(-(t - ti) * 6)
        sh = 0.0
    return z, sh


BLUR_MASK = None


def blur_text(fr):
    """벽 족자와 종이의 붓글씨 모양을 흐리게."""
    global BLUR_MASK
    x1, y1 = 470, 880
    if BLUR_MASK is None:
        m = np.zeros((y1, x1), np.float32)
        cv2.rectangle(m, (0, 0), (x1 - 60, y1 - 60), 1, -1)
        BLUR_MASK = cv2.GaussianBlur(m, (0, 0), 24)[..., None]
    roi = fr[:y1, :x1]
    b = cv2.GaussianBlur(roi, (0, 0), 9)
    fr[:y1, :x1] = (roi * (1 - BLUR_MASK) + b * BLUR_MASK).astype(np.uint8)
    return fr


def render(out):
    frames = []
    for k, seg in enumerate(SEGS):
        frames.extend(list(seg_frames(k, *seg)))
    first = frames[0].astype(np.float32)
    for j in range(SEAM):
        al = (j + 1) / (SEAM + 1)
        idx = len(frames) - SEAM + j
        frames[idx] = (frames[idx] * (1 - al) + first * al).astype(np.uint8)
    ovs = [ai_png(), tag_png()]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(5)
    cx, cy = W * 0.40, H * 0.55  # 돌덩이와 엽전이 사이
    for i, f in enumerate(frames):
        t = i / FPS
        f = blur_text(f.copy())
        z, sh = camera(t)
        dx = sh * math.sin(t * 91) if sh else 0.0
        dy = sh * math.cos(t * 77) if sh else 0.0
        M = np.array([[z, 0, cx - z * cx + dx], [0, z, cy - z * cy + dy]], np.float32)
        img = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        img = np.clip(img + rng.normal(0, 1.6, img.shape[:2])[..., None], 0, 255)
        for o in ovs:
            al = o[..., 3:4].astype(np.float32) / 255
            img = img * (1 - al) + o[..., [2, 1, 0]].astype(np.float32) * al
        enc.stdin.write(img.astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    return len(frames) / FPS


# ---------------------------------------------------------------- 소리
def put(buf, at, s, g=1.0):
    i = int(round(at * SR))
    if i >= len(buf) or i < 0:
        return
    if s.ndim == 1:
        s = np.stack([s, s], axis=1)
    m = min(len(s), len(buf) - i)
    buf[i:i + m] += s[:m] * g


def fx(name, rng):
    x = sfx.FX[name](rng)
    n = int(len(x) * SR / sfx.SR)
    return np.interp(np.arange(n) * sfx.SR / SR, np.arange(len(x)), x)


def clip_audio(clip, a, dur, rate=1.0):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a}", "-t", f"{dur}", "-i", os.path.join(FL, clip + ".mp4"),
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    if rate != 1.0:
        n = int(len(x) / rate)
        src = np.arange(n) * rate
        x = np.stack([np.interp(src, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)
    return x


def fade(x, fi=0.03, fo=0.15):
    e = np.ones(len(x))
    a, b = min(len(x), int(fi * SR)), min(len(x), int(fo * SR))
    e[:a] = np.linspace(0, 1, a)
    if b:
        e[-b:] = np.minimum(e[-b:], np.linspace(1, 0, b))
    return x * e[:, None] if x.ndim == 2 else x * e


def stone_hit(rng):
    """돌덩이에 발이 쾅: 낮고 둔한 울림과 짧은 퍽."""
    t = np.arange(int(0.6 * SR)) / SR
    f = 62 * (1 + 0.6 * np.exp(-t * 30))
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    knock = hm.lp(rng.standard_normal(len(t)), SR / 900) * np.exp(-t * 45) * 2.2
    return np.tanh((body + knock) * 1.6) * 0.8


def sad_trombone(start_m=55):
    """뒹구는 동안 내려가는 네 음, 마지막 음은 길게 떨린다(자체 합성)."""
    notes = [(start_m, 0.42), (start_m - 1, 0.42), (start_m - 2, 0.42), (start_m - 3, 1.3)]
    out = []
    for k, (m, d) in enumerate(notes):
        t = np.arange(int(d * SR)) / SR
        f0 = hm.hz(m)
        vib = 1 + (0.025 * np.sin(2 * math.pi * 6.5 * t) * np.clip(t / 0.25, 0, 1) if k == 3 else 0.004 * np.sin(2 * math.pi * 5 * t))
        ph = 2 * math.pi * np.cumsum(f0 * vib) / SR
        x = sum((1 / h) * np.sin(h * ph) for h in range(1, 9))
        x = hm.lp(x, SR / 1300)
        e = np.minimum(1, t / 0.05) * np.clip((d - t) / 0.12, 0, 1)
        if k == 3:
            e *= np.clip((d - t) / 0.6, 0, 1)
        out.append(x * e)
    y = np.concatenate(out)
    return y / (np.abs(y).max() or 1)


def epic_score(buf, t_end):
    """C단조 웅장한 빌드업: 금관 화음, 팀파니, 북, 현악 패드, 끝 1.4초 스네어 롤과 상승음. t_end에서 칼같이 끊는다."""
    rng = np.random.default_rng(3)
    beat = 60 / 80
    prog = [(0.0, [48, 51, 55], 36), (beat * 2, [44, 48, 51], 32), (beat * 3, [46, 50, 53], 34), (beat * 4, [43, 47, 50], 31)]
    put(buf, 0.0, hm.crash(0.55))
    put(buf, 0.0, hm.taiko(0.9))
    for k, (at, ch, root) in enumerate(prog):
        if at >= t_end:
            break
        nxt = prog[k + 1][0] if k + 1 < len(prog) else t_end
        dur = max(0.3, nxt - at + 0.15)
        put(buf, at, hm.brass([m + 12 for m in ch] + [ch[0]], dur, 0.65 + 0.08 * k))
        put(buf, at, hm.pad([m + 24 for m in ch], dur + 0.3, 0.32))
        put(buf, at, hm.timpani(root, 0.75 + 0.05 * k))
        put(buf, at, hm.bass(root, dur * 0.9, 0.55))
    for s in np.arange(beat, t_end - 1.4, beat):
        put(buf, s, hm.timpani(36, 0.45))
    for s in np.arange(beat * 2, t_end, beat * 2):
        put(buf, s, hm.taiko(0.7))
    roll_start = t_end - 1.4
    t = roll_start
    while t < t_end:
        u = (t - roll_start) / 1.4
        put(buf, t, hm.snare(0.25 + 0.55 * u))
        t += 0.11 - 0.06 * u
    r = fx("riser", rng)
    put(buf, t_end - len(r) / SR, r * 0.7)
    i = int(t_end * SR)
    f = int(0.012 * SR)
    buf[i - f:i] *= np.linspace(1, 0, f)[:, None]
    buf[i:] = 0


def audio(out, total):
    n = int(total * SR)
    buf = np.zeros((n + SR * 3, 2))
    rng = np.random.default_rng(9)
    ti = MARKS["freeze"]
    t_cut = ti - 0.35
    mus = np.zeros_like(buf)
    epic_score(mus, t_cut)
    buf += mus * 0.9
    # 뛰어오르는 기합(클립 소리, 영상과 같은 속도)
    k = clip_audio("s1", 1.45, 1.25, rate=1.0 / 1.4)
    put(buf, MARKS["windup"], fade(k, 0.05, 0.3), 0.35)
    put(buf, MARKS["kick"] - 0.05, fx("whoosh", rng), 0.9)
    # 쾅: 정적 속에 돌덩이 소리
    put(buf, ti, stone_hit(rng), 1.0)
    put(buf, ti, fx("thunk", rng), 0.9)
    put(buf, ti + 0.01, fx("boom", rng), 0.45)
    # 멈칫 뒤부터 끊이지 않는 비명: 클립 속 비명들을 이어 붙이고 느리게 늘려 아픔을 길게
    a1 = clip_audio("s1", 2.70, 2.05)
    put(buf, MARKS["shock"], fade(a1, 0.02, 0.12), 0.7)
    a2 = clip_audio("s2", 1.30, 1.0, rate=0.8)
    put(buf, MARKS["shock"] + 2.0, fade(a2, 0.06, 0.12), 0.8)
    a3 = clip_audio("s3", 2.90, 0.8, rate=0.7)
    put(buf, MARKS["shock"] + 3.15, fade(a3, 0.06, 0.12), 0.7)
    r0 = MARKS["roll"]
    a4 = clip_audio("s3", 0.20, 1.2, rate=0.8)
    put(buf, r0 - 0.25, fade(a4, 0.06, 0.12), 0.7)
    a6 = clip_audio("s2", 1.30, 0.7, rate=0.75)
    put(buf, r0 + 1.2, fade(a6, 0.06, 0.2), 0.55)
    a5 = clip_audio("s3", 2.20, 1.6)
    put(buf, r0 + 2.2, fade(a5, 0.02, 0.2), 0.75)
    put(buf, r0 + 2.3, fx("thunk", rng), 0.5)
    # 떨어져 뒹굴 때 슬픈 트롬본
    tb = sad_trombone()
    put(buf, MARKS["roll"] + 1.7, tb * 0.32)
    # 다시 자세: 휙, 그리고 다음 바퀴의 웅장한 시작으로 넘어가는 팀파니 롤
    put(buf, MARKS["recover"] + 0.25, fx("whoosh", rng), 0.5)
    t = total - 0.9
    while t < total - 0.03:
        u = (t - (total - 0.9)) / 0.9
        put(buf, t, hm.timpani(36, 0.15 + 0.35 * u))
        t += 0.07
    buf = buf[:n]
    fo = int(0.02 * SR)
    buf[-fo:] *= np.linspace(1, 0.3, fo)[:, None]
    buf = np.tanh(buf / 0.9) * 0.9
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    print({k: round(v, 2) for k, v in MARKS.items()}, "total", round(TOTAL, 2))
    if "audio" not in sys.argv:
        real = render(os.path.join(HERE, "v5.mp4"))
        print("video", round(real, 2))
    audio(os.path.join(HERE, "a5.wav"), TOTAL)
    print("ok")
