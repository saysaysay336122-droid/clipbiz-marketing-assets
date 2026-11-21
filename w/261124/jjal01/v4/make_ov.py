"""v4 화면 글자 PNG 만들기."""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ov")
os.makedirs(D, exist_ok=True)
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SB = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
YEL = (255, 214, 80, 255)


def font(path, size):
    for i in range(10):
        f = ImageFont.truetype(path, size, index=i)
        if "KR" in f.getname()[0]:
            return f
    return ImageFont.truetype(path, size)


def center(d, y, s, f, fill=(255, 255, 255, 255), stroke=6):
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))


def new():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


im, d = new()
t = "AI로 만든 가상 캐릭터"
f = font(FR, 26)
w = d.textlength(t, font=f)
d.rounded_rectangle((26, 40, 26 + w + 28, 84), 12, fill=(0, 0, 0, 120))
d.text((40, 46), t, font=f, fill=(255, 255, 255, 215))
im.save(f"{D}/ai.png")

im, d = new()
f = font(FB, 66)
a, b = "홍책사 출근 ", "3초 전"
wa, wb = d.textlength(a, font=f), d.textlength(b, font=f)
x = (W - wa - wb) / 2
d.text((x, 118), a, font=f, fill=(255, 255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0, 255))
d.text((x + wa, 118), b, font=f, fill=YEL, stroke_width=7, stroke_fill=(0, 0, 0, 255))
im.save(f"{D}/cap.png")

im, d = new()
f = font(FB, 44)
x, y = 770, 430
w = d.textlength("홍책사", font=f)
d.rounded_rectangle((x, y, x + w + 36, y + 66), 14, fill=(15, 15, 20, 200))
d.text((x + 18, y + 6), "홍책사", font=f, fill=YEL)
im.save(f"{D}/name.png")

# 끝 화면: 아래쪽을 어둡게 깔고 제목
im, d = new()
for yy in range(980, H):
    a = int(min(1.0, (yy - 980) / 260) * 200)
    d.line([(0, yy), (W, yy)], fill=(10, 10, 14, a))
center(d, 1170, "오늘의 운수", font(SB, 128), stroke=0)
center(d, 1335, "홍책사", font(SB, 96), fill=YEL, stroke=0)
center(d, 1478, "hongchaksa.kr", font(FB, 44), fill=(235, 235, 235, 255), stroke=0)
im.save(f"{D}/end.png")
print("ok")
