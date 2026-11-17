import json,subprocess,textwrap,sys
from PIL import Image,ImageDraw,ImageFont
B="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"; R="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
F=lambda p,s: ImageFont.truetype(p,s)
s=json.load(open(sys.argv[1],encoding="utf-8")); AUD=sys.argv[2]; OUT=sys.argv[3]
short={"S0a":"도윤 뒤 회의실 유리문이 터지며 포스트잇 폭풍(S0b 영상 앞부분)","S4a":"역재생: 노란 상자가 어깨에 철컥","S4b":"역재생: 모니터 받침대 가슴판 철컥","S4c":"역재생: 쟁반 방패 철컥",
"S4":"역재생: 헤드셋이 머리에 내려앉고 마이크 팔이 돈다(네 번째 박자, 소리 변주)","S8":"HUD 얼굴 컷 1: 남은 안건 37에서 38","S10":"HUD 얼굴 컷 2: 38에서 39","S12":"HUD 얼굴 컷 3: 메일 알림, 52로 뜀, 새 메일 13통",
"S11":"거인 왼 주먹이 정수기 옆 바닥을 친다, 물줄기","S13":"엽전이 날아 들어와 거의 정지, 세상이 청회색으로","S16":"엽전을 바닥에 놓자 금빛 바둑판 격자가 퍼진다","S18":"손가락이 헤드셋을 톡, 도윤만 깨어난다",
"S23":"포스트잇이 화면에 탁 붙는다","S27":"홍책사 클로즈업, 엽전 튕겨 받기(고정 멘트 컷)","S28":"엽전 꾸러미 9닢, hongchaksa.kr","S0b":"도윤 무표정, 어깨 포스트잇을 떼며"}
FROZ={"S13","S14","S15","S16","S17","S18","S19","S20","S21"}
def wrap(d,xy,txt,font,fill,width,lh):
    x,y=xy
    for para in txt.split("\n"):
        for ln in textwrap.wrap(para,width) or [""]:
            d.text((x,y),ln,font=font,fill=fill); y+=lh
    return y
lst=[]
for i,x in enumerate(s["shots"]):
    a,b=x["t"]; im=Image.new("RGB",(1080,1920),(18,20,26)); d=ImageDraw.Draw(im)
    if x["id"] in FROZ: im.paste((28,40,56),(0,0,1080,1920))
    if x["id"] in ("S24","S25","S26"): im.paste((34,32,28),(0,0,1080,1920))
    d.text((60,60),"AI로 만든 가상인물",font=F(R,30),fill=(170,170,170))
    d.text((60,140),f"{a:.2f}~{b:.2f}초  {x['id']}",font=F(B,54),fill=(255,214,90))
    kind={"video":"씨댄스 영상","comp":"편집 합성","still":"사진과 편집"}[x["kind"]]
    if x.get("reuse"): kind+=f" ({x['reuse']} 재사용)"
    if x.get("reverse"): kind+=", 역재생"
    d.text((60,215),kind,font=F(R,36),fill=(150,190,255))
    pic=short.get(x["id"]) or x.get("still","")
    for k in ["시간이 멈춘 세상: 화면 전체가 청회색으로 가라앉고, 허공의 물방울, 포스트잇, 먼지는 조각상처럼 완전히 정지. "]:
        pic=pic.replace(k,"")
    if "칼퇴 슈트:" in pic: pic=pic.split("칼퇴 슈트:")[0]+"칼퇴 슈트"+pic.split("모든 물건에 글자, 숫자, 로고 없음.")[-1]
    y=wrap(d,(60,320),pic[:170],F(R,38),(215,215,215),25,54)
    if x.get("tag"): d.rectangle((60,y+30,300,y+100),fill=(40,40,40)); d.text((80,y+38),x["tag"],font=F(B,48),fill=(255,214,0))
    if x.get("card"): d.text((60,y+30),x["card"]["title"],font=F(B,90),fill=(255,214,90)); d.text((60,y+140),x["card"]["sub"],font=F(R,40),fill=(230,230,230))
    cap=x.get("caption","")
    if cap and x["id"]!="S28": wrap(d,(60,1080),cap,F(B,66),(255,255,255),14,86)
    if x.get("sub"): d.text((60,1270),x["sub"],font=F(B,44),fill=(230,230,230))
    if x.get("note"): d.text((60,1000),x["note"],font=F(R,34),fill=(200,200,200))
    if x.get("hud"): wrap(d,(60,880),"HUD: "+x["hud"],F(R,32),(230,190,90),30,44)
    if x.get("line"): wrap(d,(60,1380),f"{s['characters'][x['speaker']]['name']}: {x['line']}",F(B,56),(255,230,120),16,74)
    if x["id"]=="S28": wrap(d,(60,1080),"9닢째\n무엇부터 할지 망설여질 땐 괘 하나\nhongchaksa.kr",F(B,56),(255,255,255),18,80)
    fx=" ".join(v for v in [x.get("camera",""),x.get("fx","")] if v)
    wrap(d,(60,1580),fx[:260],F(R,30),(140,150,165),34,42)
    p=f"cards/{i:02d}.png"; im.save(p); lst.append((p,round(b-a,3)))
with open("cards/list.txt","w") as f:
    for p,dur in lst: f.write(f"file '{p.split('/')[1]}'\nduration {dur}\n")
    f.write(f"file '{lst[-1][0].split('/')[1]}'\n")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","cards/list.txt","-i",AUD,
 "-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","160k","-shortest",OUT],check=True)
print("ok")
