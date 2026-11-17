"""8화 v7 소리: 영화판 효과음과 음악(sfx_cine.mix) 위에 생성 클립의 대사와 재채기를 얹고 마스터링."""
import json, subprocess, sys, wave
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import sfx_cine  # noqa: E402

D = "/home/claude/ep8"
SR = 48000
spec = json.load(open(f"{D}/ep08_spec_v7.json", encoding="utf-8"))
TOTAL = spec["target_sec"]
T = {s["id"]: s["t"] for s in spec["shots"]}

# 대사 조각: (클립, 원본 시작, 원본 끝, 배치 시각, 음높이 배율, 목표 dBFS)
DLG = [
    ("S12", 0.45, 1.20, 0.30, 1.0, -19),
    ("S3", 1.58, 2.42, 4.38, 1.0, -19),
    ("S5", 0.55, 1.65, 7.45, 1.0, -19),
    ("S8", 1.00, 2.15, 12.40, 1.0, -19),
    ("S12", 0.42, 1.25, T["S12"][0] + 0.02, 1.0, -19),
    ("S14", 0.05, 1.80, T["S14"][0] + 0.05, 0.86, -17),
    ("Q11", 0.12, 0.95, T["Q11"][0] + 0.07, 1.0, -20),
    ("S16", 1.18, 2.30, T["S16"][0] + 0.88, 1.0, -19),
    ("S17", 0.14, 0.80, T["S17"][0] + 0.04, 1.0, -19),
    ("S17", 2.58, 4.00, T["S17"][0] + 1.88, 1.0, -19),
    ("E7", 1.80, 4.75, T["S20"][0], 1.0, -19),
]
SRC = {k: f"{D}/clips/{k}.mp4" for k in ("S3", "S5", "S8", "S12", "S14", "S16", "S17")}
SRC["Q11"] = f"{D}/clips_v7/Q11.mp4"
SRC["E7"] = "/home/claude/ep7/v/clips/S16.mp4"


def load(path, a, b, pitch):
    af = f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,highpass=f=80,lowpass=f=9000"
    if pitch != 1.0:
        af += f",rubberband=pitch={pitch}:formant=preserved"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    f = int(0.025 * SR)
    if len(x) > 2 * f:
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    return x


n = int(TOTAL * SR)
dlg = np.zeros(n)
duck = []
for k, a, b, at, p, target in DLG:
    x = load(SRC[k], a, b, p)
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9)
    x = x * 10 ** ((target - lvl) / 20)
    i = int(at * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    if k != "Q11":
        duck.append((at - 0.05, at + len(x) / SR + 0.1))

# 음악 구간별 세기: 멈춘 공기 패드는 낮추고, 홍책사가 움직이기 시작하는 그루브는 올린다
mus = sfx_cine.read_st(f"{D}/ep08_music_v7.wav")
gain = np.ones(len(mus))
for a, b, style, key in spec["music"]:
    g = {"frozen": 0.5, "speed": 1.3}.get(style, 1.0)
    gain[int(a * SR):int(b * SR)] = g
gain = np.convolve(gain, np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
mus = mus * gain[:, None]
musw = f"{D}/out/ep08_music_v7_lv.wav"
with wave.open(musw, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(mus / max(1.0, np.abs(mus).max()), -1, 1) * 32767).astype(np.int16).tobytes())

events = [(at, nm, g) for s in spec["shots"] for at, nm, g in s.get("sfx", [])]
silence = [tuple(x) for x in spec["silence"]]
bgw = f"{D}/out/ep08_bg_v7.wav"
sfx_cine.mix(TOTAL, bgw, music=musw, music_gain=0.95, events=events, duck=duck, silence=silence,
             bed=[tuple(b) for b in spec.get("bed", [])])
bg = sfx_cine.read_st(bgw)[:n]
out = bg[:n] * 0.82 + np.stack([dlg, dlg], axis=1)[: len(bg)]
for a, b in silence:
    out[int(a * SR):int(b * SR)] = 0
out = out / np.abs(out).max() * 0.95
mixw = f"{D}/out/ep08_mix_v7_raw.wav"
with wave.open(mixw, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
final = f"{D}/out/ep08_mix_v7.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mixw, "-af",
                "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.6:level=false,loudnorm=I=-13.5:TP=-4:LRA=11,alimiter=limit=0.55:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("duck", [(round(a, 2), round(b, 2)) for a, b in duck])
