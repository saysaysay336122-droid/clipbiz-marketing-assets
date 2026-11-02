"""skia로 한 장씩 그리고 ffmpeg로 바로 넘기는 공통 도구. 화면 1080x1920, 30fps.

글꼴: Noto Sans CJK KR(Black, Bold, Medium), Noto Serif CJK KR(Black)
카메라: 펀치 줌, 흔들림, 번쩍임, 색 갈라짐(글리치)
"""
import math
import subprocess

import numpy as np
import skia

W, H, FPS = 1080, 1920, 30
_FONTS = {}
_PATHS = {
    "black": ("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", 1),
    "bold": ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 1),
    "medium": ("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", 1),
    "regular": ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 1),
    "serif": ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc", 1),
}


def font(kind, size):
    key = (kind, size)
    if key not in _FONTS:
        path, idx = _PATHS[kind]
        tf = skia.Typeface.MakeFromFile(path, idx)
        f = skia.Font(tf, size)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        _FONTS[key] = f
    return _FONTS[key]


def col(hexs, a=1.0):
    hexs = hexs.lstrip("#")
    r, g, b = int(hexs[0:2], 16), int(hexs[2:4], 16), int(hexs[4:6], 16)
    return skia.Color(r, g, b, int(max(0, min(1, a)) * 255))


def paint(color, a=1.0, stroke=0, aa=True, blur=0):
    p = skia.Paint(AntiAlias=aa, Color=col(color, a) if isinstance(color, str) else color)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeJoin(skia.Paint.kRound_Join)
        p.setStrokeCap(skia.Paint.kRound_Cap)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def text_w(s, f):
    return f.measureText(s)


def text(c, s, x, y, f, color="#FFFFFF", a=1.0, align="center", stroke=0, stroke_color="#000000", shadow=0):
    """y는 글자 기준선. stroke가 있으면 테두리를 먼저 그린다."""
    w = f.measureText(s)
    if align == "center":
        x0 = x - w / 2
    elif align == "right":
        x0 = x - w
    else:
        x0 = x
    blob = skia.TextBlob.MakeFromString(s, f)
    if shadow:
        c.drawTextBlob(blob, x0, y + shadow * 0.6, paint("#000000", 0.45 * a, blur=shadow))
    if stroke:
        c.drawTextBlob(blob, x0, y, paint(stroke_color, a, stroke=stroke))
    c.drawTextBlob(blob, x0, y, paint(color, a))
    return w


def wrap(s, f, maxw):
    """한국어 어절 단위 줄바꿈. 어절 하나가 넘치면 그대로 둔다."""
    lines, cur = [], ""
    for word in s.split(" "):
        trial = (cur + " " + word).strip()
        if f.measureText(trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def rrect(c, x, y, w, h, r, color, a=1.0, stroke=0):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(color, a, stroke=stroke))


def ease_out_back(k, s=1.70158):
    k = min(1, max(0, k)) - 1
    return k * k * ((s + 1) * k + s) + 1


def ease_out(k):
    k = min(1, max(0, k))
    return 1 - (1 - k) ** 3


def ease_in_out(k):
    k = min(1, max(0, k))
    return 3 * k * k - 2 * k * k * k


class Camera:
    """punch(시각, 세기), shake(시각, 길이, 세기)를 모아 두고 프레임마다 변환을 계산한다."""

    def __init__(self, seed=1):
        self.punches, self.shakes, self.flashes, self.glitches, self.zooms = [], [], [], [], []
        self.rng = np.random.default_rng(seed)

    def punch(self, t, amt=0.08, dur=0.35):
        self.punches.append((t, amt, dur))

    def shake(self, t, dur=0.4, amp=22):
        self.shakes.append((t, dur, amp))

    def flash(self, t, dur=0.18, color="#FFFFFF", a=0.85):
        self.flashes.append((t, dur, color, a))

    def glitch(self, t, dur=0.25):
        self.glitches.append((t, dur))

    def zoom(self, t0, t1, z0, z1, cx=W / 2, cy=H / 2):
        self.zooms.append((t0, t1, z0, z1, cx, cy))

    def transform(self, t):
        z, cx, cy = 1.0, W / 2, H / 2
        for t0, t1, z0, z1, zx, zy in self.zooms:
            if t >= t0:
                k = ease_in_out((t - t0) / max(1e-3, t1 - t0))
                z, cx, cy = z0 + (z1 - z0) * k, zx, zy
        for t0, amt, dur in self.punches:
            if t0 <= t < t0 + dur:
                k = (t - t0) / dur
                z *= 1 + amt * (1 - k) ** 2
        dx = dy = rot = 0.0
        for t0, dur, amp in self.shakes:
            if t0 <= t < t0 + dur:
                k = 1 - (t - t0) / dur
                ph = (t - t0) * 60
                dx += math.sin(ph * 1.7) * amp * k
                dy += math.cos(ph * 2.3) * amp * k
                rot += math.sin(ph * 1.1) * 1.2 * k
        return z, cx, cy, dx, dy, rot

    def apply(self, c, t):
        z, cx, cy, dx, dy, rot = self.transform(t)
        c.translate(cx + dx, cy + dy)
        c.rotate(rot)
        c.scale(z, z)
        c.translate(-cx, -cy)

    def overlay(self, c, t):
        for t0, dur, color, a in self.flashes:
            if t0 <= t < t0 + dur:
                k = 1 - (t - t0) / dur
                c.drawRect(skia.Rect.MakeWH(W, H), paint(color, a * k))

    def glitch_amt(self, t):
        for t0, dur in self.glitches:
            if t0 <= t < t0 + dur:
                return 1 - (t - t0) / dur
        return 0.0


def rgb_split(arr, amt, rng):
    """글리치: 빨강과 파랑 채널을 옆으로 밀고 몇 줄을 어긋나게."""
    if amt <= 0:
        return arr
    out = arr.copy()
    s = int(12 * amt) + 2
    out[:, s:, 0] = arr[:, :-s, 0]
    out[:, :-s, 2] = arr[:, s:, 2]
    for _ in range(int(6 * amt) + 1):
        y = int(rng.integers(0, H - 80))
        h = int(rng.integers(10, 70))
        sh = int(rng.integers(-60, 60) * amt)
        out[y:y + h] = np.roll(out[y:y + h], sh, axis=1)
    return out


class Writer:
    """ffmpeg로 RGBA 프레임을 넘겨 H.264로 저장한다."""

    def __init__(self, path, fps=FPS):
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps),
             "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(path)],
            stdin=subprocess.PIPE)

    def put(self, arr):
        self.p.stdin.write(np.ascontiguousarray(arr).tobytes())

    def close(self):
        self.p.stdin.close()
        return self.p.wait()


def surface():
    return skia.Surface(W, H)


def snapshot(surf):
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def mux(video, audio, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)


def vignette(c, strength=0.55):
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial(
        skia.Point(W / 2, H / 2), H * 0.75,
        [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, int(255 * strength))], [0.55, 1.0]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)


def radial_bg(c, inner, outer, cx=W / 2, cy=H * 0.45, r=H * 0.8):
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(cx, cy), r, [col(inner), col(outer)], [0.0, 1.0]))
    c.drawRect(skia.Rect.MakeWH(W, H), p)
