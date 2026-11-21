"""v6 화면 일치 보정. 클립마다 다른 색과 대비를 S2(따뜻한 오후 빛) 쪽으로 맞추고, 모든 컷에 같은 마감(곡선, 비네트, 입자)을 얹는다."""
import cv2
import numpy as np

PER = {  # 클립별 보정: Lab a, b 이동, 검은점, 흰점, 감마, 채도
    "S1": dict(da=1.5, db=5.0, black=6, white=250, gamma=1.0, sat=1.10),
    "S2": dict(da=0.0, db=0.0, black=4, white=252, gamma=1.0, sat=1.0),
    "N2": dict(da=-0.5, db=-1.5, black=24, white=250, gamma=1.06, sat=0.98),
    "N3": dict(da=1.5, db=6.0, black=2, white=246, gamma=0.94, sat=1.06),
}
_lut_curve = None
_vig = {}


def s_curve():
    x = np.arange(256) / 255.0
    y = x + 0.06 * np.sin(2 * np.pi * (x - 0.5)) * (x * (1 - x)) * 4 * -1 * -1
    y = np.clip(x + 0.05 * np.sin(np.pi * (2 * x - 1)) * 0.5 * 2 * (0.5 - abs(x - 0.5)), 0, 1)
    return (y * 255).astype(np.uint8)


def vignette(h, w, k=0.15):
    if (h, w) not in _vig:
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
        _vig[(h, w)] = (1 - k * d ** 2.2)[..., None].astype(np.float32)
    return _vig[(h, w)]


def grade(img, clip, rng):
    p = PER[clip]
    x = img.astype(np.float32)
    # 검은점, 흰점, 감마
    x = np.clip((x - p["black"]) / (p["white"] - p["black"]), 0, 1) ** p["gamma"] * 255
    lab = cv2.cvtColor(x.astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
    # 채도
    lab[..., 1:] = (lab[..., 1:] - 128) * p["sat"] + 128
    lab[..., 1] += p["da"]
    lab[..., 2] += p["db"]
    # 공통: 밝은 곳 살짝 따뜻하게
    hl = np.clip((lab[..., 0] - 150) / 105, 0, 1)
    lab[..., 2] += 2.0 * hl
    lab[..., 1] += 0.6 * hl
    x = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    global _lut_curve
    if _lut_curve is None:
        _lut_curve = s_curve()
    x = cv2.LUT(x, _lut_curve).astype(np.float32)
    x *= vignette(*x.shape[:2])
    g = rng.normal(0, 2.6, x.shape[:2]).astype(np.float32)[..., None]
    x += g
    return np.clip(x, 0, 255).astype(np.uint8)
