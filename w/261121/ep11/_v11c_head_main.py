# ---------------------------------------------------------------- 11화 v2 스릴러 편집: 샷 길이표
SHOTS = [
    ("O1", 2.4, dict(chat=True)),
    ("N1", 1.8, dict(src="N1", map=("lin", 0.3, 1.1), zz=(1.0, 1.08), c=(0.45, 0.55))),
    ("N2", 1.4, dict(src="N2", map=("lin", 0.0, 1.0), zz=(1.0, 1.14), c=(0.5, 0.45), crash=0.25)),
    ("T1", 0.55, dict(card=True)),
    ("N3", 1.2, dict(src="N3", map=("lin", 0.4, 1.0), zz=(1.0, 1.06), c=(0.5, 0.34))),
    ("XA", 0.6, dict(chat=True, whip=True)),
    ("M1", 0.6, dict(src="S2", map=("lin", 0.6, 0.5), zz=(1.15, 1.25), c=(0.45, 0.34), whip=True)),
    ("XB", 0.4, dict(chat=True, whip=True, glitch=True)),
    ("N3b", 0.7, dict(src="N3", map=("lin", 2.9, 1.0), zz=(1.2, 1.3), c=(0.5, 0.30), whip=True)),
    ("N4", 2.4, dict(src="N4", map=("lin", 1.2, 1.0), zz=(1.05, 1.15), c=(0.5, 0.42), whip=True)),
    ("S4", 3.6, dict(src="S4", map=("hero2",), zz=(1.08, 1.0), c=(0.5, 0.40), c1=(0.5, 0.64))),
    ("C4", 1.3, dict(chat=True)),
    ("C5", 1.2, dict(chat=True)),
    ("C6", 0.9, dict(chat=True)),
    ("C7", 1.0, dict(chat=True)),
    ("N5", 1.9, dict(src="N5", map=("lin", 1.0, 1.0), zz=(1.0, 1.06), c=(0.5, 0.55))),
    ("S5", 2.4, dict(src="S5", map=("dad",), c=(0.55, 0.36))),
    ("C8", 1.7, dict(chat=True)),
    ("C9", 1.5, dict(chat=True)),
    ("S6", 1.8, dict(src="S6", map=("lin", 1.9, 0.75), zz=(1.0, 1.08), c=(0.5, 0.42), warm=True)),
    ("E7a", 1.22, dict(src="E7", map=("lin", 2.20, 1.0), zz=(1.0, 1.03))),
    ("E7b", 0.58, dict(src="E7", map=("lin", 4.02, 1.0), zz=(1.06, 1.07))),
    ("END", 3.0, dict(end=True)),
]
EDL = []
_t = 0.0
for _sid, _d, _o in SHOTS:
    EDL.append((_sid, round(_t, 3), round(_t + _d, 3), _o))
    _t += _d
TOTAL = EDL[-1][2]
ORDER = [e[0] for e in EDL]
T = {e[0]: (e[1], e[2]) for e in EDL}
OPT = {e[0]: e[3] for e in EDL}
LIVE = {"N1", "N2", "N3", "M1", "N3b", "N4", "S4", "N5", "S5", "S6", "E7a", "E7b"}


def at(sid, rel):
    a0, a1 = T[sid]
    return round((a1 + rel) if rel < 0 else (a0 + rel), 3)


def src_path(name):
    return E7 if name == "E7" else f"{CL}/{name}.mp4"


def src_time(sid, lt):
    """화면 시각 lt를 원본 클립 시각으로."""
    m = OPT[sid]["map"]
    if m[0] == "lin":
        return m[1] + lt * m[2]
    if m[0] == "hero2":      # 0~1.9초 대사 그대로, 그 뒤 엽전 놓기 0.8배 슬로
        return lt if lt < 1.9 else 2.6 + (lt - 1.9) * 0.8
    if m[0] == "dad":        # 0~0.6초 얼어붙은 얼굴, 그 뒤 실제 속도로 대사
        return 0.95 if lt < 0.6 else 0.95 + (lt - 0.6)
    raise ValueError(m)


"""HELPERS"""

_SRC = {}


def src_frame(name, st):
    if name not in _SRC:
        if len(_SRC) >= 2:
            _SRC.pop(next(iter(_SRC)))
        _SRC[name] = Clip(src_path(name), 0.0, None)
    return _SRC[name].blend(st)


"""CHAT"""


# ---------------------------------------------------------------- 스릴러 효과
_RNG = np.random.default_rng(11)


def thriller(a, k=1.0):
    """청록 그림자, 주황 밝은 곳, 대비 올림."""
    lum = a.mean(axis=2, keepdims=True) / 255.0
    sh = np.array([-10, 4, 14], np.float32) * (1 - lum)
    hi = np.array([14, 4, -12], np.float32) * lum
    b = (a - 128) * 1.16 + 128 + sh + hi
    gray = b.mean(axis=2, keepdims=True)
    b = gray + (b - gray) * 0.86
    return a * (1 - k) + b * k


def golden(a, k=1.0):
    b = a * np.array([1.08, 1.0, 0.86], np.float32) + np.array([14, 8, 0], np.float32)
    return a * (1 - k) + b * k


def grain(a, s=7.0):
    n = _RNG.normal(0, s, (H // 2, W // 2, 1)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, axis=0), 2, axis=1)
    return a + n


def red_wash(a, k):
    return a * (1 - k) + np.array([210, 20, 30], np.float32) * k


def letterbox(img):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 104), fill=(0, 0, 0))
    d.rectangle((0, H - 104, W, H), fill=(0, 0, 0))
    return img


def flash_k(Tabs, t0, dur=0.18):
    if t0 <= Tabs < t0 + dur:
        return 1 - (Tabs - t0) / dur
    return 0.0


def ov_big(s, color, size=460, cx=540, cy=900):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        f = F(FB, size)
        w = d.textlength(s, font=f)
        d.text((cx - w / 2, cy - size * 0.62), s, font=f, fill=color, stroke_width=14, stroke_fill=(0, 0, 0, 255))
        return im
    return cached(("big", s, color, size, cx, cy), mk)


def stamp_img(lines, size, color=(214, 38, 38, 255)):
    def mk():
        f = F(FB, size)
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        tw = max(tmp.textlength(s, font=f) for s in lines)
        pad = int(size * 0.45)
        lh = int(size * 1.25)
        w, h = int(tw + pad * 2), int(lh * len(lines) + size * 0.5)
        im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((10, 10, 10 + w, 10 + h), int(size * 0.28), fill=(255, 250, 244, 225), outline=color, width=max(6, size // 10))
        for i, s in enumerate(lines):
            sw = d.textlength(s, font=f)
            d.text((10 + (w - sw) / 2, 10 + size * 0.2 + i * lh), s, font=f, fill=color)
        g = np.random.default_rng(len(lines[0]) + size)
        a = np.asarray(im).copy()
        holes = g.random(a.shape[:2]) < 0.05
        a[holes, 3] = (a[holes, 3] * 0.35).astype(np.uint8)
        im = Image.fromarray(a).rotate(-6, resample=Image.BICUBIC, expand=True)
        return im
    return cached(("stamp", tuple(lines), size, color), mk)


def ov_stamp(lines, size, cx, cy, lt, color=(214, 38, 38, 255)):
    im = stamp_img(lines, size, color)
    k = ease(lt / 0.12)
    s = 1.8 - 0.8 * k
    big = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    out = layer()
    out.alpha_composite(big, (int(cx - big.width / 2), int(cy - big.height / 2)))
    return with_alpha(out, min(1.0, 0.3 + k))


def ov_alarm(lt):
    """빨간 경고 띠와 차오르는 막대."""
    im = layer()
    d = ImageDraw.Draw(im)
    on = int(lt * 8) % 2 == 0
    d.rounded_rectangle((90, 168, 990, 300), 24, fill=(160, 0, 10, 225 if on else 160), outline=(255, 80, 80, 255), width=4)
    f = F(FB, 54)
    t = "경고  장문 감지"
    w = d.textlength(t, font=f)
    d.text((540 - w / 2, 176), t, font=f, fill=(255, 255, 255, 255))
    p = min(1.0, max(0.1, lt / 0.6))
    d.rectangle((130, 262, 950, 284), fill=(60, 0, 0, 255))
    d.rectangle((130, 262, 130 + 820 * p, 284), fill=(255, 210, 60, 255))
    return im


def ov_capband(s, y, size):
    def mk():
        im = layer()
        d = ImageDraw.Draw(im)
        lines = s.split("\n")
        f = F(FB, size)
        w = max(d.textlength(l, font=f) for l in lines)
        lh = int(size * 1.36)
        d.rounded_rectangle((540 - w / 2 - 36, y - 18, 540 + w / 2 + 36, y + lh * len(lines) + 4), 22, fill=(8, 8, 10, 215))
        for i, l in enumerate(lines):
            text_center(d, y + i * lh, l, f, stroke=4)
        return im
    return cached(("capband", s, y, size), mk)


def ov_glint(cx, cy, lt):
    k = math.sin(math.pi * min(1.0, lt / 0.45))
    if k <= 0:
        return None
    im = layer()
    d = ImageDraw.Draw(im)
    r = 130 * k
    for ang, ln in ((0, 1.0), (90, 1.0), (45, 0.45), (135, 0.45)):
        dx, dy = math.cos(math.radians(ang)) * r * ln, math.sin(math.radians(ang)) * r * ln
        d.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=(255, 255, 255, int(230 * k)), width=6)
    d.ellipse((cx - 18 * k, cy - 18 * k, cx + 18 * k, cy + 18 * k), fill=(255, 255, 255, int(255 * k)))
    return im.filter(ImageFilter.GaussianBlur(2))


_RAYS = {}


def ov_rays(k):
    if "r" not in _RAYS:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        ox, oy = 980, -120
        for i in range(9):
            ang = math.radians(112 + i * 7.5)
            w = 26 + (i % 3) * 18
            x1, y1 = ox + math.cos(ang) * 2600, oy + math.sin(ang) * 2600
            nx, ny = -math.sin(ang) * w, math.cos(ang) * w
            d.polygon([(ox, oy), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny)], fill=(255, 214, 140, 46))
        _RAYS["r"] = im.filter(ImageFilter.GaussianBlur(18))
    return with_alpha(_RAYS["r"], k)


# ---------------------------------------------------------------- 바탕 화면
def shot_at(Tabs):
    for sid in ORDER:
        if T[sid][0] <= Tabs < T[sid][1]:
            return sid
    return ORDER[-1]


COUNT = [(0.0, "4"), (0.45, "3"), (0.90, "2"), (1.35, "1"), (1.80, "0")]


def base_frame(sid, lt, dur, Tabs):
    o = OPT[sid]
    post = {}
    if o.get("end"):
        return endcard(lt), post
    if o.get("card"):
        img = Image.new("RGB", (W, H), (6, 4, 6))
        post.update(chroma=6 if lt < 0.12 else 0, scan=0.2)
        return img, post
    if o.get("chat"):
        img = chat_frame(Tabs)
        if sid == "O1":
            if lt < 1.8:
                z = 1.75 + 0.12 * smooth(lt / 1.8)
                img = view(img, z, 0.70, 0.80)
            else:
                z = 1.0 + 0.9 * (1 - ease((lt - 1.8) / 0.22))
                img = view(img, z, 0.70, 0.80)
                post["flash"] = flash_k(lt, 1.8, 0.2)
            post["red"] = 0.10 + 0.10 * (0.5 + 0.5 * math.sin(lt * 14))
        elif sid in ("XA", "XB"):
            img = view(img, 1.35, 0.5, 0.80)
            post["red"] = 0.16 * (0.5 + 0.5 * math.sin(lt * 26))
            if sid == "XB":
                post.update(hblur=18 * (1 - lt / dur), chroma=8, scan=0.25)
        elif sid in ("C5", "C6", "C7", "C9", "C8"):
            t0 = 0.05 if sid != "C8" else 0.1
            z = 1.16 + 0.16 * (1 - ease(max(0.0, lt - t0) / 0.14))
            img = view(img, z, 0.5, 0.80)
            post["flash"] = flash_k(lt, t0, 0.1) * 0.55
            post["vig"] = 0.35
        elif sid == "C4":
            z = 1.16 + (0.14 * (1 - ease((lt - 0.2) / 0.14)) if lt >= 0.2 else 0.0)
            img = view(img, z, 0.5, 0.80)
            if lt >= 0.2:
                post["flash"] = flash_k(lt, 0.2, 0.1) * 0.55
            post["vig"] = 0.35
        if o.get("whip") and lt < 0.09:
            post["hblur"] = 40 * (1 - lt / 0.09)
        return img, post
    st = src_time(sid, lt)
    im = src_frame(o["src"], st)
    cx, cy = o.get("c", (0.5, 0.5))
    if "c1" in o:
        k = smooth(max(0.0, lt - 1.9) / max(0.1, dur - 1.9))
        cx = cx + (o["c1"][0] - cx) * k
        cy = cy + (o["c1"][1] - cy) * k
    z0, z1 = o.get("zz", (1.0, 1.0))
    z = z0 + (z1 - z0) * smooth(lt / dur)
    if o.get("crash"):
        z = z0 + (z1 - z0) * ease(min(1.0, lt / o["crash"]))
    if sid == "S5":
        if lt < 0.6:
            step = min(2, int(lt / 0.2))
            z = (1.0, 1.28, 1.6)[step] * (1.0 + 0.04 * (1 - ease((lt - step * 0.2) / 0.06)))
            post.update(grade="bw", red=0.0, flash=flash_k(lt, step * 0.2, 0.08) * 0.8)
        else:
            z = 1.6 - 0.45 * ease((lt - 0.6) / 0.25)
    img = view(im, z, cx, cy)
    if o.get("whip") and lt < 0.09:
        post["hblur"] = 40 * (1 - lt / 0.09)
    if o.get("freeze_tail") and lt >= dur - o["freeze_tail"]:
        img = view(src_frame(o["src"], src_time(sid, dur - o["freeze_tail"])), z * 1.12, cx, cy)
        post.update(grade="bw")
    if sid == "N1":
        post["flash"] = flash_k(lt, 1.18, 0.16) * 0.9
        if 1.18 <= lt < 1.36:
            post["chroma"] = 7
    if sid == "N2":
        hb = min(abs(lt - 0.0), abs(lt - 0.7))
        post["red"] = 0.26 * max(0.0, 1 - hb / 0.18)
    if sid in ("N3", "N3b"):
        post["red"] = 0.0
        post["flick"] = 0.9 + 0.1 * math.sin(lt * 37) * math.sin(lt * 11)
    if sid == "N4":
        post["flash"] = flash_k(lt, 0.85, 0.25) * 0.7
        post["gold"] = lt >= 0.85
    if sid == "N5":
        post["flash"] = flash_k(lt, 0.55, 0.12) * 0.6
    if sid == "S4":
        if 1.9 <= lt < 2.1:
            post["flash"] = flash_k(lt, 1.9, 0.2) * 0.7
        if lt >= 3.27:
            post["flash"] = flash_k(lt, 3.27, 0.25)
            post["gold"] = True
    return img, post


def opening(lt):
    return base_frame("O1", 0.0, T["O1"][1] - T["O1"][0], 0.0)[0]


# ---------------------------------------------------------------- 자막과 표시
SUBS = [
    (at("S4", 0.10), at("S4", 2.0), "어머님은 뭐에 귀 막고 싶으실까요?"),
    (at("S5", 0.71), at("S5", -0.04), "나만 몰랐냐?"),
    (at("E7a", 0.03), at("E7b", -0.02), "홍책사 한 수면, 됐지?"),
]
CAPS = [  # (시작, 끝, 글, y, 크기)
    (at("O1", 0.0), at("O1", -0.0001), "남편한테 보낼 시어머니 흉을\n시댁 단톡방에 보냈다", 112, 70),
    (at("N1", 0.0), at("N1", -0.0001), "시부모님, 시누이, 남편까지\n4명 모두 읽었다", 180, 64),
    (at("N3", 0.0), at("N3", -0.0001), "어머님, 장문 입력 중", 190, 66),
    (at("M1", 0.0), at("M1", -0.0001), "어머님, 장문 입력 중", 190, 66),
    (at("N3b", 0.0), at("N3b", -0.0001), "어머님, 장문 입력 중", 190, 66),
    (at("N4", 0.0), at("N4", -0.0001), "그때, 카페 사장", 190, 70),
    (at("S4", 2.0), at("S4", -0.0001), "카페 사장의 한 수", 190, 66),
    (at("C5", 0.0), at("C5", -0.0001), "어머님도 귀 막고 있었다", 150, 64),
    (at("N5", 0.0), at("S5", -0.0001), "시아버지만 몰랐다", 190, 70),
    (at("C9", 0.0), at("C9", -0.0001), "어머님, 며느리 편", 150, 64),
]
HOOK = (at("S4", 0.1), at("S4", 1.9), "7화 그 카페")
SHAKE = [(at("O1", 1.8), 0.28, 0.02), (at("N1", 1.18), 0.3, 0.022), (at("T1", 0.0), 0.2, 0.02),
         (at("C4", 0.2), 0.18, 0.012), (at("C5", 0.05), 0.16, 0.012), (at("C6", 0.05), 0.16, 0.012),
         (at("C7", 0.05), 0.22, 0.018), (at("N5", 0.55), 0.3, 0.016), (at("S5", 0.0), 0.12, 0.016),
         (at("S5", 0.2), 0.12, 0.016), (at("S5", 0.4), 0.12, 0.016), (at("C8", 0.35), 0.22, 0.018),
         (at("S4", 3.27), 0.2, 0.012)]


def overlays(sid, lt, dur, Tabs):
    out = []
    for s0, s1, t, y, size in CAPS:
        a = win(Tabs, s0, s1, 0.0 if s0 < 0.01 else 0.04, 0.05)
        if a:
            cap = ov_capband(t, y, size) if OPT[sid].get("chat") and sid != "O1" else ov_caption(t, y=y, size=size)
            out.append((cap, a))
    if sid == "O1":
        cur = None
        for t0, s in COUNT:
            if lt >= t0:
                cur = (t0, s)
        if cur and lt < 2.15:
            t0, s = cur
            k = ease((lt - t0) / 0.1)
            col = (255, 40, 40, 255) if s != "0" else (255, 255, 255, 255)
            out.append((scaled(ov_big(s, col, 420, 540, 640), 1.5 - 0.5 * k, 540, 640), 1.0))
        if lt >= 1.85:
            out.append((ov_stamp(["전원 읽음"], 110, 540, 1250, lt - 1.85), 1.0))
    if sid in ("XA", "XB"):
        out.append((ov_alarm(Tabs - T["XA"][0]), 1.0))
    if sid == "T1":
        k = ease(lt / 0.1)
        out.append((scaled(ov_pop("어머님", (240, 240, 240, 255), 760, 96), 1.3 - 0.3 * k, 540, 760), 1.0))
        out.append((scaled(ov_big("입력 중", (235, 30, 40, 255), 220, 540, 1000), 1.5 - 0.5 * k, 540, 1000), 1.0))
    if sid == "N4":
        out.append((ov_rays(1.0), 1.0))
        a = win(Tabs, at("N4", 0.9), T["N4"][1], 0.0, 0.0)
        if a:
            k = ease((lt - 0.9) / 0.12)
            out.append((scaled(ov_tag("홍책사"), 1.4 - 0.4 * k, 960, 1027), a))
    if sid == "S4":
        out.append((ov_rays(0.8), 1.0))
        a = win(Tabs, HOOK[0], HOOK[1], 0.12, 0.12)
        if a:
            out.append((ov_hook(HOOK[2]), a))
    if sid == "C4" and lt >= 0.2:
        k = ease((lt - 0.2) / 0.12)
        out.append((scaled(ov_pop("반격 개시", YEL, 220, 104), 1.3 - 0.3 * k, 540, 220), 1.0))
    if sid == "C6":
        k = ease(lt / 0.1)
        out.append((scaled(ov_pop("아가씨도", (255, 255, 255, 255), 220, 100), 1.2 - 0.2 * k, 540, 220), 1.0))
    if sid == "C7":
        k = ease(lt / 0.1)
        out.append((scaled(ov_pop("남편도", YEL, 220, 116), 1.4 - 0.4 * k, 540, 220), 1.0))
    if sid == "C8" and lt >= 0.35:
        out.append((ov_stamp(["작전명", "아버지 코골이 대책방"], 76, 540, 880, lt - 0.35), 1.0))
    for s0, s1, t in SUBS:
        if s0 <= Tabs < s1:
            out.append((ov_sub(t), win(Tabs, s0, s1, 0.04, 0.06)))
    return out


def composite(base, ovs):
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    for o, a in ovs:
        o2 = with_alpha(o, a)
        if o2 is not None:
            im.alpha_composite(o2)
    return im.convert("RGB")


def frame_at(Tabs):
    sid = shot_at(Tabs)
    a0, a1 = T[sid]
    lt, dur = Tabs - a0, a1 - a0
    img, post = base_frame(sid, lt, dur, Tabs)
    for t0, d0, amp in SHAKE:
        if t0 <= Tabs < t0 + d0:
            k = 1 - (Tabs - t0) / d0
            img = view(img, 1.0 + 2.5 * amp, 0.5 + amp * k * math.sin((Tabs - t0) * 90),
                       0.5 + amp * k * math.cos((Tabs - t0) * 70))
    a = arr(img)
    if sid in LIVE:
        if OPT[sid].get("warm") or sid in ("E7a", "E7b"):
            a = golden(a, 0.7)
        else:
            a = thriller(a, 1.0)
    if post.get("flick"):
        a = a * post["flick"]
    if post.get("grade"):
        a = grade(a, post["grade"], 1.0)
    if post.get("gold"):
        a = golden(a, 1.0)
    if post.get("red"):
        a = red_wash(a, post["red"])
    if post.get("hblur"):
        a = hblur(a, post["hblur"])
    if post.get("chroma"):
        a = chroma(a, post["chroma"])
    if post.get("scan"):
        a = scanlines(a, post["scan"])
    if post.get("vig"):
        a = vignette(a, post["vig"])
    if sid in LIVE:
        a = vignette(a, 0.42)
        a = grain(a, 6.0)
    if post.get("flash"):
        f = post["flash"]
        col = np.array([255, 236, 200] if post.get("gold") else [255, 255, 255], np.float32)
        a = a * (1 - f) + col * f
    base = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if sid in LIVE and sid not in ("E7a", "E7b"):
        base = letterbox(base)
    ovs = overlays(sid, lt, dur, Tabs)
    if sid != "END" or lt < 2.3:
        ovs.append((ov_ai(), 1.0))
    return sid, composite(arr(base), ovs)


def render(out, t_from=0.0, t_to=None):
    t_to = TOTAL if t_to is None else t_to
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-vf", "unsharp=5:5:0.3", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(n0, n1):
        Tabs = min(TOTAL - 1e-3, (fi + 0.5) / FPS)
        sid, fr = frame_at(Tabs)
        p.stdin.write(np.asarray(fr, np.uint8).tobytes())
        if fi % 90 == 0:
            print(f"{Tabs:5.1f}s {sid}", flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--frames" in args:
        ts = [float(x) for x in args[args.index("--frames") + 1].split(",")]
        os.makedirs(f"{D}/out/f4", exist_ok=True)
        for t in ts:
            sid, fr = frame_at(min(TOTAL - 1e-3, t))
            fr.save(f"{D}/out/f4/f_{t:05.2f}_{sid}.jpg", quality=88)
            print(t, sid)
        sys.exit(0)
    out = args[0] if args and not args[0].startswith("--") else f"{D}/out/ep11b_video.mp4"
    render(out)
