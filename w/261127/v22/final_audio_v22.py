"""홍책사 10화 v22 공포 스릴러판 소리: 낮은 드론, 속삭임, 비명 같은 현악, 도장과 저음, 액션 북과 금관.
사용: python3 final_audio_v22.py
"""
import json, math, subprocess, sys, wave
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music, sfx_cine  # noqa: E402

D = "/home/claude/ep10"
OUT = f"{D}/out"
SR = 48000
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location("bv22", f"{D}/build_v22.py")
B = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(B)
at, T = B.at, B.T
TOTAL = B.TOTAL

MUSIC = [
    (0.0, T["S10"][0], "stop", "F"), (T["S10"][0], T["S10"][1], "theme", "F"),
    (T["F1"][0], T["H3"][1], "stop", "F"), (T["S12"][0], T["S13"][1], "action", "Fm"),
    (T["S14"][0], at("S15", 0.55), "stop", "F"), (at("S15", 0.55), T["S16"][1], "anthem", "F"),
    (T["O2"][0], T["N5"][1], "stop", "F"), (T["N3"][0], T["N4"][1], "romance", "F"),
    (T["E7a"][0], T["E7b"][1], "theme", "F"), (T["END"][0], TOTAL, "stop", "F"),
]

EVENTS = [
    # 봉투와 깜빡이는 조명
    (at("O1", 0.0), "buzz", 0.6), (at("O1", 0.0), "heartx", 0.8), (at("O1", 0.6), "buzz", 0.5), (at("O1", 0.9), "heartx", 0.7),
    # 정전 속 팀장, 속삭임
    (at("H1", 0.05), "subdrop", 0.8), (at("H1", 0.05), "buzz", 0.7), (at("H1", 0.25), "sting", 0.55),
    # 도윤 공포 눈
    (at("H2", 0.0), "hitd", 0.9), (at("H2", 0.4), "heartx", 0.9), (at("H2", 0.85), "heartx", 0.9), (at("H2", 0.2), "ring", 0.35),
    # 되감기
    (at("RW", 0.0), "tape", 0.8), (at("RW", 0.0), "glitch", 0.5),
    # 건배사 차례 정적
    (at("S6", 0.2), "buzz", 0.4), (at("S6", 0.9), "buzz", 0.35), (at("S6", 1.15), "cricket", 0.6),
    # 홍책사
    (at("S10", 0.0), "shimmer", 0.7), (at("S10", 0.05), "chime", 0.6),
    # 회상 세 번, 갈수록 크게
    (at("F1", 0.0), "buzz", 0.5), (at("F1", 0.35), "stamp", 0.6), (at("F1", 0.35), "hitd", 0.45),
    (at("F2", 0.0), "buzz", 0.5), (at("F2", 0.35), "stamp", 0.85), (at("F2", 0.35), "hitd", 0.7), (at("F2", 0.35), "subdrop", 0.5),
    (at("H3", 0.45), "vibrate", 0.9), (at("H3", 0.5), "hit", 0.9), (at("H3", 0.5), "glitch", 0.8),
    (at("H3", 0.85), "stamp", 1.0), (at("H3", 0.85), "subdrop", 0.9), (at("H3", 0.85), "hitd", 0.9),
    # 건배사로 뒤집기
    (at("S12", 0.0), "drum", 0.7), (at("S12", 1.9), "timp", 0.7), (at("S13", 0.0), "drumroll", 0.8),
    (at("S14", 0.05), "heartx", 0.9),
    (at("S15", 0.55), "hit", 1.0), (at("S15", 0.55), "braam", 0.6), (at("S15", 0.65), "cheer", 0.6),
    (at("S16", 0.2), "clink", 0.9), (at("S16", 0.25), "cheer", 0.8), (at("S16", 0.25), "shimmer", 0.7),
    # 봉투 앞 반전
    (at("O2", 0.0), "buzz", 0.7), (at("O2", 0.0), "subdrop", 0.5), (at("O2", 0.05), "paper", 0.5),
    (at("S17", 0.0), "heartx", 0.7), (at("S17", 0.5), "heartx", 0.8), (at("S17", 0.9), "heartx", 0.9),
    (at("S17", 1.2), "heartx", 1.0), (at("S17", 0.5), "buzz", 0.4),
    (at("H2b", 0.0), "hitd", 1.0), (at("H2b", 0.12), "stamp", 0.9), (at("H2b", 0.1), "ring", 0.4),
    (at("S18", 0.8), "scratch", 0.9), (at("S18", 0.8), "freeze", 0.6),
    (at("S19", 0.9), "zipper", 0.8),
    (at("FZ2", 0.0), "hit", 1.0), (at("FZ2", 0.0), "subdrop", 0.8), (at("FZ2", 0.05), "stamp", 0.8),
    # 본부장 메시지와 팀장 반사
    (at("N5a", 0.0), "vibrate", 0.9), (at("N5a", 0.2), "pop", 0.5), (at("N5a", 0.6), "stamp", 1.0), (at("N5a", 0.6), "hitd", 0.8),
    (at("N5", 0.8), "sting", 0.9),
    # 불이 다시 켜짐
    (at("N3", 0.0), "shimmer", 0.8), (at("N4", 0.0), "coin", 0.6),
    (at("E7b", -0.08), "coin", 0.45), (at("END", 0.0), "logo", 0.8), (at("END", 2.1), "suck", 0.45),
]
SILENCE = [(at("S14", 0.25), at("S15", 0.5))]
SHRIEK = [(at("H2", 0.0), 0.75), (at("H3", 0.85), 1.0), (at("H2b", 0.0), 0.7), (at("N5", 0.8), 0.55)]
DRONE = [(0.0, T["S10"][0], 1.0), (T["S10"][0], T["S12"][0], 0.55), (T["O2"][0], T["N3"][0], 1.0)]

# 대사 조각: (클립, 원본 시작, 원본 끝, 배치 시각, 목표 dBFS, 방식)
DLG = [
    ("S17", 0.56, 1.42, at("H1", 0.30), -17, "whisper"),
    ("S10", 1.60, 3.50, at("S10", 0.15), -16, None),
    ("S17", 0.56, 1.42, at("F1", 0.08), -19, "whisper"),
    ("S17", 0.56, 1.42, at("F2", 0.08), -18, "whisper"),
    ("S12", 0.50, 2.80, at("S12", 0.30), -16, None),
    ("S13", 0.85, 1.75, at("S13", 0.10), -16, None),
    ("S15", 1.95, 2.85, at("S15", 0.55), -15, None),
    ("S17", 0.18, 1.50, at("S17", 0.08), -16, None),
    ("S18", 0.25, 0.90, at("S18", 0.05), -16, None),
    ("S19", 0.85, 2.50, at("S19", 0.10), -16, None),
    ("N5", 1.02, 1.52, at("N5", 0.27), -16, None),
    ("N3", 2.25, 3.05, at("N3", 0.55), -16, None),
    ("E7", 2.22, 3.42, at("E7a", 0.02), -16, None),
    ("E7", 4.04, 4.58, at("E7b", 0.02), -16, None),
]


def src(k):
    return "/home/claude/ep7/v/clips/S16.mp4" if k == "E7" else f"{D}/clips/{k}.mp4"


def load(path, a, b, mode):
    af = f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,highpass=f=80,lowpass=f=9000"
    if mode == "whisper":
        af += ",asetrate=48000*0.86,aresample=48000,atempo=1.163,highpass=f=160,aecho=0.8:0.7:90|180|320:0.45|0.3|0.2"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    f = int(0.02 * SR)
    if len(x) > 2 * f:
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    return x


def shriek(sec=0.9):
    """비명 같은 현악 군집음: 높은 음 네 개가 어긋나 떨린다(사람 목소리 아님)."""
    t = np.arange(int(sec * SR)) / SR
    x = np.zeros_like(t)
    for f0, ph in ((1396, 0.0), (1480, 1.3), (1568, 2.1), (1661, 0.7)):
        vib = 1 + 0.012 * np.sin(2 * math.pi * 6.3 * t + ph)
        phase = 2 * math.pi * np.cumsum(f0 * vib) / SR
        x += np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.18 * np.sin(3 * phase)
    env = np.minimum(1, t / 0.015) * np.exp(-t * 3.2)
    x = x * env
    x += np.random.default_rng(3).normal(0, 0.25, len(t)) * env * 0.6
    return x / np.abs(x).max()


def drone(sec):
    t = np.arange(int(sec * SR)) / SR
    x = (np.sin(2 * math.pi * 41.2 * t) + 0.8 * np.sin(2 * math.pi * 43.7 * t) + 0.4 * np.sin(2 * math.pi * 82.4 * t)
         + 0.25 * np.sin(2 * math.pi * 123.5 * t + 0.4 * np.sin(2 * math.pi * 0.3 * t)))
    nz = np.random.default_rng(5).normal(0, 1, len(t))
    k = np.ones(60) / 60
    nz = np.convolve(nz, k, mode="same")
    x = x * 0.6 + nz * 0.5 * (0.6 + 0.4 * np.sin(2 * math.pi * 0.25 * t))
    return x / np.abs(x).max()


def write(path, st):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())


n = int(TOTAL * SR)
dlg = np.zeros(n)
duck = []
for k, a, b, t0, target, mode in DLG:
    x = load(src(k), a, b, mode)
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9)
    x = x * 10 ** ((target - lvl) / 20)
    i = int(t0 * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((t0 - 0.05, t0 + len(x) / SR + 0.1))

# 공포 층: 드론과 비명 같은 현악
hor = np.zeros(n)
dr = drone(TOTAL + 1)
for a, b, g in DRONE:
    i, j = int(a * SR), min(n, int(b * SR))
    env = np.ones(j - i) * g
    f = min(int(0.3 * SR), (j - i) // 3)
    env[:f] *= np.linspace(0, 1, f)
    env[-f:] *= np.linspace(1, 0, f)
    hor[i:j] += dr[i:j] * env * 10 ** (-22 / 20)
sh = shriek()
for t0, g in SHRIEK:
    i = int(t0 * SR)
    j = min(n, i + len(sh))
    hor[i:j] += sh[: j - i] * g * 10 ** (-12 / 20)

mus = f"{OUT}/ep10v22_music.wav"
hcs_music.make(TOTAL, MUSIC, mus, room=0.15)
bgw = f"{OUT}/ep10v22_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=mus, music_gain=0.95, events=EVENTS, duck=duck, silence=SILENCE)
bg = sfx_cine.read_st(bgw)[:n]
for a, b in duck:
    i, j = int(a * SR), min(n, int(b * SR))
    hor[i:j] *= 0.5
out = bg * 0.9 + np.stack([dlg + hor, dlg + hor], axis=1)[: len(bg)]
for a, b in SILENCE:
    i, j = int(a * SR), int(b * SR)
    out[i:j] = 0
out = out / np.abs(out).max() * 0.95
raw = f"{OUT}/ep10v22_mix_raw.wav"
write(raw, out)

pre = "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.7:level=false"
m = subprocess.run(["ffmpeg", "-v", "info", "-i", raw, "-af", pre + ",loudnorm=I=-14:TP=-3.5:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-3.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
      f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
final = f"{OUT}/ep10v22_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", pre + "," + ln + ",alimiter=limit=0.63:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
