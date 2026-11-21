# ---------------------------------------------------------------- 단톡방 화면(상표 없는 일반 대화창)
PX0, PY0, PX1, PY1 = 70, 330, 1010, 1730          # 휴대폰 바깥
SX0, SY0, SX1, SY1 = 92, 352, 988, 1708           # 화면
HEAD_H = 132
INPUT_H = 120
BG_CHAT = (234, 230, 224)
ME_BUB = (206, 226, 255)
OTHER_BUB = (255, 255, 255)
AV = {"어머님": (186, 120, 150), "아가씨": (120, 160, 200), "남편": (110, 150, 120), "아버님": (150, 140, 120)}
FT_MSG = 48
FT_NAME = 32
MAXW = 600

MSGS = [  # (등장 시각, 종류, 보낸 사람, 글)
    (-10.0, "other", "어머님", "이번 주 토요일 김장,\n일곱 시까지 와라"),
    (-10.0, "me", None, "어머님 잔소리 또 시작.\n귀 막고 싶다"),
    (at("C4", 0.20), "me", None, "어머님은 뭐가 제일\n귀 막고 싶으세요?"),
    (at("C5", 0.05), "other", "어머님", "너희 시아버지\n코 고는 소리"),
    (at("C6", 0.05), "other", "아가씨", "나도 아빠 코골이 귀 막음"),
    (at("C7", 0.05), "other", "남편", "나도"),
    (at("C8", 0.10), "sys", None, "어머님이 채팅방 이름을\n'아버지 코골이 대책방'으로 바꿨어요"),
    (at("C9", 0.05), "other", "어머님", "귀마개는 내가 산다.\n며느리 것부터"),
]


def unread_at(i, t):
    """내 말풍선 옆 안 읽은 숫자."""
    if i == 1:
        steps = [(at("O1", 0.45), 3), (at("O1", 0.90), 2), (at("O1", 1.35), 1), (at("O1", 1.80), 0)]
        n = 4
        for s, v in steps:
            if t >= s:
                n = v
        return n
    if i == 2:
        if t < at("C5", 0.0):
            return 4
        if t < at("C6", 0.0):
            return 3
        if t < at("C7", 0.0):
            return 2
        return 1
    return 0


def bubble_size(d, text, f):
    lines = text.split("\n")
    w = max(d.textlength(l, font=f) for l in lines)
    lh = int(f.size * 1.32)
    return int(w) + 52, lh * len(lines) + 36, lines, lh


def draw_msg(canvas, y_bottom, kind, who, text, t, i, k_pop):
    """메시지 하나를 y_bottom에 바닥을 맞춰 그리고, 차지한 높이를 돌려준다."""
    d = ImageDraw.Draw(canvas)
    f = F(FB, FT_MSG)
    if kind == "sys":
        fs = F(FR, 32)
        lines = text.split("\n")
        lh = 44
        w = max(d.textlength(l, font=fs) for l in lines) + 60
        h = lh * len(lines) + 28
        x0 = (SX0 + SX1) / 2 - w / 2
        y0 = y_bottom - h
        layer_ = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer_)
        dl.rounded_rectangle((x0, y0, x0 + w, y0 + h), 22, fill=(70, 80, 96, 170))
        for j, l in enumerate(lines):
            lw = dl.textlength(l, font=fs)
            dl.text(((SX0 + SX1) / 2 - lw / 2, y0 + 12 + j * lh), l, font=fs, fill=(255, 255, 255, 255))
        canvas.alpha_composite(with_alpha(layer_, k_pop) or Image.new("RGBA", canvas.size, (0, 0, 0, 0)))
        return h + 26
    bw, bh, lines, lh = bubble_size(d, text, f)
    name_h = 40 if kind == "other" else 0
    total = bh + name_h
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    y0 = y_bottom - bh
    if kind == "other":
        ax = SX0 + 26
        dl.ellipse((ax, y0 - name_h, ax + 84, y0 - name_h + 84), fill=AV.get(who, (150, 150, 150)) + (255,))
        dl.ellipse((ax + 26, y0 - name_h + 16, ax + 58, y0 - name_h + 48), fill=(255, 255, 255, 150))
        dl.ellipse((ax + 14, y0 - name_h + 50, ax + 70, y0 - name_h + 96), fill=(255, 255, 255, 150))
        bx = ax + 104
        dl.text((bx + 4, y0 - name_h), who, font=F(FR, FT_NAME), fill=(60, 66, 76, 255))
        dl.rounded_rectangle((bx, y0, bx + bw, y0 + bh), 26, fill=OTHER_BUB + (255,))
        for j, l in enumerate(lines):
            dl.text((bx + 26, y0 + 14 + j * lh), l, font=f, fill=(24, 24, 28, 255))
        anchor = (bx, y0 + bh / 2)
    else:
        bx1 = SX1 - 30
        bx = bx1 - bw
        dl.rounded_rectangle((bx, y0, bx1, y0 + bh), 26, fill=ME_BUB + (255,))
        for j, l in enumerate(lines):
            dl.text((bx + 26, y0 + 14 + j * lh), l, font=f, fill=(24, 24, 28, 255))
        n = unread_at(i, t)
        if n > 0:
            fn = F(FB, 34)
            s = str(n)
            dl.text((bx - 14 - dl.textlength(s, font=fn), y0 + bh - 46), s, font=fn, fill=(255, 140, 0, 255))
        anchor = (bx1, y0 + bh / 2)
    if k_pop < 0.999:
        s = 0.86 + 0.14 * k_pop
        big = lay.resize((int(lay.width * s), int(lay.height * s)), Image.BICUBIC)
        ox = int(anchor[0] - anchor[0] * s)
        oy = int(anchor[1] - anchor[1] * s)
        tmp = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        tmp.alpha_composite(big.crop((max(0, -ox), max(0, -oy), max(0, -ox) + min(lay.width, big.width),
                                      max(0, -oy) + min(lay.height, big.height))), (max(0, ox), max(0, oy)))
        lay = with_alpha(tmp, k_pop) or Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    canvas.alpha_composite(lay)
    return total + 30


def typing_on(t):
    for sid in ("X1", "X3"):
        if T[sid][0] <= t < T[sid][1]:
            return True
    return False


def draw_chrome(d, t):
    # 머리줄
    d.rounded_rectangle((SX0, SY0, SX1, SY0 + HEAD_H), 52, fill=(244, 246, 250, 255))
    d.rectangle((SX0, SY0 + 60, SX1, SY0 + HEAD_H), fill=(244, 246, 250, 255))
    d.line((SX0, SY0 + HEAD_H, SX1, SY0 + HEAD_H), fill=(205, 210, 220, 255), width=2)
    d.line((SX0 + 44, SY0 + 66, SX0 + 64, SY0 + 46), fill=(60, 60, 66, 255), width=6)
    d.line((SX0 + 44, SY0 + 66, SX0 + 64, SY0 + 86), fill=(60, 60, 66, 255), width=6)
    renamed = t >= at("C8", 0.10)
    title = "아버지 코골이 대책방" if renamed else "우리 가족"
    ft = F(FB, 46)
    d.text((SX0 + 96, SY0 + 38), title, font=ft, fill=(28, 28, 32, 255))
    d.text((SX0 + 110 + d.textlength(title, font=ft), SY0 + 46), "5", font=F(FR, 36), fill=(130, 134, 142, 255))
    # 입력줄
    iy0 = SY1 - INPUT_H
    d.rectangle((SX0, iy0, SX1, SY1 - 50), fill=(250, 250, 252, 255))
    d.rounded_rectangle((SX0, iy0, SX1, SY1), 52, fill=(250, 250, 252, 255))
    d.rectangle((SX0, iy0, SX1, iy0 + 40), fill=(250, 250, 252, 255))
    d.rounded_rectangle((SX0 + 30, iy0 + 22, SX1 - 120, iy0 + 92), 34, fill=(236, 238, 242, 255))
    d.ellipse((SX1 - 100, iy0 + 22, SX1 - 30, iy0 + 92), fill=(84, 124, 214, 255))
    if T["C4"][0] <= t < at("C4", 0.20):
        d.text((SX0 + 60, iy0 + 32), "어머님은 뭐가 제일 귀 막고 |", font=F(FR, 36), fill=(60, 60, 66, 255))


_CBG = {}


def chat_bg():
    if "bg" not in _CBG:
        bg = view(still("S1"), 1.0, 0.5, 0.5).filter(ImageFilter.GaussianBlur(18))
        bg = Image.fromarray((arr(bg) * np.array([0.42, 0.42, 0.46], np.float32)).astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(bg)
        d.rounded_rectangle((PX0, PY0, PX1, PY1), 70, fill=(16, 16, 18, 255))
        _CBG["bg"] = bg
    return _CBG["bg"]


def chat_frame(t):
    img = chat_bg().copy()
    scr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(scr)
    d.rounded_rectangle((SX0, SY0, SX1, SY1), 52, fill=BG_CHAT + (255,))
    iy0 = SY1 - INPUT_H
    # 메시지(아래에서 위로)
    vis = [(i, m) for i, m in enumerate(MSGS) if m[0] <= t]
    y = iy0 - 34
    if typing_on(t):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        ax = SX0 + 26
        y0 = y - 84
        dl.ellipse((ax, y0 - 40, ax + 84, y0 + 44), fill=AV["어머님"] + (255,))
        dl.text((ax + 108, y0 - 40), "어머님", font=F(FR, FT_NAME), fill=(60, 66, 76, 255))
        dl.rounded_rectangle((ax + 104, y0, ax + 104 + 170, y0 + 84), 26, fill=(255, 255, 255, 255))
        ph = t * 6
        for j in range(3):
            a = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(ph * 2 * math.pi - j * 1.2))
            c = int(120 + 100 * (1 - a))
            dl.ellipse((ax + 140 + j * 40, y0 + 30, ax + 164 + j * 40, y0 + 54), fill=(c, c, c, 255))
        scr.alpha_composite(lay)
        y = y0 - 70
    for i, m in reversed(vis):
        t0, kind, who, text = m
        k = ease((t - t0) / 0.14) if t0 > 0 else 1.0
        h = draw_msg(scr, y, kind, who, text, t, i, k)
        y -= h
        if y < SY0 + HEAD_H + 40:
            break
    draw_chrome(ImageDraw.Draw(scr), t)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((SX0, SY0, SX1, SY1), 52, fill=255)
    clipm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    clipm.paste(scr, (0, 0), mask)
    img.alpha_composite(clipm)
    return img.convert("RGB")


def chat_view(t):
    """가장 새 메시지 쪽으로 살짝 당겨 보이게."""
    img = chat_frame(t)
    sid = shot_at(t)
    lt = t - T[sid][0]
    return img


# ---------------------------------------------------------------- 끝 화면과 엽전 구멍 줌 스루
_END = {}
CXE, CYE = 840, 890
HOLE = 74 * 0.32


def opening(lt):
    return chat_view(min(TOTAL, max(0.0, lt)))


def endcard_full():
    if "full" not in _END:
        s1 = view(still("S6"), 1.0, 0.5, 0.5)
        bg = s1.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.42))
        labels = ["축사", "회식", "소개팅", "빼빼로", "택시", "다녀와", "무르기", "퇴근", "월요일", "건배사", "단톡방"]
        full = AN.coin_string(bg.copy(), labels)
        d = ImageDraw.Draw(full)

        def c(t, f, y, fill):
            w = d.textlength(t, font=f)
            d.text(((W - w) / 2, y), t, font=f, fill=fill)
        c("보낸 말은 못 지워도,", F(FB, 60), 300, (255, 255, 255))
        c("다음 말은 고를 수 있어요", F(FB, 60), 384, (255, 255, 255))
        c("11닢째", F(FB, 52), 1080, (255, 200, 60))
        c("2027 한 수", F(FB, 60), 1190, (255, 255, 255))
        f2 = F(FB, 42)
        w = d.textlength("hongchaksa.kr", font=f2)
        d.rounded_rectangle((540 - w / 2 - 32, 1310, 540 + w / 2 + 32, 1386), 38, outline=(215, 215, 215), width=2)
        c("hongchaksa.kr", f2, 1318, (245, 245, 245))
        pre = full.copy()
        pre.paste(bg.crop((CXE - 120, CYE - 135, CXE + 120, CYE + 150)), (CXE - 120, CYE - 135))
        ImageDraw.Draw(pre).line((CXE - 120, CYE, CXE + 60, CYE), fill=(170, 40, 40), width=6)
        coin = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        AN.coin(ImageDraw.Draw(coin), 90, 90, 74, True)
        pad = Image.new("RGB", (W + 1200, H + 1200), (12, 10, 9))
        pad.paste(full, (600, 600))
        _END.update(full=full, pre=pre, coin=coin, pad=pad)
    return _END


def endcard(lt):
    E = endcard_full()
    dur = TOTAL - T["END"][0]
    zt = 0.6
    if lt >= dur - zt:
        p = min(1.0, (lt - (dur - zt)) / (zt - 0.06))
        q = p ** 2.2
        s = math.exp(math.log(46.0) * q)
        m = smooth(min(1.0, p * 2.5))
        cx = 540 + (CXE - 540) * m
        cy = 960 + (CYE - 960) * m
        bw, bh = W / s, H / s
        box = (cx - bw / 2 + 600, cy - bh / 2 + 600, cx + bw / 2 + 600, cy + bh / 2 + 600)
        img = E["pad"].resize((W, H), Image.BICUBIC, box=box)
        side = 2 * HOLE * s
        sx = (CXE - cx) * s + 540
        sy = (CYE - cy) * s + 960
        sc = min(H, side) / H
        op = opening(0.0)
        if sc > 0.01:
            ow, oh = max(1, int(W * sc)), max(1, int(H * sc))
            small = op.resize((ow, oh), Image.BICUBIC)
            l, tt = int(sx - ow / 2), int(sy - oh / 2)
            mk = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mk).rectangle((sx - side / 2, sy - side / 2, sx + side / 2, sy + side / 2), fill=255)
            canvas = img.copy()
            canvas.paste(small, (l, tt))
            img = Image.composite(canvas, img, mk)
        if p >= 1.0:
            img = op
        return img
    if lt >= 0.5:
        return E["full"]
    k = ease(lt / 0.45)
    img = E["pre"].copy()
    x = int(1100 + (CXE - 1100) * k) - 90
    y = int(200 + (CYE - 200) * k) - 90
    img.paste(E["coin"], (x, y), E["coin"])
    return img


