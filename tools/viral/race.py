"""창고 설비 레이스: 창고 물건들이 긴 코스를 굴러 내려가는 마블 레이스. 카메라는 선두를 따라간다.

결말 장치: 1등으로 들어온 '사장님 첫 차'가 사장님 알림 한 줄로 실격되고, 2등이 1등이 된다.

python3 race.py search --n 300
python3 race.py render --seed 5 --out out.mp4 --tmp .
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

ITEMS = [("2009년", "선반", "#E8590C"), ("", "지게차", "#E9B949"), ("", "컴프레서", "#4C86C6"), ("", "용접기", "#D1495B"),
         ("예비", "부품", "#2A9D8F"), ("", "팔레트", "#9C7A54"), ("대형", "프린터", "#8D99AE"), ("사장님", "첫 차", "#7B5EA7")]
SHELF, CAR = 0, 7
R = 40
FPS, SUB = 30, 4
FINISH = 4960
COURSE_H = 5250
X0, X1 = 40, 1040


def build(space, rng):
    st = []

    def seg(a, b, r=8, e=0.45, f=0.5):
        s = pymunk.Segment(space.static_body, a, b, r)
        s.elasticity, s.friction = e, f
        space.add(s)
        st.append(("seg", a, b, r))

    def peg(x, y, r=12, e=0.75):
        s = pymunk.Circle(space.static_body, r, (x, y))
        s.elasticity, s.friction = e, 0.3
        space.add(s)
        st.append(("peg", (x, y), r))

    seg((X0, -400), (X0, COURSE_H))
    seg((X1, -400), (X1, COURSE_H))
    # A: 핀 숲
    for row in range(8):
        y = 330 + row * 112
        off = 60 if row % 2 else 0
        for x in range(170 + off, 911, 120):
            peg(x + rng.uniform(-6, 6), y)
    # B: 지그재그 경사
    y = 1330
    for k in range(4):
        if k % 2 == 0:
            seg((X0, y), (880, y + 150))
        else:
            seg((X1, y), (200, y + 150))
        y += 270
    # C: 회전 막대
    spinners = []
    for (x, yy, w) in ((300, 2520, 2.4), (780, 2720, -2.1), (430, 2960, 2.8), (760, 3180, -2.6)):
        b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        b.position = (x, yy)
        b.angular_velocity = w
        s = pymunk.Segment(b, (-170, 0), (170, 0), 11)
        s.elasticity, s.friction = 0.6, 0.4
        space.add(b, s)
        spinners.append((b, 170))
    # D: 촘촘한 핀과 범퍼
    bumpers = ((300, 3560), (760, 3760), (540, 3960))
    for row in range(7):
        y = 3420 + row * 100
        off = 60 if row % 2 else 0
        for x in range(160 + off, 911, 120):
            if rng.random() < 0.85 and all(math.hypot(x - bx, y - by) > 150 for bx, by in bumpers):
                peg(x + rng.uniform(-8, 8), y, 11)
    for (x, yy) in bumpers:
        peg(x, yy, 44, 1.05)
    # E: 깔때기와 한 줄 통로
    seg((X0, 4180), (468, 4650))
    seg((X1, 4180), (612, 4650))
    seg((468, 4650), (468, 5250))
    seg((612, 4650), (612, 5250))
    seg((468, 5250), (612, 5250))
    return st, spinners


def simulate(seed, tmax=60):
    rng = np.random.default_rng(seed)
    space = pymunk.Space()
    space.gravity = (0, 980)
    statics, spinners = build(space, rng)
    balls = []
    order = list(range(len(ITEMS)))
    rng.shuffle(order)
    for k, i in enumerate(order):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, R))
        b.position = (120 + k * 120 + rng.uniform(-10, 10), 120 + rng.uniform(-30, 30))
        b.velocity = (rng.uniform(-60, 60), 0)
        s = pymunk.Circle(b, R)
        s.elasticity, s.friction = 0.55, 0.45
        space.add(b, s)
        balls.append(dict(i=i, body=b, fin=None, still=0.0, nudges=0))
    dt = 1 / (FPS * SUB)
    t = 0.0
    frames, finish, events = [], [], []
    leader_hist = []
    f = 0
    while t < tmax:
        for _ in range(SUB):
            space.step(dt)
            t += dt
        for bb in balls:
            p, v = bb["body"].position, bb["body"].velocity
            if bb["fin"] is None and p.y > FINISH:
                bb["fin"] = t
                finish.append(bb["i"])
                space.remove(bb["body"], *bb["body"].shapes)
                events.append(dict(t=t, kind="finish", a=bb["i"], rank=len(finish)))
            if bb["fin"] is None and math.hypot(v.x, v.y) < 25 and p.y < 4600:
                bb["still"] += 1 / FPS
                if bb["still"] > 1.6:
                    bb["body"].velocity = (rng.choice([-1, 1]) * rng.uniform(250, 450), -650)
                    bb["still"] = 0
                    bb["nudges"] += 1
                    events.append(dict(t=t, kind="stuck", a=bb["i"], y=p.y))
            else:
                bb["still"] = 0
        run = [bb for bb in balls if bb["fin"] is None]
        lead = max(balls, key=lambda bb: bb["body"].position.y if bb["fin"] is None else 1e9 - (bb["fin"] or 0))
        leader_hist.append(lead["i"])
        frames.append(dict(t=f / FPS, b=[(bb["i"], bb["body"].position.x, bb["body"].position.y, bb["body"].angle,
                                           bb["fin"] is not None) for bb in balls],
                           sp=[(sb.position.x, sb.position.y, sb.angle, ln) for sb, ln in spinners]))
        f += 1
        if len(finish) == len(ITEMS) or (len(finish) >= 3 and t > 75):
            break
    end = t
    # 선두 바뀐 순간
    changes = []
    cur = None
    for k, li in enumerate(leader_hist):
        if li != cur:
            if cur is not None:
                changes.append((k / FPS, li))
            cur = li
    return dict(seed=seed, frames=frames, finish=finish, events=events, end=end, statics=statics, changes=changes)


def score(res):
    fin = res["finish"]
    if len(fin) < len(ITEMS):
        return -99, {}
    first_t = [e["t"] for e in res["events"] if e["kind"] == "finish"][0]
    s = 0
    s += 50 if fin[0] == CAR else 0
    s += 40 if fin[1] == SHELF else 0
    s += 20 if 19 <= first_t <= 27 else (0 if 16 <= first_t <= 32 else -30)
    ch = [c for c in res["changes"] if c[0] > 2]
    s += min(len(ch), 8) * 3
    late = [c for c in ch if c[0] > first_t - 6]
    s += 10 if late else 0
    stuck = sum(1 for e in res["events"] if e["kind"] == "stuck")
    s -= 4 * max(0, stuck - 2)
    return s, dict(first=round(first_t, 1), changes=len(ch), late=len(late), stuck=stuck,
                   order=[ITEMS[i][1] for i in fin])


def label(i):
    a, b, _ = ITEMS[i]
    return (a + " " + b).strip()


def draw_ball(c, x, y, ang, i, scale=1.0, a=1.0, dim=False):
    top, bot, color = ITEMS[i]
    r = R * scale
    c.drawCircle(x, y, r + 5, fx.paint(color, 0.35 * a, blur=12))
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x - r * 0.35, y - r * 0.4), r * 1.6,
                                               [fx.col("#FFFFFF", 0.55 * a), fx.col(color, a)], [0.0, 0.55]))
    c.drawCircle(x, y, r, p)
    c.drawCircle(x, y, r, fx.paint("#FFFFFF", 0.9 * a, stroke=3))
    # 굴러가는 느낌의 줄무늬
    c.save()
    c.translate(x, y)
    c.rotate(math.degrees(ang))
    c.drawLine(-r * 0.75, 0, -r * 0.45, 0, fx.paint("#FFFFFF", 0.45 * a, stroke=4))
    c.restore()
    if top:
        fx.text(c, top, x, y - 2 * scale, fx.font("bold", int(19 * scale)), "#FFFFFF", a, stroke=4, stroke_color=color)
        fx.text(c, bot, x, y + 22 * scale, fx.font("black", int(23 * scale)), "#FFFFFF", a, stroke=4, stroke_color=color)
    else:
        f_ = fx.font("black", int((23 if len(bot) <= 3 else 19) * scale))
        fx.text(c, bot, x, y + 8 * scale, f_, "#FFFFFF", a, stroke=4, stroke_color=color)
    if dim:
        c.drawCircle(x, y, r, fx.paint("#000000", 0.55))


def render(seed, out, tmp, ep=1):
    res = simulate(seed)
    sc, info = score(res)
    print("seed", seed, sc, info)
    frames, events, fin = res["frames"], res["events"], res["finish"]
    t_first = [e["t"] for e in events if e["kind"] == "finish"][0]
    fin_t = {e["a"]: e["t"] for e in events if e["kind"] == "finish"}
    t_second = [e["t"] for e in events if e["kind"] == "finish"][1]
    # 결말 연출 시각
    T_DQ = t_second + 0.9          # 사장님 알림
    T_UP = T_DQ + 1.3              # 선반 1등
    T_END = T_UP + 1.7             # 끝 화면
    total = T_END + 2.3
    nfr = int(total * FPS)
    cam = fx.Camera(seed)
    pops = []
    sfx_ev = []
    last_tone = -1
    for e in events:
        t = e["t"]
        if t > T_DQ:
            continue
        if e["kind"] == "finish" and e["rank"] <= 2:
            nm = label(e["a"])
            pops.append((t, t + 1.1 if e["rank"] == 1 else T_DQ - 0.05, f"{e['rank']}등  {nm}", "#FFD54A", 74))
            sfx_ev.append((t, "ding", 0.9))
            cam.punch(t, 0.05, 0.3)
        elif e["kind"] == "stuck" and t < t_first - 1 and sum(1 for p in pops if "끼었" in p[2]) < 2:
            pops.append((t, t + 1.2, f"{label(e['a'])} 끼었어요", "#FFFFFF", 60))
            sfx_ev.append((t, "boing", 0.7))
    ch = [c for c in res["changes"] if 3 < c[0] < t_first - 0.5]
    said = 0
    for tt, li in ch:
        if said >= 3:
            break
        if not any(abs(tt - p[0]) < 2.2 for p in pops):
            pops.append((tt, tt + 1.1, f"선두 {label(li)}", "#FFFFFF", 62))
            sfx_ev.append((tt, "whoosh", 0.6))
            said += 1
    pops.append((T_DQ, T_UP, "사장님\n그건 안 판다", "#FFFFFF", 70))
    pops.append((T_UP, T_END, "2009년 선반\n16년 만에 1등", "#FFD54A", 84))
    pops.sort()
    fixed = []
    for st, en, s, cc, sz in pops:
        if fixed and st < fixed[-1][1]:
            p = fixed[-1]
            fixed[-1] = (p[0], max(p[0] + 0.5, st), p[2], p[3], p[4])
        fixed.append((st, en, s, cc, sz))
    pops = fixed
    sfx_ev += [(T_DQ - 0.35, "vibrate", 0.9), (T_DQ, "buzz", 0.8), (T_UP, "orch", 0.9), (T_UP, "cash", 0.6)]
    cam.shake(T_DQ, 0.4, 18)
    cam.glitch(T_DQ, 0.22)
    cam.flash(T_UP, 0.2)
    cam.punch(T_UP, 0.08, 0.4)
    # 충돌음 대신 코스 구간을 지날 때마다 박자감 있는 음
    mus = sound.phonk(total + 1, seed=seed % 5 + 11, bpm=146)
    audio = Path(tmp) / f"race_{seed}.wav"
    sound.mix(total, audio, music=mus, events=sfx_ev, mute=[(T_DQ - 0.4, T_UP - 0.05)], music_gain=0.6)

    vid = Path(tmp) / f"race_{seed}_v.mp4"
    wr = fx.Writer(vid)
    surf = fx.surface()
    cam_y = -560.0
    rng = np.random.default_rng(seed)
    stat = res["statics"]
    trails = {i: [] for i in range(len(ITEMS))}
    for fi in range(nfr):
        t = fi / FPS
        fr = frames[min(fi, len(frames) - 1)]
        c = surf.getCanvas()
        c.clear(fx.col("#0B1726"))
        # 카메라: 선두 기준(완주 전), 완주 뒤에는 결승선
        run = [b for b in fr["b"] if not b[4]]
        if run and t < t_first:
            target = max(b[2] for b in run) - 1180
        else:
            target = FINISH - 1180
        target = max(-560, min(COURSE_H - 1500, target))
        cam_y += (target - cam_y) * 0.12
        c.save()
        cam.apply(c, t)
        c.translate(0, -cam_y)
        # 배경 띠와 거리
        y0 = int((cam_y) // 500) * 500
        for yy in range(y0, int(cam_y + 2000), 500):
            c.drawRect(skia.Rect.MakeXYWH(X0, yy, X1 - X0, 250), fx.paint("#10203A", 0.6))
        # 결승선
        sq = 40
        for k in range(int((612 - 468) / sq) + 1):
            for row in range(2):
                colr = "#FFFFFF" if (k + row) % 2 == 0 else "#111111"
                c.drawRect(skia.Rect.MakeXYWH(468 + k * sq, FINISH - 40 + row * sq, sq, sq), fx.paint(colr, 0.9))
        fx.text(c, "출고", 540, FINISH - 70, fx.font("black", 44), "#FFD54A")
        for kind, *rest in stat:
            if kind == "seg":
                a, b, r_ = rest
                c.drawLine(a[0], a[1], b[0], b[1], fx.paint("#C9D6E3", 0.9, stroke=r_ * 2))
            else:
                (x, y), r_ = rest
                if cam_y - 60 < y < cam_y + 2000:
                    c.drawCircle(x, y, r_, fx.paint("#E8590C" if r_ > 30 else "#C9D6E3", 0.95))
        for x, y, ang, ln in fr["sp"]:
            dx, dy = math.cos(ang) * ln, math.sin(ang) * ln
            c.drawLine(x - dx, y - dy, x + dx, y + dy, fx.paint("#E8590C", 1.0, stroke=22))
            c.drawCircle(x, y, 14, fx.paint("#FFFFFF"))
        for i, x, y, ang, done in fr["b"]:
            trails[i].append((x, y))
            trails[i] = trails[i][-6:]
            for k, (tx, ty) in enumerate(trails[i][:-1]):
                c.drawCircle(tx, ty, R * (0.35 + 0.08 * k), fx.paint(ITEMS[i][2], 0.06 + 0.03 * k))
        for i, x, y, ang, done in sorted(fr["b"], key=lambda b: b[0] == CAR):
            if done:
                k = (t - fin_t[i]) / 0.45
                if k >= 1:
                    continue
                draw_ball(c, x, y + 160 * k, ang, i, 1.0 - 0.3 * k, 1.0 - k)
                c.drawCircle(x, FINISH, R + 120 * k, fx.paint("#FFD54A", 0.8 * (1 - k), stroke=8))
                continue
            draw_ball(c, x, y, ang, i, 1.0, 1.0)
        c.restore()

        # ---- 위쪽 고정 요소
        c.drawRect(skia.Rect.MakeXYWH(0, 0, fx.W, 560), fx.paint("#0B1726", 0.88))
        fx.text(c, f"창고 설비 레이스 {ep}회", 540, 205, fx.font("bold", 38), "#FFB37A", 0.95)
        hs = 1.0 + 0.06 * max(0, 1 - t / 0.25)
        fx.text(c, "제일 먼저 팔려 나갈 물건은", 540, 292, fx.font("black", int(68 * hs)), "#FFFFFF", 1, stroke=10)
        # 현재 순위
        cur = sorted(fr["b"], key=lambda b: (-(1e6 - fin.index(b[0])) if b[4] else -b[2]))
        if t >= T_UP:
            cur = [b for b in cur if b[0] != CAR] + [b for b in cur if b[0] == CAR]
        for k, (i, x, y, ang, done) in enumerate(cur):
            col_, row = k % 4, k // 4
            bx, by = 64 + col_ * 240, 345 + row * 92
            fx.rrect(c, bx, by, 226, 78, 18, "#000000", 0.4)
            c.drawCircle(bx + 38, by + 39, 24, fx.paint(ITEMS[i][2]))
            fx.text(c, str(k + 1), bx + 38, by + 51, fx.font("black", 32), "#FFFFFF")
            nm = ITEMS[i][1]
            a_ = 0.45 if (i == CAR and t >= T_DQ) else 1.0
            fx.text(c, nm, bx + 74, by + 52, fx.font("black", 34 if len(nm) <= 3 else 29), "#FFFFFF", a_, align="left")
            if i == CAR and t >= T_DQ:
                c.drawLine(bx + 70, by + 40, bx + 210, by + 40, fx.paint("#FF4B3E", 1, stroke=5))
        # 진행 막대
        lead_y = max([b[2] for b in fr["b"]])
        prog = max(0, min(1, lead_y / FINISH))
        fx.rrect(c, 64, 535, 952, 10, 5, "#FFFFFF", 0.15)
        fx.rrect(c, 64, 535, 952 * prog, 10, 5, "#E8590C", 0.95)
        # 해설
        for st, en, s, cc, sz in pops:
            if st <= t < en:
                k = (t - st) / 0.22
                scl = 0.6 + 0.4 * fx.ease_out_back(k)
                a_ = min(1.0, (en - t) / 0.18)
                head, _, tail = s.partition("\n")
                f_ = fx.font("black", sz)
                f2_ = fx.font("black", int(sz * (0.62 if not s.startswith("사장님") else 1.0)))
                if s.startswith("사장님"):
                    # 휴대폰 알림처럼 위에서 내려오는 띠
                    yy = 640 + (1 - fx.ease_out((t - st) / 0.25)) * -120
                    fx.rrect(c, 70, yy, 940, 190, 34, "#F5F7F9", 0.97 * a_)
                    fx.text(c, "사장님", 120, yy + 62, fx.font("bold", 34), "#5A6672", a_, align="left")
                    fx.text(c, "지금", 960, yy + 62, fx.font("regular", 28), "#5A6672", a_, align="right")
                    fx.text(c, "그건 안 판다", 120, yy + 140, fx.font("black", 62), "#141A21", a_, align="left")
                    continue
                c.save()
                c.translate(540, 1180)
                c.scale(scl, scl)
                bw = max(f_.measureText(head), f2_.measureText(tail) if tail else 0) + 70
                bh = sz * 1.2 + (sz * 0.75 if tail else 0) + 30
                fx.rrect(c, -bw / 2, -sz * 0.95 - 10, bw, bh, 26, "#05080A", 0.62 * a_)
                fx.text(c, head, 0, 0, f_, cc, a_, stroke=12)
                if tail:
                    fx.text(c, tail, 0, sz * 0.8, f2_, "#FFFFFF", a_, stroke=10)
                c.restore()
        if t >= T_END:
            k = fx.ease_out((t - T_END) / 0.35)
            c.drawRect(skia.Rect.MakeWH(fx.W, fx.H), fx.paint("#0B1726", 0.9 * k))
            draw_ball(c, 540, 820, 0, SHELF, 2.4, k)
            fx.text(c, "16년 만에 출고 1등", 540, 1060, fx.font("black", 74), "#FFFFFF", k, stroke=10)
            fx.text(c, "다음 회는 사장님 차 없이 다시", 540, 1150, fx.font("bold", 42), "#C9D6E3", k)
            fx.text(c, "쓰지 않는 설비, 사진만 보내 주세요", 540, 1640, fx.font("bold", 36), "#C9D6E3", 0.9 * k)
            fx.text(c, "clipmarket.kr", 540, 1690, fx.font("medium", 30), "#C9D6E3", 0.8 * k)
            fx.text(c, "등장 설비는 가상 설정이에요", 540, 1730, fx.font("regular", 17), "#7D8C9B", 0.6 * k)
        cam.overlay(c, t)
        arr = fx.snapshot(surf)
        g = cam.glitch_amt(t)
        if g > 0:
            arr = fx.rgb_split(arr, g, rng)
        wr.put(arr)
    wr.close()
    fx.mux(vid, audio, out)
    meta = dict(seed=seed, score=sc, info=info, total=total)
    Path(str(out) + ".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="race.mp4")
    ap.add_argument("--tmp", default=".")
    a = ap.parse_args()
    if a.cmd == "search":
        best = []
        for s in range(a.start, a.start + a.n):
            r = simulate(s)
            sc, info = score(r)
            best.append((sc, s, info))
        best.sort(key=lambda x: -x[0])
        for b in best[:12]:
            print(b, flush=True)
    else:
        render(a.seed, a.out, a.tmp)


if __name__ == "__main__":
    main()
