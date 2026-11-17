"""영화 예고편 느낌의 웅장한 효과음을 직접 합성하고(남의 음원 없음), 48kHz 스테레오로 음악과 섞는다.

sfx.py의 짧은 효과음은 그대로 두고, 액션판 회차에 쓰는 큰 소리를 여기에 모았다.
모든 소리는 (샘플 수, 2) 스테레오 배열이고, 큰 소리는 공간 울림(합성 홀 잔향)이 붙는다.

효과음
  hit       시네마틱 충격음: 저음 킥 하강, 몸통, 금속 울림, 긴 홀 잔향(시간 정지, 복귀, 반전)
  hitd      짧은 충격음: 저음이 빨리 빠지고 잔향 0.9초(바로 뒤 대사나 웃음 박자가 오는 곳)
  subdrop   초저음 하강 1.2초(시간이 멈추는 무게)
  suck      역재생 빨려 들어가는 상승음 0.7초(충격음 직전)
  braam     낮은 금관 덩어리 1.8초(영웅 등장, 반전 공개)
  bigbell   큰 종 4초(18:00:00)
  tickh     무거운 시계 초침(카운트다운)
  timp      팀파니 한 번(카운트다운 마지막 박)
  glitch    디지털 지직(작전 표시 멈춤, 잡음)
  lockon    조준 고정 삐 세 번과 확정음
  alarm     짧은 경보 두 번(발각)
  swishr    왼쪽에서 오른쪽으로 지나가는 큰 휙(도플러)
  swishl    오른쪽에서 왼쪽
  gust      돌풍과 종이 펄럭임(오른쪽에서 왼쪽)
  paper     종이 흩날림
  roll      의자 바퀴 구르는 소리 1.6초
  stamp     도장 쾅(작전 실패, 성공)
  coinx     엽전 튕김: 맑은 금속음과 반짝임, 긴 잔향(이번 편 시간 스위치)
  heartx    심장 두 번, 초저음 포함
  shimmer   반짝이는 풍경과 별가루(홍책사 등장)
  drum      낮은 북 한 번(영웅 걸음 박자)
  tapestop, tapestart, scratch, rewind, logo 는 sfx.py 소리를 48kHz 스테레오로 옮겨 쓴다(소리 상표 logo는 매 편 같게).

mix(초, 출력 wav, music=음악 wav, events=[(초, 이름, 크기, 좌우)], cuts=[(시작, 끝)], duck=[(시작, 끝)], silence=[(시작, 끝)])
  silence 구간은 음악과 효과음 잔향까지 모두 완전 무음(엽전을 잡기 직전 0.1초 같은 곳).
  좌우는 -1(왼쪽)~1(오른쪽). duck 구간(대사)에서는 음악을 8dB 낮춘다. 큰 충격음 뒤 0.35초도 음악을 4dB 눌러 소리가 서게 한다.
"""
import math
import wave

import numpy as np
from scipy.signal import fftconvolve, resample_poly, butter, sosfilt

import sfx as _old

SR = 48000
_rng = np.random.default_rng(23)


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _env(n, a=0.003, d=6.0):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t * d)


def _sweep(f0, f1, sec, curve=2.0):
    t = _t(sec)
    p = (t / t[-1]) ** (1 / curve)
    f = f0 * (f1 / f0) ** p
    return np.sin(2 * math.pi * np.cumsum(f) / SR)


def _bp(x, lo, hi, order=2):
    sos = butter(order, [lo / (SR / 2), min(0.99, hi / (SR / 2))], btype="band", output="sos")
    return sosfilt(sos, x)


def _lp(x, fc, order=2):
    sos = butter(order, min(0.99, fc / (SR / 2)), btype="low", output="sos")
    return sosfilt(sos, x)


def _hp(x, fc, order=2):
    sos = butter(order, fc / (SR / 2), btype="high", output="sos")
    return sosfilt(sos, x)


def _st(x, width=0.0, pan=0.0):
    """모노를 스테레오로. width는 좌우 미세 지연(넓이), pan은 -1~1."""
    d = int(abs(width) * 0.012 * SR)
    l = x.copy()
    r = np.concatenate([np.zeros(d), x])[: len(x)] if d else x.copy()
    gl = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
    gr = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
    return np.stack([l * gl, r * gr], axis=1)


_IR = {}


def _ir(sec):
    """합성 홀 잔향 응답: 초기 반사 몇 개와 지수 감쇠 잡음, 시간이 갈수록 어두워짐. 좌우 다른 잡음."""
    if sec in _IR:
        return _IR[sec]
    n = int(sec * SR)
    t = np.arange(n) / SR
    out = []
    for seed in (1, 2):
        g = np.random.default_rng(seed)
        x = g.standard_normal(n) * np.exp(-t * (6.9 / sec))
        dark = _lp(x, 2500)
        mixw = np.clip(t / sec * 2.2, 0, 1)
        x = x * (1 - mixw) + dark * mixw * 1.4
        for k in range(6):
            i = int((0.007 + 0.011 * k + g.random() * 0.006) * SR)
            x[i] += (0.5 - 0.06 * k) * (1 if g.random() > 0.5 else -1)
        x[: int(0.004 * SR)] = 0
        out.append(x / np.sqrt(np.sum(x ** 2)))
    _IR[sec] = np.stack(out, axis=1)
    return _IR[sec]


def _verb(st, sec=2.4, wet=0.35):
    ir = _ir(sec)
    tail = np.zeros((len(st) + len(ir) - 1, 2))
    for c in range(2):
        tail[:, c] = fftconvolve(st[:, c], ir[:, c])
    dry = np.zeros_like(tail)
    dry[: len(st)] = st
    return dry * (1 - wet * 0.5) + tail * wet


def _norm(x, peak=0.9):
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


# 소리들 ------------------------------------------------------------------------

def hit():
    kick = _sweep(95, 32, 0.9, 1.6) * _env(int(0.9 * SR), 0.002, 4.2)
    kick = np.tanh(kick * 1.6)
    body = _lp(_rng.standard_normal(int(0.25 * SR)), 900) * _env(int(0.25 * SR), 0.001, 14) * 1.4
    click = _hp(_rng.standard_normal(int(0.02 * SR)), 2500) * _env(int(0.02 * SR), 0.0003, 200) * 0.6
    t = _t(1.4)
    ring = sum(a * np.sin(2 * math.pi * f * t + _rng.random()) for f, a in
               [(183, 0.5), (412, 0.35), (667, 0.25), (1033, 0.18), (1571, 0.1)]) * _env(len(t), 0.002, 3.2) * 0.35
    n = len(t)
    x = np.zeros(n)
    x[: len(kick)] += kick * 1.1
    x[: len(body)] += body
    x[: len(click)] += click
    x += ring
    st = _st(x, 0.6)
    return _norm(_verb(st, 2.8, 0.45), 0.95)


def hitd():
    """짧은 충격음: hit와 같은 재료에 저음 감쇠를 빠르게, 잔향을 짧게. 바로 뒤에 대사나 웃음 박자가 오는 곳."""
    kick = _sweep(95, 40, 0.45, 1.6) * _env(int(0.45 * SR), 0.002, 9)
    kick = np.tanh(kick * 1.6)
    body = _lp(_rng.standard_normal(int(0.18 * SR)), 900) * _env(int(0.18 * SR), 0.001, 18) * 1.3
    click = _hp(_rng.standard_normal(int(0.02 * SR)), 2500) * _env(int(0.02 * SR), 0.0003, 200) * 0.6
    t = _t(0.6)
    ring = sum(a * np.sin(2 * math.pi * f * t + _rng.random()) for f, a in
               [(183, 0.5), (412, 0.35), (667, 0.25), (1033, 0.18)]) * _env(len(t), 0.002, 7) * 0.3
    x = np.zeros(len(t))
    x[: len(kick)] += kick
    x[: len(body)] += body
    x[: len(click)] += click
    x += ring
    y = _verb(_st(x, 0.5), 0.9, 0.22)
    return _norm(y, 0.92)


def subdrop():
    x = _sweep(72, 26, 1.3, 1.3) * _env(int(1.3 * SR), 0.01, 1.8)
    x = np.tanh(x * 2.0) * 0.9
    return _st(x, 0.0) * 0.95


def suck():
    """역재생 상승음: 잡음과 음을 잔향에 넣은 뒤 뒤집는다."""
    n = int(0.35 * SR)
    src = _bp(_rng.standard_normal(n), 300, 6000) * _env(n, 0.002, 9) * 0.6
    t = _t(0.35)
    src += np.sin(2 * math.pi * 220 * t) * _env(n, 0.002, 7) * 0.4
    st = _verb(_st(src, 0.8), 1.4, 0.95)[: int(0.75 * SR)]
    st = st[::-1].copy()
    fade = np.linspace(0, 1, len(st)) ** 1.5
    return _norm(st * fade[:, None], 0.8)


def braam():
    t = _t(1.9)
    notes = [33, 40, 45, 52]  # A1, E2, A2, E3
    x = np.zeros(len(t))
    for m in notes:
        f = 440 * 2 ** ((m - 69) / 12)
        for d in (-0.12, 0, 0.11):
            fd = f * 2 ** (d / 12)
            x += 2 * ((fd * t + _rng.random()) % 1) - 1
    cutoff = 250 + 1600 * np.clip(t / 0.35, 0, 1) * np.exp(-np.clip(t - 0.35, 0, None) * 1.3)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(0, len(x)):
        a = 1 - math.exp(-2 * math.pi * cutoff[i] / SR)
        acc += a * (x[i] - acc)
        y[i] = acc
    e = np.minimum(1, t / 0.05) * np.clip((1.9 - t) / 0.9, 0, 1)
    y = np.tanh(y * e * 0.25)
    sub = np.sin(2 * math.pi * 55 * t) * e * 0.5
    st = _st(y + sub, 0.9)
    return _norm(_verb(st, 2.6, 0.35), 0.9)


def bigbell():
    t = _t(4.5)
    f0 = 196.0  # G3 근처
    parts = [(0.5, 0.5, 0.6), (1.0, 0.6, 0.9), (1.19, 0.45, 1.2), (1.5, 0.35, 1.4), (2.0, 0.5, 1.7),
             (2.51, 0.22, 2.4), (2.99, 0.18, 2.9), (4.07, 0.1, 4.0)]
    x = sum(a * np.sin(2 * math.pi * f0 * r * t + _rng.random()) * np.exp(-t * dcy) for r, a, dcy in parts)
    strike = _bp(_rng.standard_normal(int(0.03 * SR)), 1500, 8000) * _env(int(0.03 * SR), 0.0003, 120) * 0.5
    x[: len(strike)] += strike
    x *= np.minimum(1, t / 0.002)
    st = _st(x, 0.7)
    return _norm(_verb(st, 3.5, 0.4), 0.9)


def tickh():
    n = int(0.35 * SR)
    wood = _bp(_rng.standard_normal(int(0.03 * SR)), 1200, 5000) * _env(int(0.03 * SR), 0.0003, 160)
    t = _t(0.35)
    thump = np.sin(2 * math.pi * np.cumsum(70 * (1 + 0.8 * np.exp(-t * 40))) / SR) * _env(n, 0.001, 14)
    metal = (np.sin(2 * math.pi * 2350 * t) + 0.6 * np.sin(2 * math.pi * 3720 * t)) * _env(n, 0.0005, 40) * 0.15
    x = thump * 0.9 + metal
    x[: len(wood)] += wood * 0.9
    return _norm(_verb(_st(x, 0.3), 1.6, 0.3), 0.85)


def timp():
    t = _t(1.6)
    f = 98 * (1 + 0.12 * np.exp(-t * 25))
    x = (np.sin(2 * math.pi * np.cumsum(f) / SR) + 0.4 * np.sin(2 * math.pi * np.cumsum(f * 1.5) / SR)) * _env(len(t), 0.002, 2.6)
    x += _lp(_rng.standard_normal(len(t)), 400) * _env(len(t), 0.001, 30) * 0.8
    return _norm(_verb(_st(np.tanh(x * 1.3), 0.5), 2.4, 0.35), 0.9)


def glitch():
    n = int(0.28 * SR)
    x = np.zeros(n)
    k = 0
    while k < n:
        L = int(_rng.uniform(0.008, 0.03) * SR)
        f = _rng.choice([180, 360, 720, 1440, 2880])
        seg = np.sign(np.sin(2 * math.pi * f * np.arange(L) / SR)) * 0.5
        if _rng.random() < 0.4:
            seg = _rng.standard_normal(L) * 0.4
        x[k:k + L] = seg[: n - k] * (_rng.random() > 0.25)
        k += L + int(_rng.uniform(0, 0.01) * SR)
    x = np.round(x * 6) / 6
    return _st(_lp(x, 7000) * _env(n, 0.001, 4), 0.4) * 0.6


def lockon():
    out = np.zeros(int(0.75 * SR))
    for i, (at, f) in enumerate([(0, 1320), (0.12, 1560), (0.24, 1760)]):
        t = _t(0.07)
        b = np.sin(2 * math.pi * f * t) * _env(len(t), 0.002, 25)
        j = int(at * SR)
        out[j:j + len(b)] += b * 0.5
    t = _t(0.35)
    conf = (np.sin(2 * math.pi * 880 * t) + np.sin(2 * math.pi * 1320 * t)) * _env(len(t), 0.003, 8) * 0.35
    j = int(0.38 * SR)
    out[j:j + len(conf)] += conf
    return _verb(_st(out, 0.3), 1.0, 0.2) * 0.8


def alarm():
    out = np.zeros(int(0.6 * SR))
    for i, f in enumerate([960, 720]):
        t = _t(0.16)
        sq = np.sign(np.sin(2 * math.pi * f * t)) * 0.4 + np.sin(2 * math.pi * f * t) * 0.3
        sq = _lp(sq, 4000) * np.minimum(1, t / 0.005) * np.clip((0.16 - t) / 0.02, 0, 1)
        j = int(i * 0.2 * SR)
        out[j:j + len(sq)] += sq
    return _verb(_st(out, 0.3), 1.2, 0.25) * 0.7


def _swish(direction):
    sec = 0.7
    n = int(sec * SR)
    t = _t(sec)
    shape = np.exp(-((t - 0.32) / 0.13) ** 2)
    noise = _rng.standard_normal(n)
    hi = _bp(noise, 900, 7000) * shape
    lo = _lp(noise, 300) * shape * 1.6
    tone = np.sin(2 * math.pi * np.cumsum(260 * (1.25 - 0.5 * t / sec)) / SR) * shape * 0.25
    x = hi + lo + tone
    pan = np.clip((t - 0.32) / 0.25, -1, 1) * direction
    gl = np.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
    gr = np.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
    st = np.stack([x * gl, x * gr], axis=1)
    return _norm(_verb(st, 1.2, 0.2), 0.8)


def swishr():
    return _swish(1)


def swishl():
    return _swish(-1)


def gust():
    sec = 1.6
    n = int(sec * SR)
    t = _t(sec)
    shape = np.minimum(1, t / 0.12) * np.exp(-np.clip(t - 0.25, 0, None) * 3.2)
    noise = _rng.standard_normal(n)
    howl = np.zeros(n)
    acc = 0.0
    fc = 500 + 900 * shape
    for i in range(n):
        a = 1 - math.exp(-2 * math.pi * fc[i] / SR)
        acc += a * (noise[i] - acc)
        howl[i] = acc
    flutter = _bp(noise, 2000, 8000) * (0.5 + 0.5 * np.sign(np.sin(2 * math.pi * 23 * t))) * shape * 0.35
    x = howl * shape * 2.2 + flutter
    pan = 1 - 2 * np.clip(t / 0.9, 0, 1)
    gl = np.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
    gr = np.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
    return _norm(_verb(np.stack([x * gl, x * gr], axis=1), 1.6, 0.25), 0.85)


def paper():
    sec = 0.9
    n = int(sec * SR)
    t = _t(sec)
    am = (0.5 + 0.5 * np.sin(2 * math.pi * (14 + 6 * t) * t)) ** 3
    x = _bp(_rng.standard_normal(n), 1800, 9000) * am * np.minimum(1, t / 0.05) * np.exp(-t * 2.5)
    return _st(x, 0.8) * 0.45


def roll():
    sec = 1.6
    n = int(sec * SR)
    t = _t(sec)
    rumble = _lp(_rng.standard_normal(n), 180) * 2.5
    clicks = np.zeros(n)
    k = 0.0
    while k < sec:
        j = int(k * SR)
        c = _hp(_rng.standard_normal(int(0.006 * SR)), 2000) * 0.3
        clicks[j:j + len(c)] += c[: n - j]
        k += 0.055 + 0.02 * k
    e = np.minimum(1, t / 0.08) * np.clip((sec - t) / 0.3, 0, 1)
    return _st((rumble + clicks) * e, 0.3) * 0.6


def stamp():
    t = _t(0.6)
    thud = np.sin(2 * math.pi * np.cumsum(120 * (1 + 1.2 * np.exp(-t * 35))) / SR) * _env(len(t), 0.001, 12)
    slap = _bp(_rng.standard_normal(int(0.05 * SR)), 300, 4000) * _env(int(0.05 * SR), 0.0005, 70)
    x = thud
    x[: len(slap)] += slap * 1.2
    return _norm(_verb(_st(np.tanh(x * 1.5), 0.4), 1.4, 0.3), 0.9)


def coinx():
    t = _t(2.2)
    ping = sum(a * np.sin(2 * math.pi * f * t + _rng.random()) * np.exp(-t * d) for f, a, d in
               [(2093, 0.6, 2.0), (3140, 0.35, 2.6), (4410, 0.25, 3.4), (5274, 0.15, 4.0), (6890, 0.08, 5.0)])
    ping *= np.minimum(1, t / 0.0008)
    spark = np.zeros(len(t))
    for k in range(14):
        at = 0.04 + k * 0.045 + _rng.random() * 0.02
        f = _rng.uniform(5000, 9000)
        s = np.sin(2 * math.pi * f * _t(0.06)) * _env(int(0.06 * SR), 0.001, 60) * (0.18 * (1 - k / 16))
        j = int(at * SR)
        spark[j:j + len(s)] += s
    old = _from_old("coin")[:, 0]
    x = ping * 0.55 + spark
    x[: len(old)] += old * 0.5
    return _norm(_verb(_st(x, 0.9), 3.0, 0.4), 0.85)


def heartx():
    out = np.zeros(int(1.0 * SR))
    for at, g in [(0, 1.0), (0.28, 0.75)]:
        t = _t(0.35)
        b = np.sin(2 * math.pi * np.cumsum(58 * (1 + 0.5 * np.exp(-t * 30))) / SR) * _env(len(t), 0.004, 11) * g
        j = int(at * SR)
        out[j:j + len(b)] += np.tanh(b * 1.8)
    return _st(out, 0.0) * 0.9


def shimmer():
    t = _t(2.5)
    x = np.zeros(len(t))
    for k in range(18):
        at = k * 0.06 + _rng.random() * 0.03
        f = 1760 * 2 ** (_rng.choice([0, 3, 5, 7, 10, 12, 15]) / 12)
        s = np.sin(2 * math.pi * f * _t(1.2)) * _env(int(1.2 * SR), 0.002, 4) * 0.2 * (1 - k / 22)
        j = int(at * SR)
        x[j:j + len(s)] += s[: len(x) - j]
    old = _from_old("chime")[:, 0]
    x[: len(old)] += old * 0.6
    return _norm(_verb(_st(x, 0.9), 2.5, 0.45), 0.7)


def drum():
    t = _t(1.0)
    f = 62 * (1 + 0.9 * np.exp(-t * 28))
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) * _env(len(t), 0.002, 5)
    x += _lp(_rng.standard_normal(len(t)), 600) * _env(len(t), 0.001, 35) * 0.7
    return _norm(_verb(_st(np.tanh(x * 1.6), 0.4), 2.2, 0.4), 0.9)


def _from_old(name):
    x = _old.FX[name](np.random.default_rng(3))
    y = resample_poly(x, 160, 147)
    return _st(y, 0.2)


CINE = dict(hit=hit, hitd=hitd, subdrop=subdrop, suck=suck, braam=braam, bigbell=bigbell, tickh=tickh, timp=timp, glitch=glitch,
            lockon=lockon, alarm=alarm, swishr=swishr, swishl=swishl, gust=gust, paper=paper, roll=roll, stamp=stamp,
            coinx=coinx, heartx=heartx, shimmer=shimmer, drum=drum)
OLD = ["tapestop", "tapestart", "scratch", "rewind", "logo", "whoosh", "pop", "ding", "click", "thunk", "boom",
       "riser", "tick", "chime", "coin", "heart", "bell"]
_CACHE = {}


def sound(name):
    if name not in _CACHE:
        _CACHE[name] = CINE[name]() if name in CINE else _from_old(name)
    return _CACHE[name]


def read_st(path):
    with wave.open(str(path), "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        d = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32767
    d = d.reshape(-1, ch)
    if ch == 1:
        d = np.repeat(d, 2, axis=1)
    if sr != SR:
        g = math.gcd(SR, sr)
        d = np.stack([resample_poly(d[:, c], SR // g, sr // g) for c in range(2)], axis=1)
    return d


def mix(seconds, out, music=None, music_gain=0.55, events=(), cuts=(), duck=(), duck_db=8.0, silence=()):
    n = int((seconds + 0.1) * SR)
    buf = np.zeros((n, 2))
    if music:
        m = read_st(music)[:n]
        g = np.full(len(m), music_gain)
        fade = int(0.04 * SR)
        for a, b in duck:
            i, j = int(a * SR), min(len(m), int(b * SR))
            seg = np.full(max(0, j - i), 10 ** (-duck_db / 20))
            g[i:j] *= seg
        for at, name, gg, *_ in events:
            if name in ("hit", "hitd", "bigbell", "braam", "timp", "stamp"):
                i = int(at * SR)
                j = min(len(m), i + int(0.35 * SR))
                if i < len(m):
                    g[i:j] *= 10 ** (-4 / 20)
        for a, b in cuts:
            i, j = int(a * SR), min(len(m), int(b * SR))
            if i >= len(m):
                continue
            g[i:j] = 0
            g[max(0, i - fade):i] *= np.linspace(1, 0, min(fade, i))
            if j < len(m):
                k = min(fade * 3, len(m) - j)
                g[j:j + k] *= np.linspace(0, 1, k)
        g = np.convolve(g, np.ones(int(0.01 * SR)) / int(0.01 * SR), mode="same")
        buf[: len(m)] += m * g[:, None]
    for ev in events:
        at, name, gg = ev[0], ev[1], ev[2]
        pan = ev[3] if len(ev) > 3 else 0.0
        s = sound(name) * gg
        if pan:
            gl = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
            gr = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
            s = s * np.array([gl, gr])
        i = int(at * SR)
        if i >= n:
            continue
        j = min(n, i + len(s))
        buf[i:j] += s[: j - i]
    for a, b in silence:
        i, j = int(a * SR), min(n, int(b * SR))
        f = int(0.008 * SR)
        buf[max(0, i - f):i] *= np.linspace(1, 0, min(f, i))[:, None]
        buf[i:j] = 0
    peak = np.abs(buf).max() or 1.0
    buf = np.tanh(buf / peak * 1.3) / math.tanh(1.3) * 0.9
    buf = buf[: int(seconds * SR)]
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    return out
