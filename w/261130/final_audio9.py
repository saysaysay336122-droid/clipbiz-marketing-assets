"""9화 소리: 자체 제작 음악과 영화판 효과음(sfx_cine.mix) 위에 생성 클립의 대사를 얹고 마스터링."""
import json
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music  # noqa: E402
import sfx_cine  # noqa: E402

D = "/home/claude/clipbiz-marketing-assets/w/261130"
SR = 48000
spec = json.load(open(f"{D}/ep09_spec_v6.json", encoding="utf-8"))
TOTAL = spec["target_sec"]
T = {s["id"]: s["t"] for s in spec["shots"]}

# 대사 조각: (클립, 원본 시작, 원본 끝, 배치 시각, 목표 dBFS)
DLG = [
    ("S0b", 0.70, 1.75, T["S0b"][0] + 0.40, -19),
    ("S19", 0.20, 2.30, T["S19"][0], -19),
    ("S20", 2.50, 4.40, T["S20"][0] + 0.60, -19),
    ("S24", 0.10, 2.80, T["S24"][0], -19),
    ("S25", 0.20, 3.15, T["S25"][0], -19),
    ("EP7", 1.85, 4.75, T["S27"][0] - 0.05, -19),
]
SRC = {k: f"{D}/gen9/clips/{k}.mp4" for k in ("S0b", "S19", "S20", "S24", "S25")}
SRC["EP7"] = "/home/claude/ep7/v/clips/S16.mp4"


def load(path, a, b):
    af = f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,highpass=f=80,lowpass=f=9000"
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
for k, a, b, at, target in DLG:
    x = load(SRC[k], a, b)
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9)
    x = x * 10 ** ((target - lvl) / 20)
    i = int(at * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((at - 0.05, at + len(x) / SR + 0.1))

musw0 = f"{D}/out/ep09_music_final.wav"
hcs_music.make(TOTAL, [tuple(x) for x in spec["music"]], musw0, room=spec.get("music_room", 0.0))
mus = sfx_cine.read_st(musw0)
gain = np.ones(len(mus))
for a, b, style, key in spec["music"]:
    g = {"frozen": 0.6, "action": 1.05, "anthem": 1.1}.get(style, 1.0)
    gain[int(a * SR):int(b * SR)] = g
gain = np.convolve(gain, np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
mus = mus * gain[:, None]
musw = f"{D}/out/ep09_music_final_lv.wav"
write(musw, mus / max(1.0, np.abs(mus).max()))

events = [(at, nm, g) for s in spec["shots"] for at, nm, g in s.get("sfx", [])]
silence = [tuple(x) for x in spec.get("silence", [])]
bgw = f"{D}/out/ep09_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=musw, music_gain=0.95, events=events, duck=duck, silence=silence,
             bed=[tuple(b) for b in spec.get("bed", [])])
bg = sfx_cine.read_st(bgw)[:n]
out = bg[:n] * 0.82 + np.stack([dlg, dlg], axis=1)[: len(bg)]
for a, b in silence:
    out[int(a * SR):int(b * SR)] = 0
out = out / np.abs(out).max() * 0.95
mixw = f"{D}/out/ep09_mix_raw.wav"
write(mixw, out)
final = f"{D}/out/ep09_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mixw, "-af",
                "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.6:level=false,loudnorm=I=-14:TP=-2.5:LRA=11,alimiter=limit=0.7:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([ln.strip() for ln in r.splitlines() if "I:" in ln or "Peak:" in ln][-2:])
print("duck", [(round(a, 2), round(b, 2)) for a, b in duck])
