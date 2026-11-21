"""홍책사 짤 '엽전이 병뚜껑 격파' 편집(1080x1920, 30fps, 끝없이 반복되는 6초).
원본 생성 클립 raw.mp4(Veo 3.1 Lite 720p 6초, 시작과 끝 프레임이 같은 사진)를 프레임마다 확대, 흔들림, 글자로 과장한다.
"""
import math
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

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 44100
SRC = os.path.join(HERE, "raw.mp4")
DUR = 6.0
IMPACT = 2.0
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
YEL = (255, 214, 80, 255)


def font(path, size):
    for i in range(10):
        f = ImageFont.truetype(path, size, index=i)
        if "KR" in f.getname()[0]:
            return f
    return ImageFont.truetype(path, size)


def overlay_png(parts, y, size=66):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(FB, size)
    total = sum(d.textlength(s, font=f) for s, _ in parts)
    x = (W - total) / 2
    for s, col in parts:
        d.text((x, y), s, font=f, fill=col, stroke_width=7, stroke_fill=(0, 0, 0, 255))
        x += d.textlength(s, font=f)
    return np.array(im)


def ai_png():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t = "AI로 만든 가상 캐릭터"
    f = font(FR, 26)
    w = d.textlength(t, font=f)
    d.rounded_rectangle((26, 40, 26 + w + 28, 84), 12, fill=(0, 0, 0, 120))
    d.text((40, 46), t, font=f, fill=(255, 255, 255, 215))
    return np.array(im)


def brand_png():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1, f2 = font(FB, 54), font(FB, 34)
    for s, f, y, col in (("오늘의 운수", f1, 1600, (255, 255, 255, 255)), ("홍책사  hongchaksa.kr", f2, 1680, YEL)):
        w = d.textlength(s, font=f)
        d.text(((W - w) / 2, y), s, font=f, fill=col, stroke_width=6, stroke_fill=(0, 0, 0, 255))
    return np.array(im)


OV = [
    (0.0, 1.9, overlay_png([("엽전이 ", (255, 255, 255, 255)), ("병뚜껑 격파", YEL), (" 도전", (255, 255, 255, 255))], 150)),
    (2.45, 3.95, overlay_png([("병은 ", (255, 255, 255, 255)), ("멀쩡합니다", YEL)], 150)),
    (4.98, 6.1, brand_png()),
]
AI = ai_png()


def ease(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


def camera(t):
    """확대 배율, 중심(720x1280 원본 좌표), 흔들림(px)."""
    z, cx, cy, shake = 1.0, 360, 640, 0.0
    face = (300, 480)
    cat = (600, 600)
    if 1.95 <= t < 2.45:  # 부딪히는 순간 확 다가가며 흔들림
        k = ease((t - 1.95) / 0.08)
        z = 1.0 + 0.22 * k
        cx, cy = 360 + (face[0] - 360) * k * 0.5, 640 + (face[1] - 640) * k * 0.5
        shake = 16 * math.exp(-(t - 1.98) * 9) if t > 1.98 else 0
        if t >= 2.3:
            k2 = ease((t - 2.3) / 0.15)
            z = 1.22 + (1.45 - 1.22) * k2
            cx, cy = cx + (face[0] - cx) * k2, cy + (face[1] - cy) * k2
    elif 2.45 <= t < 3.9:  # 과장된 비명 얼굴 크게
        z, cx, cy = 1.45 + 0.04 * (t - 2.45), face[0], face[1]
        shake = 3 * math.sin(t * 60)
    elif 3.9 <= t < 4.25:
        k = ease((t - 3.9) / 0.35)
        z = 1.5 - 0.5 * k
        cx, cy = face[0] + (360 - face[0]) * k, face[1] + (640 - face[1]) * k
    elif 4.3 <= t < 4.98:  # 복채 하품
        k = ease((t - 4.3) / 0.12) * (1 - ease((t - 4.85) / 0.13))
        z = 1.0 + 0.55 * k
        cx, cy = 360 + (cat[0] - 360) * k, 640 + (cat[1] - 640) * k
    return z, cx, cy, shake


def blur_text(fr):
    # 왼쪽 위 벽 족자와 종이의 붓글씨 모양을 흐리게(원본 좌표)
    x0, y0, x1, y1 = 0, 0, 335, 360
    roi = fr[y0:y1, x0:x1]
    b = cv2.GaussianBlur(roi, (0, 0), 7)
    m = np.zeros(roi.shape[:2], np.float32)
    cv2.rectangle(m, (0, 0), (x1 - x0 - 25, y1 - y0 - 25), 1, -1)
    m = cv2.GaussianBlur(m, (0, 0), 12)[..., None]
    fr[y0:y1, x0:x1] = (roi * (1 - m) + b * m).astype(np.uint8)
    return fr


def render(out_video):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-vf", "fps=30", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, 1280, 720, 3)
    n = int(round(DUR * FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", out_video], stdin=subprocess.PIPE)
    rng = np.random.default_rng(5)
    for i in range(n):
        t = i / FPS
        fr = blur_text(frames[min(i, len(frames) - 1)].copy())
        z, cx, cy, sh = camera(t)
        cw, ch = 720 / z, 1280 / z
        x0 = min(max(cx - cw / 2, 0), 720 - cw) + sh * math.sin(t * 97)
        y0 = min(max(cy - ch / 2, 0), 1280 - ch) + sh * math.cos(t * 83)
        x0, y0 = min(max(x0, 0), 720 - cw), min(max(y0, 0), 1280 - ch)
        M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
        img = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
        # 같은 결의 입자
        img = np.clip(img.astype(np.float32) + rng.normal(0, 2.2, img.shape[:2])[..., None], 0, 255)
        rgba = [AI] + [o for a, b, o in OV if a <= t < b]
        for o in rgba:
            al = o[..., 3:4].astype(np.float32) / 255
            img = img * (1 - al) + o[..., [2, 1, 0]].astype(np.float32) * al
        enc.stdin.write(img.astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()


def audio(out_wav):
    n = int(DUR * SR)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)[:n]
    buf = np.zeros((n, 2))
    buf[: len(a)] += a * 1.0
    rng = np.random.default_rng(9)
    for at, name, g in ((1.0, "whoosh", 0.55), (IMPACT, "boom", 0.9), (IMPACT, "thunk", 0.7), (4.45, "pop", 0.35), (5.0, "logo", 0.45)):
        s = sfx.FX[name](rng) * g
        i = int(at * SR)
        m = min(len(s), n - i)
        buf[i:i + m, 0] += s[:m]
        buf[i:i + m, 1] += s[:m]
    mus = os.path.join(HERE, "music.wav")
    hcs_music.make(DUR, [(0, IMPACT - 0.45, "comedy", "F"), (IMPACT - 0.45, DUR, "stop", "F")], mus)
    with wave.open(mus) as w:
        ch = w.getnchannels()
        m = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767
        msr = w.getframerate()
    m = m.reshape(-1, ch) if ch > 1 else np.stack([m, m], axis=1)
    if msr != SR:
        idx = (np.arange(int(len(m) * SR / msr)) * msr / SR).astype(int)
        m = m[np.clip(idx, 0, len(m) - 1)]
    k = min(n, len(m))
    buf[:k] += m[:k] * 0.28
    fade = int(0.03 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    buf = np.tanh(buf / 0.95) * 0.95
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    v = os.path.join(HERE, "v.mp4")
    a = os.path.join(HERE, "a.wav")
    render(v)
    audio(a)
    print("ok")
