"""홍책사 10화 송년회 건배사 설계서 생성. python3 mk_ep10_spec.py -> ep10_spec.json"""
import json

S8 = json.load(open("../261123/ep08_spec_v6.json", encoding="utf-8"))
CH = S8["characters"]
OFFICE_URL = "https://cdn.aistudio.dropshot.io/public/jobs/prod/mcp_16c817442bd9418a8fad8bdd69aea44a/output/output_0.png"
COIN_URL = "https://cdn.aistudio.dropshot.io/public/jobs/prod/mcp_5dabf3348afb4cfb847faf57b6253dcb/output/output_0.png"

doyun = dict(CH["doyun"])
doyun["fixed"] = ("인물 도윤: 20대 후반 한국 남성 3년 차 회사원, 볼륨 있게 손질한 앞머리가 이마를 살짝 덮는 검은 머리, 웃으면 오른쪽 볼에 보조개, "
                  "맑고 자신감 있는 눈빛, 어깨선이 맞는 슬림 핏 남색 니트 카디건을 앞섶을 열어 입고, 첫 단추를 푼 흰 옥스퍼드 셔츠의 소매를 팔뚝까지 걷어 올렸다, "
                  "은색 손목시계, 참고 사진 얼굴과 똑같이. 얼굴 생김새는 참고 사진 그대로 두고 머리 손질, 피부 결, 옷 핏, 자세만 단정하게 정돈.")
choi = dict(CH["choi"])
hong = dict(CH["hong"])
hong["fixed"] = ("인물 홍책사: 30대 후반 한국 남성, 고깃집 직원으로 일하지만 늘 입는 몸에 잘 맞는 검은 울 터틀넥과 허리를 단정하게 묶은 남색 캔버스 앞치마, "
                 "팔뚝까지 살짝 걷은 소매, 단정하게 정돈한 짧은 머리, 차분하고 깊은 눈빛과 여유 있는 미소, 참고 사진 얼굴과 똑같이. "
                 "얼굴 생김새는 참고 사진 그대로 두고 머리 손질, 피부 결, 옷 핏, 자세만 단정하게 정돈.")

TEAM = "뒤쪽 팀원 남녀 셋은 초점 밖의 흐린 옆모습이나 뒷모습으로만 보이고 얼굴이 또렷하지 않다."
GRILL = "테이블 가운데 둥근 숯불 불판에서 김이 오른다."

sets = {
    "gogi": {"model": "nano-banana-pro", "desc": (
        "겨울 저녁 한국 고깃집의 회식용 단체 룸. 긴 원목 테이블 두 개를 붙였고 가운데에 둥근 숯불 불판 세 개, 은색 환기 덕트가 불판 위로 내려와 있다. "
        "천장의 호박색 백열 펜던트 조명, 창호지 미닫이문, 나무 판넬 벽. 테이블 위 상추 바구니, 쌈장 종지, 상표 없는 초록 유리병과 작은 투명 잔, 물병, 집게와 가위. "
        "벽, 메뉴판, 병, 잔에 글자와 숫자 없음.")},
    "office": {"model": "nano-banana-pro", "url": OFFICE_URL, "desc": S8["sets"]["office"]["desc"].replace("저녁 5시 59분 ", "").replace("오른쪽 큰 창밖은 해 질 녘 주황빛 하늘이 푸른 저녁으로 바뀌는 중이고 천장 형광등이 켜져 있다.", "오른쪽에 큰 창이 있고 천장 형광등이 켜져 있다.")},
}

style = {
    "still": ("실사 한국 드라마의 한 장면, 한 장의 단일 장면, 분할 화면 없음, 인물 얼굴에는 45도 부드러운 키 라이트와 은은한 림 라이트, "
              "눈에 캐치라이트, 얼굴이 크게 나오는 컷은 50~85mm 화각으로 얼굴 왜곡 없음, 얕은 심도, 자연스러운 피부결, 과한 보정 없음, 따뜻한 색감, "
              "잔과 병에 상표 없음, 화면에 글자와 자막과 로고와 숫자 없음."),
    "video": ("실사 한국 직장 코미디 드라마, 9:16 세로, 720p, 호박색 백열등과 불판의 붉은 빛, 인물 얼굴에 부드러운 키 라이트와 은은한 림 라이트, "
              "자연스러운 피부결과 움직임, 마시는 동작 없음, 배경음악 없음, 화면에 글자와 자막과 로고와 숫자 없음."),
    "negative": ("자막, 글자, 숫자, 워터마크, 로고, 상표 라벨, 얼굴 변형, 다른 얼굴로 바뀜, 손가락 왜곡, 과한 보정, 만화풍, 배경음악, 다른 사람 목소리, "
                 "장면 전환, 화면 분할, 과한 피부 보정, 턱선 변경, 컷마다 다른 얼굴 비율, 술을 마시는 동작, 실존 인물이나 연예인을 닮은 얼굴"),
}

# (id, 길이, 정의)
plan = [
    ("S1", 2.4, dict(kind="video", gen_sec=4, use=[0.2, 2.6], set="gogi", chars=["doyun", "choi"], audio=True, speaker="doyun",
                     line="그리고 이월에는,", cue=0.2,
                     framing="미디엄 숏, 도윤 가슴 높이, 전경에 새까맣게 탄 고기가 연기를 내는 불판이 흐릿하게, 뒤쪽 테이블 끝에 최 팀장이 초점 밖으로 보인다, 50mm.",
                     camera="아주 느린 푸시 인, 1.6초에 초점이 뒤쪽 최 팀장에게 옮겨 간다.",
                     still=f"도윤이 테이블 앞에 서서 작은 투명 잔을 가슴 높이로 든 채 손가락을 하나씩 꼽으며 진지하게 말하는 중, 앞 불판의 고기는 숯처럼 까맣게 탔다. 뒤쪽 최 팀장은 주먹으로 입을 가리고 하품을 참는다. {TEAM}",
                     action="0.3초 앞 불판의 탄 고기에서 작은 불꽃이 확 올랐다 꺼진다, 0~1.5초 도윤은 눈치채지 못하고 손가락을 꼽으며 열심히 말한다, 1.6초부터 초점이 뒤로 옮겨 가고 최 팀장이 크게 하품을 하다 주먹으로 가린다, 앞 불판의 연기가 계속 오른다.",
                     caption="송년회 건배사 4분째\n아직 2월", hud="1트",
                     sfx=[[0.0, "sizzle", 0.7], [0.0, "tickh", 0.35], [0.3, "gust", 0.5]])),
    ("S3", 0.6, dict(kind="video", gen_sec=4, use=[0.0, 0.6], set="gogi", chars=["hong"], audio=False,
                     framing="익스트림 클로즈업, 테이블 높이 매크로, 원목 결이 보이는 테이블 모서리, 85mm.",
                     camera="고정, 동전이 서서 도는 순간만 아주 살짝 줌 인.",
                     still="검은 터틀넥 소매의 손가락이 가운데 네모 구멍이 뚫린 오래된 놋쇠 엽전 하나를 원목 테이블 위에 세워 막 튕기려는 순간. 얼굴은 화면 밖.",
                     action="0~0.4초 손가락이 엽전을 튕긴다, 0.4초부터 엽전이 선 채로 빠르게 돈다, 손은 화면 밖으로 빠진다.",
                     refs_extra=[COIN_URL], sfx=[[0.05, "coinx", 0.8]])),
    ("R1", 0.6, dict(kind="comp", comp="rewind", base="S1과 S3을 4배속으로 거꾸로, 위아래로 흐르는 되감기 줄무늬와 색 번짐", caption="다시",
                     sfx=[[0.0, "rewind", 0.9]])),
    ("S4", 2.4, dict(kind="video", gen_sec=4, use=[0.3, 2.7], set="gogi", chars=["choi"], audio=True, speaker="choi",
                     line="마무리는 도윤 씨.", cue=0.4,
                     framing="미디엄 클로즈업, 테이블 끝 상석의 최 팀장, 눈높이, 85mm.",
                     camera="고정, 대사 끝에 아주 살짝 푸시 인.",
                     still="최 팀장이 작은 투명 잔을 들어 올리며 도윤 쪽을 손바닥으로 가리키는 순간, 너그러운 미소. 앞 불판의 고기는 막 올려 붉고 싱싱하다.",
                     action="0~0.4초 잔을 들어 올린다, 0.4초부터 손바닥으로 화면 밖 도윤을 가리키며 말한다.",
                     tag="도윤과 최 팀장, 8화 17:59 그 팀", hud="2트",
                     sfx=[[0.0, "sizzle", 0.5], [0.05, "tapestart", 0.6]])),
    ("S5", 1.5, dict(kind="video", gen_sec=4, use=[0.2, 1.7], set="gogi", chars=["doyun"], audio=True, speaker="doyun",
                     line="청바지.", cue=0.3,
                     framing="미디엄 숏, 약간 로우 앵글, 50mm.",
                     camera="고정.",
                     still="도윤이 자신만만하게 잔을 높이 들고 입을 크게 벌려 구호를 외치기 직전, 가슴을 편 자세.",
                     action="0~0.3초 숨을 들이쉰다, 0.3초 잔을 번쩍 들며 크게 외친다, 그 뒤 기대에 찬 얼굴로 굳는다.")),
    ("S6", 0.8, dict(kind="still", set="gogi", chars=[],
                     framing="와이드 숏, 도윤의 어깨 너머 시점, 35mm.",
                     still=f"고깃집 룸 전체가 조용하다. 테이블에 앉은 팀원들이 잔을 든 채 아무도 따라 외치지 않고 멀뚱히 도윤을 본다, 불판 위 고기만 지글거린다. {TEAM}",
                     sfx=[[0.0, "sizzle", 0.4]])),
    ("S7", 2.4, dict(kind="video", gen_sec=4, use=[0.2, 2.6], set="gogi", chars=["choi"], audio=True, speaker="choi",
                     line="청춘은 바로 지금.", cue=0.3,
                     framing="미디엄 숏, 최 팀장 정면, 50mm.",
                     camera="고정, 0.8초에 짧은 크래시 줌 인.",
                     still="조용한 룸에서 최 팀장 혼자 엉덩이를 반쯤 들고 잔을 높이 든 채 진지한 얼굴로 구호를 받아 주려는 순간.",
                     action="0~0.3초 혼자 일어선다, 0.3초부터 잔을 높이 들고 힘차게 혼자 외친다, 끝에 주변을 둘러본다.")),
    ("S8", 0.6, dict(kind="video", reuse="S3", use=[0.0, 0.6], sfx=[[0.05, "coinx", 0.8]])),
    ("R2", 0.6, dict(kind="comp", comp="rewind", base="S7, S6, S5를 4배속으로 거꾸로, R1과 같은 줄무늬", caption="다시",
                     sfx=[[0.0, "rewind", 0.9]])),
    ("S9", 0.8, dict(kind="video", reuse="S4", use=[0.3, 1.1], hud="3트", sfx=[[0.05, "tapestart", 0.6]])),
    ("S10", 3.2, dict(kind="video", gen_sec=4, use=[0.2, 3.4], set="gogi", chars=["hong", "doyun"], audio=True, speaker="hong",
                      line="제일 많이 들은 말, 뭐예요?", cue=0.3,
                      framing="미디엄 클로즈업, 홍책사 얼굴 정면, 전경 왼쪽에 도윤의 어깨가 흐릿하게, 85mm.",
                      camera="아주 느린 푸시 인.",
                      still="고기 접시를 테이블에 내려놓던 홍책사가 몸을 숙여 서 있는 도윤의 귀 쪽으로 다가와 조용히 묻는 순간, 차분한 미소.",
                      action="0~0.3초 접시를 내려놓는다, 0.3초부터 도윤 쪽으로 몸을 숙여 낮고 천천히 묻는다, 끝에 살짝 미소 짓는다.",
                      tag="홍책사", sfx=[[0.0, "chime", 0.5]])),
    ("F1", 0.8, dict(kind="still", set="office", chars=["choi", "doyun"],
                     framing="미디엄 숏, 35mm, 아침 햇빛.",
                     still="아침 사무실, 막 출근해 커피 컵을 내려놓는 도윤 책상 옆에 최 팀장이 다가와 칸막이에 손을 얹고 말을 거는 순간.",
                     caption="09:00", sfx=[[0.0, "swishr", 0.6]])),
    ("F2", 1.1, dict(kind="still", set="office", chars=["choi", "doyun"],
                     framing="미디엄 와이드 숏, 35mm, 해 질 녘 주황 역광.",
                     still="퇴근 직전, 검은 백팩을 메고 유리 출입문 쪽으로 가던 도윤 앞에 최 팀장이 서류철을 들고 막아서는 순간.",
                     caption="17:59", sfx=[[0.0, "swishr", 0.6], [0.3, "tickh", 0.5]])),
    ("F3", 1.3, dict(kind="comp", comp="messenger", base="불 꺼진 방의 어두운 휴대폰 화면 가득 상표 없는 일반 메신저 알림 한 장, 시각 23:40",
                     chat_title="최 팀장", chat=["도윤 씨, 잠깐 시간 돼?"], caption="23:40",
                     sfx=[[0.1, "mail", 0.8]])),
    ("S12", 3.2, dict(kind="video", gen_sec=4, use=[0.2, 3.4], set="gogi", chars=["doyun"], audio=True, speaker="doyun",
                      line="잠깐 시간 돼, 하면 내년에.", cue=0.3,
                      framing="미디엄 숏, 도윤 정면 눈높이, 50mm.",
                      camera="고정.",
                      still="도윤이 자신감 있는 미소로 잔을 가슴 높이에 들고 팀원들을 둘러보며 손바닥을 펴 규칙을 알려 주는 순간.",
                      action="0~0.3초 숨을 고른다, 0.3초부터 웃으며 규칙을 또박또박 알려 준다, 끝에 잠깐 멈춰 모두를 본다.",
                      caption="선창 잠깐 시간 돼?\n후창 내년에")),
    ("S13", 1.9, dict(kind="video", gen_sec=4, use=[0.1, 2.0], set="gogi", chars=["doyun"], audio=True, speaker="doyun",
                      line="잠깐 시간 돼?", cue=0.2,
                      framing="미디엄 숏, 로우 앵글, 35mm, 머리 위 펜던트 조명이 후광처럼.",
                      camera="고정, 0.2초에 짧은 크래시 줌 인.",
                      still="도윤이 잔을 머리 위로 번쩍 들어 올리며 크게 선창하기 직전, 자신만만한 얼굴.",
                      action="0~0.2초 잔을 번쩍 든다, 0.2초부터 크고 또렷하게 선창한다, 그 뒤 잔을 든 채 대답을 기다린다.",
                      sfx=[[0.0, "drum", 0.6]])),
    ("S14", 0.4, dict(kind="still", set="gogi", chars=["choi"],
                      framing="와이드 숏, 테이블 옆 낮은 시점, 35mm.",
                      still=f"모두 잔을 든 채 동시에 고개를 돌려 테이블 끝 최 팀장을 쳐다보는 순간, 최 팀장은 무표정으로 잔을 들고 있다. {TEAM}",
                      sfx=[])),
    ("S15", 2.2, dict(kind="video", gen_sec=4, use=[0.0, 2.2], set="gogi", chars=["choi"], audio=True, speaker="choi",
                      line="내년에.", cue=0.9,
                      framing="미디엄 클로즈업, 최 팀장 정면, 약간 로우 앵글, 85mm.",
                      camera="0~0.9초 일어서는 팀장을 따라 천천히 틸트 업, 0.9초에 크래시 줌 인.",
                      still="최 팀장이 굳은 얼굴로 잔을 쥔 채 의자에서 천천히 일어나기 시작하는 순간, 안경 너머로 도윤을 똑바로 노려본다.",
                      action="0~0.9초 굳은 얼굴로 천천히 일어서며 도윤을 노려본다, 0.9초 눈썹이 풀리며 활짝 웃음이 터지고 잔을 높이 들어 누구보다 크게 외친다.",
                      sfx=[[0.15, "subdrop", 0.5], [0.87, "hit", 0.7]])),
    ("S16", 1.8, dict(kind="video", gen_sec=4, use=[0.0, 1.8], set="gogi", chars=["choi", "doyun"], audio=False,
                      framing="와이드 숏, 테이블 위 높은 시점에서 잔들이 모이는 가운데를 내려다봄, 35mm.",
                      camera="슬로모션, 잔이 모이는 순간을 따라 아주 느리게 내려온다.",
                      still=f"도윤과 최 팀장과 팀원들이 일어서서 작은 투명 잔을 가운데로 모아 부딪치기 직전, 모두 웃는다, 불판 김이 빛을 받는다. {TEAM}",
                      action="슬로모션으로 잔들이 가운데에서 부딪치고 모두 크게 웃으며 환호한다, 아무도 마시지 않는다.",
                      sfx=[[0.3, "clink", 0.8], [0.3, "cheer", 0.7]])),
    ("S17", 2.7, dict(kind="video", gen_sec=4, use=[0.2, 2.9], set="gogi", chars=["choi", "doyun"], audio=True, speaker="choi",
                      line="도윤 씨, 잠깐 시간 돼?", cue=0.3,
                      framing="미디엄 숏, 최 팀장 얼굴 정면, 전경 오른쪽에 도윤의 어깨가 흐릿하게, 85mm.",
                      camera="고정.",
                      still="환호가 가라앉은 뒤 최 팀장이 도윤 쪽으로 몸을 기울이며 진심 어린 표정으로 말을 거는 순간.",
                      action="0~0.3초 도윤 쪽으로 몸을 기울인다, 0.3초부터 다정하고 진지하게 묻는다.")),
    ("S18", 1.4, dict(kind="video", gen_sec=4, use=[0.2, 1.6], set="gogi", chars=["doyun"], audio=True, speaker="doyun",
                      line="내년에.", cue=0.2,
                      framing="미디엄 클로즈업, 도윤 정면, 85mm.",
                      camera="고정.",
                      still="도윤이 웃는 얼굴로 반사적으로 잔을 들어 올리는 순간.",
                      action="0~0.2초 반사적으로 잔을 들며 밝게 외친다, 0.6초부터 자기가 무슨 말을 했는지 깨닫고 웃음이 굳는다, 2.2초부터 천천히 고개를 돌려 무표정으로 카메라를 정면으로 본다.",
                      sfx=[[0.1, "pop", 0.5]])),
    ("S19", 3.4, dict(kind="video", gen_sec=4, use=[0.0, 3.4], set="gogi", chars=["choi"], audio=True, speaker="choi",
                      line="내년에도 건배사는 도윤 씨.", cue=0.5,
                      framing="미디엄 클로즈업, 최 팀장 정면, 85mm.",
                      camera="고정, 대사 끝에 아주 살짝 푸시 인.",
                      still="최 팀장이 고개를 젖히고 크게 웃음을 터뜨리는 순간, 잔을 든 손으로 도윤을 가리킨다.",
                      action="0~0.5초 크게 웃는다, 0.5초부터 웃음을 머금은 채 잔으로 도윤을 가리키며 말한다.",
                      sfx=[])),
    ("S20", 0.7, dict(kind="video", reuse="S18", use=[2.4, 3.1], fx="카메라를 보는 도윤, 마지막 0.2초 정지와 1.1배 줌 인, 채도 살짝 빼기", hud="4트 예약",
                      sfx=[[0.0, "thunk", 0.8]])),
    ("S21", 2.4, dict(kind="comp", comp="hong_close", base="7화부터 쓰는 홍책사 클로즈업 고정 컷과 1화 녹음 '홍책사 한 수면, 됐지?'",
                      sfx=[[0.0, "coin", 0.6]])),
    ("S22", 3.0, dict(kind="comp", comp="endcard", base="엽전 꾸러미 끝 화면, 10닢째만 빛남, 열 번째 닢 소품은 작은 투명 잔",
                      coins=["10닢째", "2027 한 수", "hongchaksa.kr"], sfx=[[0.0, "logo", 0.8]])),
]

t = 0.0
shots = []
for sid, dur, d in plan:
    sh = {"id": sid, "t": [round(t, 2), round(t + dur, 2)]}
    sh.update(d)
    if sh.get("sfx"):
        sh["sfx"] = [[round(t + a, 2), n, g] for a, n, g in sh["sfx"]]
    shots.append(sh)
    t += dur


def music_cues(shots, total):
    T = {x["id"]: x["t"] for x in shots}
    shout = round(T["S15"][0] + 0.9, 2)
    c = [(0, T["S3"][0], "comedy"), (T["S3"][0], T["S4"][0], "stop"), (T["S4"][0], T["S6"][0], "comedy"),
         (T["S6"][0], T["S7"][0], "stop"), (T["S7"][0], T["S8"][0], "comedy"), (T["S8"][0], T["S9"][0], "stop"),
         (T["S9"][0], T["S12"][0], "theme"), (T["S12"][0], T["S14"][0], "comedy"), (T["S14"][0], shout, "stop"),
         (shout, T["S17"][0], "anthem"), (T["S17"][0], T["S20"][0], "comedy"), (T["S20"][0], T["S21"][0], "stop"),
         (T["S21"][0], T["S22"][0], "theme"), (T["S22"][0], round(total, 2), "stop")]
    return [[round(a, 2), round(b, 2), st, "F"] for a, b, st in c]


spec = {
    "title": "홍책사 10화 송년회 건배사 3트 v4",
    "target_sec": round(t, 2),
    "reserve_ratio": 0.25,
    "characters": {"doyun": doyun, "choi": choi, "hong": hong},
    "sets": sets,
    "style": style,
    "video_model": "bytedance/seedance-2.0",
    "shots": shots,
    "music": music_cues(shots, t),
    "new_sfx": {"sizzle": "불판 지글: 분홍 잡음 띠 2~8kHz에 무작위 톡 소리", "clink": "작은 유리잔 여러 개가 부딪는 맑은 소리",
                "cheer": "박수 잡음 연타와 낮은 환호 덩어리(말소리 없음)"},
}
json.dump(spec, open("ep10_spec.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("total", round(t, 2), "shots", len(shots))
