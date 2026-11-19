"""상표처럼 보이는 병 라벨을 지우고(인페인트) 흐리게 만든다. python3 retouch.py"""
import cv2, numpy as np
D = "/home/claude/ep10/gen"
JOBS = {
    "N4": [(640, 1830, 800, 2130, 0), (850, 1850, 915, 2110, 0), (1180, 1110, 1395, 1310, 1), (1410, 1130, 1536, 1250, 1)],
    "N5": [(1250, 2180, 1536, 2752, 1)],
}
for name, rects in JOBS.items():
    im = cv2.imread(f"{D}/stills/{name}.png")
    out = im.copy()
    for x0, y0, x1, y1, soft in rects:
        m = np.zeros(im.shape[:2], np.uint8)
        m[y0:y1, x0:x1] = 255
        # 라벨(밝은 흰색과 글씨)만 골라 인페인트
        roi = im[y0:y1, x0:x1].astype(np.int16)
        g = roi[..., 1] - (roi[..., 0] + roi[..., 2]) / 2
        lab = ((roi.mean(axis=2) > 120) & (g < 25)) | (roi.mean(axis=2) < 60)
        mk = np.zeros(im.shape[:2], np.uint8)
        mk[y0:y1, x0:x1][lab] = 255
        mk = cv2.dilate(mk, np.ones((9, 9), np.uint8))
        out = cv2.inpaint(out, mk, 9, cv2.INPAINT_TELEA)
        k = 41 if soft else 25
        bl = cv2.GaussianBlur(out, (k, k), 0)
        f = cv2.GaussianBlur(m.astype(np.float32) / 255, (61, 61), 0)[..., None]
        out = (out * (1 - f) + bl * f).astype(np.uint8)
    cv2.imwrite(f"{D}/retouch/{name}.png", out)
    print(name)
