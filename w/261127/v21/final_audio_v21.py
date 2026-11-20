"""홍책사 10화 v21 소리(39.8초): 자체 음악과 효과음 위에 생성 클립 대사를 얹고 2패스 음량 맞춤.
사용: python3 final_audio_v21.py
"""
import json, subprocess, sys, wave
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music, sfx_cine  # noqa: E402

D = "/home/claude/ep10"
OUT = f"{D}/out"
SR = 48000
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location("bv21", f"{D}/build_v21.py")
B = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(B)
at, T = B.at, B.T
TOTAL = B.TOTAL

MUSIC = [
    (0.0, T["S10"][0], "stop", "F"), (T["S10"][0], T["S10"][1], "theme", "F"),
    (T["F1"][0], T["F3"][1], "stop", "F"), (T["S12"][0], T["S13"][1], "comedy", "F"),
    (T["S14"][0], at("S15", 0.55), "stop", "F"), (at("S15", 0.55), T["S3"][1], "fanfare", "F"),
    (T["O2"][0], T["N5"][1], "stop", "F"), (T["N3"][0], T["N4"][1], "romance", "F"),
    (T["E7a"][0], T["E7b"][1], "theme", "F"), (T["END"][0], TOTAL, "stop", "F"),
]

EVENTS = [
    (at("O1", 0.0), "paper", 0.7), (at("O1", 0.6), "pop", 0.35),
    (at("S4", 0.0), "sizzle", 0.3), (at("S6", 0.05), "clink", 0.3), (at("S7", 1.85), "cricket", 0.75),
    (at("S10", 0.0), "chime", 0.6),
    (at("F1", 0.3), "stamp", 0.45), (at("F2", 0.3), "stamp", 0.65), (at("F3", 0.05), "mail", 0.7),
    (at("F3", 0.55), "stamp", 1.0), (at("F3", 0.55), "subdrop", 0.7),
    (at("S13", 0.0), "drumroll", 0.75), (at("S15", 0.0), "heart", 0.7),
    (at("S16", 0.0), "clink", 0.8), (at("S16", 0.03), "cheer", 0.7), (at("S3", 0.0), "coinx", 0.6),
    (at("O2", 0.0), "paper", 0.5), (at("S18", 1.45), "tickh", 0.4), (at("S19", 0.9), "zipper", 0.7),
    (at("FZ2", 0.0), "scratch", 0.9), (at("N5a", 0.0), "vibrate", 0.8), (at("N5", 0.8), "sting", 0.9),
    (at("N4", 0.0), "coin", 0.6), (at("E7b", -0.08), "coin", 0.45), (at("END", 0.0), "logo", 0.8),
    (at("END", 2.1), "suck", 0.45),
]
SILENCE = [(T["S14"][0], at("S14", -0.03)), (at("F3", 0.45), at("F3", 0.55)), (at("S18", 0.78), at("S18", 1.42))]

# 대사 조각: (클립, 원본 시작, 원본 끝, 배치 시각, 목표 dBFS, 회상 울림, 속도)
DLG = [
    ("S4", 1.00, 2.75, at("S4", 0.20), -19, False, 1.0),
    ("S5", 1.10, 2.15, at("S5", 0.10), -18, False, 1.0),
    ("S7", 0.25, 1.85, at("S7", 0.10), -19, False, 1.0),
    ("S10", 1.60, 3.50, at("S10", 0.15), -19, False, 1.0),
    ("S17", 0.56, 1.42, at("F1", 0.10), -22, True, 1.0),
    ("S17", 0.56, 1.42, at("F2", 0.10), -22, True, 1.0),
    ("S12", 0.50, 2.80, at("S12", 0.30), -19, False, 1.0),
    ("S13", 0.85, 1.75, at("S13", 0.10), -19, False, 1.0),
    ("S15", 1.95, 2.85, at("S15", 0.55), -17, False, 1.0),
    ("S17", 0.18, 1.50, at("S17", 0.08), -19, False, 1.0),
    ("S18", 0.25, 0.90, at("S18", 0.05), -19, False, 1.0),
    ("S19", 0.85, 2.50, at("S19", 0.10), -19, False, 1.0),
    ("N5", 1.02, 1.52, at("N5", 0.27), -19, False, 1.0),
    ("N3", 2.25, 3.05, at("N3", 0.55), -19, False, 1.0),
    ("E7", 2.22, 3.42, at("E7a", 0.02), -19, False, 1.0),
    ("E7", 4.04, 4.58, at("E7b", 0.02), -19, False, 1.0),
]


def src(k):
    return "/home/claude/ep7/v/clips/S16.mp4" if k == "E7" else f"{D}/clips/{k}.mp4"


def load(path, a, b, memory, tempo):
    af = f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,highpass=f=80,lowpass=f=9000"
    if tempo != 1.0:
        af += f",atempo={tempo}"
    if memory:
        af += ",highpass=f=220,lowpass=f=5000,aecho=0.8:0.55:70|140:0.32|0.18"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    f = int(0.02 * SR)
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
for k, a, b, at, target, mem, tempo in DLG:
    x = load(src(k), a, b, mem, tempo)
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9)
    x = x * 10 ** ((target - lvl) / 20)
    i = int(at * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((at - 0.05, at + len(x) / SR + 0.1))

mus = f"{OUT}/ep10v21_music.wav"
hcs_music.make(TOTAL, MUSIC, mus, room=0.15)
bgw = f"{OUT}/ep10v21_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=mus, music_gain=0.9, events=EVENTS, duck=duck, silence=SILENCE)
bg = sfx_cine.read_st(bgw)[:n]
out = bg * 0.82 + np.stack([dlg, dlg], axis=1)[: len(bg)]
for a, b in SILENCE:
    i, j = int(a * SR), int(b * SR)
    out[i:j] = 0
out = out / np.abs(out).max() * 0.95
raw = f"{OUT}/ep10v21_mix_raw.wav"
write(raw, out)

pre = "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.7:level=false"
m = subprocess.run(["ffmpeg", "-v", "info", "-i", raw, "-af", pre + ",loudnorm=I=-14:TP=-3:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-3:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
      f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
final = f"{OUT}/ep10v21_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", pre + "," + ln + ",alimiter=limit=0.71:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("duck", [(round(a, 2), round(b, 2)) for a, b in duck])
