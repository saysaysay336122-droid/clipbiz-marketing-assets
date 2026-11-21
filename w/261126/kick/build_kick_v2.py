"""홍책사 짤 '엽전이 병뚜껑 격파' v2: 원본 릴스와 같은 박자(긴 자세, 발차기, 긴 비명, 원위치, 끝없는 반복).
확대, 흔들림, 화면 자막 없이 고정 카메라. 복채는 처음부터 끝까지 무표정(하품 구간은 첫 프레임 복채로 덮음).
raw60.mp4 = raw.mp4를 minterpolate 60fps로 늘린 것.
"""
import os
import subprocess
import sys
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music  # noqa: E402
import sfx  # noqa: E402
from build_kick import ai_png, blur_text, font, YEL  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 44100
SEGS = [(0.0, 0.8, 0.6), (0.8, 0.0, 0.6), (0.0, 1.95, 0.8), (1.95, 4.0, 0.75), (4.0, 6.0, 1.25)]
CAT_BOX = (505, 540, 690, 790)   # 원본 720x1280 좌표
CAT_T = (3.7, 5.95)


def seg_len(a, b, s):
    return abs(b - a) / s


TOTAL = sum(seg_len(*s) for s in SEGS)
T_KICK = seg_len(*SEGS[0]) + seg_len(*SEGS[1])
IMPACT = T_KICK + seg_len(*SEGS[2]) + (2.0 - 1.95) / 0.75


def raw_time(t):
    pos = 0.0
    for a, b, s in SEGS:
        d = seg_len(a, b, s)
        if t < pos + d or (a, b, s) == SEGS[-1]:
            u = min(max((t - pos) / d, 0), 1)
            return a + (b - a) * u
        pos += d


def tag_png():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 30)
    s = "홍책사"
    w = d.textlength(s, font=f)
    x = W - 40 - w - 28
    d.rounded_rectangle((x, 40, x + w + 28, 88), 12, fill=(15, 15, 20, 150))
    d.text((x + 14, 45), s, font=f, fill=YEL)
    return np.array(im)


def render(out):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "raw60.mp4"), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 1280, 720, 3)
    cat0 = fr[0].copy()
    x0, y0, x1, y1 = CAT_BOX
    m = np.zeros((1280, 720), np.float32)
    cv2.rectangle(m, (x0 + 22, y0 + 22), (x1 - 22, y1 - 22), 1, -1)
    m = cv2.GaussianBlur(m, (0, 0), 11)[..., None]
    ovs = [ai_png(), tag_png()]
    n = int(round(TOTAL * FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(5)
    for i in range(n):
        t = i / FPS
        rt = raw_time(t)
        k = min(int(round(rt * 60)), len(fr) - 1)
        f = fr[k].copy()
        # 복채 무표정 고정
        a = 0.0
        if CAT_T[0] - 0.15 <= rt <= CAT_T[1] + 0.15:
            a = min(1, (rt - (CAT_T[0] - 0.15)) / 0.15, (CAT_T[1] + 0.15 - rt) / 0.15)
        if a > 0:
            f = (f * (1 - m * a) + cat0 * (m * a)).astype(np.uint8)
        f = blur_text(f)
        img = cv2.resize(f, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        img = np.clip(img + rng.normal(0, 2.2, img.shape[:2])[..., None], 0, 255)
        for o in ovs:
            al = o[..., 3:4].astype(np.float32) / 255
            img = img * (1 - al) + o[..., [2, 1, 0]].astype(np.float32) * al
        enc.stdin.write(img.astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()


def stretch(a, b, speed):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(min(a, b)), "-t", str(abs(b - a)), "-i", os.path.join(HERE, "raw.mp4"),
                          "-af", f"atempo={speed}", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def audio(out):
    n = int(TOTAL * SR)
    buf = np.zeros((n, 2))
    pos = 0.0
    for idx, (a, b, s) in enumerate(SEGS):
        d = seg_len(a, b, s)
        if idx >= 2:
            x = stretch(a, b, s)[: int(d * SR)]
            i = int(pos * SR)
            buf[i:i + len(x)] += x
        pos += d
    rng = np.random.default_rng(9)
    for at, name, g in ((T_KICK + 1.0 / 0.8, "whoosh", 0.6), (IMPACT, "boom", 0.95), (IMPACT, "thunk", 0.8)):
        s = sfx.FX[name](rng) * g
        i = int(at * SR)
        mm = min(len(s), n - i)
        buf[i:i + mm, 0] += s[:mm]
        buf[i:i + mm, 1] += s[:mm]
    mus = os.path.join(HERE, "music_v2.wav")
    hcs_music.make(TOTAL, [(0, IMPACT - 0.45, "anthem", "Cm"), (IMPACT - 0.45, TOTAL, "stop", "Cm")], mus, bpm=72, room=0.22)
    with wave.open(mus) as w:
        ch, msr = w.getnchannels(), w.getframerate()
        mu = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767
    mu = mu.reshape(-1, ch) if ch > 1 else np.stack([mu, mu], axis=1)
    if msr != SR:
        idx = (np.arange(int(len(mu) * SR / msr)) * msr / SR).astype(int)
        mu = mu[np.clip(idx, 0, len(mu) - 1)]
    k = min(n, len(mu))
    ramp = np.clip(np.arange(k) / (SR * 3.0), 0.35, 1.0)[:, None]  # 처음엔 작게 시작해 커지는 비장한 빌드업
    buf[:k] += mu[:k] * 0.45 * ramp
    fade = int(0.03 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    buf = np.tanh(buf / 0.95) * 0.95
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    print("total", round(TOTAL, 2), "impact", round(IMPACT, 2))
    render(os.path.join(HERE, "v2.mp4"))
    audio(os.path.join(HERE, "a2.wav"))
    print("ok")
