# 영상 표지 만들기(v3, 2026-11-14 개정)
# 사용: python3 tools/make_cover.py 장면.png 표지.jpg "홍책사 5화" "첫 줄" "둘째 줄" [AI 표기] [영어 한 줄] [hcs|b2b] [얼굴 높이] [확대] [가로 위치]
#
# 글자는 위쪽 띠(세로 312~725행)에만 놓는다. 아래쪽에는 글자를 두지 않는다.
# 근거(2026-11-14 대표 휴대폰 캡처 실측, 1080x1920 기준):
#   유튜브 앱 쇼츠 카드는 표지의 82~1838행만 보여 주고, 1496행부터 아래에 영상 제목 두 줄과 조회수를 덧씌운다.
#   카드 오른쪽 위(96~222행)에는 점 세 개 메뉴가 놓인다.
#   인스타 프로필 격자는 240~1680행(3:4)만 보여 주고 오른쪽 위에 릴스 아이콘을 얹는다.
# 그래서 색 줄, 회차와 AI 표기 한 줄, 두 줄 제목, 영어 한 줄을 왼쪽 위에 모으고,
# 얼굴은 글자 띠와 유튜브 덧글자 사이(800~1450행)에 오게 장면을 아래로 내려 깐다.
# 아래 1380행부터는 먹색으로 덮어 장면에 박힌 자막이 유튜브 제목 뒤로 비치지 않게 한다.
#
# 얼굴 높이: 장면에서 얼굴 중심이 있는 세로 위치(0~1, 기본 0.36). 그 지점을 1110행에 맞춘다.
#   얼굴이 글자에 가리면 값을 줄이고, 유튜브 제목 자리까지 내려가면 값을 키운다.
# 확대: 기본 1.12. 인물이 작으면 1.3 안팎, 얼굴이 화면을 채운 장면이면 1.0.
# 가로 위치: 확대했을 때 보여 줄 가로 지점(0 왼쪽, 0.5 가운데, 1 오른쪽, 기본 0.5).
# 장면 위쪽에 박힌 AI 표기와 자막은 위 먹색 띠가 덮는다. 아래쪽 자막이 1380~1700행에 걸리면 확대를 키워 밀어낸다.
# 박힌 표기나 자막이 얼굴 자리(600~1380행)에 남으면 그 장면은 쓰지 않고 다른 장면을 고른다.
# 만든 뒤에는 표지를 열어 얼굴이 글자 띠와 아래 먹색 사이에 온전히 보이는지 확인한다.
# 테마를 주지 않으면 회차 글에 홍책사나 작전회의가 있을 때 hcs(명조, 붉은 줄), 그 밖에는 b2b(고딕, 주황 줄).
import sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

a = sys.argv[1:]
src, out, ep, l1, l2 = a[:5]
label = a[5] if len(a) > 5 and a[5] else "AI로 만든 가상인물"
en = a[6].upper() if len(a) > 6 and a[6] else ""
theme = a[7] if len(a) > 7 and a[7] else ("hcs" if ("홍책사" in ep or "작전회의" in ep) else "b2b")
fy = float(a[8]) if len(a) > 8 and a[8] else 0.36
z = float(a[9]) if len(a) > 9 and a[9] else 1.12
ax = float(a[10]) if len(a) > 10 and a[10] else 0.5

FD = "/usr/share/fonts/opentype/noto/"
TH = {
    "hcs": ((15, 22, 19), (200, 64, 47), FD + "NotoSerifCJK-Black.ttc"),
    "b2b": ((10, 24, 40), (232, 89, 12), FD + "NotoSansCJK-Black.ttc"),
}
ink, accent, tfont = TH.get(theme, TH["b2b"])
W, H, X = 1080, 1920, 84
TOP, FACE_Y = 312, 1110
HEAD_SOLID, HEAD_FADE = 540, 940
FOOT_START, FOOT_SOLID = 1380, 1700
TEXT_LIMIT = 760          # 글자 묶음이 이 행을 넘으면 얼굴과 겹친다


def font(p, s):
    return ImageFont.truetype(p, s, index=1)


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def spaced(d, xy, text, f, fill, sp):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + sp
    return x


def spaced_w(d, text, f, sp):
    return sum(d.textlength(ch, font=f) + sp for ch in text) - sp


# 장면: 가로를 채우고, 얼굴 중심을 FACE_Y에 맞춰 아래로 내려 깐다
nw, nh = int(W * z), int(H * z)
sc = Image.open(src).convert("RGB").resize((nw, nh), Image.LANCZOS)
ox = int((nw - W) * ax)
off = int(FACE_Y - fy * nh)
off = max(H - nh, min(HEAD_SOLID, off))      # 장면 위 끝은 먹색 띠 아래에 숨기고, 아래는 비지 않게
sc = sc.crop((ox, 0, ox + W, nh))
sc = ImageEnhance.Contrast(sc).enhance(1.06)
sc = ImageEnhance.Color(sc).enhance(1.05)
im = Image.new("RGB", (W, H), ink)
im.paste(sc, (0, off))
im = im.convert("RGBA")

# 위아래 먹색
g = Image.new("L", (1, H), 0)
px = g.load()
for y in range(H):
    v = 1 - smooth((y - HEAD_SOLID) / (HEAD_FADE - HEAD_SOLID))
    v = max(v, smooth((y - FOOT_START) / (FOOT_SOLID - FOOT_START)))
    px[0, y] = int(255 * v)
sh = Image.new("RGBA", (W, H), ink + (255,))
sh.putalpha(g.resize((W, H)))
im = Image.alpha_composite(im, sh)

# 글자 묶음
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
size = 112
while True:
    ft = font(tfont, size)
    if max(d.textlength(t, font=ft) for t in (l1, l2)) <= W - 2 * X or size <= 70:
        break
    size -= 4
lh = int(size * 1.19)
fc = font(FD + "NotoSansCJK-Bold.ttc", 36)
fa = font(FD + "NotoSansCJK-Medium.ttc", 30)
fe = font(FD + "NotoSansCJK-Medium.ttc", 33)
y = TOP
d.rectangle([X, y, X + 70, y + 5], fill=accent + (255,))
y += 5 + 26
x = spaced(d, (X, y), ep, fc, (255, 255, 255, 235), 2)
d.rectangle([x + 16, y + 13, x + 18, y + 43], fill=(255, 255, 255, 110))
d.text((x + 34, y + 7), label, font=fa, fill=(255, 255, 255, 200))
y += 50 + 8
for t in (l1, l2):
    d.text((X + 2, y + 3), t, font=ft, fill=(0, 0, 0, 130))
    d.text((X, y), t, font=ft, fill=(250, 246, 238, 255))
    y += lh
if en:
    y += 14
    sp = 5
    while spaced_w(d, en, fe, sp) > W - 2 * X and sp > 1:
        sp -= 1
    spaced(d, (X + 1, y + 2), en, fe, (0, 0, 0, 120), sp)
    spaced(d, (X, y), en, fe, (255, 255, 255, 215), sp)
    y += 44
if y > TEXT_LIMIT:
    sys.exit("글자 묶음이 %d행까지 내려갑니다. 제목을 줄이세요(한 줄 8자 안팎)." % y)

Image.alpha_composite(im, ov).convert("RGB").save(out, quality=92)
print("표지 저장:", out, "글자 끝", y, "행, 장면 내림", off)
