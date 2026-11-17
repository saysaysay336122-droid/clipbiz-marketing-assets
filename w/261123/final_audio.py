"""8화 완성본 소리: 영화판 효과음과 음악(sfx_cine.mix) 위에 생성 클립의 대사를 얹고 -14 LUFS로 마스터링."""
import json, subprocess, sys, wave
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import sfx_cine  # noqa: E402

D = "/home/claude/ep8"
SR = 48000
spec = json.load(open(f"{D}/ep08_spec_v6.json", encoding="utf-8"))
TOTAL = spec["target_sec"]

# 대사 조각: (클립, 원본 시작, 원본 끝, 배치 시각, 음높이 배율)
DLG = [
    ("S12", 0.45, 1.20, 0.30, 1.0),
    ("S3", 1.58, 2.42, 4.38, 1.0),
    ("S5", 0.55, 1.65, 7.45, 1.0),
    ("S8", 1.00, 2.15, 12.40, 1.0),
    ("S12", 0.42, 1.25, 19.92, 1.0),
    ("S14", 0.05, 1.80, 24.15, 0.86),
    ("S16", 1.18, 2.30, 33.08, 1.0),
    ("S17", 0.14, 0.80, 35.44, 1.0),
    ("S17", 2.58, 4.00, 37.28, 1.0),
    ("E7", 1.80, 4.75, 43.90, 1.0),
]
SRC = {k: f"{D}/clips/{k}.mp4" for k in ("S3", "S5", "S8", "S12", "S14", "S16", "S17")}
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


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


n = int(TOTAL * SR)
dlg = np.zeros(n)
duck = []
for k, a, b, at, p in DLG:
    x = load(SRC[k], a, b, p)
    # 말소리 구간만 기준으로 음량 맞춤(-19 dBFS)
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9) if act.any() else rms_db(x)
    x = x * 10 ** (((-17 if k == "S14" else -19) - lvl) / 20)
    i = int(at * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((at - 0.05, at + len(x) / SR + 0.1))

# 효과음 큐(설계서 v6에서 S14 낚아채기 시각만 실제 프레임에 맞춤)
events, silence = [], []
for sh in spec["shots"]:
    for at, nm, g in sh.get("sfx", []):
        if sh["id"] == "S14":
            if nm in ("suck", "rise1"):
                at = 25.95
            elif nm in ("hit", "coinx"):
                at = 26.85
            elif nm == "tapestart":
                at = 26.87
            elif nm == "swishl":
                at, g = 23.98, 0.3
        events.append((at, nm, g))
silence = [(26.75, 26.85), (40.25, 40.7)]

bgw = f"{D}/out/ep08_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=f"{D}/ep08_music_v6.wav", music_gain=0.95, events=events, duck=duck,
             silence=silence, bed=[tuple(b) for b in spec.get("bed", [])])
bg = sfx_cine.read_st(bgw)[:n]
out = bg * 0.82 + np.stack([dlg, dlg], axis=1)
for a, b in silence:
    out[int(a * SR):int(b * SR)] = 0
pk = np.abs(out).max()
out = out / pk * 0.95
mixw = f"{D}/out/ep08_mix_raw.wav"
with wave.open(mixw, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
final = f"{D}/out/ep08_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mixw, "-af",
                "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.75:level=false,loudnorm=I=-14:TP=-2.5:LRA=11,alimiter=limit=0.76:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("duck", [(round(a, 2), round(b, 2)) for a, b in duck])
