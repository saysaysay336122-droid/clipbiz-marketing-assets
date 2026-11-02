"""숏폼용 음악과 효과음을 직접 만든다. 남의 음원과 샘플은 쓰지 않는다.

음악
  phonk(초, seed)      : 128~136 BPM 카우벨 리프, 808 베이스, 찌그러진 킥, 박수, 하이햇 롤
  sneaky(초, seed)     : 104~112 BPM 피치카토와 바순, 우드블록. 뭔가 꼬이기 직전 분위기
  두 곡 모두 stems(드럼, 베이스, 멜로디)로 돌려주고, mix()에서 구간별로 끄거나 먹먹하게 만든다.

악기 소리는 시스템 GM 사운드폰트(TimGM6mb.sf2)를 tinysoundfont로 직접 연주해 만든다.

효과음(SFX 사전)
  boom, hit, whoosh, riser, scratch, glitch, heart, tick, ding, buzz, pop, vibrate,
  shutter, slide_up, slide_down, boing, cash, orch, timpani, typing
"""
import math
import wave

import numpy as np
from scipy import signal

SR = 44100
SF2 = "/usr/share/sounds/sf2/TimGM6mb.sf2"


# ---------------------------------------------------------------- 기본 도구
def t_(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, attack=0.002, decay=8.0, hold=0.0):
    t = np.arange(n) / SR
    a = np.minimum(1.0, t / max(attack, 1e-4))
    d = np.where(t < hold, 1.0, np.exp(-(t - hold) * decay))
    return a * d


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    sos = signal.butter(order, f, btype="high", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    sos = signal.butter(order, f, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def sat(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


def add(buf, start, sig, gain=1.0):
    s = int(round(start * SR))
    if s < 0:
        sig = sig[-s:]
        s = 0
    if s >= len(buf) or len(sig) == 0:
        return
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[: e - s] * gain


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sweep_sine(f0, f1, sec, curve="exp"):
    n = int(sec * SR)
    k = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** k if curve == "exp" else f0 + (f1 - f0) * k
    return np.sin(2 * math.pi * np.cumsum(f) / SR)


# ---------------------------------------------------------------- 사운드폰트 연주
_SYN = None


def _synth():
    global _SYN
    if _SYN is None:
        import tinysoundfont
        s = tinysoundfont.Synth(samplerate=SR, gain=-3)
        sfid = s.sfload(SF2)
        _SYN = (s, sfid)
    return _SYN


def sf_render(notes, sec):
    """notes = [(시작초, 길이초, 프로그램, 음, 세기, 채널)]. 채널 9는 타악기. 모노 배열을 돌려준다."""
    s, sfid = _synth()
    s.notes_off()
    s.sounds_off()
    ev = []
    for i, (st, ln, prog, note, vel, ch) in enumerate(notes):
        ev.append((st, 1, ch, prog, note, vel))
        ev.append((st + ln, 0, ch, prog, note, vel))
    ev.sort(key=lambda e: (e[0], e[1]))
    out = []
    cur = 0
    total = int(sec * SR)
    for st, on, ch, prog, note, vel in ev:
        pos = min(total, int(st * SR))
        if pos > cur:
            out.append(np.frombuffer(s.generate(pos - cur), dtype=np.float32).copy())
            cur = pos
        if on:
            if ch == 9:
                s.program_select(9, sfid, 128, 0)
            else:
                s.program_select(ch, sfid, 0, prog)
            s.noteon(ch, int(note), int(vel))
        else:
            s.noteoff(ch, int(note))
    if total > cur:
        out.append(np.frombuffer(s.generate(total - cur), dtype=np.float32).copy())
    st = np.concatenate(out) if out else np.zeros(total * 2, np.float32)
    mono = st.reshape(-1, 2).mean(axis=1)
    return mono[:total].astype(np.float64)


# ---------------------------------------------------------------- 효과음
def sfx_boom(rng):
    t = t_(1.6)
    f = 38 + 34 * np.exp(-t * 9)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    click = lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 60) * 0.6
    x = sat(body * 1.4 + click, 2.5)
    tail = lp(rng.standard_normal(len(t)), 200) * np.exp(-t * 3) * 0.15
    return (x + tail) * 0.95


def sfx_burst(rng):
    t = t_(0.45)
    pop_ = np.sin(2 * math.pi * np.cumsum(900 * np.exp(-t * 9) + 120) / SR) * np.exp(-t * 16) * 0.6
    noise = bp(rng.standard_normal(len(t)), 1200, 7000) * np.exp(-t * 22) * 0.6
    return sat(pop_ + noise, 1.8) * 0.85


def sfx_hit(rng):
    t = t_(0.9)
    body = np.sin(2 * math.pi * np.cumsum(60 + 90 * np.exp(-t * 25)) / SR) * np.exp(-t * 5)
    noise = bp(rng.standard_normal(len(t)), 300, 4000) * np.exp(-t * 14) * 0.7
    return sat(body + noise, 3) * 0.8


def sfx_whoosh(rng, sec=0.45):
    n = int(sec * SR)
    x = rng.standard_normal(n)
    k = np.linspace(0, 1, n)
    out = np.zeros(n)
    for i, (lo, hi) in enumerate([(300, 900), (900, 2500), (2500, 6000)]):
        w = np.exp(-((k - (0.3 + 0.25 * i)) ** 2) / 0.03)
        out += bp(x, lo, hi) * w
    return out * np.sin(np.pi * k) * 0.55


def sfx_riser(rng, sec=1.6):
    n = int(sec * SR)
    k = np.linspace(0, 1, n)
    noise = hp(rng.standard_normal(n), 1500) * k ** 2 * 0.35
    tone = sweep_sine(200, 1600, sec) * k ** 1.5 * 0.25
    return noise + tone


def sfx_scratch(rng):
    t = t_(0.32)
    f = 900 * (1 + 0.8 * np.sin(2 * math.pi * 7 * t)) * np.exp(-t * 2)
    x = sat(np.sign(np.sin(2 * math.pi * np.cumsum(f) / SR)) * 0.6 + bp(rng.standard_normal(len(t)), 800, 3000) * 0.5, 2)
    return x * env(len(t), 0.005, 6) * 0.45


def sfx_glitch(rng, sec=0.35):
    n = int(sec * SR)
    out = np.zeros(n)
    pos = 0
    while pos < n:
        ln = int(rng.uniform(0.012, 0.05) * SR)
        f = rng.choice([180, 330, 660, 1320, 2400])
        seg = np.sign(np.sin(2 * math.pi * f * np.arange(ln) / SR)) * rng.uniform(0.2, 0.5)
        if rng.random() < 0.4:
            seg = rng.standard_normal(ln) * 0.35
        out[pos:pos + ln] = seg[: n - pos]
        pos += ln + int(rng.uniform(0, 0.02) * SR)
    q = np.round(out * 6) / 6
    return q * 0.6


def sfx_heart(rng):
    out = np.zeros(int(0.9 * SR))
    for st, g in ((0.0, 1.0), (0.22, 0.75)):
        t = t_(0.25)
        th = np.sin(2 * math.pi * np.cumsum(55 + 30 * np.exp(-t * 30)) / SR) * np.exp(-t * 18)
        add(out, st, sat(th * g, 2))
    return out * 0.9


def sfx_tick(rng):
    t = t_(0.06)
    return bp(rng.standard_normal(len(t)), 2500, 6000) * np.exp(-t * 120) * 0.7 + np.sin(2 * math.pi * 3200 * t) * np.exp(-t * 90) * 0.25


def sfx_ding(rng):
    t = t_(0.9)
    x = sum(np.sin(2 * math.pi * f * t) * a * np.exp(-t * d) for f, a, d in ((1318.5, 0.5, 4), (1975.5, 0.3, 5), (2637, 0.15, 7)))
    return x * env(len(t), 0.002, 0.1) * 0.7


def sfx_buzz(rng):
    t = t_(0.45)
    x = np.sign(np.sin(2 * math.pi * 110 * t)) * 0.5 + np.sign(np.sin(2 * math.pi * 116 * t)) * 0.5
    return lp(x, 2200) * env(len(t), 0.005, 0.1, hold=0.35) * 0.35


def sfx_pop(rng):
    t = t_(0.08)
    f = 500 + 1100 * (t / t[-1])
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * env(len(t), 0.001, 40) * 0.5


def sfx_vibrate(rng):
    t = t_(0.5)
    am = (np.sin(2 * math.pi * 24 * t) > -0.2).astype(float)
    return lp(np.sign(np.sin(2 * math.pi * 165 * t)), 600) * am * env(len(t), 0.01, 0.1, hold=0.42) * 0.4


def sfx_shutter(rng):
    out = np.zeros(int(0.2 * SR))
    for st in (0, 0.07):
        t = t_(0.05)
        add(out, st, bp(rng.standard_normal(len(t)), 1500, 7000) * np.exp(-t * 90) * 0.7)
    return out


def sfx_slide(rng, up=True):
    t = t_(0.7)
    f0, f1 = (400, 1500) if up else (1500, 350)
    f = (f0 * (f1 / f0) ** (t / t[-1])) * (1 + 0.02 * np.sin(2 * math.pi * 6 * t))
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) + 0.2 * np.sin(4 * math.pi * np.cumsum(f) / SR)
    return x * env(len(t), 0.03, 0.1, hold=0.55) * 0.35


def sfx_boing(rng):
    t = t_(0.6)
    f = 180 * (1 + 0.45 * np.sin(2 * math.pi * 11 * t) * np.exp(-t * 4))
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.55


def sfx_cash(rng):
    t = t_(1.0)
    bell = sum(np.sin(2 * math.pi * f * t) * a * np.exp(-t * d) for f, a, d in ((2093, 0.4, 5), (2637, 0.3, 6), (3136, 0.25, 7), (4186, 0.15, 9)))
    clunk = bp(rng.standard_normal(len(t)), 200, 1200) * np.exp(-t * 40) * 0.6
    return bell * 0.8 + clunk


def sfx_orch(rng, root=50):
    notes = [(0, 0.6, 55, root, 127, 0), (0, 0.6, 55, root + 7, 120, 0), (0, 0.6, 55, root + 12, 120, 0),
             (0, 0.9, 47, root - 12, 127, 1)]
    return sf_render(notes, 1.6) * 1.6


def sfx_timpani(rng):
    notes = [(i * 0.06, 0.08, 47, 41, 70 + i * 3, 0) for i in range(18)] + [(1.1, 1.0, 47, 41, 127, 1)]
    return sf_render(notes, 2.4) * 1.4


def sfx_typing(rng, sec=0.6):
    out = np.zeros(int(sec * SR))
    tt = 0.0
    while tt < sec - 0.05:
        t = t_(0.03)
        add(out, tt, hp(rng.standard_normal(len(t)), 2000) * np.exp(-t * 200) * rng.uniform(0.15, 0.3))
        tt += rng.uniform(0.06, 0.12)
    return out


SFX = {
    "boom": sfx_boom, "burst": sfx_burst, "hit": sfx_hit, "whoosh": sfx_whoosh, "riser": sfx_riser, "scratch": sfx_scratch,
    "glitch": sfx_glitch, "heart": sfx_heart, "tick": sfx_tick, "ding": sfx_ding, "buzz": sfx_buzz,
    "pop": sfx_pop, "vibrate": sfx_vibrate, "shutter": sfx_shutter,
    "slide_up": lambda r: sfx_slide(r, True), "slide_down": lambda r: sfx_slide(r, False),
    "boing": sfx_boing, "cash": sfx_cash, "orch": sfx_orch, "timpani": sfx_timpani, "typing": sfx_typing,
}
_CACHE = {}


def sfx(name, seed=1):
    key = (name, seed)
    if key not in _CACHE:
        _CACHE[key] = SFX[name](np.random.default_rng(seed))
    return _CACHE[key]


def tone_pluck(freq, sec=0.35):
    """충돌음용 짧은 마림바풍 음."""
    t = t_(sec)
    x = np.sin(2 * math.pi * freq * t) + 0.35 * np.sin(2 * math.pi * freq * 4 * t) * np.exp(-t * 30)
    return x * env(len(t), 0.001, 14) * 0.4


# ---------------------------------------------------------------- 폰크
MINOR = [0, 2, 3, 5, 7, 8, 10]


def _cowbell(freq, sec=0.22):
    t = t_(sec)
    a = np.sign(np.sin(2 * math.pi * freq * t)) + np.sign(np.sin(2 * math.pi * freq * 1.48 * t))
    x = bp(a, freq * 0.9, freq * 3.2) * env(len(t), 0.001, 9) * 0.5
    return sat(x, 1.6)


def _808(freq, sec, glide_to=None):
    t = t_(sec)
    f = np.full(len(t), freq)
    f = f * (1 + 1.0 * np.exp(-t * 60))
    if glide_to:
        k = np.clip((t - sec * 0.55) / (sec * 0.35), 0, 1)
        f = f * (glide_to / freq) ** k
    x = np.sin(2 * math.pi * np.cumsum(f) / SR)
    x = sat(x * env(len(t), 0.002, 1.8), 3.0)
    return x * np.minimum(1, (sec - t) / 0.02)


def _kick():
    t = t_(0.35)
    f = 45 + 160 * np.exp(-t * 35)
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    return sat(x * 1.3, 4) * 0.9


def _clap(rng):
    n = int(0.3 * SR)
    noise = bp(rng.standard_normal(n), 900, 4200)
    e = np.zeros(n)
    for d in (0, 0.012, 0.024):
        s = int(d * SR)
        e[s:] += np.exp(-np.arange(n - s) / SR * (60 if d < 0.02 else 14))
    return noise * e * 0.45


def _hat(rng, open_=False):
    sec = 0.25 if open_ else 0.05
    n = int(sec * SR)
    return hp(rng.standard_normal(n), 7000) * env(n, 0.0005, 9 if open_ else 70) * 0.28


def phonk(sec, seed=1, bpm=None):
    rng = np.random.default_rng(seed)
    bpm = bpm or int(rng.integers(128, 137))
    root = int(rng.choice([41, 42, 43, 44, 45]))  # F2~A2
    beat = 60 / bpm
    step = beat / 4
    n = int(sec * SR)
    drums, bass, mel = np.zeros(n), np.zeros(n), np.zeros(n)
    riffs = [
        [0, None, 0, None, 3, None, 0, 5, None, 3, None, 0, None, 7, 5, 3],
        [7, None, 7, 5, None, 3, None, 5, 7, None, 10, None, 8, 7, None, 5],
        [0, 0, None, 3, None, 5, 3, None, 0, None, 0, 3, 5, None, 7, None],
        [12, None, 10, None, 7, None, 8, 7, None, 5, None, 3, 5, None, 3, None],
    ]
    order = [int(rng.integers(0, 4)) for _ in range(2)]
    hat_rng = np.random.default_rng(seed + 7)
    bar = 0
    tt = 0.0
    kick = _kick()
    while tt < sec:
        riff = riffs[order[bar % 2]]
        for i, deg in enumerate(riff):
            st = tt + i * step
            if deg is not None:
                octv, d = divmod(deg, 7) if deg < 7 else (deg // 7, deg % 7)
                semis = MINOR[deg % 7] + 12 * (deg // 7)
                add(mel, st, _cowbell(hz(root + 36 + semis)), 0.9)
        # 드럼: 킥 1, 2.75, 박수 3(하프타임)
        for b in (0, 1.75, 2.5):
            add(drums, tt + b * beat, kick, 1.0)
        add(drums, tt + 2 * beat, _clap(hat_rng), 1.0)
        for i in range(16):
            if i % 2 == 0 or hat_rng.random() < 0.35:
                add(drums, tt + i * step, _hat(hat_rng), 0.9 if i % 4 == 0 else 0.6)
        if bar % 2 == 1:  # 롤
            for k in range(6):
                add(drums, tt + 3 * beat + k * beat / 6, _hat(hat_rng), 0.55)
        # 808
        pat = [(0, 1.5, 0, None), (1.75, 0.75, 0, None), (2.5, 1.5, 0 if bar % 2 == 0 else 3, -2 if bar % 2 else None)]
        for b, ln, d, g in pat:
            f = hz(root + MINOR[d % 7])
            add(bass, tt + b * beat, _808(f, ln * beat, hz(root + g) if g is not None else None), 0.85)
        tt += 4 * beat
        bar += 1
    return dict(drums=drums * 0.85, bass=bass * 0.75, mel=mel * 0.5, bpm=bpm)


# ---------------------------------------------------------------- 몰래 피치카토
def sneaky(sec, seed=1, bpm=None):
    rng = np.random.default_rng(seed)
    bpm = bpm or int(rng.integers(104, 113))
    beat = 60 / bpm
    root = int(rng.choice([50, 52, 53]))  # D3~F3
    motif = [[0, None, 3, None, 5, 6, 7, None], [7, None, 6, None, 5, None, 3, 2],
             [0, None, 3, 5, None, 7, None, 8], [7, 5, None, 3, None, 2, 0, None]]
    chrom = {0: 0, 2: 3, 3: 5, 5: 7, 6: 8, 7: 10, 8: 12}
    notes_m, notes_b, notes_d = [], [], []
    tt = 0.0
    bar = 0
    while tt < sec:
        m = motif[bar % 4]
        for i, d in enumerate(m):
            if d is None:
                continue
            st = tt + i * beat / 2
            semis = {0: 0, 2: 2, 3: 3, 5: 5, 6: 6, 7: 7, 8: 8}[d]
            notes_m.append((st, beat * 0.3, 45, root + 12 + semis, 110, 0))
        for i in range(4):
            notes_b.append((tt + i * beat, beat * 0.4, 70, root - 12 + (0 if i % 2 == 0 else 7), 100, 1))
        for i in range(8):
            if i % 2 == 0 or rng.random() < 0.3:
                notes_d.append((tt + i * beat / 2, 0.08, 76 if i % 4 == 0 else 77, 76 if i % 4 == 0 else 77, 90, 9))
        tt += 4 * beat
        bar += 1
    mel = sf_render(notes_m, sec) * 1.4
    bass = sf_render(notes_b, sec) * 1.2
    drums = sf_render(notes_d, sec) * 1.0
    return dict(drums=drums, bass=bass, mel=mel, bpm=bpm)


# ---------------------------------------------------------------- 섞기
def _automation(n, regions, default=1.0, fade=0.03):
    g = np.full(n, default, dtype=np.float64)
    for a, b, v in regions:
        s, e = int(a * SR), int(b * SR)
        g[s:e] = v
    k = max(1, int(fade * SR))
    return np.convolve(g, np.ones(k) / k, mode="same")


def mix(sec, out_wav, music=None, events=(), mute=(), muffle=(), duck=0.55, music_gain=0.55, drop=()):
    """music: phonk()나 sneaky() 결과. events: [(초, 효과음 이름, 크기) 또는 (초, 배열, 크기)].
    mute: 음악을 끄는 구간 [(시작, 끝)], muffle: 저역만 남기는 구간, drop: 이 시각 이전 0.5초는 끄고 이후 다시 크게."""
    n = int(sec * SR)
    bus = np.zeros(n)
    if music:
        stems = {k: np.pad(v, (0, max(0, n - len(v))))[:n] for k, v in music.items() if k != "bpm"}
        full = stems["drums"] + stems["bass"] + stems["mel"]
        rms = float(np.sqrt(np.mean(full ** 2))) or 1.0
        full = full * (0.16 / rms)
        dull = lp(full, 450, order=4)
        mreg = [(a, b, 1.0) for a, b in muffle]
        wm = _automation(n, mreg, 0.0, 0.08)
        m = full * (1 - wm) + dull * wm * 1.2
        mt = [(a, b, 0.0) for a, b in mute] + [(d - 0.45, d, 0.0) for d in drop]
        m = m * _automation(n, mt, 1.0, 0.02) * music_gain
        bus += m
    fx = np.zeros(n)
    for i, (st, name, g) in enumerate(events):
        s = sfx(name, i % 3 + 1) if isinstance(name, str) else name
        add(fx, st, s, g)
    # 효과음이 나올 때 음악을 살짝 낮춘다
    envf = np.abs(signal.hilbert(fx)) if len(fx) < 6 * 10 ** 6 else np.abs(fx)
    envf = np.convolve(envf, np.ones(2205) / 2205, mode="same")
    ducker = 1 - np.clip(envf * 2.0, 0, 1) * (1 - duck)
    out = bus * ducker + fx
    try:
        from pedalboard import Compressor, Limiter, Pedalboard, Reverb
        board = Pedalboard([Compressor(threshold_db=-16, ratio=3, attack_ms=5, release_ms=120), Limiter(threshold_db=-1.0)])
        st = np.vstack([out, out]).astype(np.float32)
        st = board(st, SR)
        out = st[0]
    except Exception:
        out = np.clip(out, -1, 1)
    pcm = (np.clip(out, -1, 1) * 32000).astype(np.int16)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_wav


def bed(sec, parts):
    """여러 곡을 이어 붙인 배경. parts = [(시작, 끝, stems, 크기)]. 이음매는 0.05초로 부드럽게."""
    n = int(sec * SR)
    out = {"drums": np.zeros(n), "bass": np.zeros(n), "mel": np.zeros(n)}
    for st, en, stems, g in parts:
        s, e = int(st * SR), min(n, int(en * SR))
        ln = e - s
        fade = np.ones(ln)
        k = min(int(0.05 * SR), ln // 2)
        if k > 0:
            fade[:k] = np.linspace(0, 1, k)
            fade[-k:] = np.linspace(1, 0, k)
        for key in out:
            src = stems[key]
            seg = src[:ln] if len(src) >= ln else np.pad(src, (0, ln - len(src)))
            rms = float(np.sqrt(np.mean((stems["drums"] + stems["bass"] + stems["mel"]) ** 2))) or 1.0
            out[key][s:e] += seg * fade * g * (0.16 / rms)
    return out


# ---------------------------------------------------------------- 예고편, 다큐, 라디오용
def sfx_braam(rng, sec=2.6, root=36):
    """예고편 '브와암'. 톱니파 여러 겹을 찌그러뜨리고 길게 끈다(자체 합성)."""
    t = t_(sec)
    out = np.zeros(len(t))
    for k, (m, a) in enumerate(((root, 1.0), (root + 12, 0.6), (root + 7, 0.45), (root - 12, 0.7))):
        f = hz(m) * (1 + 0.004 * np.sin(2 * math.pi * (0.7 + k * 0.3) * t)) * (1 - 0.03 * t / sec)
        ph = np.cumsum(f) / SR
        saw = 2 * (ph % 1.0) - 1
        out += saw * a
    out = lp(out, 900, order=2)
    out = sat(out * 0.6, 3.0)
    e = np.minimum(1, t / 0.04) * np.exp(-t * 0.9)
    noise = lp(rng.standard_normal(len(t)), 300) * np.exp(-t * 6) * 0.4
    return (out * e + noise) * 0.55


def sfx_fart(rng, sec=0.9):
    t = t_(sec)
    f = 75 + 25 * np.sin(2 * math.pi * 3 * t) + 10 * rng.standard_normal(len(t)).cumsum() / SR * 30
    buzz = np.sign(np.sin(2 * math.pi * np.cumsum(f) / SR))
    am = 0.6 + 0.4 * np.sin(2 * math.pi * 23 * t + rng.uniform(0, 6))
    x = lp(buzz * am, 700) + lp(rng.standard_normal(len(t)), 400) * 0.25
    return sat(x, 2) * env(len(t), 0.02, 2.5) * 0.6


def sfx_sting(rng):
    """코미디 마무리 '빠밤'(사운드폰트 금관)."""
    notes = [(0, 0.12, 61, 60, 110, 0), (0, 0.12, 61, 64, 100, 0), (0.18, 0.5, 61, 67, 120, 0), (0.18, 0.5, 61, 72, 110, 0),
             (0.18, 0.6, 47, 43, 120, 1)]
    return sf_render(notes, 1.2) * 1.5


def sfx_dun(rng):
    """드라마틱 '두둥'(현악 저음 + 팀파니)."""
    notes = [(0, 0.35, 48, 38, 127, 0), (0, 0.35, 48, 50, 120, 0), (0.42, 1.2, 48, 37, 127, 0), (0.42, 1.2, 48, 49, 120, 0),
             (0, 0.3, 47, 38, 127, 1), (0.42, 1.0, 47, 37, 127, 1)]
    return sf_render(notes, 2.0) * 1.5


SFX.update({"braam": sfx_braam, "fart": sfx_fart, "sting": sfx_sting, "dun": sfx_dun})


def trailer_music(sec, seed=1, bpm=96, root=38):
    """예고편 배경: 짧게 끊는 현악 오스티나토, 팀파니, 금관 화음. 점점 커진다."""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    notes_s, notes_b, notes_t = [], [], []
    minor = [0, 3, 7, 10]
    tt = 0.0
    bar = 0
    prog = [0, 0, 8, 5]  # i, i, VI, iv
    while tt < sec:
        r = root + prog[bar % 4]
        inten = min(1.0, tt / max(1, sec * 0.7))
        for i in range(8):
            notes_s.append((tt + i * beat / 2, beat * 0.35, 48, r + 12 + (0 if i % 2 == 0 else 7), int(70 + 50 * inten), 0))
        if bar % 2 == 0 or inten > 0.5:
            for m in (0, 7, 12):
                notes_b.append((tt, beat * 3.6, 61, r + m, int(60 + 60 * inten), 1))
        for i in (0, 2.5, 3):
            notes_t.append((tt + i * beat, 0.4, 47, r - 12, int(80 + 40 * inten), 2))
        tt += 4 * beat
        bar += 1
    mel = sf_render(notes_s, sec) * 1.3
    bass = sf_render(notes_b, sec) * 1.0
    drums = sf_render(notes_t, sec) * 1.4
    return dict(drums=drums, bass=bass, mel=mel, bpm=bpm)


def doc_music(sec, seed=1, bpm=72, root=60):
    """자연 다큐 배경: 하프 아르페지오, 현악 패드, 플루트 선율. 차분하고 진지하다."""
    beat = 60 / bpm
    major = [0, 2, 4, 5, 7, 9, 11]
    prog = [0, 5, 3, 4]
    notes_h, notes_p, notes_f = [], [], []
    tt = 0.0
    bar = 0
    rng = np.random.default_rng(seed)
    while tt < sec:
        deg = prog[bar % 4]
        chord = [major[(deg + k) % 7] + 12 * ((deg + k) // 7) for k in (0, 2, 4)]
        for i in range(8):
            n = root - 12 + chord[i % 3] + 12 * (i // 3 % 2)
            notes_h.append((tt + i * beat / 2, beat * 1.5, 46, n, 80, 0))
        for c in chord:
            notes_p.append((tt, beat * 4, 49, root - 12 + c, 55, 1))
        if bar % 2 == 0:
            for i, k in enumerate(rng.choice([0, 2, 4, 5, 7], 3)):
                notes_f.append((tt + i * beat * 1.3, beat * 1.2, 73, root + 12 + major[k % 7], 70, 2))
        tt += 4 * beat
        bar += 1
    return dict(mel=sf_render(notes_h, sec) * 1.2, bass=sf_render(notes_p, sec) * 1.1, drums=sf_render(notes_f, sec) * 0.9,
                bpm=bpm)


def radio_music(sec, seed=1, bpm=84, root=57):
    """심야 라디오 배경: 일렉트릭 피아노 화음과 가벼운 베이스, 브러시 느낌의 하이햇."""
    beat = 60 / bpm
    prog = [[0, 4, 7, 11], [5, 9, 12, 16], [2, 5, 9, 12], [7, 11, 14, 17]]
    notes_k, notes_b, notes_d = [], [], []
    tt = 0.0
    bar = 0
    while tt < sec:
        ch = prog[bar % 4]
        for i in (0, 1.5, 2.5):
            for c in ch:
                notes_k.append((tt + i * beat, beat * 0.9, 4, root + c, 60, 0))
        notes_b.append((tt, beat * 1.8, 33, root - 24 + ch[0], 90, 1))
        notes_b.append((tt + 2 * beat, beat * 1.8, 33, root - 24 + ch[0] + 7, 85, 1))
        for i in range(8):
            notes_d.append((tt + i * beat / 2, 0.05, 42, 42, 40 if i % 2 else 60, 9))
        tt += 4 * beat
        bar += 1
    return dict(mel=sf_render(notes_k, sec) * 1.0, bass=sf_render(notes_b, sec) * 1.2, drums=sf_render(notes_d, sec) * 0.8,
                bpm=bpm)


def sfx_gurgle(rng, sec=1.1):
    """배에서 꾸르륵(저음 거품 소리 여러 개)."""
    out = np.zeros(int(sec * SR))
    tt = 0.0
    while tt < sec - 0.15:
        ln = rng.uniform(0.06, 0.16)
        t = t_(ln)
        f0 = rng.uniform(90, 220)
        f = f0 * (1 + 0.8 * t / ln) if rng.random() < 0.5 else f0 * (1.6 - 0.6 * t / ln)
        b = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / ln) ** 2
        add(out, tt, lp(b, 600), rng.uniform(0.4, 0.8))
        tt += ln * rng.uniform(0.5, 1.1)
    return out * 0.8


SFX.update({"gurgle": sfx_gurgle})
