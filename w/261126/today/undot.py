"""화면 자막의 가운뎃점만 찾아 지운다(프레임별 탐지, 주변 픽셀로 메움)."""
import subprocess, sys
import numpy as np, cv2
from scipy import ndimage

SRC, DST = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
# (시작초, 끝초, 띠 y0, y1, 점 크기 최대, 점 중심 y 범위, 밝기 기준)
ZONES = [
    # (시작초, 끝초, 띠 y0, y1, 크기 범위, 중심 y 범위, 밝기 기준, 왼쪽 x 범위, 가로세로 차 허용, 최소 면적)
    (15.3, 15.75, 140, 215, (6, 14), (175, 186), 45, (0, 530), 10, 20),   # 머리 상자 들어오는 동안(흐림)
    (15.75, 20.6, 140, 215, (8, 12), (170, 188), 100, (300, 530), 3, 38), # 머리 상자 멈춘 뒤
    (20.0, 26.7, 1845, 1880, (2, 7), (1855, 1868), 35, (515, 540), 3, 4), # 아래 작은 안내 글(서서히 나타나고 사라짐)
]

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", DST], stdin=subprocess.PIPE)
n = 0
log = []
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
    t = n / FPS
    for (a, b, y0, y1, mx, (cy0, cy1), th, (cx0, cx1), dd, amin) in ZONES:
        if not (a <= t <= b):
            continue
        band = fr[y0:y1].astype(np.int32).sum(axis=2) // 3
        lab, k = ndimage.label(band > th)
        mask = np.zeros((H, W), np.uint8)
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            area = (lab[sl] == i).sum()
            cy = y0 + (sl[0].start + sl[0].stop) / 2
            if mx[0] <= hh <= mx[1] and mx[0] <= ww <= mx[1] and abs(hh - ww) <= dd and area >= amin and cy0 <= cy <= cy1 and cx0 <= sl[1].start <= cx1:
                mask[y0 + sl[0].start - 3:y0 + sl[0].stop + 3, sl[1].start - 3:sl[1].stop + 3] = 255
                log.append((round(t, 2), sl[1].start, y0 + sl[0].start, ww, hh))
        if mask.any():
            fr = cv2.inpaint(fr, mask, 4, cv2.INPAINT_TELEA)
    enc.stdin.write(fr.tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print("frames", n, "patched", len(log))
for row in [r for r in log if r[0] < 15.8]:
    print(row)
xs = sorted(set((r[0] >= 20.2, r[1]) for r in log))
print("x positions", sorted(set(r[1] for r in log)))
