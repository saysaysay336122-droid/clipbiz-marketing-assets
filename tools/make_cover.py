# 영상 표지 만들기. 사용: python3 tools/make_cover.py 장면.png 표지.jpg "홍책사 5화" "첫 줄" "둘째 줄" [label]
# 장면을 1.12배로 키워 위쪽 원래 AI 표기를 밀어내고, 3:4 그리드 안전 구역(위 240px, 아래 240px 제외)에 AI 표기, 회차 띠, 두 줄 문구를 얹는다.
import sys
from PIL import Image, ImageDraw, ImageFont
src,out,ep,l1,l2=sys.argv[1:6]; label=sys.argv[6] if len(sys.argv)>6 else "AI로 만든 가상인물"
im=Image.open(src).convert("RGB").resize((1210,2150)); im=im.crop((65,130,1145,2050))
ov=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(ov)
for y in range(880,1920):
    a=int(245*min(1,(y-880)/200)); d.line([(0,y),(1080,y)],fill=(0,0,0,a))
im=Image.alpha_composite(im.convert("RGBA"),ov)
d=ImageDraw.Draw(im)
B="/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
fb=ImageFont.truetype(B,118,index=1); fs=ImageFont.truetype(B,40,index=1); fe=ImageFont.truetype(B,54,index=1)
# AI label (always), episode badge at fixed spot
d.rounded_rectangle([40,262,40+d.textlength(label,font=fs)+40,326],12,fill=(0,0,0,170)); d.text((60,270),label,font=fs,fill="white")
w=d.textlength(ep,font=fe); d.rounded_rectangle([(1080-w)/2-30,1060,(1080+w)/2+30,1144],16,fill=(232,182,72)); d.text(((1080-w)/2,1066),ep,font=fe,fill=(20,20,20))
y=1180
for i,t in enumerate([l1,l2]):
    w=d.textlength(t,font=fb); col=(255,255,255) if i==0 else (255,214,102)
    d.text(((1080-w)/2,y),t,font=fb,fill=col,stroke_width=8,stroke_fill=(0,0,0)); y+=150
im.convert("RGB").save(out,quality=90)
