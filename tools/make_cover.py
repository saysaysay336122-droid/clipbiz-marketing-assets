# 영상 표지 만들기. 사용: python3 tools/make_cover.py 장면.png 표지.jpg "홍책사 5화" "첫 줄" "둘째 줄" [AI 표기] [영어 한 줄] [hcs|b2b]
# 장면을 1.12배로 키워 위쪽 원래 AI 표기를 밀어내고, 화면 가득 쓴 장면 아래에 먹색 그러데이션을 깐다.
# 글은 왼쪽 정렬: 짧은 색 줄, 회차와 AI 표기 한 줄, 두 줄 제목, 영어 한 줄. 인스타 3:4 그리드(위아래 240px 잘림) 안에서 끝난다.
# 테마를 주지 않으면 회차 글에 홍책사나 작전회의가 있을 때 hcs(명조, 붉은 줄), 그 밖에는 b2b(고딕, 주황 줄).
import sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
a=sys.argv[1:]
src,out,ep,l1,l2=a[:5]
label=a[5] if len(a)>5 and a[5] else "AI로 만든 가상인물"
en=a[6].upper() if len(a)>6 else ""
theme=a[7] if len(a)>7 else ("hcs" if ("홍책사" in ep or "작전회의" in ep) else "b2b")
FD="/usr/share/fonts/opentype/noto/"
TH={"hcs":((15,22,19),(200,64,47),FD+"NotoSerifCJK-Black.ttc"),"b2b":((10,24,40),(232,89,12),FD+"NotoSansCJK-Black.ttc")}
ink,accent,tfont=TH.get(theme,TH["b2b"])
W,H,X=1080,1920,84
def font(p,s): return ImageFont.truetype(p,s,index=1)
im=Image.open(src).convert("RGB").resize((1210,2150),Image.LANCZOS).crop((65,207,1145,2127))
im=ImageEnhance.Contrast(im).enhance(1.06); im=ImageEnhance.Color(im).enhance(1.05)
g=Image.new("L",(1,H),0); px=g.load()
for y in range(H):
    v=0
    if y>940:
        u=min(1,(y-940)/440); v=int(251*u*u*(3-2*u))
    if y<300: v=max(v,int(80*(1-y/300)))
    px[0,y]=v
sh=Image.new("RGBA",(W,H),ink+(255,)); sh.putalpha(g.resize((W,H)))
im=Image.alpha_composite(im.convert("RGBA"),sh)
ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
def spaced(xy,text,f,fill,sp):
    x,y=xy
    for ch in text:
        d.text((x,y),ch,font=f,fill=fill); x+=d.textlength(ch,font=f)+sp
def spaced_w(text,f,sp): return sum(d.textlength(ch,font=f)+sp for ch in text)-sp
size=128
while True:
    ft=font(tfont,size)
    if max(d.textlength(t,font=ft) for t in (l1,l2))<=W-2*X or size<=70: break
    size-=4
lh=int(size*1.20)
fa=font(FD+"NotoSansCJK-Medium.ttc",27); fc=font(FD+"NotoSansCJK-Bold.ttc",38); fe=font(FD+"NotoSansCJK-Medium.ttc",35)
y=1648-(5+28+50+14+lh*2+(20+46 if en else 0))
d.rectangle([X,y,X+70,y+5],fill=accent+(255,)); y+=33
spaced((X,y),ep,fc,(255,255,255,228),2)
d.text((W-X-d.textlength(label,font=fa),y+9),label,font=fa,fill=(255,255,255,178)); y+=64
for t in (l1,l2):
    d.text((X+2,y+3),t,font=ft,fill=(0,0,0,110)); d.text((X,y),t,font=ft,fill=(250,246,238,255)); y+=lh
if en:
    sp=5
    while spaced_w(en,fe,sp)>W-2*X and sp>1: sp-=1
    spaced((X,y+22),en,fe,(255,255,255,205),sp)
Image.alpha_composite(im,ov).convert("RGB").save(out,quality=92)
