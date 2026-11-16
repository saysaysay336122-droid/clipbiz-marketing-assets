# 7화 v3 시간표: 메신저 읽는 시간 확보, 무르기 설명 줄, 시도별 자막
import json, copy
sp = json.load(open("ep07_spec_v2.json", encoding="utf-8"))
old = {s["id"]: s for s in sp["shots"]}
# 샷별 새 길이, 메신저는 말풍선마다 보이는 시간(마지막 값은 다 뜬 뒤 머무는 시간)
NEW = {
    "S1": 3.0, "S2": [1.4, 1.5, 1.7], "S3": 2.5, "S4": 4.2, "S5": 1.4, "S6": 2.0,
    "S7": [1.7, 1.3, 1.4], "S8": 2.0, "S9": 5.0, "S10": 1.4, "S11": 1.8,
    "S12": [2.4, 1.8], "S13": 3.0, "S13b": [1.3, 1.0, 1.0, 1.0, 1.5], "S14": 4.0,
    "S15": 2.7, "S16": 4.0, "S17": 3.0,
}
SND = {  # 메신저 말풍선이 뜰 때 소리
    "S2": [("pop", .7), ("pop", .7), ("ding", .9)],
    "S7": [("pop", .6), ("pop", .6), ("ding", .9)],
    "S12": [("pop", .6), ("ding", .8)],
    "S13b": [None, ("click", .5), ("heart", .8), ("click", .5), ("pop", .7)],
}
CAP = {"S7": "솔직하게 보냈다", "S12": "질문으로 보냈다"}
REW = {"S5": "답장 보내기 전으로", "S10": "한 번 더, 보내기 전으로"}
t = 0.0
shots, starts = [], {}
for s in sp["shots"]:
    n = copy.deepcopy(s)
    v = NEW[s["id"]]
    dur = sum(v) if isinstance(v, list) else v
    o0 = s["t"][0]
    n["t"] = [round(t, 2), round(t + dur, 2)]
    starts[s["id"]] = (o0, t)
    if s["kind"] == "video" and s.get("use"):
        n["use"] = [s["use"][0], round(s["use"][0] + dur, 2)]
    if isinstance(v, list):
        n["hold"] = v
        ev, tt = [], t
        if s["id"] == "S12":
            ev.append([round(t + v[0] + 0.35, 2), "heart", 0.7])
        for k, h in enumerate(v):
            if SND[s["id"]][k]:
                nm, g = SND[s["id"]][k]
                ev.append([round(tt, 2), nm, g])
            tt += h
        n["sfx"] = sorted(ev)
    else:
        n["sfx"] = [[round(e[0] - o0 + t, 2), e[1], e[2]] for e in s.get("sfx", [])]
    if s["id"] in CAP:
        n["caption"] = CAP[s["id"]]
    if s["id"] in REW:
        n["rewind_sub"] = REW[s["id"]]
    shots.append(n)
    t += dur
T = {s["id"]: s["t"] for s in shots}
thunk = [e[0] for e in next(s for s in shots if s["id"] == "S8")["sfx"] if e[1] == "thunk"][0]
sp["shots"] = shots
sp["target_sec"] = round(t, 2)
sp["music"] = [
    [0, T["S4"][0], "comedy", "F"], [T["S4"][0], T["S5"][0], "theme", "F"], [T["S5"][0], T["S5"][1], "stop", "F"],
    [T["S6"][0], round(thunk - 0.45, 2), "comedy", "F"], [round(thunk - 0.45, 2), thunk, "stop", "F"],
    [thunk, T["S9"][0], "comedy", "F"], [T["S9"][0], T["S10"][0], "theme", "F"], [T["S10"][0], T["S10"][1], "stop", "F"],
    [T["S11"][0], round(T["S14"][0] - 0.45, 2), "romance", "F"], [round(T["S14"][0] - 0.45, 2), T["S14"][0], "stop", "F"],
    [T["S14"][0], T["S16"][0], "comedy", "F"], [T["S16"][0], round(t, 2), "theme", "F"],
]
json.dump(sp, open("ep07_spec_v3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for s in shots:
    print(s["id"], s["t"], s.get("use"), s.get("hold"), s.get("caption", ""), s.get("rewind_sub", ""), s["sfx"])
print("TOTAL", round(t, 2))
print(sp["music"])
