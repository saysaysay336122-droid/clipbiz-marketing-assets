import json,re,sys
s=json.load(open("ep08_spec_v5.json",encoding="utf-8"))
K={"tick":"초침","thunk":"쿵","whoosh":"휙","scratch":"레코드 긁힘","rewind":"되감기","chime":"풍경","coin":"엽전","riser":"상승음","boom":"낮은 충격음","pop":"뽁","click":"딸깍","bell":"종","logo":"소리 상표","ding":"딩","heart":"두근","bell":"종","tapestop":"테이프 정지","tapestart":"테이프 재생"}
short={"S0":"불릿타임 영상 일부: 멈춘 사무실 가운데 도윤, 카메라만 돈다(S11 재사용), 0.3초에 도윤 목소리 '뭐야, 이거.'","S20":"홍책사 클로즈업, 엽전을 튕겨 받는다(7화 고정 멘트 컷 재사용)",
"S2":"S3 시작 사진 정지, 이름 카드와 디지털 시계 17:59",
"S6":"S4 마지막 프레임 정지, 빨간 도장 '작전 실패 1', 3배속 되감기",
"S9":"S7 칸막이 위로 눈만 내민 프레임 정지, 빨간 도장 '작전 실패 2'",
"S18":"S17 마지막 프레임, 팀장이 출입문 쪽으로 잔상 4겹을 남기며 사라짐",
"S21":"끝 화면: 엽전 꾸러미 8닢(축사, 회식, 소개팅, 빼빼로, 택시, 다녀와, 무르기, 퇴근), 엽전 튕기기"}
rows=["| 시간(초) | 샷 | 화면 | 대사 | 자막 | 소리 | 카메라와 효과 |","| --- | --- | --- | --- | --- | --- | --- |"]
for x in s["shots"]:
    a,b=x["t"]; kind={"video":"영상","comp":"합성","still":"사진"}[x["kind"]]
    pic=short.get(x["id"]) or x.get("still","")
    pic=pic.replace(" 동료는 실존 인물을 닮지 않은 평범한 얼굴.","").replace(" 동료들은 실존 인물을 닮지 않은 평범한 얼굴.","")
    line=""
    if x.get("line"): line=f"{s['characters'][x['speaker']]['name']}: {x['line']}"
    if x["id"]=="S20": line="홍책사: 홍책사 한 수면, 됐지?"
    cap=x.get("caption","")
    if x.get("tag"): cap=f"이름표 '{x['tag']}', {cap}"
    if x.get("sub"): cap=f"{cap}, 작은 자막 '{x['sub']}'"
    if x.get("hud"): cap=(cap+", " if cap else "")+"HUD: "+x["hud"]
    snd=", ".join(f"{K.get(n,n)} {t:g}" for t,n,g in x.get("sfx",[]))
    cam=" ".join(v for v in [x.get("camera",""),x.get("fx","")] if v)
    rows.append(f"| {a:g}~{b:g} | {x['id']} {kind} | {pic} | {line} | {cap} | {snd} | {cam} |")
md="\n".join(rows)
bad=[c for c in "·・‧∙•!…—–→←※" if c in md]
print(len(md), bad)
open("conti_table.md","w",encoding="utf-8").write(md)
