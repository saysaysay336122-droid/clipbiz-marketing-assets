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
_sp = importlib.util.spec_from_file_location("b11", f"{D}/build11.py")
B = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(B)
at, T, OPT = B.at, B.T, B.OPT
TOTAL = B.TOTAL

MUSIC = [
    (0.0, T["S4"][0], "stop", "F"), (T["S4"][0], T["S4"][1], "theme", "F"),
    (T["C4"][0], at("C7", 0.45), "comedy", "F"), (at("C7", 0.45), T["C7"][1], "stop", "F"),
    (T["S5"][0], T["S5"][1], "comedy", "F"), (T["C8"][0], T["C9"][1], "fanfare", "F"),
    (T["S6"][0], T["E7b"][1], "theme", "F"), (T["END"][0], TOTAL, "stop", "F"),
]

EVENTS = [
    # 첫 장면: 보냄, 숫자 줄어듦 세 번 같은 소리, 0에서 쿵
    (at("O1", 0.0), "pop", 1.0), (at("O1", 0.02), "swishr", 0.5),
    (at("O1", 0.40), "tickh", 0.75), (at("O1", 0.75), "tickh", 0.75), (at("O1", 1.10), "tickh", 0.75),
    (at("O1", 1.45), "hitd", 0.9), (at("O1", 1.45), "subdrop", 0.7),
    (at("S1", 0.0), "heartx", 0.8), (at("S1", 1.6), "heartx", 0.6),
    # 입력 중: 째깍, 사라질 때 끊김, 다시 뜰 때 상승
    (at("C2", 0.05), "tickh", 0.7), (at("C2", 0.42), "stutter", 0.6), (at("C2", 0.68), "tickh", 0.7),
    (at("C2", 0.30), "rise1", 0.6),
    (at("S2", 0.0), "keys", 0.9),
    (at("S3", 1.75), "cricket", 0.55),
    # 홍책사
    (at("S4", 0.0), "shimmer", 0.8), (at("S4", 3.55), "coinx", 0.8),
    # 답장들: 같은 소리 두 번, 세 번째 변주
    (at("C4", 0.25), "swishr", 0.6), (at("C4", 0.27), "pop", 0.9),
    (at("C5", 0.05), "pop", 1.0), (at("C5", 0.08), "drum", 0.6),
    (at("C6", 0.05), "pop", 1.0),
    (at("C7", 0.05), "plink", 1.0),
    # 반전: 정적 뒤 레코드 긁힘
    (at("S5", 0.0), "scratch", 1.0), (at("S5", 0.0), "hitd", 0.6), (at("S5", 1.35), "cricket", 0.6),
    (at("C8", 0.05), "mail", 0.8), (at("C8", 0.30), "stamp", 0.9),
    (at("C9", 0.05), "pop", 0.9), (at("C9", 0.10), "heart", 0.6),
    (at("S6", 0.0), "chime", 0.6),
    (at("E7b", -0.08), "coin", 0.45), (at("END", 0.0), "logo", 0.8), (at("END", 2.1), "suck", 0.45),
]
SILENCE = [(at("C7", 0.45), T["C7"][1])]


def seg(sid, s0, s1):
    """클립 sid의 원본 s0~s1 구간을 화면과 같은 시각에 놓는다."""
    a = OPT[sid]["a"]
    return (sid, s0, s1, T[sid][0] + (s0 - a))


DLG = [seg("S1", 0.45, 1.95), seg("S3", 0.25, 1.95), seg("S4", 0.05, 1.90)]
if "S5" in json.load(open(f"{D}/speech.json")):
    s5 = json.load(open(f"{D}/speech.json"))["S5"]
    DLG.append(seg("S5", max(OPT["S5"]["a"], s5[0] - 0.08), s5[1] + 0.12))
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
    x = x * 10 ** ((-18 - lvl) / 20)
    i = int(t0 * SR)
    j = min(n, i + len(x))
    dlg[i:j] += x[: j - i]
    duck.append((t0 - 0.05, t0 + len(x) / SR + 0.1))

mus = f"{OUT}/ep11_music.wav"
hcs_music.make(TOTAL, MUSIC, mus, room=0.15)
bgw = f"{OUT}/ep11_bg.wav"
sfx_cine.mix(TOTAL, bgw, music=mus, music_gain=0.85, events=EVENTS, duck=duck, silence=SILENCE)
bg = sfx_cine.read_st(bgw)[:n]
out = bg * 0.9 + np.stack([dlg, dlg], axis=1)[: len(bg)]
for a, b in SILENCE:
    i, j = int(a * SR), int(b * SR)
    out[i:j] = 0
out = out / np.abs(out).max() * 0.95
raw = f"{OUT}/ep11_mix_raw.wav"
write(raw, out)

pre = "highpass=f=30,lowshelf=f=90:g=-2,alimiter=limit=0.7:level=false"
m = subprocess.run(["ffmpeg", "-v", "info", "-i", raw, "-af", pre + ",loudnorm=I=-14:TP=-3.5:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-3.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
      f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
final = f"{OUT}/ep11_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", pre + "," + ln + ",alimiter=limit=0.63:level=false",
                "-ar", "48000", final], check=True)
r = subprocess.run(["ffmpeg", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print([l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("dlg", [(k, round(t0, 2)) for k, a, b, t0 in DLG])
