"""홍책사 10화 소리: 자체 음악(hcs_music)과 효과음(sfx_cine) 위에 생성 클립 대사를 얹고 2패스 음량 맞춤.
사용: python3 final_audio10.py
"""
import json, subprocess, sys, wave
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music, sfx_cine  # noqa: E402

D = "/home/claude/ep10"
OUT = f"{D}/out"
SR = 48000
TOTAL = 42.4

# 음악 구간(편집 시간표 기준)
MUSIC = [
    (0.0, 2.4, "comedy", "F"), (2.4, 3.6, "stop", "F"), (3.6, 7.5, "comedy", "F"), (7.5, 8.3, "stop", "F"),
    (8.3, 10.7, "comedy", "F"), (10.7, 11.9, "stop", "F"), (11.9, 18.7, "theme", "F"), (18.7, 24.2, "comedy", "F"),
    (24.2, 25.94, "stop", "F"), (25.94, 28.7, "anthem", "F"), (28.7, 35.8, "comedy", "F"), (35.8, 36.5, "stop", "F"),
    (36.5, 39.4, "theme", "F"), (39.4, TOTAL, "stop", "F"),
]

# 효과음(시각, 이름, 세기)
EVENTS = [
    (0.0, "sizzle", 0.7), (0.0, "tickh", 0.35), (0.42, "gust", 0.5),
    (2.45, "coinx", 0.8), (3.0, "rewind", 0.9),
    (3.6, "sizzle", 0.5), (3.65, "tapestart", 0.6),
    (7.5, "sizzle", 0.4), (7.95, "clank", 0.3),
    (10.75, "coinx", 0.8), (11.3, "rewind", 0.9), (11.95, "tapestart", 0.6),
    (12.8, "chime", 0.5),
    (15.5, "swishr", 0.6), (16.3, "swishr", 0.6), (16.6, "tickh", 0.5), (17.5, "mail", 0.8),
    (21.9, "drum", 0.6),
    (24.2, "scratch", 0.8), (24.95, "subdrop", 0.5), (25.94, "hit", 0.7),
    (27.0, "clink", 0.8), (27.1, "cheer", 0.7),
    (30.86, "plink", 0.5), (35.05, "paper", 0.4),
    (35.8, "thunk", 0.8), (36.5, "coin", 0.6), (39.4, "logo", 0.8),
    (TOTAL - 0.45, "sizzle", 0.35),
]
SILENCE = [(25.49, 25.84)]  # 팀장 '내년에' 0.45초 앞 정적

# 대사 조각: (클립, 원본 시작, 원본 끝, 배치 시각, 목표 dBFS, 회상 울림)
DLG = [
    ("S1", 0.45, 1.85, 0.05, -19, False),
    ("S4", 1.00, 2.75, 3.80, -19, False),
    ("S5", 1.05, 2.30, 6.10, -18, False),
    ("S7", 0.25, 1.85, 8.35, -19, False),
    ("S4", 1.00, 1.85, 11.95, -19, False),
    ("S10", 1.60, 3.50, 13.24, -19, False),
    ("S17", 0.56, 1.42, 15.62, -22, True),
    ("S17", 0.24, 1.42, 16.42, -22, True),
    ("S12", 0.50, 2.80, 18.80, -19, False),
    ("S13", 0.85, 1.75, 22.00, -19, False),
    ("S15", 1.95, 2.85, 25.85, -17, False),
    ("S17", 0.18, 1.50, 28.78, -19, False),
    ("S18", 0.25, 0.90, 30.85, -19, False),
    ("S19", 0.85, 2.50, 33.45, -19, False),
    ("E7", 1.80, 4.75, 36.50, -19, False),
]


def src(k):
    return "/home/claude/ep7/v/clips/S16.mp4" if k == "E7" else f"{D}/clips/{k}.mp4"


def load(path, a, b, memory):
    af = f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,highpass=f=80,lowpass=f=9000"
    if memory:
        af += ",highpass=f=220,lowpass=f=5000,aecho=0.8:0.55:70|140:0.32|0.18"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    f = int(0.025 * SR)
    if len(x) > 2 * f:
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    return x


def write(path, st):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())


n = int(TOTAL * SR)
dlg = np.zeros(n)
duck = []
for k, a, b, at, target, mem in DLG:
    x = load(src(k), a, b, mem)
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9)
    x = x * 10 ** ((target - lvl) / 20)
    i = int(at * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((at - 0.05, at + len(x) / SR + 0.1))

mus = f"{OUT}/ep10_music.wav"
hcs_music.make(TOTAL, MUSIC, mus, room=0.15)
bgw = f"{OUT}/ep10_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=mus, music_gain=0.9, events=EVENTS, duck=duck, silence=SILENCE)
bg = sfx_cine.read_st(bgw)[:n]
out = bg * 0.82 + np.stack([dlg, dlg], axis=1)[: len(bg)]
for a, b in SILENCE:
    i, j = int(a * SR), int(b * SR)
    out[i:j] = 0
out = out / np.abs(out).max() * 0.95
raw = f"{OUT}/ep10_mix_raw.wav"
write(raw, out)

pre = "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.7:level=false"
m = subprocess.run(["ffmpeg", "-v", "info", "-i", raw, "-af", pre + ",loudnorm=I=-14:TP=-3:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-3:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
      f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
final = f"{OUT}/ep10_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", pre + "," + ln + ",alimiter=limit=0.71:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("duck", [(round(a, 2), round(b, 2)) for a, b in duck])
