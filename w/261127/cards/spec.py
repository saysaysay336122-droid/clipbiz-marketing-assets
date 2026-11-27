# 홍책사 카드 영상 묶음(2026-11-27): 2027 띠별 12편(고급정보형), 직언 4편(재미형)
# 띠별 달 근거: 정미년(丁未) 월지. 寅 2월(입춘)부터 子 12월까지, 절기로 달이 바뀐다.
#   좋은 달 = 그 띠 글자와 육합 또는 삼합인 달, 쉬어 갈 달 = 충(양띠만 형) 인 달.
BR = "子丑寅卯辰巳午未申酉戌亥"
KO = dict(zip(BR, "자축인묘진사오미신유술해"))
MONTH = {"寅": 2, "卯": 3, "辰": 4, "巳": 5, "午": 6, "未": 7, "申": 8, "酉": 9, "戌": 10, "亥": 11, "子": 12}
YUKHAP = {frozenset(p) for p in ["子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"]}
SAMHAP = ["申子辰", "亥卯未", "寅午戌", "巳酉丑"]
CHUNG = {frozenset(p) for p in ["子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥"]}
HYEONG = {frozenset(p) for p in ["丑戌", "戌未", "丑未"]}


def rel(a, b):
    if frozenset(a + b) in YUKHAP:
        return "육합"
    if any(a in s and b in s for s in SAMHAP) and a != b:
        return "삼합"
    if frozenset(a + b) in CHUNG:
        return "충"
    if frozenset(a + b) in HYEONG:
        return "형"
    return ""


BODY = {
    "삼합": "같은 편이 모이는 달,\n일 벌이기 좋아요.",
    "육합": "짝이 맞는 달,\n부탁하고 손잡기 좋아요.",
    "충": "마주 부딪히는 달,\n큰 결정은 한 박자 늦게.",
    "형": "서로 걸리는 달,\n말과 계약은 두 번 확인.",
}
FOOT = {
    "삼합": "{a}({ah})와 {b}({bh})가 같은 편(삼합)인 달",
    "육합": "{a}({ah})와 {b}({bh})가 짝(육합)인 달",
    "충": "{a}({ah})와 {b}({bh})가 마주 부딪히는(충) 달",
    "형": "{a}({ah})와 {b}({bh})가 서로 걸리는(형) 달",
}

# 띠, 글자, 영어, 해(년생), 올해 한 줄(큰 글), 올해 한 수(작은 글), 올해 근거, 좋은 달 둘, 쉬어 갈 달
TTI = [
    ("쥐", "子", "rat", ["72", "84", "96"], ["말 한마디가", "오해로 번지는 해"], "보내기 전에 한 번 더 읽어요.", "미(未)와 자(子)는 서로 꺼리는 사이(원진)", ["辰", "申"], "午"),
    ("소", "丑", "ox", ["73", "85", "97"], ["판이 자주", "바뀌는 해"], "계획은 연필로 써요.", "축(丑)과 미(未)가 마주 부딪혀요(충)", ["巳", "子"], "未"),
    ("호랑이", "寅", "tiger", ["74", "86", "98"], ["크게 튀지", "않는 해"], "그래서 꾸준한 쪽이 이겨요.", "정미년과 크게 부딪히는 글자가 없어요", ["午", "亥"], "申"),
    ("토끼", "卯", "rabbit", ["75", "87", "99"], ["올해 글자와", "같은 편인 해"], "미뤄 둔 일, 올해 꺼내요.", "해(亥), 묘(卯), 미(未)는 같은 편(삼합)", ["未", "戌"], "酉"),
    ("용", "辰", "dragon", ["76", "88", "00"], ["남 일에 힘이", "새기 쉬운 해"], "내 일부터 챙겨요.", "정미년과 크게 부딪히는 글자가 없어요", ["酉", "子"], "戌"),
    ("뱀", "巳", "snake", ["77", "89", "01"], ["흐름을 타는 해"], "혼자 끙끙대지 말고 같이 가요.", "사(巳), 오(午), 미(未)는 같은 방향(방합)", ["申", "酉"], "亥"),
    ("말", "午", "horse", ["78", "90", "02"], ["짝이 맞는 해"], "혼자 하던 일, 둘이 하면 빨라져요.", "오(午)와 미(未)는 짝(육합)", ["寅", "未"], "子"),
    ("양", "未", "goat", ["79", "91", "03"], ["내 띠의 해"], "다 하려 말고 하나만 크게 해요.", "올해 글자 미(未)가 내 띠와 같아요", ["卯", "午"], "戌"),
    ("원숭이", "申", "monkey", ["80", "92", "04"], ["재주를 보여 줄", "자리가 생기는 해"], "공짜로 해 주던 일, 값을 매겨 봐요.", "정미년과 크게 부딪히는 글자가 없어요", ["辰", "巳"], "寅"),
    ("닭", "酉", "rooster", ["81", "93", "05"], ["정리가 운을", "부르는 해"], "안 쓰는 구독부터 끊어요.", "정미년과 크게 부딪히는 글자가 없어요", ["辰", "巳"], "卯"),
    ("개", "戌", "dog", ["82", "94", "06"], ["바른말이", "날카롭게 들리는 해"], "맞는 말도 반만 해요.", "술(戌)과 미(未)는 서로 걸리는 사이(형)", ["卯", "午"], "辰"),
    ("돼지", "亥", "pig", ["83", "95", "07"], ["같은 편이", "많아지는 해"], "사람 모이는 자리에 일단 가요.", "해(亥), 묘(卯), 미(未)는 같은 편(삼합)", ["寅", "未"], "巳"),
]

# 게시일(띠별 화목토, 직언 월수금일)
TTI_DATES = ["2026-11-28", "2026-12-01", "2026-12-03", "2026-12-05", "2026-12-08", "2026-12-10",
             "2026-12-12", "2026-12-15", "2026-12-17", "2026-12-19", "2026-12-22", "2026-12-24"]
JIK_DATES = ["2026-11-29", "2026-11-30", "2026-12-02", "2026-12-04"]

# 장면 사진(87년생 토끼띠 영상의 홍책사 장면, 초)
STILLS = {"read": 12.0, "smile": 18.5, "calm": 19.0, "warm": 21.5, "smirk": 22.0, "mid": 22.5,
          "mid2": 16.0, "fan": 25.0, "talk": 10.0, "coin": 8.0}


def tti_videos():
    out = []
    order = ["read", "smile", "calm", "smirk", "mid", "mid2", "talk", "coin"]
    for i, (nm, br, en, yrs, yline, ytip, yfoot, goods, rest) in enumerate(TTI):
        goods = sorted(goods, key=lambda b: MONTH[b])
        scenes = []
        years = ", ".join(yrs) + "년생"
        scenes.append(dict(dur=2.8, still=order[i % 8], tag="2027 띠별 한 수", big=[years, f"{nm}띠"],
                           accent="2027년 좋은 달은 따로 있어요", hook=True))
        scenes.append(dict(dur=3.8, still=order[(i + 3) % 8], tag="올해 한 줄", big=yline, body=ytip, foot=yfoot))
        for k, g in enumerate(goods):
            r = rel(br, g)
            assert r in ("육합", "삼합"), (nm, g, r)
            scenes.append(dict(dur=3.6, still=order[(i + 5 + k * 2) % 8], tag=f"좋은 달 {'하나' if k == 0 else '둘'}",
                               big=[f"{MONTH[g]}월쯤"], body=BODY[r],
                               foot=FOOT[r].format(a=KO[br], ah=br, b=KO[g], bh=g)))
        r = rel(br, rest)
        assert r in ("충", "형"), (nm, rest, r)
        scenes.append(dict(dur=3.6, still=order[(i + 2) % 8], tag="쉬어 갈 달", big=[f"{MONTH[rest]}월쯤"], body=BODY[r],
                           foot=FOOT[r].format(a=KO[br], ah=br, b=KO[rest], bh=rest), rest=True))
        scenes.append(dict(dur=3.6, still="warm" if i % 2 == 0 else "fan", end=True,
                           tag="2027 한 수", big=["내 생일로 보는 2027"],
                           body="1월생과 2월 초생은 입춘 전이면\n앞 띠로 봐요.", url="hongchaksa.kr/2027",
                           small="결과부터 무료로 봐요"))
        out.append(dict(id=f"tti{i + 1:02d}", kind="tti", name=nm, en=en, br=br, years=yrs, yline=yline, ytip=ytip,
                        goods=[MONTH[g] for g in goods], rest=MONTH[rest], rest_type=rel(br, rest),
                        date=TTI_DATES[i], scenes=scenes, music=("theme", ["F", "D", "Bb", "C", "G", "Eb"][i % 6])))
    return out


JIK = [
    dict(id="jik01", slug="money", hook=["올해 돈 안 모인 거,"], accent="운 탓 아니에요",
         why=["들어올 길보다", "새는 길이 많았어요"], whybody="사주에서 재물은 들어오는 문과\n나가는 문을 같이 봐요.",
         tip=["통장은 두 개로"], tipbody="쓸 돈과 안 쓸 돈,\n그것부터 나눠요.", endbody="내 재물 흐름은\n생일로 따로 봐요.",
         stills=["smirk", "read", "coin", "warm"], key="F"),
    dict(id="jik02", slug="reply", hook=["연락 기다리는 거,"], accent="운이 아니라 성격이에요",
         why=["답장 속도는", "마음보다 하루를 닮았어요"], whybody="바쁜 날엔 좋아하는 사람한테도\n늦어요.",
         tip=["할 말은 오전에"], tipbody="밤에 보낸 장문은\n아침에 후회해요.", endbody="그 사람과 나,\n2027 흐름은 생일로 봐요.",
         stills=["calm", "mid", "smirk", "fan"], key="D"),
    dict(id="jik03", slug="job", hook=["이직 고민만 1년째면,"], accent="그건 고민이 아니라 습관이에요",
         why=["정미년은", "정리하는 쪽이 웃는 해"], whybody="미(未)는 한 해를 갈무리하는\n흙의 글자예요.",
         tip=["이력서부터", "고쳐 둬요"], tipbody="가든 남든, 고친 이력서가 있으면\n마음이 편해요.", endbody="내 일 운은\n생일로 따로 봐요.",
         stills=["mid2", "talk", "read", "warm"], key="Bb"),
    dict(id="jik04", slug="plan", hook=["새해 계획 열 개면,"], accent="하나도 못 해요",
         why=["2027년은", "하나만 크게 하는 해"], whybody="불(丁)이 흙(未) 위에서 타는 해,\n한곳을 오래 데워야 익어요.",
         tip=["계획은 세 줄만"], tipbody="하고 싶은 것, 버릴 것,\n지킬 것 하나씩.", endbody="2027 내 흐름은\n생일로 따로 봐요.",
         stills=["smile", "coin", "mid", "fan"], key="C"),
]


def jik_videos():
    out = []
    for i, j in enumerate(JIK):
        s = j["stills"]
        scenes = [
            dict(dur=3.0, still=s[0], tag="홍책사 직언", big=j["hook"], accent=j["accent"], accent_size=96, hook=True),
            dict(dur=4.0, still=s[1], tag="왜냐면", big=j["why"], body=j["whybody"]),
            dict(dur=4.0, still=s[2], tag="2027 한 수", big=j["tip"], body=j["tipbody"]),
            dict(dur=3.6, still=s[3], end=True, tag="2027 한 수", big=["내 생일로 보는 2027"], body=j["endbody"],
                 url="hongchaksa.kr/2027", small="결과부터 무료로 봐요"),
        ]
        out.append(dict(id=j["id"], kind="jik", slug=j["slug"], date=JIK_DATES[i], scenes=scenes, src=j,
                        music=("comedy", j["key"])))
    return out


ALL = tti_videos() + jik_videos()

if __name__ == "__main__":
    for v in ALL:
        t = sum(s["dur"] for s in v["scenes"])
        if v["kind"] == "tti":
            print(v["id"], v["date"], v["name"], v["goods"], v["rest"], v["rest_type"], round(t, 1))
        else:
            print(v["id"], v["date"], v["slug"], round(t, 1))
