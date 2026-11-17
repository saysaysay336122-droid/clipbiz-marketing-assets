"""8화 v7(퀵실버 판) 시간표. v6 설계서에서 1막(S0~S10)과 뒷부분 샷은 그대로 두고, 시간 정지 구간을 새 샷으로 바꾼다.
그루브(120BPM)가 23.3초에 시작하므로 정지 구간의 컷은 0.5초 박 격자에 맞춘다."""
import json

D = "/home/claude/ep8"
v6 = json.load(open(f"{D}/ep08_spec_v6.json", encoding="utf-8"))
old = {s["id"]: s for s in v6["shots"]}

# (id, 길이, 자막/표시, 새 효과음[(샷 안 시각, 이름, 세기)])
NEW = [
    ("Q1", 1.2, "", [(0.02, "tapestop", 2.5), (0.0, "stutter", 0.35), (1.0, "subdrop", 0.5)]),
    ("Q2", 1.2, "", [(0.0, "freeze", 1.0), (0.02, "ring", 0.45), (0.6, "heartx", 0.8)]),
    ("S11", 1.7, "시간이 멈췄다", [(0.0, "shimmer", 0.4), (0.6, "heartx", 0.7)]),
    ("S12", 1.3, "", [(0.45, "click", 0.7)]),
    ("Q3", 1.5, "홍책사는 산책 중", [(0.0, "swishr", 0.35)]),
    ("Q4", 1.0, "", [(0.0, "passr", 0.9), (0.5, "swishl", 0.5)]),
    ("Q5", 6.5, "재채기 대비", [(0.0, "swishr", 0.5), (0.9, "pop", 0.6), (2.6, "shimmer", 0.3), (4.9, "paper", 0.5), (5.7, "paper", 0.5)]),
    ("Q6", 0.5, "", [(0.0, "pop", 0.5)]),
    ("Q7", 1.0, "커피 되돌리기", [(0.0, "rewind", 0.7)]),
    ("Q8", 0.5, "", [(0.0, "tickh", 0.5)]),
    ("Q9", 1.0, "", [(0.2, "paper", 0.6)]),
    ("S13a", 0.5, "", [(0.0, "swishl", 0.7), (0.15, "pop", 0.4)]),
    ("Q10", 1.75, "종이 넣기 완료", [(0.75, "kachunk", 0.6), (1.3, "pop", 0.5)]),
    ("S14", 3.6, "", None),  # 아래에서 따로
    ("Q11", 2.0, "", [(0.25, "kachunk", 0.5), (0.35, "paper", 0.45)]),
]
TAIL = ["S14b", "S15", "S15c", "S16", "S17"]
BSEQ = [
    ("B1", 0.4, "", [(0.0, "shimmer", 0.8), (0.0, "coinx", 0.8)]),
    ("B2", 1.2, "", [(0.0, "freeze", 0.8), (0.02, "ring", 0.35), (0.45, "swishr", 0.5)]),
    ("B3", 1.4, "", [(0.6, "swishr", 0.6), (0.85, "passr", 0.8)]),
]
END = ["S18v", "S19", "S20", "S21"]

shots = []
t = 0.0
for s in v6["shots"]:
    if s["id"] == "S11":
        break
    shots.append(dict(s))
    t = s["t"][1]
assert abs(t - 17.9) < 1e-6


def add_old(sid, t0):
    s = dict(old[sid])
    a, b = s["t"]
    s["t"] = [round(t0, 3), round(t0 + (b - a), 3)]
    s["sfx"] = [[round(at - a + t0, 3), nm, g] for at, nm, g in s.get("sfx", [])]
    shots.append(s)
    return t0 + (b - a)


for sid, dur, cap, sfx in NEW:
    if sid == "S14":
        s = dict(old["S14"])
        s["t"] = [round(t, 3), round(t + dur, 3)]
        # 낚아채기(샷 안 2.75초)를 박 위(40.30)에 둔다
        s["sfx"] = [[round(t - 0.12, 3), "swishl", 0.3], [round(t + 1.85, 3), "suck", 1.0], [round(t + 1.85, 3), "rise1", 0.5],
                    [round(t + 2.75, 3), "hit", 1.0], [round(t + 2.75, 3), "coinx", 0.9], [round(t + 2.77, 3), "tapestart", 2.5]]
        shots.append(s)
        t += dur
        continue
    if sid in ("S11", "S12", "S13a"):
        s = dict(old[sid])
        s["t"] = [round(t, 3), round(t + dur, 3)]
    else:
        s = {"id": sid, "t": [round(t, 3), round(t + dur, 3)], "kind": "video" if sid not in ("Q6", "Q8") else "still"}
    s["caption"] = cap
    s["sfx"] = [[round(t + at, 3), nm, g] for at, nm, g in sfx]
    shots.append(s)
    t += dur

for sid in TAIL:
    t = add_old(sid, t)
for sid, dur, cap, sfx in BSEQ:
    shots.append({"id": sid, "t": [round(t, 3), round(t + dur, 3)], "caption": cap, "sfx": [[round(t + at, 3), nm, g] for at, nm, g in sfx]})
    t += dur
for sid in END:
    t = add_old(sid, t)

T = {s["id"]: s["t"] for s in shots}
total = round(t, 3)
rel = T["S14"][0] + 2.75
music = [
    [0, 1.2, "stop", "Dm"], [1.2, 9.3, "action", "Dm"], [9.3, 9.6, "stop", "Dm"], [9.6, 14.6, "action", "Dm"],
    [14.6, 14.9, "stop", "Dm"], [14.9, 17.9, "theme", "F"], [17.9, T["Q2"][0] + 0.2, "stop", "F"],
    [T["Q2"][0] + 0.2, T["Q3"][0], "frozen", "F"], [T["Q3"][0], rel - 0.1, "speed", "F"], [rel - 0.1, T["S15"][0], "stop", "F"],
    [T["S15"][0], T["S15c"][0], "anthem", "F"], [T["S15c"][0], T["B2"][0], "stop", "F"], [T["B2"][0], T["S18v"][0], "speed", "F"],
    [T["S18v"][0], T["S18v"][0] + 1.1, "stop", "F"], [T["S18v"][0] + 1.1, T["S20"][0], "comedy", "F"], [T["S20"][0], total, "theme", "F"],
]
spec = dict(v6)
spec["title"] = "홍책사 8화 칼퇴작전 v7(시간 정지 확장판)"
spec["target_sec"] = total
spec["shots"] = shots
spec["music"] = music
spec["release"] = round(rel, 3)
spec["bed"] = [[1.2, 17.9, 0.22], [round(rel, 3), T["B1"][0], 0.22], [T["S18v"][0], T["S19"][0] + 0.8, 0.22]]
spec["silence"] = [[round(rel - 0.1, 3), round(rel, 3)], [round(T["S18v"][0] + 0.65, 3), round(T["S18v"][0] + 1.1, 3)]]
json.dump(spec, open(f"{D}/ep08_spec_v7.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for s in shots:
    print(f'{s["id"]:5s} {s["t"][0]:6.2f} {s["t"][1]:6.2f} {s.get("caption","")}')
print("total", total, "release", rel)
print("groove start", T["Q3"][0], "beats to release", (rel - T["Q3"][0]) / 0.5)
