"""9화 드롭샷 생성 요청 만들기. 사용: python3 mk_gen9.py 단계(P1|P2|P3)
gen9/urls.json 의 주소(기준 사진, 시작 사진)를 읽어 단계별 요청을 gen9/req_단계.json 으로 쓴다.
P1: 기준 사진 셋(사무실, 거인, 슈트)과 장소 겸용 사진 둘(S3 탕비실, S24 회의실)
P2: 나머지 시작 사진과 사진 전용 컷
P3: 영상 11개
"""
import json
import os
import sys

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
from episode_preflight import build_prompts  # noqa: E402

SPEC = "ep09_spec_v6.json"
os.makedirs("gen9", exist_ok=True)
U = json.load(open("gen9/urls.json", encoding="utf-8")) if os.path.exists("gen9/urls.json") else {}
spec = json.load(open(SPEC, encoding="utf-8"))
CH = spec["characters"]
CH["doyun"]["fixed"] = CH["doyun"]["fixed"].replace("미니멀한 검은 백팩, ", "")
NOTES = [" 거인 합성 배경으로도 쓴다.", " S5h 히어로 컷으로 쓰고, 슈트가 들어가는 모든 컷(S4a~d, S5, S7, S14, S20, S26)의 참고 이미지로 써서 상자 크기, 받침대, 쟁반, 헤드셋 모양을 고정한다."]


def clean(t):
    for n in NOTES:
        t = t.replace(n, "")
    return t.replace("  ", " ")

STILL = spec["style"]["still"]
OFFICE8 = "https://cdn.aistudio.dropshot.io/public/jobs/prod/mcp_16c817442bd9418a8fad8bdd69aea44a/output/output_0.png"

PH = {  # 자리표시와 실제 주소, 참고 이미지 이름
    CH["doyun"]["face"]: ("도윤 얼굴", CH["doyun"]["face"]),
    CH["choi"]["face"]: ("최 팀장 얼굴", CH["choi"]["face"]),
    CH["hong"]["face"]: ("홍책사 얼굴", CH["hong"]["face"]),
    CH["giant"]["face"]: ("기계 거인 디자인", U.get("giant")),
    "[장소 office_m 기준 사진]": ("장소 아침 사무실", U.get("office_m")),
    "[장소 pantry 기준 사진]": ("장소 탕비실", U.get("S3")),
    "[장소 meeting 기준 사진]": ("장소 회의실", U.get("S24")),
    "[소품 suit 기준 사진]": ("칼퇴 슈트 모양", U.get("suit")),
}


def head(labels):
    if not labels:
        return ""
    s = ", ".join(f"{i + 1}번 {l}" for i, l in enumerate(labels))
    return f"참고 이미지 순서: {s}. 얼굴, 장소, 거인, 슈트는 각 참고 이미지와 똑같이. "


def refs_of(raw, self_id=None):
    labels, urls = [], []
    for r in raw:
        lab, url = PH.get(r, (None, None))
        if lab is None or not url:
            continue
        if self_id and url == U.get(self_id):
            continue
        labels.append(lab)
        urls.append(url)
    return labels, urls


def img(prompt, urls):
    o = {"prompt": clean(prompt), "aspect_ratio": "9:16", "resolution": "2K"}
    if urls:
        o["input_image"] = urls
    return {"model": "google/nano-banana-pro", "options": o}


phase = sys.argv[1]
# 참고 이미지가 있으니 글 묘사는 짧고 정확하게(9화 v6 최종 명령)
import importlib.util
_sp = importlib.util.spec_from_file_location("m9", "mk_ep09.py")
LONG_SUIT = None
src = open("mk_ep09.py", encoding="utf-8").read()
ns = {}
exec(src.split("CH[\"giant\"] =")[0].split("v7 = json.load")[0] + "\n", ns) if False else None
SHORT = {
 "doyun": "인물 도윤: 20대 후반 한국 남성 회사원, 참고 사진 얼굴과 똑같이(앞머리가 이마를 살짝 덮는 검은 머리, 오른쪽 볼 보조개, 맑은 눈빛), 남색 니트 카디건과 첫 단추를 푼 흰 옥스퍼드 셔츠, 은색 손목시계.",
 "hong": "인물 홍책사: 30대 후반 한국 남성 카페 사장, 참고 사진 얼굴과 똑같이, 검은 울 터틀넥, 남색 캔버스 앞치마, 단정한 짧은 머리, 차분하고 깊은 눈빛과 여유 있는 미소.",
 "choi": "인물 최 팀장: 40대 중반 한국 남성 팀장, 참고 사진 얼굴과 똑같이, 희끗희끗한 짧은 머리, 검은 뿔테 안경, 차콜 니트 조끼, 하늘색 셔츠, 남색 니트 타이.",
 "giant": "기계 거인 주간 보고(참고 이미지 디자인 그대로): 빈 화면 모니터 비늘 몸통과 가슴 한가운데 큰 빈 모니터, 검은 키보드를 이어 붙인 팔, 검은 전선 다발 근육, 서류철 손가락, 흰 화이트보드 머리와 빈 모니터 두 눈, 몸 곳곳 노란 포스트잇, 사람 얼굴 없음, 초록색 없음, 빨강과 금색 장갑 없음.",
}
for k, v in SHORT.items():
    CH[k]["fixed"] = v
spec["characters"] = CH
spec["sets"]["office_m"]["desc"] = "참고 이미지의 월요일 아침 사무실(회색 칸막이 책상 통로, 빈 화면 모니터와 키보드, 안쪽 유리벽 회의실, 정수기, 창의 아침 햇살과 천장 형광등), 글자 없음."
spec["sets"]["pantry"]["desc"] = "참고 이미지의 사무실 탕비실(흰 수납장, 커피 머신, 창의 아침 햇살), 글자 없음."
spec["sets"]["meeting"]["desc"] = "참고 이미지의 유리벽 회의실(긴 흰 회의 테이블, 회색 의자, 노트북과 서류철, 창의 아침 햇살), 글자 없음."
spec["style"]["still"] = ("실사 한국 오피스 액션 코미디 블록버스터 영화의 한 장면, 한 장의 단일 장면, 분할 화면 없음, 따뜻한 아침 햇살과 형광등 청록의 색 대비, 빛줄기 속 먼지, "
                          "아나모픽 렌즈 느낌의 얕은 심도, 얼굴에 부드러운 키 라이트와 림 라이트, 눈에 캐치라이트, 얼굴 왜곡 없음, 자연스러운 피부결, 과한 보정 없음, "
                          "화면에 글자, 자막, 로고, 숫자 없음, 모니터와 화이트보드는 빈 화면.")
SUIT_SHORT = "칼퇴 슈트(참고 이미지 그대로: 왼쪽 어깨에 노란 무지 상자를 은색 덕트 테이프로, 가슴에 검은 철제 모니터 받침대, 왼팔에 둥근 은색 쟁반, 검은 헤드셋과 입 앞 마이크 팔, 글자 없음)"
for sh in spec["shots"]:
    for f in ("still",):
        if sh.get(f):
            t = sh[f]
            i = t.find("칼퇴 슈트: ")
            if i >= 0:
                j = t.find("모든 물건에 글자, 숫자, 로고 없음.", i)
                t = t[:i] + SUIT_SHORT + t[j + len("모든 물건에 글자, 숫자, 로고 없음."):]
            sh[f] = t
set_p, vp, neg = build_prompts(spec)
req = {}
if phase == "P1":
    req["office_m"] = img(head(["8화 사무실(같은 사무실, 빛만 월요일 아침으로)"]) + set_p["office_m"], [OFFICE8])
    giant_txt = CH["giant"]["fixed"].replace("사무실 천장 타일을 뚫고 선 거인, 키는 천장 높이의 두 배.", "사람 키의 다섯 배쯤 되는 거대한 기계 거인.")
    req["giant"] = img("9:16 세로. 기계 거인 디자인 기준 사진: 밝은 회색 무지 스튜디오 배경 앞에 선 정면 3/4 전신, 머리부터 발끝까지 화면 안에 다 들어오게, "
                       "부드럽고 고른 조명, 그림자 약하게, 배경에 다른 물건 없음. " + giant_txt +
                       " 실사 영화 소품 사진 질감, 금속과 플라스틱과 전선의 실제 재질, 화면과 종이에 글자와 숫자와 로고 없음, 한 장의 단일 장면, 분할 화면 없음.", [])
    req["suit"] = img(head(["도윤 얼굴"]) + "9:16 세로. " + CH["doyun"]["fixed"] + " " + spec["props"]["suit"]["desc"] + " " + STILL, [CH["doyun"]["face"]])
    for p in vp:
        if p["id"] == "S3":
            req["S3"] = img(p["still"], [])
        if p["id"] == "S24":
            lab, urls = refs_of(p["refs"], "S24")
            req["S24"] = img(head(lab) + p["still"], urls)
elif phase == "P2":
    for p in vp:
        if p["id"] in ("S3", "S24"):
            continue
        lab, urls = refs_of(p["refs"])
        req[p["id"]] = img(head(lab) + p["still"], urls)
elif phase == "P3":
    for p in vp:
        if p.get("still_only"):
            continue
        sid = p["id"]
        req[sid] = {"model": spec.get("video_model", "bytedance/seedance-2.0"),
                    "options": {"prompt": p["video"], "start_frame": U[sid], "duration": p["sec"],
                                "resolution": "720p", "aspect_ratio": "9:16", "generate_audio": bool(p["audio"])}}
json.dump(req, open(f"gen9/req_{phase}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in req.items():
    o = v["options"]
    print(k, v["model"], len(o["prompt"]), "refs", len(o.get("input_image", [])), o.get("duration", ""))
