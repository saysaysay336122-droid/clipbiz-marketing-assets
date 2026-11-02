"""천간 배틀 로얄: 열 개 일간 공이 원 안에서 부딪히며 마지막 하나가 남을 때까지 싸우는 물리 시뮬레이션.

규칙(화면에 그대로 보인다)
  상극에 부딪히면 맞은 쪽 -1, 상생을 만나면 받는 쪽 +1(최대 5)
  자기장 단계부터 원이 줄어들고 벽에 닿아도 -1

python3 battle.py search --n 400          좋은 판(seed)을 고른다
python3 battle.py render --seed 17 --ep 1 --out out.mp4
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pymunk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx  # noqa: E402
import sound  # noqa: E402
import skia  # noqa: E402

STEMS = [("갑", "甲", "목"), ("을", "乙", "목"), ("병", "丙", "화"), ("정", "丁", "화"), ("무", "戊", "토"),
         ("기", "己", "토"), ("경", "庚", "금"), ("신", "辛", "금"), ("임", "壬", "수"), ("계", "癸", "수")]
EL_HANJA = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}
EL_COLOR = {"목": ("#2FB36B", "#1B7A47"), "화": ("#F0503F", "#A8261B"), "토": ("#F2C14E", "#B9862A"),
            "금": ("#F4F5F7", "#AEB4BC"), "수": ("#3A7BEA", "#1C4AA6")}
EL_TEXT = {"목": "#FFFFFF", "화": "#FFFFFF", "토": "#2A2112", "금": "#1C2128", "수": "#FFFFFF"}
EL_PITCH = {"목": 60, "화": 62, "토": 64, "금": 67, "수": 69}
SAENG = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
GEUK = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}

R_BALL = 50
CX, CY = 540, 1065
R0, RMIN = 395, 205
SPEED = 640
HPMAX = 6
P2 = 12.0          # 자기장 시작
WALL_CD = 1.0
DUEL_WALL_CD = 1.6
SHRINK = 22.0      # 이 시간 동안 R0에서 RMIN까지
FPS = 30
SUB = 4


def has_jong(ch):
    code = ord(ch) - 0xAC00
    return code >= 0 and code % 28 != 0


def ga(w):
    return w + ("이" if has_jong(w[-1]) else "가")


def reul(w):
    return w + ("을" if has_jong(w[-1]) else "를")


def wa(w):
    return w + ("과" if has_jong(w[-1]) else "와")


def radius_at(t):
    if t < P2:
        return R0
    k = min(1.0, (t - P2) / SHRINK)
    return R0 + (RMIN - R0) * fx.ease_in_out(k)


def simulate(seed, tmax=70.0):
    rng = np.random.default_rng(seed)
    space = pymunk.Space()
    space.gravity = (0, 0)
    balls = []
    # 처음 자리: 원 안에 겹치지 않게 흩어 놓는다
    placed = []
    order = list(range(10))
    rng.shuffle(order)
    for i in order:
        for _ in range(500):
            ang = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0, R0 - R_BALL - 20)
            x, y = CX + rr * math.cos(ang), CY + rr * math.sin(ang)
            if all((x - px) ** 2 + (y - py) ** 2 > (2 * R_BALL + 16) ** 2 for px, py in placed):
                break
        placed.append((x, y))
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, R_BALL))
        b.position = (x, y)
        a = rng.uniform(0, 2 * math.pi)
        b.velocity = (SPEED * math.cos(a), SPEED * math.sin(a))
        s = pymunk.Circle(b, R_BALL)
        s.elasticity = 1.0
        s.friction = 0.0
        s.collision_type = 1
        s.idx = i
        space.add(b, s)
        balls.append(dict(i=i, body=b, shape=s, hp=HPMAX, alive=True, rank=None, hits=0, minhp=HPMAX))
    by_idx = {bb["i"]: bb for bb in balls}
    contacts = []

    def begin(arb, sp, data):
        a, b = arb.shapes
        contacts.append((a.idx, b.idx))

    space.on_collision(1, 1, begin=begin)
    frames, events = [], []
    last_pair = {}
    last_wall = {}
    alive_n = 10
    dt = 1.0 / (FPS * SUB)
    t = 0.0
    end_t = None
    f = 0
    while t < tmax:
        for _ in range(SUB):
            contacts.clear()
            space.step(dt)
            t += dt
            R = radius_at(t)
            for bb in balls:
                if not bb["alive"]:
                    continue
                body = bb["body"]
                v = body.velocity
                sp = math.hypot(v.x, v.y) or 1
                jitter = rng.normal(0, 0.002)
                ca, sa = math.cos(jitter), math.sin(jitter)
                vx, vy = (v.x * ca - v.y * sa) * SPEED / sp, (v.x * sa + v.y * ca) * SPEED / sp
                body.velocity = (vx, vy)
                dx, dy = body.position.x - CX, body.position.y - CY
                d = math.hypot(dx, dy) or 1
                if d + R_BALL > R:
                    nx, ny = dx / d, dy / d
                    dot = vx * nx + vy * ny
                    if dot > 0:
                        body.velocity = (vx - 2 * dot * nx, vy - 2 * dot * ny)
                    body.position = (CX + nx * (R - R_BALL - 0.5), CY + ny * (R - R_BALL - 0.5))
                    if t >= P2 and t - last_wall.get(bb["i"], -9) > (DUEL_WALL_CD if alive_n == 2 else WALL_CD) and alive_n > 1:
                        last_wall[bb["i"]] = t
                        bb["hp"] -= 1
                        bb["last"] = "wall"
                        bb["minhp"] = min(bb["minhp"], bb["hp"])
                        events.append(dict(t=t, kind="wall", a=bb["i"], x=CX + nx * R, y=CY + ny * R))
                    else:
                        events.append(dict(t=t, kind="bounce", a=bb["i"]))
            for ia, ib in contacts:
                A, B = by_idx[ia], by_idx[ib]
                if not (A["alive"] and B["alive"]) or alive_n <= 1:
                    continue
                key = tuple(sorted((ia, ib)))
                if t - last_pair.get(key, -9) < 0.25:
                    continue
                last_pair[key] = t
                ea, eb = STEMS[ia][2], STEMS[ib][2]
                mx = (A["body"].position.x + B["body"].position.x) / 2
                my = (A["body"].position.y + B["body"].position.y) / 2
                if ea == eb:
                    events.append(dict(t=t, kind="same", a=ia, b=ib, x=mx, y=my))
                    continue
                if GEUK[ea] == eb:
                    att, vic = A, B
                elif GEUK[eb] == ea:
                    att, vic = B, A
                else:
                    att = vic = None
                if att:
                    vic["last"] = att["i"]
                    vic["hp"] -= 1
                    vic["minhp"] = min(vic["minhp"], vic["hp"])
                    att["hits"] += 1
                    events.append(dict(t=t, kind="hit", a=att["i"], b=vic["i"], x=mx, y=my))
                else:
                    giver, recv = (A, B) if SAENG[ea] == eb else (B, A)
                    if recv["hp"] < HPMAX:
                        recv["hp"] += 1
                        events.append(dict(t=t, kind="heal", a=giver["i"], b=recv["i"], x=mx, y=my))
                    else:
                        events.append(dict(t=t, kind="same", a=giver["i"], b=recv["i"], x=mx, y=my))
            for bb in balls:
                if bb["alive"] and bb["hp"] <= 0:
                    bb["alive"] = False
                    bb["rank"] = alive_n
                    alive_n -= 1
                    events.append(dict(t=t, kind="out", a=bb["i"], rank=bb["rank"], by=bb.get("last"),
                                       x=bb["body"].position.x, y=bb["body"].position.y))
                    space.remove(bb["body"], bb["shape"])
                    if alive_n == 2:
                        events.append(dict(t=t, kind="final2", a=[x["i"] for x in balls if x["alive"]]))
                    if alive_n == 1:
                        w = [x for x in balls if x["alive"]][0]
                        w["rank"] = 1
                        events.append(dict(t=t, kind="win", a=w["i"]))
                        end_t = t
        frames.append(dict(t=f / FPS, R=radius_at(t),
                           b=[(bb["i"], bb["body"].position.x, bb["body"].position.y, bb["hp"], bb["alive"]) for bb in balls]))
        f += 1
        if end_t is not None and t > end_t + 3.3:
            break
    res = dict(seed=seed, frames=frames, events=events, end=end_t,
               ranks={bb["i"]: bb["rank"] for bb in balls}, minhp={bb["i"]: bb["minhp"] for bb in balls})
    return res


def score(res):
    if res["end"] is None:
        return -1, {}
    ev = res["events"]
    end = res["end"]
    f2 = [e for e in ev if e["kind"] == "final2"]
    duel = end - f2[0]["t"] if f2 else 0
    win = [e for e in ev if e["kind"] == "win"][0]["a"]
    outs = [e["t"] for e in ev if e["kind"] == "out"]
    first_out = outs[0] if outs else 99
    comeback = res["minhp"][win] <= 2
    # 결승에서 상성상 불리한 쪽이 이겼나
    underdog = False
    if f2:
        a, b = f2[0]["a"]
        lose = b if a == win else a
        underdog = GEUK[STEMS[lose][2]] == STEMS[win][2]
    rel = 0
    if f2:
        a, b = f2[0]["a"]
        ea, eb = STEMS[a][2], STEMS[b][2]
        rel = 15 if (GEUK[ea] == eb or GEUK[eb] == ea) else (-25 if ea == eb else 0)
    gaps = np.diff([0] + outs) if outs else [99]
    s = 0
    s += 30 if 21 <= end <= 32 else (10 if 18 <= end <= 38 else -30)
    s += min(duel, 9) * 3 if duel >= 4 else -20
    s += 20 if comeback else 0
    s += 25 if underdog else 0
    s += 10 if 4 <= first_out <= 9 else -10
    s -= 6 * sum(1 for g in gaps[1:] if g > 9)
    s -= 6 * sum(1 for g in gaps[1:] if g < 0.8)
    s += rel
    return s, dict(end=round(end, 1), duel=round(duel, 1), win=STEMS[win][0], comeback=comeback,
                   underdog=underdog, first_out=round(first_out, 1))


# ---------------------------------------------------------------- 그리기
def draw_ball(c, x, y, i, hp, scale=1.0, flash=0.0, a=1.0):
    name, hanja, el = STEMS[i]
    c1, c2 = EL_COLOR[el]
    r = R_BALL * scale
    glow = fx.paint(c1, 0.35 * a, blur=18)
    c.drawCircle(x, y, r + 6, glow)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x - r * 0.35, y - r * 0.4), r * 1.5,
                                               [fx.col(c1, a), fx.col(c2, a)], [0.0, 1.0]))
    c.drawCircle(x, y, r, p)
    if flash > 0:
        c.drawCircle(x, y, r, fx.paint("#FFFFFF", flash * a))
    # 체력 고리
    rect = skia.Rect.MakeLTRB(x - r - 9, y - r - 9, x + r + 9, y + r + 9)
    c.drawArc(rect, -90, 360, False, fx.paint("#000000", 0.35 * a, stroke=7))
    hpcol = "#FFFFFF" if hp >= 3 else ("#FFB020" if hp == 2 else "#FF3B30")
    c.drawArc(rect, -90, 360 * max(0, hp) / HPMAX, False, fx.paint(hpcol, a, stroke=7))
    tc = EL_TEXT[el]
    fx.text(c, name, x, y + 14 * scale, fx.font("black", int(48 * scale)), tc, a)
    fx.text(c, hanja + EL_HANJA[el], x, y + 38 * scale, fx.font("serif", int(17 * scale)), tc, 0.85 * a)


def render(seed, ep, out, tmp, title_kicker=None):
    res = simulate(seed)
    sc, info = score(res)
    print("seed", seed, sc, info)
    frames, events = res["frames"], res["events"]
    end = res["end"]
    win = [e for e in events if e["kind"] == "win"][0]["a"]
    total = len(frames) / FPS
    cam = fx.Camera(seed)
    rng = np.random.default_rng(seed)

    # ---- 해설 문구와 효과음 계획
    pops = []          # (시작, 끝, 문구, 색, 크기)
    sfx_ev = []
    floats = []        # (t, x, y, 문구, 색)
    flashes = {}       # idx -> [t]
    bursts = []        # (t, x, y, 색)
    last_tone = -1
    said_same = set()
    said_low = set()
    first_heal = True
    for e in events:
        t = e["t"]
        k = e["kind"]
        if k == "hit":
            floats.append((t, e["x"], e["y"] - 30, "-1", "#FF4B3E"))
            flashes.setdefault(e["b"], []).append(t)
            sfx_ev.append((t, "pop", 0.55))
            sfx_ev.append((t, sound.tone_pluck(sound.hz(EL_PITCH[STEMS[e["a"]][2]] + 12)), 0.7))
        elif k == "heal":
            floats.append((t, e["x"], e["y"] - 30, "+1", "#38E07B"))
            sfx_ev.append((t, sound.tone_pluck(sound.hz(EL_PITCH[STEMS[e["b"]][2]] + 24), 0.5), 0.6))
            if first_heal and t > 2.5:
                first_heal = False
                g, r = STEMS[e["a"]][0], STEMS[e["b"]][0]
                pops.append((t, t + 1.4, f"{ga(g)} {reul(r)} 살려요", "#38E07B", 64))
        elif k == "same":
            if t - last_tone > 0.07:
                sfx_ev.append((t, sound.tone_pluck(sound.hz(EL_PITCH[STEMS[e["a"]][2]])), 0.45))
                last_tone = t
            el = STEMS[e["a"]][2]
            if STEMS[e["a"]][2] == STEMS[e["b"]][2] and el not in said_same and len(said_same) < 1 and 3 < t < P2 - 1:
                said_same.add(el)
                line = {"목": "같은 나무끼리 왜 싸워요", "화": "불끼리 붙으면 더 뜨거워요", "토": "흙끼리 부딪혀 봐야 흙이에요",
                        "금": "쇠끼리 쨍, 아무 일 없어요", "수": "물끼리는 섞일 뿐이에요"}[el]
                pops.append((t, t + 1.5, line, "#FFFFFF", 60))
        elif k == "wall":
            floats.append((t, e["x"], e["y"], "-1", "#FF4B3E"))
            flashes.setdefault(e["a"], []).append(t)
            sfx_ev.append((t, "tick", 0.8))
        elif k == "out":
            name = STEMS[e["a"]][0]
            bursts.append((t, e["x"], e["y"], EL_COLOR[STEMS[e["a"]][2]][0]))
            cam.shake(t, 0.35, 16)
            cam.punch(t, 0.05, 0.3)
            sfx_ev.append((t, "burst", 0.9))
            by = e.get("by")
            if by == "wall":
                why = "자기장에 깎였어요"
            elif by is not None:
                why = {"수": "물에 꺼졌어요", "화": "불에 녹았어요", "금": "쇠에 베였어요", "목": "나무뿌리에 파였어요",
                       "토": "흙에 막혔어요"}[STEMS[by][2]]
                why = f"{STEMS[by][0]}한테 " + why
            else:
                why = ""
            pops.append((t, t + 1.5, f"{name} 탈락  {e['rank']}위\n{why}", "#FF4B3E", 76))
        elif k == "final2":
            a, b = e["a"]
            na, nb = STEMS[a][0], STEMS[b][0]
            ea, eb = STEMS[a][2], STEMS[b][2]
            if GEUK[ea] == eb:
                adv = f"상성은 {na} 쪽이 유리해요"
            elif GEUK[eb] == ea:
                adv = f"상성은 {nb} 쪽이 유리해요"
            elif ea == eb:
                adv = "같은 오행끼리라 벽이 승부를 가려요"
            else:
                adv = "서로 살려 주는 사이라 벽이 승부예요"
            pops.append((t + 1.3, t + 3.3, f"결승  {na} 대 {nb}", "#FFD54A", 84))
            pops.append((t + 3.3, t + 5.0, adv, "#FFFFFF", 58))
            sfx_ev.append((t + 1.3, "orch", 0.7))
            cam.zoom(t + 1.3, t + 3.0, 1.0, 1.08, CX, CY)
        elif k == "win":
            bursts.append((t, None, None, "#FFD54A"))
            cam.flash(t, 0.25)
            cam.shake(t, 0.5, 24)
            sfx_ev.append((t, "boom", 1.0))
            sfx_ev.append((t + 0.05, "orch", 0.9))
    # 체력 1 남은 순간
    hp_track = {}
    for fr in frames:
        for i, x, y, hp, alive in fr["b"]:
            if alive and hp == 1 and i not in said_low and fr["t"] > 4 and len(said_low) < 1:
                said_low.add(i)
                pops.append((fr["t"], fr["t"] + 1.4, f"{STEMS[i][0]} 체력 1, 숨만 쉬어요", "#FFB020", 62))
    p2 = P2
    pops.append((p2, p2 + 1.8, "자기장 시작, 이제 벽도 아파요", "#FF4B3E", 66))
    sfx_ev.append((p2 - 1.6, "riser", 0.6))
    sfx_ev.append((p2, "hit", 0.8))
    cam.punch(p2, 0.06, 0.4)
    # 역전 문구
    if info.get("underdog"):
        pops.append((end + 0.3, end + 1.5, "상성에서 밀렸는데 이겼어요\n역전", "#FFD54A", 64))
    elif res["minhp"][win] <= 2:
        pops.append((end + 0.3, end + 1.5, "체력 바닥에서 올라왔어요", "#FFD54A", 62))
    pops.sort()
    # 중요한 문구(탈락, 결승, 자기장, 역전)는 제때 띄우고 앞 문구를 자른다. 덜 중요한 문구는 늦어지면 버린다.
    def important(s):
        return any(k in s for k in ("탈락", "결승", "자기장 시작", "이겼어요", "올라왔어요", "상성은", "벽이 승부"))
    fixed = []
    for st, en, s, cc, sz in pops:
        if fixed and st < fixed[-1][1]:
            if important(s):
                p = fixed[-1]
                if st - p[0] < 0.35 and important(p[2]):
                    st = p[0] + 0.35
                fixed[-1] = (p[0], st, p[2], p[3], p[4])
            elif st - fixed[-1][1] < -0.4:
                continue
            else:
                st = fixed[-1][1]
        fixed.append((st, max(en, st + 0.8), s, cc, sz))
    pops = fixed

    # ---- 음악
    mus = sound.phonk(total + 1, seed=seed % 7 + 2, bpm=146)
    f2t = [e["t"] for e in events if e["kind"] == "final2"][0]
    sfx_ev.append((f2t + 3.4, "heart", 0.8))
    sfx_ev.append((f2t + 4.3, "heart", 0.8))
    audio = Path(tmp) / f"battle_{seed}.wav"
    sound.mix(total, audio, music=mus, events=sfx_ev, muffle=[(f2t + 1.3, end)], drop=[end], music_gain=0.62)

    # ---- 프레임
    trails = {i: [] for i in range(10)}
    parts = []
    for t0, x, y, cc in bursts:
        prng = np.random.default_rng(int(t0 * 1000))
        n = 26 if x is not None else 60
        for _ in range(n):
            ang = prng.uniform(0, 2 * math.pi)
            spd = prng.uniform(250, 900)
            px = x if x is not None else CX
            py = y if y is not None else CY
            parts.append((t0, px, py, math.cos(ang) * spd, math.sin(ang) * spd, cc, prng.uniform(5, 12)))
    vid = Path(tmp) / f"battle_{seed}_v.mp4"
    wr = fx.Writer(vid)
    surf = fx.surface()
    order = {i: res["ranks"][i] for i in range(10)}
    big_hook = "내 일간은 몇 등까지 버틸까요"
    kicker = title_kicker or f"천간 배틀 로얄 {ep}회전"
    win_pos = None
    for fi, fr in enumerate(frames):
        t = fr["t"]
        c = surf.getCanvas()
        c.clear(fx.col("#0E1412"))
        fx.radial_bg(c, "#1F2C27", "#0B0F0E", CX, CY, 900)
        c.save()
        cam.apply(c, t)
        R = fr["R"]
        # 원
        ring_col = "#FFFFFF" if t < p2 else "#FF4B3E"
        if t >= p2:
            pulse = 0.5 + 0.5 * math.sin(t * 8)
            c.drawCircle(CX, CY, R, fx.paint("#FF4B3E", 0.25 + 0.25 * pulse, stroke=26, blur=14))
            c.drawCircle(CX, CY, R0, fx.paint("#FF4B3E", 0.10, stroke=2))
        c.drawCircle(CX, CY, R, fx.paint(ring_col, 0.9, stroke=8))
        # 자국
        for i, x, y, hp, alive in fr["b"]:
            if alive:
                trails[i].append((x, y))
                trails[i] = trails[i][-7:]
                el = STEMS[i][2]
                for k, (tx, ty) in enumerate(trails[i][:-1]):
                    c.drawCircle(tx, ty, R_BALL * (0.45 + 0.07 * k), fx.paint(EL_COLOR[el][0], 0.05 + 0.03 * k))
        # 공
        for i, x, y, hp, alive in fr["b"]:
            if not alive:
                continue
            fl = 0.0
            for ft in flashes.get(i, []):
                if 0 <= t - ft < 0.14:
                    fl = 0.8 * (1 - (t - ft) / 0.14)
            sc_ = 1.0 + 0.12 * fl
            if i == win and end is not None and t > end:
                if win_pos is None:
                    win_pos = (x, y)
                k = fx.ease_in_out((t - end) / 0.9)
                x = win_pos[0] + (CX - win_pos[0]) * k
                y = win_pos[1] + (CY - win_pos[1]) * k
                sc_ = 1.0 + 1.1 * fx.ease_out_back(min(1, (t - end) / 0.9))
            draw_ball(c, x, y, i, hp, sc_, fl)
        # 파편
        for t0, px, py, vx, vy, cc, sz in parts:
            dt = t - t0
            if 0 <= dt < 0.9:
                k = 1 - dt / 0.9
                c.drawCircle(px + vx * dt * (1 - dt * 0.5), py + vy * dt * (1 - dt * 0.5), sz * k, fx.paint(cc, k))
        for t0, x, y, cc in bursts:
            dt = t - t0
            if 0 <= dt < 0.5 and x is not None:
                c.drawCircle(x, y, R_BALL + 260 * dt, fx.paint(cc, 0.8 * (1 - dt / 0.5), stroke=10))
        # 떠오르는 숫자
        for t0, x, y, s, cc in floats:
            dt = t - t0
            if 0 <= dt < 0.7:
                fx.text(c, s, x, y - 90 * dt, fx.font("black", 46), cc, 1 - dt / 0.7, stroke=8)
        c.restore()

        # ---- 고정 화면 요소
        # 위 문구
        fx.text(c, kicker, CX, 205, fx.font("bold", 38), "#FFD54A", 0.95)
        hook_scale = 1.0 + 0.06 * max(0, 1 - t / 0.25)
        fhk = fx.font("black", int(66 * hook_scale))
        fx.text(c, big_hook, CX, 290, fhk, "#FFFFFF", 1.0, stroke=10)
        fx.text(c, "상극에 맞으면 -1   상생을 만나면 +1", CX, 350, fx.font("bold", 32), "#C9D3CE", 0.95)
        # 남은 수와 시간
        alive_n = sum(1 for b in fr["b"] if b[4])
        fx.text(c, f"생존 {alive_n}", 64, 630, fx.font("black", 40), "#FFFFFF", 0.95, align="left")
        mm, ss = divmod(int(t), 60)
        fx.text(c, f"{mm}:{ss:02d}", 1016, 630, fx.font("bold", 38), "#C9D3CE", 0.9, align="right")
        # 아래 점수판
        for k, (i, x, y, hp, alive) in enumerate(sorted(fr["b"], key=lambda b: b[0])):
            col_ = k % 5
            row = k // 5
            bx, by = 64 + col_ * 176, 385 + row * 88
            name, hanja, el = STEMS[i]
            a_ = 1.0 if alive else 0.32
            fx.rrect(c, bx, by, 166, 76, 20, "#000000", 0.38)
            c.drawCircle(bx + 38, by + 38, 26, fx.paint(EL_COLOR[el][0], a_))
            fx.text(c, name, bx + 38, by + 50, fx.font("black", 32), EL_TEXT[el], a_)
            if alive:
                for h in range(HPMAX):
                    c.drawRoundRect(skia.Rect.MakeXYWH(bx + 74 + h * 14, by + 28, 10, 20), 3, 3,
                                    fx.paint("#FFFFFF" if h < hp else "#3A443F", 1.0))
            else:
                rk = order[i]
                fx.text(c, f"{rk}위", bx + 112, by + 51, fx.font("black", 34), "#FF4B3E", 0.9)
        # 해설 팝업
        for st, en, s, cc, sz in pops:
            if st <= t < en:
                k = (t - st) / 0.22
                scl = 0.6 + 0.4 * fx.ease_out_back(k)
                a_ = min(1.0, (en - t) / 0.2)
                c.save()
                c.translate(CX, 1065 - 30)
                c.scale(scl, scl)
                f_ = fx.font("black", sz)
                head, _, tail = s.partition("\n")
                lines = fx.wrap(head, f_, 940)
                f2_ = fx.font("black", int(sz * 0.62))
                bw = max([f_.measureText(ln) for ln in lines] + ([f2_.measureText(tail)] if tail else [])) + 70
                bh = len(lines) * sz * 1.15 + (sz * 0.62 * 1.2 if tail else 0) + 34
                fx.rrect(c, -bw / 2, -sz * 0.95 - 10, bw, bh, 26, "#05080A", 0.62 * a_)
                for li, ln in enumerate(lines):
                    fx.text(c, ln, 0, li * sz * 1.15, f_, cc, a_, stroke=12)
                if tail:
                    f2_ = fx.font("black", int(sz * 0.62))
                    fx.text(c, tail, 0, len(lines) * sz * 1.15 - sz * 0.2, f2_, "#FFFFFF", a_, stroke=10)
                c.restore()
        # 끝 화면
        if end is not None and t > end + 1.5:
            k = fx.ease_out((t - end - 1.5) / 0.35)
            c.drawRect(skia.Rect.MakeWH(fx.W, fx.H), fx.paint("#0B0F0E", 0.82 * k))
            name, hanja, el = STEMS[win]
            fx.text(c, f"{ep}회전 1위", CX, 760, fx.font("bold", 54), "#FFD54A", k)
            fx.text(c, f"{name} {hanja}{EL_HANJA[el]}", CX, 930, fx.font("black", 150), "#FFFFFF", k, stroke=14)
            fx.text(c, "내 일간은 몇 등 했어요", CX, 1110, fx.font("black", 64), "#FFFFFF", k)
            fx.text(c, "다음 판은 상생 팀전", CX, 1200, fx.font("bold", 46), "#C9D3CE", k)
            fx.text(c, "내 일간 모르면 hongchaksa.kr", CX, 1700, fx.font("medium", 34), "#C9D3CE", 0.8 * k)
            fx.text(c, "재미로 보는 시뮬레이션이에요", CX, 1750, fx.font("regular", 17), "#8C9791", 0.6 * k)
        cam.overlay(c, t)
        arr = fx.snapshot(surf)
        wr.put(arr)
    wr.close()
    fx.mux(vid, audio, out)
    meta = dict(seed=seed, ep=ep, score=sc, info=info, end=end, total=total,
                ranks={STEMS[i][0]: res["ranks"][i] for i in range(10)})
    Path(str(out) + ".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ep", type=int, default=1)
    ap.add_argument("--out", default="battle.mp4")
    ap.add_argument("--tmp", default=".")
    a = ap.parse_args()
    if a.cmd == "search":
        best = []
        for s in range(a.start, a.start + a.n):
            res = simulate(s)
            sc, info = score(res)
            best.append((sc, s, info))
        best.sort(key=lambda x: -x[0])
        for b in best[:15]:
            print(b)
    else:
        render(a.seed, a.ep, a.out, a.tmp)


if __name__ == "__main__":
    main()
