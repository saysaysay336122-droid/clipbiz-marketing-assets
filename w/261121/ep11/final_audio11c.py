"""홍책사 11화 소리: 자체 음악, 세게 넣은 효과음, 생성 클립 대사, 2패스 음량 맞춤(-14 LUFS).
사용: python3 final_audio11.py
"""
import json, subprocess, sys, wave
import numpy as np

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music, sfx_cine  # noqa: E402

D = "/home/claude/ep11"
OUT = f"{D}/out"
SR = 48000
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location("b11c", f"{D}/build11c.py")
B = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(B)
at, T, OPT = B.at, B.T, B.OPT
TOTAL = B.TOTAL

MUSIC = [
    (0.0, T["T1"][0], "stop", "Fm"), (T["T1"][0], T["N3b"][1], "action", "Fm"),
    (T["N4"][0], T["N4"][1], "anthem", "F"), (T["S4"][0], at("S4", 1.95), "stop", "F"), (at("S4", 1.95), T["S4"][1], "anthem", "F"),
    (T["C4"][0], at("C7", 0.55), "action", "Fm"), (at("C7", 0.55), T["S5"][1], "stop", "F"),
    (T["C8"][0], T["S6"][1], "anthem", "F"), (T["E7a"][0], T["E7b"][1], "theme", "F"), (T["END"][0], TOTAL, "stop", "F"),
]

EVENTS = [
    # 숫자 폭탄
    (at("O1", 0.0), "glitch", 0.7), (at("O1", 0.0), "hitd", 0.75), (at("O1", 0.45), "hitd", 0.75),
    (at("O1", 0.90), "hitd", 0.8), (at("O1", 1.35), "hitd", 0.85), (at("O1", 0.90), "rise1", 0.8),
    (at("O1", 1.80), "hit", 1.0), (at("O1", 1.80), "braam", 0.85), (at("O1", 1.82), "stamp", 0.8),
    # 휴대폰 낙하: 슬로 속 휙, 바닥 충돌
    (at("N1", 0.0), "swishl", 0.5), (at("N1", 0.25), "rise1", 0.6), (at("N1", 1.18), "hit", 1.0), (at("N1", 1.2), "clink", 0.7),
    (at("N1", 1.2), "subdrop", 0.7),
    # 공포 클로즈업: 심장 두 번, 이명
    (at("N2", 0.0), "heartx", 1.0), (at("N2", 0.7), "heartx", 0.9), (at("N2", 0.2), "ring", 0.35),
    # 입력 중 카드와 추격
    (at("T1", 0.0), "hit", 0.9), (at("T1", 0.0), "glitch", 0.8),
    (at("N3", 0.0), "braam", 0.6), (at("N3", 0.1), "keys", 0.7),
    (at("XA", 0.0), "swishr", 0.7), (at("XA", 0.0), "alarm", 0.7), (at("M1", 0.0), "timp", 0.7),
    (at("M1", 0.05), "keys", 0.9), (at("XB", 0.0), "glitch", 0.9), (at("XB", 0.05), "stutter", 0.7),
    (at("N3b", 0.0), "swishl", 0.7), (at("N3b", 0.05), "lockon", 0.7), (at("N3b", -0.15), "hitd", 0.7),
    # 홍책사 역광 등장, 엽전 튕김
    (at("N4", 0.0), "braam", 0.9), (at("N4", 0.0), "shimmer", 0.9), (at("N4", 0.85), "coinx", 0.9),
    (at("N4", 0.9), "hitd", 0.6),
    (at("S4", 1.9), "swishr", 0.5), (at("S4", 2.4), "revcym", 0.6), (at("S4", 3.27), "coinx", 1.0), (at("S4", 3.27), "hitd", 0.55),
    # 반격과 답장 폭격
    (at("C4", 0.0), "rise1", 0.7), (at("C4", 0.2), "swishr", 0.8), (at("C4", 0.2), "hit", 0.8),
    (at("C5", 0.05), "hitd", 0.95), (at("C5", 0.05), "pop", 0.7),
    (at("C6", 0.05), "hitd", 0.95), (at("C6", 0.05), "pop", 0.7),
    (at("C7", 0.05), "hit", 1.0), (at("C7", 0.05), "drum", 0.8),
    # 시아버지 귤 엎기, 정지 세 번 줌
    (at("N5", 0.0), "swishl", 0.6), (at("N5", 0.55), "hit", 0.9), (at("N5", 0.6), "roll", 0.8), (at("N5", 0.9), "plink", 0.6),
    (at("N5", 1.2), "plink", 0.6), (at("S5", 0.0), "scratch", 0.9), (at("S5", 0.0), "drum", 1.0),
    (at("S5", 0.2), "drum", 1.0), (at("S5", 0.4), "drum", 1.0), (at("S5", 0.6), "ring", 0.4), (at("S5", 1.85), "cricket", 0.6),
    # 작전명 도장, 며느리 편
    (at("C8", 0.1), "mail", 0.6), (at("C8", 0.35), "stamp", 1.0), (at("C8", 0.35), "lockon", 0.6),
    (at("C8", 0.35), "timp", 0.7), (at("C9", 0.05), "pop", 0.8), (at("C9", 0.05), "timp", 0.7),
    (at("S6", 0.0), "shimmer", 0.6),
    (at("E7b", -0.08), "coin", 0.45), (at("END", 0.0), "logo", 0.8), (at("END", 2.1), "suck", 0.45),
]
SILENCE = [(at("C7", 0.6), T["C7"][1])]


def seg(sid, s0, s1):
    m = OPT[sid]["map"]
    if m[0] == "lin":
        return (OPT[sid]["src"], s0, s1, T[sid][0] + (s0 - m[1]) / m[2])
    if m[0] == "hero2":
        return (OPT[sid]["src"], s0, s1, T[sid][0] + s0)
    if m[0] == "dad":
        return (OPT[sid]["src"], s0, s1, T[sid][0] + 0.6 + (s0 - 0.95))
    raise ValueError(m)


DLG = [seg("S4", 0.05, 1.88), seg("S5", 1.0, 2.1)]
DLG += [("E7", 2.22, 3.42, at("E7a", 0.02)), ("E7", 4.04, 4.58, at("E7b", 0.02))]


def src(k):
    return "/home/claude/ep7/v/clips/S16.mp4" if k == "E7" else f"{D}/clips/{k}.mp4"


def load(path, a, b):
    af = f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,highpass=f=80,lowpass=f=9000"
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
for k, a, b, t0 in DLG:
    x = load(src(k), a, b)
    fr = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, max(1, len(x) - fr), fr)])
    act = e > (e.max() * 0.2)
    lvl = 20 * np.log10(np.sqrt(np.mean(e[act] ** 2)) + 1e-9)
    x = x * 10 ** ((-16 - lvl) / 20)
    i = int(t0 * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((t0 - 0.05, t0 + len(x) / SR + 0.1))

mus = f"{OUT}/ep11c_music.wav"
hcs_music.make(TOTAL, MUSIC, mus, room=0.15)
bgw = f"{OUT}/ep11c_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=mus, music_gain=0.95, events=EVENTS, duck=duck, silence=SILENCE)
bg = sfx_cine.read_st(bgw)[:n]
out = bg * 0.9 + np.stack([dlg, dlg], axis=1)[: len(bg)]
for a, b in SILENCE:
    i, j = int(a * SR), int(b * SR)
    out[i:j] = 0
out = out / np.abs(out).max() * 0.95
raw = f"{OUT}/ep11c_mix_raw.wav"
write(raw, out)

pre = "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.7:level=false"
m = subprocess.run(["ffmpeg", "-v", "info", "-i", raw, "-af", pre + ",loudnorm=I=-14:TP=-3.5:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-3.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
      f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
final = f"{OUT}/ep11c_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", pre + "," + ln + ",alimiter=limit=0.63:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("dlg", [(k, round(t0, 2)) for k, a, b, t0 in DLG])
