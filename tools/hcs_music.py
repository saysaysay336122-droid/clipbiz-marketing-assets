"""홍책사, 클립비즈 숏드라마 배경음악을 프로그램으로 직접 만든다(남의 음원 없음, 가사 없음).

구간 목록으로 곡을 짠다. 구간마다 스타일과 조성을 고른다.
  comedy   피치카토 리듬(웃음 구간)
  theme    홍책사 테마: 피아노 4음 동기(1, 3, 5, 4도에서 3도로)와 패드. 매 편 홍책사 등장과 끝에 같은 선율
  romance  패드와 느린 피아노 분산화음(설렘)
  heist    스타카토 현과 낮은 북, 초침(액션 패러디)
  groove   신스 베이스와 손가락 튕김(쇼핑, 일상)
  fanfare  금관 느낌 화음(송년회, 승리)
  xmas     첼레스타와 작은 방울(겨울, 선물)
  office   첼로 지속음과 초침(긴장, 사무실)
  stop     무음(반전 직전 정적)

make(총초, [(시작, 끝, 스타일, 조성), ...], 출력 wav, bpm=None)
조성은 'F', 'D', 'Bb', 'C', 'Cm', 'G', 'Eb' 가운데 하나. 단조는 m을 붙인다.
"""
import math
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(16)
ROOT = {"C": 48, "D": 50, "Eb": 51, "E": 52, "F": 53, "G": 55, "A": 57, "Bb": 58}
DEF_BPM = dict(comedy=100, theme=72, romance=72, heist=128, groove=112, fanfare=120, xmas=76, office=90)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def _t(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.005, d=4.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t * d)


def lp(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode="same")


def piano(m, dur=2.5, vel=0.5):
    t = _t(dur)
    f = hz(m)
    x = sum(a * np.sin(2 * math.pi * f * k * t + rng.random()) * np.exp(-t * (1.2 + 0.9 * k + f / 400))
            for k, a in enumerate([1, 0.45, 0.22, 0.12, 0.07], 1))
    x = x * np.minimum(1, t / 0.004)
    r = int(0.2 * SR)
    x[-r:] *= np.linspace(1, 0, r)
    return x * vel * 0.33


def pizz(m, vel=0.5):
    f = hz(m)
    L = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, L) * 0.8
    n = int(0.6 * SR)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % L]
        buf[i % L] = 0.5 * (buf[i % L] + buf[(i + 1) % L]) * 0.993
    return out * np.exp(-_t(0.6) * 5) * vel * 0.45


def saw(f, t):
    return 2 * ((f * t + rng.random()) % 1) - 1


def pad(ms, dur, vel=0.3):
    t = _t(dur)
    x = sum(saw(hz(m) * 2 ** (d / 12), t) for m in ms for d in (-0.07, 0, 0.06))
    x = lp(lp(x, SR / 1400), SR / 1400)
    e = np.minimum(1, t / 1.2) * np.clip((dur - t) / 1.2, 0, 1)
    return x * e * vel * 0.06 / len(ms) * 3


def stacc(m, vel=0.4):
    t = _t(0.18)
    x = lp(saw(hz(m), t) + saw(hz(m) * 1.003, t), SR / 2500)
    return x * env(len(t), 0.004, 18) * vel * 0.3


def tom(m, vel=0.6):
    t = _t(0.5)
    f = hz(m) * (1 + 0.6 * np.exp(-t * 30))
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 9) * vel * 0.6


def snap(vel=0.4):
    n = int(0.07 * SR)
    x = np.diff(rng.standard_normal(n), prepend=0)
    return x * env(n, 0.0005, 90) * vel * 0.5


def bass(m, dur=0.4, vel=0.5):
    t = _t(dur)
    x = np.sin(2 * math.pi * hz(m) * t) + 0.3 * lp(saw(hz(m), t), SR / 800)
    return x * env(len(t), 0.005, 5) * vel * 0.45


def brass(ms, dur=1.0, vel=0.4):
    t = _t(dur)
    x = sum(lp(saw(hz(m), t) + saw(hz(m) * 1.004, t), SR / 1800) for m in ms)
    e = np.minimum(1, t / 0.06) * np.clip((dur - t) / 0.3, 0, 1)
    return x * e * vel * 0.12 / len(ms) * 2


def celesta(m, vel=0.4):
    t = _t(1.6)
    f = hz(m)
    x = np.sin(2 * math.pi * f * t) + 0.3 * np.sin(2 * math.pi * 4 * f * t) * np.exp(-t * 8)
    return x * env(len(t), 0.002, 3) * vel * 0.25


def jingle(vel=0.25):
    n = int(0.25 * SR)
    x = sum(np.sin(2 * math.pi * f * _t(0.25)) for f in (5200, 6100, 7300)) + rng.standard_normal(n) * 0.2
    return x * env(n, 0.002, 18) * vel * 0.2


def tick(vel=0.3):
    n = int(0.04 * SR)
    return np.diff(rng.standard_normal(n), prepend=0) * env(n, 0.0005, 150) * vel


def chords(key):
    minor = key.endswith("m")
    r = ROOT[key.rstrip("m")]
    if minor:
        return [[r, r + 3, r + 7], [r - 4, r, r + 3], [r - 7, r - 4, r], [r - 5, r - 1, r + 2]]
    return [[r, r + 4, r + 7], [r + 5, r + 9, r + 12], [r - 3, r, r + 4], [r + 7, r + 11, r + 14]]


def put(buf, at, sig):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def section(buf, a, b, style, key, bpm):
    beat = 60 / bpm
    ch = chords(key)
    r = ROOT[key.rstrip("m")]
    bars = int(math.ceil((b - a) / (beat * 4)))
    if style == "stop":
        return
    if style in ("theme", "romance", "xmas", "office"):
        for k in range(bars):
            c = ch[k % 4]
            t0 = a + k * beat * 4
            put(buf, t0, pad([m + 12 for m in c], min(beat * 4.4, b - t0 + 0.6), 0.32))
    for k in range(bars):
        c = ch[k % 4]
        t0 = a + k * beat * 4
        for s in range(16):
            at = t0 + s * beat / 4
            if at >= b:
                break
            if style == "comedy" and s % 4 in (0, 2):
                put(buf, at, pizz(c[(s // 2) % 3] + 24 if s % 8 == 0 else c[(s // 2) % 3] + 12, 0.5 if s % 8 == 0 else 0.38))
            elif style == "heist":
                if s % 2 == 0:
                    put(buf, at, stacc(c[0] + 12 + (7 if s % 8 == 6 else 0), 0.5))
                if s in (0, 6, 10):
                    put(buf, at, tom(c[0] - 12, 0.7))
                if s % 4 == 0:
                    put(buf, at, tick(0.25))
            elif style == "groove":
                if s in (0, 3, 6, 10, 12):
                    put(buf, at, bass(c[0] - 12, 0.3, 0.55))
                if s in (4, 12):
                    put(buf, at, snap(0.5))
            elif style == "fanfare" and s in (0, 6, 8):
                put(buf, at, brass([m + 12 for m in c], beat * (2 if s == 8 else 1.2), 0.45))
            elif style == "romance" and s % 4 == 0:
                put(buf, at, piano(c[(s // 4) % 3] + 24, 2.2, 0.32))
            elif style == "xmas" and s % 2 == 0:
                put(buf, at, celesta(c[(s // 2) % 3] + 36, 0.35))
                if s % 8 == 4:
                    put(buf, at, jingle(0.3))
            elif style == "office" and s % 4 == 0:
                put(buf, at, tick(0.35))
                if s == 0:
                    put(buf, at, piano(c[0], 3.0, 0.3))
    if style == "theme":
        motif = [(0, 12), (1, 16), (2, 19), (3, 17), (4.5, 16)]
        for k in range(max(1, int((b - a) // (beat * 8)))):
            for st, iv in motif:
                at = a + k * beat * 8 + st * beat
                if at < b:
                    put(buf, at, piano(r + 12 + iv, 2.4, 0.42))


def make(total, sections, out, bpm=None):
    buf = np.zeros(int((total + 2) * SR))
    for a, b, style, key in sections:
        section(buf, a, b, style, key, bpm or DEF_BPM.get(style, 96))
    buf = buf[: int(total * SR)]
    fade = int(0.04 * SR)
    for a, b, style, key in sections:
        if style == "stop":
            i, j = int(a * SR), int(b * SR)
            buf[i:j] = 0
            if i > fade:
                buf[i - fade:i] *= np.linspace(1, 0, fade)
    peak = np.abs(buf).max() or 1
    buf = np.tanh(buf / peak * 1.2) * 0.8
    st = np.stack([buf, np.roll(buf, int(0.012 * SR)) * 0.96], axis=1)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
    return out
