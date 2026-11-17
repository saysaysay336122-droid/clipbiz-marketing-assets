"""영화 예고편 수준의 효과음을 직접 합성하고(남의 음원 없음), 48kHz 스테레오로 음악과 섞는다.

설계 원칙(예고편 사운드 디자인 관행을 따른다)
  1. 큰 충격음은 순간음(찰칵), 몸통(북), 초저음 하강, 금속 울림, 꼬리(긴 잔향과 먼 우르릉)를 따로 만들어 겹친다.
  2. 상승음은 음높이 상승(셰퍼드 톤)과 잡음 상승을 함께 쓰고, 정점이 충격음 순간에 정확히 닿게 길이를 맞춘다.
  3. 브람은 낮은 금관 덩어리에 포먼트와 왜곡, 긴 잔향을 준다.
  4. 시간이 멈출 때는 세상 소리(사무실 공기음)를 빨아들이듯 끊고, 흔들리는 이명음과 심장 소리만 남긴다.
  5. 효과음은 따로 묶어 압축과 포화로 한 덩어리로 만든 뒤 음악과 섞는다.

공간 울림은 세 가지: room(0.9초), hall(2.8초), cathedral(5.5초). 저음은 길게, 고음은 짧게 사라진다.

효과음
  hit       예고편 충격음: 순간음, 북 몸통, 초저음 하강, 모루 금속 울림, 성당 잔향, 먼 우르릉(시간 복귀)
  hitd      짧은 충격음: 같은 재료, 저음 0.45초 안에 빠지고 홀 잔향 짧게(바로 뒤 대사나 웃음이 오는 곳)
  freeze    시간 정지 충격: 짧은 충격음, 유리 결정이 얼어붙는 바스락, 종소리 흡입 꼬리(정지 순간)
  subdrop   초저음 하강 1.3초
  boom      느리게 차오르는 큰 붐(공격이 부드러운 예고편 붐)
  suck      종소리와 잡음을 거꾸로 빨아들이는 소리 0.9초(충격음 직전, 끝이 정점)
  rise1     셰퍼드 상승음과 잡음 상승 0.9초(끝이 정점)
  rise2     같은 상승음 2.0초
  revcym    역재생 심벌 1.2초(끝이 정점)
  braam     낮은 금관 덩어리 2.6초, 포먼트와 왜곡, 성당 잔향(영웅 등장)
  bigbell   큰 종, 성당 잔향과 초저음. 1.5초 뒤부터 저음을 걷어 뒤 대사를 가리지 않음(18:00:00)
  ring      흔들리는 이명음 2.6초(3.6kHz 두 음이 맥놀이, 시간이 멈춘 귀)
  tickh     무거운 시계 초침, 기계음과 홀 잔향
  timp      팀파니와 큰북 한 번
  stamp     도장 쾅: 몸통 충격과 종이 때림, 홀 잔향
  kachunk   큰 형광등 차단기 철컥, 빈 사무실 울림(소등)
  glitch    디지털 지직
  stutter   빨라지며 끊기는 디지털 떨림 0.5초(시계가 얼어붙는 순간)
  lockon    조준 고정 삐 세 번과 확정음
  alarm     짧은 경보 두 번(발각)
  swishr    왼쪽에서 오른쪽으로 지나가는 큰 휙(공기, 저음 몸통, 도플러 음)
  swishl    오른쪽에서 왼쪽
  passr     초고속으로 지나가는 휙과 저음 쿵(팀장 퇴장)
  gust      큰 돌풍과 종이 펄럭임(오른쪽에서 왼쪽)
  paper     종이 흩날림
  roll      의자 바퀴 구름 1.6초
  coinx     엽전 튕김: 맑은 금속음, 반짝임, 성당 잔향
  heartx    심장 두 번, 초저음
  shimmer   풍경과 별가루(홍책사 등장, 정지 세계)
  drum      큰 북 한 번
  tapestop, tapestart, scratch, rewind, logo 등은 sfx.py 소리를 48kHz 스테레오로 옮겨 쓴다(소리 상표 logo는 매 편 같게).

ambience(초) 사무실 공기음: 공조기 바람, 아주 작은 자판 소리, 먼 웅성임 없음(대사 가림 방지)

mix(초, 출력 wav, music=음악 wav, events=[(초, 이름, 크기)], cuts=[], duck=[], silence=[], bed=[(시작, 끝, 크기)])
  bed 구간에 사무실 공기음을 깐다. 시작과 끝은 0.25초로 부드럽게, 시간이 멈출 때 끊는 데 쓴다.
  silence 구간은 음악, 효과음, 공기음, 잔향까지 모두 완전 무음.
  duck 구간(대사)에서는 음악을 8dB, 공기음을 6dB, 효과음 묶음(앞 소리의 꼬리 포함)을 7dB 낮춘다.
  큰 충격음 뒤 0.35초는 음악을 4dB 눌러 소리가 서게 한다.
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


def _sos(kind, f, order=2):
    if kind == "band":
        lo, hi = f
        return butter(order, [lo / (SR / 2), min(0.99, hi / (SR / 2))], btype="band", output="sos")
    return butter(order, min(0.99, f / (SR / 2)), btype=kind, output="sos")


def _bp(x, lo, hi, order=2):
    return sosfilt(_sos("band", (lo, hi), order), x, axis=0)


def _lp(x, fc, order=2):
    return sosfilt(_sos("low", fc, order), x, axis=0)


def _hp(x, fc, order=2):
    return sosfilt(_sos("high", fc, order), x, axis=0)


def _pan(x, pan=0.0, width=0.0):
    """모노를 스테레오로. pan -1~1. 휴대폰 한쪽 스피커(모노)에서 소리가 깎이지 않게 좌우 지연은 쓰지 않고,
    넓이는 잔향에서만 만든다(width 인자는 호환용)."""
    r = x.copy()
    gl = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
    gr = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
    return np.stack([x * gl, r * gr], axis=1)


def _mono_to_moving(x, p0, p1, t0=0.0, t1=None):
    t = np.arange(len(x)) / SR
    t1 = t1 if t1 is not None else t[-1]
    p = np.clip(p0 + (p1 - p0) * (t - t0) / max(1e-3, t1 - t0), -1, 1)
    return np.stack([x * np.cos((p + 1) * math.pi / 4) * math.sqrt(2), x * np.sin((p + 1) * math.pi / 4) * math.sqrt(2)], axis=1)


_IR = {}
SPACES = {"room": (0.9, 0.012, 1.4), "hall": (2.8, 0.025, 1.7), "cathedral": (5.5, 0.04, 2.0)}


def _ir(space):
    """주파수별로 사라지는 속도가 다른 합성 잔향 응답(저음 길게, 고음 짧게), 초기 반사, 좌우 다른 잡음."""
    if space in _IR:
        return _IR[space]
    rt, pre, low_mult = SPACES[space]
    n = int((rt + pre) * SR)
    t = np.arange(n) / SR
    out = []
    for seed in (11, 12):
        g = np.random.default_rng(seed)
        noise = g.standard_normal(n)
        lo = _lp(noise, 300) * np.exp(-t * 6.9 / (rt * low_mult))
        mid = _bp(noise, 300, 3000) * np.exp(-t * 6.9 / rt)
        hi = _hp(noise, 3000) * np.exp(-t * 6.9 / (rt * 0.45))
        x = lo * 1.3 + mid + hi * 0.6
        x[: int(pre * SR)] = 0
        for k in range(10):
            i = int((pre * 0.4 + 0.004 * k + g.random() * 0.006) * SR)
            if i < n:
                x[i] += (0.6 - 0.05 * k) * (1 if g.random() > 0.5 else -1)
        out.append(x / np.sqrt(np.sum(x ** 2)))
    l, r = out
    r = 0.6 * l + 0.4 * r
    r /= np.sqrt(np.sum(r ** 2))
    _IR[space] = np.stack([l, r], axis=1)
    return _IR[space]


def _verb(st, space="hall", wet=0.35):
    ir = _ir(space)
    tail = np.stack([fftconvolve(st[:, c], ir[:, c]) for c in range(2)], axis=1)
    dry = np.zeros_like(tail)
    dry[: len(st)] = st
    return dry * (1 - wet * 0.4) + tail * wet


def _glue(st, thr_db=-16.0, ratio=3.0, att=0.004, rel=0.15, drive=1.25):
    """간단한 RMS 압축과 부드러운 포화로 겹친 층을 한 덩어리로."""
    x = st.mean(axis=1)
    p = x ** 2
    a_att = math.exp(-1 / (att * SR))
    a_rel = math.exp(-1 / (rel * SR))
    env = np.zeros_like(p)
    e = 0.0
    for i in range(len(p)):
        a = a_att if p[i] > e else a_rel
        e = a * e + (1 - a) * p[i]
        env[i] = e
    lvl = 10 * np.log10(env + 1e-12)
    over = np.maximum(0, lvl - thr_db)
    gain = 10 ** (-(over - over / ratio) / 20)
    y = st * gain[:, None]
    y = np.tanh(y * drive) / math.tanh(drive)
    return y


def _norm(x, peak=0.9):
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


def _widen(st, k=1.0):
    m = (st[:, 0] + st[:, 1]) / 2
    s = (st[:, 0] - st[:, 1]) / 2 * k
    return np.stack([m + s, m - s], axis=1)


def _from_old(name):
    x = _old.FX[name](np.random.default_rng(3))
    return _pan(resample_poly(x, 160, 147), 0, 0.2)


# 층 재료 -------------------------------------------------------------------------

def _crack(sec=0.02, lo=2500, hi=9000, d=200):
    n = int(sec * SR)
    return _bp(_rng.standard_normal(n), lo, hi) * _env(n, 0.0002, d)


def _drum_body(f0=90, f1=52, sec=0.7, d=5.0):
    t = _t(sec)
    f = f1 + (f0 - f1) * np.exp(-t * 22)
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) * _env(len(t), 0.002, d)
    x += _lp(_rng.standard_normal(len(t)), 800) * _env(len(t), 0.001, 28) * 0.8
    return np.tanh(x * 1.6)


def _sub(f0=55, f1=30, sec=1.5, d=2.0):
    x = _sweep(f0, f1, sec, 1.4) * _env(int(sec * SR), 0.004, d)
    return np.tanh(x * 1.8) * 0.9


def _anvil(sec=1.6, base=170, d=2.6):
    t = _t(sec)
    ratios = [1.0, 2.32, 3.86, 5.41, 6.93, 8.7]
    x = sum((0.55 / (k + 1)) * np.sin(2 * math.pi * base * r * t + _rng.random()) * np.exp(-t * d * (1 + 0.35 * k))
            for k, r in enumerate(ratios))
    return x * np.minimum(1, t / 0.0008)


def _rumble(sec=3.0, d=1.1):
    n = int(sec * SR)
    t = _t(sec)
    x = _lp(_rng.standard_normal(n), 110, 4) * 6
    return x * np.minimum(1, t / 0.08) * np.exp(-t * d)


def _place(n, *parts):
    out = np.zeros(n)
    for at, sig in parts:
        i = int(at * SR)
        j = min(n, i + len(sig))
        out[i:j] += sig[: j - i]
    return out


# 소리 ---------------------------------------------------------------------------

def hit():
    n = int(1.8 * SR)
    core = _place(n, (0, _crack() * 0.8), (0, _drum_body() * 1.0), (0, _anvil() * 0.6))
    sub = _place(n, (0, _sub(58, 28, 1.8, 1.6)))
    st = _verb(_pan(core, 0, 0.6), "cathedral", 0.5)
    tail = _pan(_rumble(3.5, 0.9), 0, 0.9) * 0.5
    out = np.zeros((len(st) + SR, 2))
    out[: len(st)] += st
    out[: len(tail)] += tail
    out[: n] += _pan(sub, 0, 0) * 0.9
    return _norm(_widen(_glue(out, -18, 3.5)), 0.95)


def hitd():
    n = int(0.9 * SR)
    core = _place(n, (0, _crack() * 0.8), (0, _drum_body(95, 55, 0.5, 8) * 0.9), (0, _anvil(0.7, 190, 6) * 0.45))
    sub = _place(n, (0, _sub(60, 38, 0.6, 7)))
    st = _verb(_pan(core, 0, 0.5), "hall", 0.25)
    st[: n] += _pan(sub, 0, 0) * 0.8
    return _norm(_widen(_glue(st, -18, 3)), 0.93)


def _chime_cluster(sec=1.6, n_notes=9, base=2093, d=3.0):
    t = _t(sec)
    x = np.zeros(len(t))
    for k in range(n_notes):
        at = k * 0.018 + _rng.random() * 0.01
        f = base * 2 ** (_rng.choice([0, 2, 4, 7, 9, 12]) / 12) * (1 + _rng.normal() * 0.002)
        s = np.sin(2 * math.pi * f * _t(sec - at)) * _env(int((sec - at) * SR), 0.001, d) * 0.25
        j = int(at * SR)
        x[j:j + len(s)] += s
    return x


def freeze():
    n = int(1.4 * SR)
    crackle = np.zeros(n)
    for k in range(60):
        at = 0.02 + k * 0.012 * (1 + k / 60)
        if at > 1.2:
            break
        c = _bp(_rng.standard_normal(int(0.004 * SR)), 3000, 12000) * (0.5 - k / 140)
        j = int(at * SR)
        crackle[j:j + len(c)] += c
    core = _place(n, (0, _crack(0.03, 1500, 9000, 120) * 0.9), (0, _drum_body(80, 45, 0.6, 7) * 0.8),
                  (0, _chime_cluster(1.3) * 0.7), (0, crackle * 0.6))
    st = _verb(_pan(core, 0, 0.7), "cathedral", 0.45)
    st[: n] += _pan(_place(n, (0, _sub(52, 26, 1.3, 2.2))), 0, 0) * 0.8
    return _norm(_widen(_glue(st, -18, 3), 1.1), 0.93)


def subdrop():
    return _pan(_sub(72, 24, 1.3, 1.8), 0, 0) * 0.95


def boom():
    sec = 2.5
    t = _t(sec)
    swell = np.minimum(1, (t / 0.18) ** 1.5) * np.exp(-np.clip(t - 0.18, 0, None) * 1.6)
    x = (np.sin(2 * math.pi * 44 * t) + 0.5 * np.sin(2 * math.pi * 88 * t) + _lp(_rng.standard_normal(len(t)), 200, 4) * 3) * swell
    return _norm(_glue(_verb(_pan(np.tanh(x * 1.5), 0, 0.6), "hall", 0.4), -18, 3), 0.9)


def suck():
    """종소리 묶음과 잡음, 충격 몸통을 성당 잔향에 넣은 뒤 거꾸로 돌려 끝이 정점이 되게."""
    n = int(0.3 * SR)
    src = _place(n, (0, _chime_cluster(0.3, 6, 1568, 8) * 0.8), (0, _bp(_rng.standard_normal(n), 400, 7000) * _env(n, 0.001, 12) * 0.5),
                 (0, _drum_body(110, 70, 0.3, 12) * 0.5))
    st = _verb(_pan(src, 0, 0.8), "cathedral", 0.98)[: int(0.9 * SR)]
    st = st[::-1].copy()
    curve = np.linspace(0, 1, len(st)) ** 2.2
    return _norm(st * curve[:, None], 0.85)


def _shepard_rise(sec):
    t = _t(sec)
    pos = t / t[-1]
    x = np.zeros(len(t))
    for k in range(6):
        octave = (k + pos * 1.0) / 6.0
        f = 80 * 2 ** (octave * 6)
        amp = np.exp(-((octave - 0.5) / 0.22) ** 2)
        x += np.sin(2 * math.pi * np.cumsum(f) / SR) * amp
    noise = _rng.standard_normal(len(t))
    nr = np.zeros(len(t))
    for a, b in [(0, 0.5), (0.5, 0.8), (0.8, 1.0)]:
        i, j = int(a * len(t)), int(b * len(t))
        lo = 300 + 2500 * a
        nr[i:j] = _bp(noise[i:j], lo, lo * 4)
    env = pos ** 2.4
    y = (x * 0.5 + nr * 0.6) * env
    st = _pan(y, 0, 0.8)
    return _norm(_widen(st, 1.1), 0.8)


def rise1():
    return _shepard_rise(0.9)


def rise2():
    return _shepard_rise(2.0)


def revcym():
    sec = 1.4
    n = int(sec * SR)
    t = _t(sec)
    cym = _hp(_rng.standard_normal(n), 4000) * np.exp(-t * 2.4)
    cym += sum(np.sin(2 * math.pi * f * t) * np.exp(-t * 3) * 0.05 for f in (3150, 4870, 6230, 7710))
    st = _pan(cym, 0, 0.9)[::-1].copy()
    return _norm(_widen(st, 1.1), 0.7)


def braam():
    sec = 2.6
    t = _t(sec)
    notes = [33, 40, 45, 52, 57]
    x = np.zeros(len(t))
    for m in notes:
        f = 440 * 2 ** ((m - 69) / 12)
        for d in (-0.14, -0.05, 0.05, 0.13):
            fd = f * 2 ** (d / 12)
            x += 2 * ((fd * t + _rng.random()) % 1) - 1
    x /= len(notes) * 4
    open_ = np.clip(t / 0.3, 0, 1)
    bright = _lp(x, 1800) * open_ + _lp(x, 380) * (1 - open_)
    f1 = _bp(bright, 450, 800) * 1.6
    f2 = _bp(bright, 1000, 1500) * 1.0
    body = bright * 0.6 + f1 + f2
    growl = 1 + 0.12 * np.sin(2 * math.pi * 28 * t)
    e = np.minimum(1, t / 0.07) * np.clip((sec - t) / 1.4, 0, 1)
    y = np.tanh(body * growl * e * 3.5)
    sub = np.sin(2 * math.pi * 55 * t) * e * 0.7 + np.sin(2 * math.pi * 27.5 * t) * e * 0.4
    st = _verb(_pan(y, 0, 1.0), "cathedral", 0.4)
    st[: len(sub)] += _pan(sub, 0, 0)
    return _norm(_widen(_glue(st, -16, 2.5), 1.1), 0.92)


def bigbell():
    t = _t(6.0)
    f0 = 98.0
    parts = [(1.0, 0.55, 1.1), (2.0, 0.6, 0.8), (2.4, 0.45, 0.8), (3.0, 0.4, 0.9), (4.0, 0.5, 1.0),
             (5.04, 0.25, 1.4), (6.0, 0.2, 1.7), (8.15, 0.12, 2.4), (10.4, 0.06, 3.0)]
    x = sum(a * np.sin(2 * math.pi * f0 * r * t * (1 + 0.0005 * k) + _rng.random()) * np.exp(-t * d)
            for k, (r, a, d) in enumerate(parts))
    strike = _bp(_rng.standard_normal(int(0.04 * SR)), 1200, 9000) * _env(int(0.04 * SR), 0.0003, 100) * 0.7
    x[: len(strike)] += strike
    x *= np.minimum(1, t / 0.002)
    st = _verb(_pan(x, 0, 0.7), "cathedral", 0.45)
    sub = _pan(_place(len(st), (0, _sub(50, 36, 0.9, 4.0))), 0, 0)
    st += sub * 0.7
    tt = np.arange(len(st)) / SR
    k = np.clip((tt - 0.6) / 0.9, 0, 1)[:, None]
    st = st * (1 - k) + _hp(st, 160, 4) * k
    return _norm(_widen(_glue(st, -18, 2.5), 1.1), 0.9)


def ring():
    sec = 2.6
    t = _t(sec)
    waver = 1 + 0.18 * np.sin(2 * math.pi * 0.9 * t) + 0.08 * np.sin(2 * math.pi * 2.3 * t)
    x = (np.sin(2 * math.pi * 3600 * t) + 0.8 * np.sin(2 * math.pi * 3623 * t)) * waver
    e = np.minimum(1, t / 0.02) * np.clip((sec - t) / 1.4, 0, 1) ** 1.5
    return _pan(x * e * 0.12, 0, 0.3)


def tickh():
    n = int(0.5 * SR)
    t = _t(0.5)
    wood = _bp(_rng.standard_normal(int(0.025 * SR)), 1200, 6000) * _env(int(0.025 * SR), 0.0003, 180)
    thump = np.sin(2 * math.pi * np.cumsum(65 * (1 + 0.9 * np.exp(-t * 40))) / SR) * _env(n, 0.001, 12)
    mech = np.zeros(n)
    j = int(0.012 * SR)
    mech[j:j + int(0.01 * SR)] += _hp(_rng.standard_normal(int(0.01 * SR)), 3000) * 0.3
    metal = (np.sin(2 * math.pi * 2350 * t) + 0.6 * np.sin(2 * math.pi * 3720 * t)) * _env(n, 0.0005, 35) * 0.15
    x = thump + metal + mech
    x[: len(wood)] += wood
    return _norm(_glue(_verb(_pan(x, 0, 0.3), "hall", 0.35), -18, 2.5), 0.85)


def timp():
    t = _t(1.8)
    f = 82 * (1 + 0.12 * np.exp(-t * 25))
    x = (np.sin(2 * math.pi * np.cumsum(f) / SR) + 0.4 * np.sin(2 * math.pi * np.cumsum(f * 1.5) / SR)) * _env(len(t), 0.002, 2.4)
    x += _place(len(t), (0, _drum_body(70, 42, 1.0, 4) * 0.7))
    x += _lp(_rng.standard_normal(len(t)), 500) * _env(len(t), 0.001, 28) * 0.8
    return _norm(_glue(_verb(_pan(np.tanh(x * 1.3), 0, 0.5), "hall", 0.4), -18, 3), 0.9)


def stamp():
    n = int(0.7 * SR)
    t = _t(0.7)
    slap = _bp(_rng.standard_normal(int(0.05 * SR)), 300, 5000) * _env(int(0.05 * SR), 0.0004, 70)
    core = _place(n, (0, _drum_body(130, 70, 0.6, 9) * 1.0), (0, slap * 1.1), (0, _crack(0.015, 2000, 8000, 250) * 0.5))
    st = _verb(_pan(core, 0, 0.4), "hall", 0.3)
    st[: n] += _pan(_place(n, (0, _sub(70, 45, 0.5, 8))), 0, 0) * 0.6
    return _norm(_glue(st, -16, 3), 0.9)


def kachunk():
    n = int(0.6 * SR)
    t = _t(0.6)
    relay = np.zeros(n)
    for at, g in [(0, 1.0), (0.035, 0.6), (0.06, 0.4)]:
        c = _bp(_rng.standard_normal(int(0.012 * SR)), 800, 6000) * _env(int(0.012 * SR), 0.0003, 260) * g
        j = int(at * SR)
        relay[j:j + len(c)] += c
    thump = np.sin(2 * math.pi * np.cumsum(75 * (1 + 0.6 * np.exp(-t * 35))) / SR) * _env(n, 0.001, 14)
    hum_off = np.sin(2 * math.pi * 120 * t) * np.exp(-t * 18) * 0.15
    x = relay + thump * 0.9 + hum_off
    return _norm(_glue(_verb(_pan(x, 0, 0.5), "cathedral", 0.45), -18, 2.5), 0.85)


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
    return _pan(_lp(x, 7000) * _env(n, 0.001, 4), 0, 0.4) * 0.6


def stutter():
    sec = 0.5
    n = int(sec * SR)
    grain = _bp(_rng.standard_normal(int(0.02 * SR)), 500, 6000) * _env(int(0.02 * SR), 0.0005, 60)
    tone = np.sin(2 * math.pi * 880 * _t(0.02)) * _env(int(0.02 * SR), 0.0005, 60) * 0.5
    g = grain + tone
    x = np.zeros(n)
    at = 0.0
    gap = 0.07
    while at < sec - 0.03:
        j = int(at * SR)
        x[j:j + len(g)] += g[: n - j]
        at += gap
        gap = max(0.012, gap * 0.8)
    return _norm(_verb(_pan(x, 0, 0.5), "room", 0.2), 0.6)


def lockon():
    out = np.zeros(int(0.75 * SR))
    for at, f in [(0, 1320), (0.12, 1560), (0.24, 1760)]:
        t = _t(0.07)
        b = np.sin(2 * math.pi * f * t) * _env(len(t), 0.002, 25)
        j = int(at * SR)
        out[j:j + len(b)] += b * 0.5
    t = _t(0.35)
    conf = (np.sin(2 * math.pi * 880 * t) + np.sin(2 * math.pi * 1320 * t)) * _env(len(t), 0.003, 8) * 0.35
    j = int(0.38 * SR)
    out[j:j + len(conf)] += conf
    return _verb(_pan(out, 0, 0.3), "room", 0.25) * 0.8


def alarm():
    out = np.zeros(int(0.6 * SR))
    for i, f in enumerate([960, 720]):
        t = _t(0.16)
        sq = np.sign(np.sin(2 * math.pi * f * t)) * 0.4 + np.sin(2 * math.pi * f * t) * 0.3
        sq = _lp(sq, 4000) * np.minimum(1, t / 0.005) * np.clip((0.16 - t) / 0.02, 0, 1)
        j = int(i * 0.2 * SR)
        out[j:j + len(sq)] += sq
    return _verb(_pan(out, 0, 0.3), "room", 0.3) * 0.7


def _swish(direction, sec=0.8, center=0.36, width=0.14, low=1.6, sub=False):
    n = int(sec * SR)
    t = _t(sec)
    shape = np.exp(-((t - center) / width) ** 2)
    noise = _rng.standard_normal(n)
    air = _bp(noise, 700, 9000) * shape
    body = _lp(noise, 260) * shape * low
    dop = np.sin(2 * math.pi * np.cumsum(300 * (1.3 - 0.6 * np.clip((t - center + 0.2) / 0.4, 0, 1))) / SR) * shape * 0.22
    x = air + body + dop
    st = _mono_to_moving(x, -direction, direction, center - 0.15, center + 0.15)
    if sub:
        k = _sub(70, 40, 0.5, 8)
        j = int(center * SR)
        st[j:j + len(k)] += _pan(k, 0, 0)[: n - j] * 0.8
    return _norm(_verb(st, "room", 0.25), 0.85)


def swishr():
    return _swish(1)


def swishl():
    return _swish(-1)


def passr():
    return _swish(1, 0.6, 0.22, 0.07, 2.2, sub=True)


def gust():
    sec = 1.8
    n = int(sec * SR)
    t = _t(sec)
    shape = np.minimum(1, t / 0.1) * np.exp(-np.clip(t - 0.3, 0, None) * 3.0)
    noise = _rng.standard_normal(n)
    howl = np.zeros(n)
    acc = 0.0
    fc = 400 + 1100 * shape
    for i in range(n):
        a = 1 - math.exp(-2 * math.pi * fc[i] / SR)
        acc += a * (noise[i] - acc)
        howl[i] = acc
    low = _lp(noise, 120, 4) * shape * 4
    flutter = _bp(noise, 2000, 9000) * (0.5 + 0.5 * np.sign(np.sin(2 * math.pi * (19 + 8 * t) * t))) * shape * 0.4
    x = howl * shape * 2.4 + low + flutter
    st = _mono_to_moving(x, 1, -1, 0.0, 0.9)
    return _norm(_widen(_verb(st, "hall", 0.25), 1.1), 0.88)


def paper():
    sec = 0.9
    n = int(sec * SR)
    t = _t(sec)
    am = (0.5 + 0.5 * np.sin(2 * math.pi * (14 + 6 * t) * t)) ** 3
    x = _bp(_rng.standard_normal(n), 1800, 9000) * am * np.minimum(1, t / 0.05) * np.exp(-t * 2.5)
    return _verb(_pan(x, 0, 0.8), "room", 0.2) * 0.45


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
    return _mono_to_moving((rumble + clicks) * e, -0.4, 0.5) * 0.6


def coinx():
    t = _t(2.4)
    ping = sum(a * np.sin(2 * math.pi * f * t + _rng.random()) * np.exp(-t * d) for f, a, d in
               [(2093, 0.6, 1.6), (3140, 0.35, 2.2), (4410, 0.25, 3.0), (5274, 0.15, 3.6), (6890, 0.08, 4.5)])
    ping *= np.minimum(1, t / 0.0008)
    spark = np.zeros(len(t))
    for k in range(16):
        at = 0.04 + k * 0.045 + _rng.random() * 0.02
        f = _rng.uniform(5000, 9000)
        s = np.sin(2 * math.pi * f * _t(0.06)) * _env(int(0.06 * SR), 0.001, 60) * (0.18 * (1 - k / 18))
        j = int(at * SR)
        spark[j:j + len(s)] += s
    old = _from_old("coin")[:, 0]
    x = ping * 0.55 + spark
    x[: len(old)] += old * 0.5
    return _norm(_widen(_verb(_pan(x, 0, 0.9), "cathedral", 0.4), 1.1), 0.85)


def heartx():
    out = np.zeros(int(1.0 * SR))
    for at, g in [(0, 1.0), (0.28, 0.75)]:
        t = _t(0.4)
        b = np.sin(2 * math.pi * np.cumsum(52 * (1 + 0.5 * np.exp(-t * 30))) / SR) * _env(len(t), 0.004, 10) * g
        j = int(at * SR)
        out[j:j + len(b)] += np.tanh(b * 1.8)
    return _verb(_pan(out, 0, 0), "room", 0.15) * 0.9


def shimmer():
    x = _chime_cluster(2.5, 18, 1760, 3.2)
    old = _from_old("chime")[:, 0]
    x[: len(old)] += old * 0.6
    return _norm(_widen(_verb(_pan(x, 0, 0.9), "cathedral", 0.5), 1.1), 0.7)


def drum():
    x = _drum_body(68, 40, 1.0, 4.5)
    return _norm(_glue(_verb(_pan(x, 0, 0.4), "hall", 0.45), -18, 3), 0.9)


CINE = dict(hit=hit, hitd=hitd, freeze=freeze, subdrop=subdrop, boom=boom, suck=suck, rise1=rise1, rise2=rise2,
            revcym=revcym, braam=braam, bigbell=bigbell, ring=ring, tickh=tickh, timp=timp, stamp=stamp, kachunk=kachunk,
            glitch=glitch, stutter=stutter, lockon=lockon, alarm=alarm, swishr=swishr, swishl=swishl, passr=passr,
            gust=gust, paper=paper, roll=roll, coinx=coinx, heartx=heartx, shimmer=shimmer, drum=drum)
_CACHE = {}


def sound(name):
    if name not in _CACHE:
        _CACHE[name] = CINE[name]() if name in CINE else _from_old(name)
    return _CACHE[name]


def ambience(sec, seed=31):
    """사무실 공기음: 공조기 바람과 낮은 웅웅거림, 아주 작은 자판 소리. 대사를 가리지 않게 300Hz~2kHz는 비운다."""
    g = np.random.default_rng(seed)
    n = int(sec * SR)
    t = np.arange(n) / SR
    hvac = _bp(g.standard_normal(n), 90, 350, 3) * 1.1 + _hp(_lp(g.standard_normal(n), 7000), 2500) * 0.12
    hum = (np.sin(2 * math.pi * 120 * t) * 0.025 + np.sin(2 * math.pi * 240 * t) * 0.012) * (1 + 0.1 * np.sin(2 * math.pi * 0.3 * t))
    keys = np.zeros(n)
    at = 0.3
    while at < sec:
        c = _hp(g.standard_normal(int(0.004 * SR)), 3500) * _env(int(0.004 * SR), 0.0002, 600) * g.uniform(0.05, 0.12)
        j = int(at * SR)
        keys[j:j + len(c)] += c[: n - j]
        at += g.uniform(0.09, 0.25) if g.random() > 0.15 else g.uniform(0.8, 1.6)
    l = hvac + hum + keys
    r = np.roll(hvac, int(0.011 * SR)) + hum + np.roll(keys, int(0.4 * SR)) * 0.8
    st = np.stack([l, r], axis=1)
    return _verb(st, "room", 0.3)[:n] * 0.5


def read_st(path):
    with wave.open(str(path), "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        d = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32767
    d = d.reshape(-1, ch)
    if ch == 1:
        d = np.repeat(d, 2, axis=1)
    if sr != SR:
        gg = math.gcd(SR, sr)
        d = np.stack([resample_poly(d[:, c], SR // gg, sr // gg) for c in range(2)], axis=1)
    return d


BIG = ("hit", "hitd", "freeze", "bigbell", "braam", "timp", "stamp", "boom", "kachunk")


def mix(seconds, out, music=None, music_gain=0.55, events=(), cuts=(), duck=(), duck_db=8.0, silence=(), bed=(), sfx_gain=1.0, fx_duck_db=7.0):
    n = int((seconds + 0.1) * SR)
    mus = np.zeros((n, 2))
    if music:
        m = read_st(music)[:n]
        g = np.full(len(m), music_gain)
        fade = int(0.04 * SR)
        for a, b in duck:
            i, j = int(a * SR), min(len(m), int(b * SR))
            g[i:j] *= 10 ** (-duck_db / 20)
        for ev in events:
            if ev[1] in BIG:
                i = int(ev[0] * SR)
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
        mus[: len(m)] += m * g[:, None]
    amb = np.zeros((n, 2))
    if bed:
        base = ambience(seconds + 0.2)[:n]
        ga = np.zeros(n)
        f = int(0.25 * SR)
        for a, b, gg in bed:
            i, j = int(a * SR), min(n, int(b * SR))
            seg = np.full(j - i, gg)
            k = min(f, (j - i) // 2)
            seg[:k] *= np.linspace(0, 1, k)
            seg[-k:] *= np.linspace(1, 0, k)
            ga[i:j] += seg
        for a, b in duck:
            i, j = int(a * SR), min(n, int(b * SR))
            ga[i:j] *= 10 ** (-6 / 20)
        amb = base * ga[:, None]
    fx = np.zeros((n, 2))
    for ev in events:
        at, name, gg = ev[0], ev[1], ev[2]
        s = sound(name) * gg
        i = int(at * SR)
        if i >= n:
            continue
        j = min(n, i + len(s))
        fx[i:j] += s[: j - i]
    fx = _glue(fx * sfx_gain, -14, 2.0, 0.003, 0.2, 1.1)
    if duck and fx_duck_db:
        gd = np.ones(n)
        for a, b in duck:
            i, j = int(a * SR), min(n, int(b * SR))
            gd[i:j] = 10 ** (-fx_duck_db / 20)
        gd = np.convolve(gd, np.ones(int(0.03 * SR)) / int(0.03 * SR), mode="same")
        fx *= gd[:, None]
    buf = mus + amb + fx
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
