"""홍책사 11화 시댁 단톡방(1080x1920, 30fps, 30.5초).
사용: python3 build_v20.py [출력.mp4] [--from 초 --to 초] [--frames 0,24.3,42.3]
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import animatic as AN  # noqa: E402

W, H, FPS = 1080, 1920, 30
D = "/home/claude/ep11"
CL = f"{D}/clips"
ST = f"{D}/gen/stills"
E7 = "/home/claude/ep7/v/clips/S16.mp4"
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
YEL = (255, 214, 80, 255)
_FC = {}


def F(path, size):
    k = (path, size)
    if k not in _FC:
        if path.endswith(".ttc"):
            for i in range(10):
                f = ImageFont.truetype(path, size, index=i)
                if "KR" in f.getname()[0]:
                    break
        else:
            f = ImageFont.truetype(path, size)
        _FC[k] = f
    return _FC[k]


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


