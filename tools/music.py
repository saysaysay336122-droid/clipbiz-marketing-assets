"""릴스와 쇼츠용 배경 음악을 프로그램으로 직접 만든다(저작권 걱정 없는 자체 제작음).

밝은 장조, 박자감 있는 요즘 숏폼 느낌. 같은 seed면 같은 곡, seed가 바뀌면 조, 빠르기, 코드 진행, 멜로디가 바뀐다.

스타일
  bright  : 112~118 BPM, 마림바 멜로디와 엇박 코드, 박수. 안심클립, 하이클립, 클립마켓 기본
  playful : 118~124 BPM, 짧게 튕기는 코드와 종소리 멜로디. 홍책사 기본
  chill   : 90~96 BPM, 가볍게 흔들리는 리듬과 부드러운 건반. 정보형 차분한 편

사용: from music import make_track; make_track(초, "out.wav", style="bright", seed=3)
"""
import math
import wave

import numpy as np

SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
# 장조 안의 화음(근음 음계 번호). 모두 밝게 들리는 진행만 쓴다
PROGRESSIONS = [[0, 4, 5, 3], [5, 3, 0, 4], [0, 5, 3, 4], [3, 4, 0, 0], [0, 3, 4, 3]]
STYLES = {
    "bright": dict(bpm=(112, 118), swing=0.0, kick=[0, 1.5, 2], clap=[1, 3], hat=0.13, pluck=0.55, mel=0.5, bass=0.3),
    "playful": dict(bpm=(118, 124), swing=0.0, kick=[0, 2, 2.5], clap=[1, 3], hat=0.11, pluck=0.6, mel=0.55, bass=0.28),
    "chill": dict(bpm=(90, 96), swing=0.12, kick=[0, 2.5], clap=[1, 3], hat=0.09, pluck=0.5, mel=0.45, bass=0.3),
}


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_exp(n, decay):
    return np.exp(-np.arange(n) / SR * decay)


def add(buf, start, sig):
    s = int(start * SR)
    if s >= len(buf):
        return
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[: e - s]


def kick():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 32)
    ph = 2 * math.pi * np.cumsum(f) / SR
    click = np.sin(2 * math.pi * 1800 * t) * np.exp(-t * 400) * 0.25
    return np.sin(ph) * np.exp(-t * 11) + 0.3 * np.sin(ph * 2) * np.exp(-t * 25) + click


def clap(rng):
    n = int(0.22 * SR)
    noise = rng.standard_normal(n)
    # 대역 통과 비슷하게: 고역만 남기고 너무 높은 소리는 깎는다
    hp = np.diff(noise, prepend=0)
    bp = np.convolve(hp, np.ones(6) / 6, mode="same")
    e = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.023]):
        s = int(off * SR)
        e[s:] += env_exp(n - s, 70 if k < 2 else 22) * (0.8 if k < 2 else 1.0)
    return bp * e * 0.9


def hat(rng, open_=False):
    n = int((0.12 if open_ else 0.045) * SR)
    noise = rng.standard_normal(n)
    hp = np.diff(np.diff(noise, prepend=0), prepend=0)
    return hp * env_exp(n, 30 if open_ else 90) * 0.35


def pluck(freqs, dur, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for h in range(1, 7):
            if f * h > 9000:
                break
            out += (bright ** (h - 1)) / h * np.sin(2 * math.pi * f * h * t + h)
    return out / len(freqs) * env_exp(n, 9)


def bell(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * math.pi * f * t) + 0.35 * np.sin(2 * math.pi * f * 4 * t) * np.exp(-t * 18)
            + 0.15 * np.sin(2 * math.pi * f * 2.01 * t)) * env_exp(n, 6.5)


def bass_note(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * math.pi * f * t) + 0.25 * np.sin(2 * math.pi * 2 * f * t) + 0.08 * np.sin(2 * math.pi * 3 * f * t)
    a = np.minimum(1, t / 0.008)
    return sig * a * env_exp(n, 3.5)


def make_track(seconds, path, style="bright", seed=7):
    st = STYLES.get(style, STYLES["bright"])
    rng = np.random.default_rng(seed)
    bpm = float(rng.integers(st["bpm"][0], st["bpm"][1] + 1))
    beat = 60.0 / bpm
    key = int(rng.choice([NOTE["C"], NOTE["D"], NOTE["F"], NOTE["G"], NOTE["A"]]))
    prog = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]
    n = int((seconds + 0.5) * SR)
    drums, bassb, chords, mel, kenv = (np.zeros(n) for _ in range(5))
    k = kick()
    # 멜로디: 2마디짜리 모티브를 만들어 반복(외우기 쉬운 짧은 소리)
    penta = [0, 2, 4, 7, 9]
    motif = []
    for step in range(16):
        if rng.random() < (0.55 if step % 2 == 0 else 0.25):
            motif.append((step, int(rng.choice(penta)), int(rng.choice([0, 0, 12]))))
    bars = int(seconds / (4 * beat)) + 2
    for bar in range(bars):
        t0 = bar * 4 * beat
        deg = prog[bar % 4]
        root = 48 + key + MAJOR[deg]          # 베이스 옥타브
        triad = [MAJOR[(deg + i) % 7] + 12 * ((deg + i) // 7) for i in (0, 2, 4)]
        chord = [midi_hz(60 + key + x) for x in triad]
        # 드럼
        for b in st["kick"]:
            add(drums, t0 + b * beat, k * 0.6)
            kn = int(0.25 * SR)
            add(kenv, t0 + b * beat, env_exp(kn, 12))
        for b in st["clap"]:
            add(drums, t0 + b * beat, clap(rng) * 0.5)
        for e in range(8):
            sw = st["swing"] * beat if e % 2 else 0
            add(drums, t0 + e * beat / 2 + sw, hat(rng, open_=(e == 7)) * (1.0 if e % 2 else 0.6) * st["hat"] / 0.12)
        # 베이스: 8분음 근음, 마지막 박은 5도로
        for e in range(8):
            if e in (2, 6) and style != "chill":
                continue
            f = midi_hz(root + (7 if e == 7 else 0) - 12 * (root > 52))
            add(bassb, t0 + e * beat / 2, bass_note(f, beat / 2 * 0.95))
        # 코드: 엇박 스탭
        for e in range(8):
            if e % 2 == 1 or (style == "chill" and e in (0, 4)):
                add(chords, t0 + e * beat / 2 + (st["swing"] * beat if e % 2 else 0), pluck(chord, beat * 0.6, 0.75))
        # 멜로디(첫 1마디는 비워 시작을 가볍게, 4마디마다 한 번 쉰다)
        if bar >= 1 and bar % 4 != 3:
            half = bar % 2
            for step, p, octv in motif:
                if step // 8 != half:
                    continue
                f = midi_hz(72 + key + p + octv)
                add(mel, t0 + (step % 8) * beat / 2, bell(f, beat * 0.9))
    duck = 1 - 0.55 * np.clip(kenv, 0, 1)
    mix = drums * 0.85 + bassb * st["bass"] * duck + chords * st["pluck"] * duck + mel * st["mel"]
    mix = np.tanh(mix * 1.2)
    fade_in, fade_out = int(0.05 * SR), int(1.0 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    mix = mix[: int(seconds * SR)]
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.55
    data = (mix * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return dict(style=style, bpm=bpm, key=key, prog=prog)


if __name__ == "__main__":
    import sys
    print(make_track(float(sys.argv[2]) if len(sys.argv) > 2 else 20, sys.argv[1],
                     sys.argv[3] if len(sys.argv) > 3 else "bright", int(sys.argv[4]) if len(sys.argv) > 4 else 7))
