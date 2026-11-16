# 7화 v4: 처음 보는 사람 기준. 준이 전 남친임을 알림, 홍책사 장면의 빈 시간을 덜고 말을 1.1배로, 메신저는 읽을 만큼만
import json, copy
sp = json.load(open("ep07_spec_v3.json", encoding="utf-8"))
# 영상 샷: (쓸 구간 시작, 길이, 배속)
VID = {
    "S1": (0.6, 3.0, 1.0), "S3": (0.1, 2.5, 1.0), "S4": (1.0, 3.1, 1.1), "S6": (0.2, 1.8, 1.0),
    "S8": (0.6, 2.0, 1.0), "S9": (0.6, 3.55, 1.1), "S11": (2.2, 1.6, 1.0), "S13": (0.3, 2.8, 1.0),
    "S14": (0.3, 3.6, 1.0), "S15": (0.1, 2.3, 1.0), "S16": (1.0, 3.8, 1.0),
}
HOLD = {"S2": [1.3, 1.4, 1.5], "S7": [1.6, 1.2, 1.4], "S12": [2.3, 1.7], "S13b": [1.2, 1.0, 1.0, 1.0, 1.4]}
FIX = {"S5": 1.4, "S10": 1.4, "S17": 3.0}
SND = {
    "S2": [("pop", .7), ("pop", .7), ("ding", .9)], "S7": [("pop", .6), ("pop", .6), ("ding", .9)],
    "S12": [("pop", .6), ("ding", .8)], "S13b": [None, ("click", .5), ("heart", .8), ("click", .5), ("pop", .7)],
}
CAP = {"S1": "새벽 3시 전 남친의 자니,\n나흘 만에 답했다", "S2": "준, 은서의 전 남친"}
t, shots = 0.0, []
for s in sp["shots"]:
    n = copy.deepcopy(s)
    i = s["id"]
    o0 = s["t"][0]
    if i in VID:
        u0, dur, spd = VID[i]
        n["use"] = [u0, round(u0 + dur * spd, 3)]
        n["speed"] = spd
        ev = []
        for e in s.get("sfx", []):
            clip_t = s["use"][0] + (e[0] - o0)
            st = min(max((clip_t - u0) / spd, 0.0), dur - 0.1)
            ev.append([round(t + st, 2), e[1], e[2]])
        if i == "S4":
            ev = [[round(t, 2), "chime", 1.0], [round(t + 0.12, 2), "coin", 1.0]]
        if i == "S16":
            ev = [[round(t + 0.1, 2), "coin", 1.0], [round(t + dur - 0.6, 2), "chime", 0.5]]
        n["sfx"] = ev
    elif i in HOLD:
        v = HOLD[i]
        dur = sum(v)
        n["hold"] = v
        ev, tt = [], t
        if i == "S12":
            ev.append([round(t + v[0] + 0.35, 2), "heart", 0.7])
        for k, h in enumerate(v):
            if SND[i][k]:
                ev.append([round(tt, 2), SND[i][k][0], SND[i][k][1]])
            tt += h
        n["sfx"] = sorted(ev)
    else:
        dur = FIX[i]
        n["sfx"] = [[round(e[0] - o0 + t, 2), e[1], e[2]] for e in s.get("sfx", [])]
    if i in CAP:
        n["caption"] = CAP[i]
    n["t"] = [round(t, 2), round(t + dur, 2)]
    shots.append(n)
    t += dur
T = {s["id"]: s["t"] for s in shots}
thunk = [e[0] for e in next(s for s in shots if s["id"] == "S8")["sfx"] if e[1] == "thunk"][0]
sp["shots"], sp["target_sec"] = shots, round(t, 2)
sp["music"] = [
    [0, T["S4"][0], "comedy", "F"], [T["S4"][0], T["S5"][0], "theme", "F"], [T["S5"][0], T["S5"][1], "stop", "F"],
    [T["S6"][0], round(thunk - 0.45, 2), "comedy", "F"], [round(thunk - 0.45, 2), thunk, "stop", "F"],
    [thunk, T["S9"][0], "comedy", "F"], [T["S9"][0], T["S10"][0], "theme", "F"], [T["S10"][0], T["S10"][1], "stop", "F"],
    [T["S11"][0], round(T["S14"][0] - 0.45, 2), "romance", "F"], [round(T["S14"][0] - 0.45, 2), T["S14"][0], "stop", "F"],
    [T["S14"][0], T["S16"][0], "comedy", "F"], [T["S16"][0], round(t, 2), "theme", "F"],
]
json.dump(sp, open("ep07_spec_v4.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for s in shots:
    print(s["id"], s["t"], s.get("use"), s.get("speed", ""), s.get("hold", ""), repr(s.get("caption", "")), s["sfx"])
print("TOTAL", round(t, 2))
