import json,subprocess,textwrap
from PIL import Image,ImageDraw,ImageFont
B="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"; R="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
F=lambda p,s: ImageFont.truetype(p,s)
s=json.load(open("ep08_spec_v5.json",encoding="utf-8"))
short={"S0":"불릿타임: 멈춘 사무실 가운데 도윤, 카메라만 돈다. 0.3초 도윤 목소리 '뭐야, 이거.'","S20":"홍책사 클로즈업, 엽전 튕겨 받기(7화 고정 멘트 컷)","S2":"정지 화면 이름 카드, 디지털 시계 17:59","S6":"웃는 얼굴 정지, 빨간 도장, 되감기","S9":"눈만 내민 도윤 정지, 빨간 도장","S18":"팀장이 잔상 4겹을 남기며 순간 퇴장","S21":"엽전 꾸러미 8닢, hongchaksa.kr"}
def wrap(d,xy,txt,font,fill,width,lh):
    x,y=xy
    for para in txt.split("\n"):
        for ln in textwrap.wrap(para,width) or [""]:
            d.text((x,y),ln,font=font,fill=fill); y+=lh
    return y
lst=[]
for i,x in enumerate(s["shots"]):
    a,b=x["t"]; im=Image.new("RGB",(1080,1920),(18,20,26)); d=ImageDraw.Draw(im)
    blue=x["id"] in ("S0","S11","S12","S13","S13a","S13b","S14")
    if blue: im.paste((28,40,56),(0,0,1080,1920))
    d.text((60,60),"AI로 만든 가상인물",font=F(R,30),fill=(170,170,170))
    d.text((60,140),f"{a:.2f}~{b:.2f}초  {x['id']}",font=F(B,54),fill=(255,214,90))
    kind={"video":"씨댄스 영상","comp":"편집 합성","still":"사진과 편집"}[x["kind"]]
    d.text((60,215),kind,font=F(R,36),fill=(150,190,255))
    pic=short.get(x["id"]) or x.get("still","")
    pic=pic.replace(" 동료는 실존 인물을 닮지 않은 평범한 얼굴.","").replace(" 동료들은 실존 인물을 닮지 않은 평범한 얼굴.","")
    y=wrap(d,(60,320),pic,F(R,40),(215,215,215),24,58)
    if x.get("tag"): d.rectangle((60,y+30,300,y+100),fill=(40,40,40)); d.text((80,y+38),x["tag"],font=F(B,48),fill=(255,214,0))
    cap=x.get("caption","")
    if cap: wrap(d,(60,1080),cap,F(B,66),(255,255,255),14,86)
    if x.get("sub"): d.text((60,1270),x["sub"],font=F(B,44),fill=(230,230,230))
    if x.get("hud"): wrap(d,(60,250 if False else 900),"HUD: "+x["hud"],F(R,32),(230,190,90),30,44)
    if x.get("line"): wrap(d,(60,1380),f"{s['characters'][x['speaker']]['name']}: {x['line']}",F(B,56),(255,230,120),16,74)
    fx=" ".join(v for v in [x.get("camera",""),x.get("fx","")] if v)
    wrap(d,(60,1580),fx,F(R,30),(140,150,165),34,42)
    p=f"cards/{i:02d}.png"; im.save(p); lst.append((p,round(b-a,3)))
with open("cards/list.txt","w") as f:
    for p,dur in lst: f.write(f"file '{p.split('/')[1]}'\nduration {dur}\n")
    f.write(f"file '{lst[-1][0].split('/')[1]}'\n")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","cards/list.txt","-i","ep08_sfx_cue_preview.wav",
 "-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","160k","-shortest","홍책사_8화_글콘티_시간확인.mp4"],check=True)
