"""9화 v7 소리: 자체 음악과 효과음 위에 대사와 생성 클립의 현장음(속도에 맞춰 늘이거나 줄임)을 얹고 마스터링."""
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
spec = json.load(open(f"{D}/ep09_spec_v7.json", encoding="utf-8"))
TOTAL = spec["target_sec"]
T = {s["id"]: s["t"] for s in spec["shots"]}
DLG = [
    ("S0b", 0.70, 1.75, T["S0b"][0] + 0.40, -19),
    ("S19", 0.20, 2.30, T["S19"][0], -19),
    ("S20n", 1.50, 3.50, T["S20n"][0] + 0.50, -19),
    ("S24", 0.10, 2.80, T["S24"][0], -19),
    ("S25", 0.20, 3.10, T["S25"][0], -19),
    ("EP7", 1.85, 4.75, T["S27"][0] - 0.05, -19),
]


def path(k):
    return "/home/claude/ep7/v/clips/S16.mp4" if k == "EP7" else f"{D}/gen9/clips/{k}.mp4"


def load(k, a, b, speed=1.0, voice=True):
    af = f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,highpass=f={80 if voice else 45}"
    if voice:
        af += ",lowpass=f=9000"
    sp = speed
    while sp > 2.0:
        af += ",atempo=2.0"
        sp /= 2.0
    if abs(sp - 1.0) > 0.01:
        af += f",atempo={sp:.4f}"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path(k), "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    f = int(0.02 * SR)
    if len(x) > 2 * f:
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    return x


def level(x, target):
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    if len(e) == 0 or e.max() <= 0:
        return x
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9)
    return x * 10 ** ((target - lvl) / 20)


def write(p, st):
    with wave.open(p, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())


n = int(TOTAL * SR)
dlg = np.zeros(n)
duck = []
for k, a, b, at, target in DLG:
    x = level(load(k, a, b), target)
    i = int(at * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((at - 0.05, at + len(x) / SR + 0.1))
nat = np.zeros(n)
for k, a, b, at, sp, target in spec["nat"]:
    x = level(load(k, a, b, sp, voice=False), target)
    i = int(max(0, at) * SR)
    j = min(n, i + len(x))
    nat[i:j] += x[: j - i]

musw0 = f"{D}/out/ep09v7_music.wav"
hcs_music.make(TOTAL, [tuple(x) for x in spec["music"]], musw0, room=spec.get("music_room", 0.0))
mus = sfx_cine.read_st(musw0)
gain = np.ones(len(mus))
for a, b, style, key in spec["music"]:
    g = {"frozen": 0.6, "action": 0.9, "anthem": 1.1}.get(style, 1.0)
    gain[int(a * SR):int(b * SR)] = g
gain = np.convolve(gain, np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
mus = mus * gain[:, None]
musw = f"{D}/out/ep09v7_music_lv.wav"
write(musw, mus / max(1.0, np.abs(mus).max()))
events = [(at, nm, g) for s in spec["shots"] for at, nm, g in s.get("sfx", []) if at >= 0]
silence = [tuple(x) for x in spec.get("silence", [])]
bgw = f"{D}/out/ep09v7_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=musw, music_gain=0.95, events=events, duck=duck, silence=silence, bed=[tuple(b) for b in spec.get("bed", [])])
bg = sfx_cine.read_st(bgw)[:n]
out = bg[:n] * 0.82 + np.stack([dlg + nat, dlg + nat], axis=1)[: len(bg)]
for a, b in silence:
    out[int(a * SR):int(b * SR)] *= 0.05
out = out / np.abs(out).max() * 0.95
mixw = f"{D}/out/ep09v7_mix_raw.wav"
write(mixw, out)
final = f"{D}/out/ep09v7_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mixw, "-af",
                "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.6:level=false,loudnorm=I=-14:TP=-2.5:LRA=11,alimiter=limit=0.7:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([ln.strip() for ln in r.splitlines() if "I:" in ln or "Peak:" in ln][-2:])
print("events", len(events), "nat", len(spec["nat"]))
