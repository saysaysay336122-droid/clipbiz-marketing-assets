"""홍책사 10화 v20 소리(28.6초): 자체 음악과 효과음 위에 생성 클립 대사를 얹고 2패스 음량 맞춤.
사용: python3 final_audio_v20.py
"""
import json, subprocess, sys, wave
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music, sfx_cine  # noqa: E402

D = "/home/claude/ep10"
OUT = f"{D}/out"
SR = 48000
TOTAL = 28.6

MUSIC = [
    (0.0, 4.65, "stop", "F"), (4.65, 6.55, "theme", "F"), (6.55, 8.95, "stop", "F"),
    (8.95, 11.85, "comedy", "F"), (11.85, 12.90, "stop", "F"), (12.90, 14.75, "fanfare", "F"),
    (14.75, 21.50, "stop", "F"), (21.50, 23.80, "romance", "F"), (23.80, 25.60, "theme", "F"),
    (25.60, TOTAL, "stop", "F"),
]

EVENTS = [
    (0.0, "paper", 0.7), (0.30, "pop", 0.35),
    (1.45, "rewind", 0.9), (1.75, "sizzle", 0.3),
    (2.70, "clink", 0.3), (4.25, "cricket", 0.75),
    (4.65, "chime", 0.6),
    (6.80, "stamp", 0.4), (7.62, "stamp", 0.6), (8.28, "mail", 0.7), (8.52, "stamp", 1.0), (8.52, "subdrop", 0.7),
    (10.95, "drumroll", 0.75),
    (12.35, "heart", 0.7),
    (13.85, "clink", 0.8), (13.88, "cheer", 0.7),
    (14.35, "coinx", 0.6),
    (16.05, "sizzle", 0.25), (17.55, "zipper", 0.7),
    (18.40, "scratch", 0.9),
    (19.02, "vibrate", 0.8), (19.50, "stamp", 1.0),
    (21.00, "sting", 0.9),
    (23.10, "coin", 0.6),
    (25.50, "coin", 0.45), (25.60, "logo", 0.8),
    (27.70, "suck", 0.45),
]
SILENCE = [(1.15, 1.45), (8.43, 8.52), (11.85, 12.32)]

# 대사 조각: (클립, 원본 시작, 원본 끝, 배치 시각, 목표 dBFS, 회상 울림, 속도)
DLG = [
    ("S18", 0.25, 0.90, 0.50, -18, False, 1.0),
    ("S5", 1.10, 2.15, 1.77, -18, False, 1.2),
    ("S7", 0.25, 1.85, 3.35, -19, False, 1.25),
    ("S10", 1.60, 3.50, 4.65, -19, False, 1.0),
    ("S17", 0.56, 1.42, 6.58, -22, True, 1.1),
    ("S17", 0.56, 1.42, 7.43, -22, True, 1.1),
    ("S12", 0.50, 2.80, 8.95, -19, False, 1.15),
    ("S13", 0.85, 1.75, 10.95, -19, False, 1.0),
    ("S15", 1.95, 2.85, 12.90, -17, False, 1.0),
    ("S17", 0.18, 1.50, 14.82, -19, False, 1.1),
    ("S18", 0.25, 0.90, 16.10, -19, False, 1.0),
    ("S19", 0.85, 2.50, 16.895, -19, False, 1.1),
    ("N5", 1.02, 1.52, 20.47, -19, False, 1.0),
    ("N3", 2.25, 3.05, 22.05, -19, False, 1.0),
    ("E7", 2.22, 3.42, 23.82, -19, False, 1.0),
    ("E7", 4.04, 4.58, 25.04, -19, False, 1.0),
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

mus = f"{OUT}/ep10v20_music.wav"
hcs_music.make(TOTAL, MUSIC, mus, room=0.15)
bgw = f"{OUT}/ep10v20_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=mus, music_gain=0.9, events=EVENTS, duck=duck, silence=SILENCE)
bg = sfx_cine.read_st(bgw)[:n]
out = bg * 0.82 + np.stack([dlg, dlg], axis=1)[: len(bg)]
for a, b in SILENCE:
    i, j = int(a * SR), int(b * SR)
    out[i:j] = 0
out = out / np.abs(out).max() * 0.95
raw = f"{OUT}/ep10v20_mix_raw.wav"
write(raw, out)

pre = "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.7:level=false"
m = subprocess.run(["ffmpeg", "-v", "info", "-i", raw, "-af", pre + ",loudnorm=I=-14:TP=-3:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-3:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
      f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
final = f"{OUT}/ep10v20_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", pre + "," + ln + ",alimiter=limit=0.71:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("duck", [(round(a, 2), round(b, 2)) for a, b in duck])
