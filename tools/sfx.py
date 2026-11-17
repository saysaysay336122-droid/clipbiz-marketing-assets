"""짧은 효과음을 프로그램으로 직접 만들고, 배경 음악과 섞는다(남의 음원 없음).

효과음
  click   자판 한 번 누르는 소리(아주 작게)
  pop     메시지 도착 '톡'
  ding    알림 '띠링'
  whoosh  화면이 지나가는 '휙'
  thunk   카드가 칸에 들어가는 '툭'
  boom    반전 순간 낮게 '쿵'
  scratch 음악이 끊기는 '끽'
  bell    초인종 '띵동'
  tick    초침 '똑'(카운트다운, 긴장)
  rewind  테이프 되감기 '위이잉'(무르기, 시간 되돌리기)
  riser   반전 직전 올라가는 긴장음(1.2초)
  heart   심장 두 번 '두근'(설렘)
  chime   풍경 소리(홍책사 등장)
  coin    엽전 튕김, 회전, 착지
  logo    홍책사 소리 상표(엽전 한 번, 풍경, 낮은 북). 매 편 끝 화면에 같은 소리

mix(초, 출력 wav, music=음악 wav 경로, events=[(초, 이름, 크기)], cuts=[(시작, 끝)])
  cuts 구간에서는 음악을 끈다(웃음 직전 정적). 시작과 끝은 0.04초로 부드럽게.
"""
import math
import wave

import numpy as np

SR = 44100


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _env(n, attack=0.003, decay=10.0):
    t = np.arange(n) / SR
    a = np.minimum(1.0, t / max(attack, 1e-4))
    return a * np.exp(-t * decay)


def _lowpass(x, alpha):
    """한 극 저역 통과. alpha가 배열이면 시간에 따라 바뀐다."""
    y = np.zeros_like(x)
    acc = 0.0
    al = np.broadcast_to(alpha, x.shape)
    for i in range(len(x)):
        acc += al[i] * (x[i] - acc)
        y[i] = acc
    return y


def click(rng):
    n = int(0.03 * SR)
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=0)
    return hp * _env(n, 0.0005, 180) * 0.18


def pop(rng):
    t = _t(0.09)
    f = 700 + 900 * (t / t[-1])
    ph = 2 * math.pi * np.cumsum(f) / SR
    return np.sin(ph) * _env(len(t), 0.002, 38) * 0.5


def ding(rng):
    out = np.zeros(int(0.6 * SR))
    for k, (f, st) in enumerate([(1318.5, 0.0), (1760.0, 0.11)]):
        t = _t(0.45)
        s = (np.sin(2 * math.pi * f * t) + 0.3 * np.sin(2 * math.pi * 2 * f * t)) * _env(len(t), 0.002, 7)
        i = int(st * SR)
        out[i:i + len(s)] += s[: len(out) - i]
    return out * 0.32


def bell(rng):
    out = np.zeros(int(1.3 * SR))
    for f, st in [(659.3, 0.0), (523.3, 0.42)]:
        t = _t(0.85)
        s = (np.sin(2 * math.pi * f * t) + 0.4 * np.sin(2 * math.pi * 2.76 * f * t) * np.exp(-t * 6)) * _env(len(t), 0.002, 3.2)
        i = int(st * SR)
        out[i:i + len(s)] += s[: len(out) - i]
    return out * 0.35


def whoosh(rng):
    n = int(0.38 * SR)
    noise = rng.standard_normal(n)
    pos = np.linspace(0, 1, n)
    alpha = 0.02 + 0.35 * np.sin(math.pi * pos)
    y = _lowpass(noise, alpha)
    return y * np.sin(math.pi * pos) ** 1.5 * 0.55


def thunk(rng):
    t = _t(0.18)
    f = 180 * np.exp(-t * 9) + 70
    ph = 2 * math.pi * np.cumsum(f) / SR
    body = np.sin(ph) * _env(len(t), 0.001, 22)
    c = click(rng)
    c = np.pad(c, (0, max(0, len(t) - len(c))))[: len(t)]
    return (body + c) * 0.55


def boom(rng):
    t = _t(1.1)
    f = 62 * np.exp(-t * 1.4) + 34
    ph = 2 * math.pi * np.cumsum(f) / SR
    body = np.sin(ph) * _env(len(t), 0.004, 3.0)
    hit = rng.standard_normal(len(t)) * _env(len(t), 0.001, 45) * 0.35
    return np.tanh((body + _lowpass(hit, 0.08)) * 1.6) * 0.75


def scratch(rng):
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    wob = 0.5 + 0.5 * np.sin(2 * math.pi * 16 * t)
    y = _lowpass(noise, 0.05 + 0.25 * wob)
    tone = np.sin(2 * math.pi * np.cumsum(900 - 700 * (t / t[-1])) / SR) * 0.3
    return (y + tone) * _env(n, 0.002, 5) * 0.5


def tick(rng):
    n = int(0.06 * SR)
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=0)
    t = _t(0.06)
    tone = np.sin(2 * math.pi * 2400 * t) * 0.4
    return (hp * 0.5 + tone) * _env(n, 0.0005, 120) * 0.35


def rewind(rng):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 300 + 2200 * (t / t[-1]) ** 1.5
    ph = 2 * math.pi * np.cumsum(f) / SR
    warble = 0.6 + 0.4 * np.sin(2 * math.pi * 22 * t)
    tone = np.sign(np.sin(ph)) * 0.25 + np.sin(ph * 0.5) * 0.35
    noise = _lowpass(rng.standard_normal(n), 0.2) * 0.4
    env = np.minimum(1, t / 0.05) * np.minimum(1, (t[-1] - t) / 0.08 + 0.01)
    return np.tanh((tone * warble + noise) * env * 1.2) * 0.45


def riser(rng):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    pos = t / t[-1]
    noise = rng.standard_normal(n)
    y = _lowpass(noise, 0.01 + 0.4 * pos ** 2)
    f = 200 + 900 * pos ** 2
    tone = np.sin(2 * math.pi * np.cumsum(f) / SR) * 0.25
    return (y * 0.6 + tone) * pos ** 2 * 0.55


def heart(rng):
    out = np.zeros(int(0.75 * SR))
    for st, g in [(0.0, 1.0), (0.22, 0.75)]:
        t = _t(0.25)
        f = 70 * np.exp(-t * 12) + 45
        s = np.sin(2 * math.pi * np.cumsum(f) / SR) * _env(len(t), 0.004, 16) * g
        i = int(st * SR)
        out[i:i + len(s)] += s[: len(out) - i]
    return np.tanh(out * 1.8) * 0.6


def chime(rng):
    out = np.zeros(int(1.8 * SR))
    for f, st in [(2093.0, 0.0), (2637.0, 0.12), (3136.0, 0.27), (2349.3, 0.45)]:
        t = _t(1.3)
        s = (np.sin(2 * math.pi * f * t) + 0.25 * np.sin(2 * math.pi * 2.4 * f * t) * np.exp(-t * 9)) * _env(len(t), 0.001, 3.5)
        i = int(st * SR)
        out[i:i + len(s)] += s[: len(out) - i]
    return out * 0.16


def coin(rng):
    out = np.zeros(int(1.4 * SR))
    t = _t(0.7)
    ring = (np.sin(2 * math.pi * 3520 * t) + 0.5 * np.sin(2 * math.pi * 5274 * t) + 0.3 * np.sin(2 * math.pi * 7040 * t)) * _env(len(t), 0.0008, 6)
    out[: len(ring)] += ring * 0.5
    spin_t = _t(0.45)
    spin = np.sin(2 * math.pi * 4200 * spin_t) * (0.5 + 0.5 * np.sin(2 * math.pi * 30 * spin_t)) * _env(len(spin_t), 0.01, 4) * 0.12
    i = int(0.15 * SR)
    out[i:i + len(spin)] += spin
    land = thunk(rng) * 0.6
    j = int(0.75 * SR)
    out[j:j + len(land)] += land[: len(out) - j]
    tail = np.sin(2 * math.pi * 3300 * _t(0.4)) * _env(int(0.4 * SR), 0.0008, 9) * 0.25
    out[j:j + len(tail)] += tail[: len(out) - j]
    return out * 0.6


def logo(rng):
    out = np.zeros(int(2.2 * SR))
    c = coin(rng)[: int(0.7 * SR)]
    out[: len(c)] += c
    ch = chime(rng) * 0.9
    i = int(0.35 * SR)
    out[i:i + len(ch)] += ch[: len(out) - i]
    t = _t(1.2)
    f = 98 * np.exp(-t * 1.2) + 55
    drum = np.sin(2 * math.pi * np.cumsum(f) / SR) * _env(len(t), 0.003, 3.5) * 0.5
    j = int(0.95 * SR)
    out[j:j + len(drum)] += drum[: len(out) - j]
    return np.tanh(out * 1.3) * 0.7


def tapestop(rng):
    """시간이 멈출 때: 음높이가 뚝 떨어지며 꺼지는 테이프 정지 느낌."""
    n = int(0.75 * SR)
    t = np.arange(n) / SR
    pos = t / t[-1]
    f = 260 * (1 - pos) ** 2.2 + 18
    ph = 2 * math.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * math.pi)) % 1.0) - 1
    y = _lowpass(saw * 0.6 + np.sin(ph) * 0.5, 0.08)
    return y * (1 - pos) ** 1.4 * 0.7


def tapestart(rng):
    """시간이 돌아올 때: 테이프가 다시 감기며 음높이가 올라오는 느낌."""
    return tapestop(rng)[::-1].copy() * 0.85


FX = dict(click=click, pop=pop, ding=ding, bell=bell, whoosh=whoosh, thunk=thunk, boom=boom, scratch=scratch,
          tick=tick, rewind=rewind, riser=riser, heart=heart, chime=chime, coin=coin, logo=logo,
          tapestop=tapestop, tapestart=tapestart)


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32767
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
    return data


def mix(seconds, out, music=None, music_gain=0.5, events=(), cuts=(), seed=3):
    rng = np.random.default_rng(seed)
    n = int((seconds + 0.2) * SR)
    buf = np.zeros(n)
    if music:
        m = read_wav(music)[:n]
        gain = np.full(len(m), music_gain)
        fade = int(0.04 * SR)
        for a, b in cuts:
            i, j = int(a * SR), min(len(m), int(b * SR))
            if i >= len(m):
                continue
            gain[i:j] = 0
            gain[max(0, i - fade):i] *= np.linspace(1, 0, min(fade, i))
            if j < len(m):
                k = min(fade * 3, len(m) - j)
                gain[j:j + k] *= np.linspace(0, 1, k)
        buf[: len(m)] += m * gain
    for at, name, g in events:
        s = FX[name](rng) * g
        i = int(at * SR)
        if i >= n:
            continue
        buf[i:i + len(s)] += s[: n - i]
    # 숏폼 평균 크기에 맞춘다: 소리 나는 구간의 RMS를 약 -17dBFS로 올리고, 큰 소리(쿵)는 부드럽게 눌러 0.95를 넘지 않게.
    loud = np.abs(buf) > 0.003
    rms = np.sqrt(np.mean(buf[loud] ** 2)) if loud.any() else 0.0
    if rms > 0:
        buf = buf * min(4.0, 0.14 / rms)
    buf = np.tanh(buf / 0.92) * 0.92
    buf = buf[: int(seconds * SR)]
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    return out
