"""메신저 사고극 렌더러(skia). 잘못 보낸 방, 읽음 숫자, 삭제, 입력 중, 경고 자막, 반전 줌, 드롭, 장면 전환, 드라마식 끊기.

spec(json)
  theme   : dark | light
  title   : 화면 위 고정 제목(사고를 한 줄로)
  room, members, me, people {이름: 색}
  script  : 시각순 목록
    {t, who, text, fx?: hit|boom|zoom, react?: 큰 자막, unread?, quote?: true}   말풍선
    {t, who, file, size?}                                                      파일 말풍선
    {t, kind: system, text}                                                    가운데 회색 알림
    {t, kind: read}                                                            읽음 숫자 0으로
    {t, kind: delete, targets: [말풍선 번호]}
    {t, kind: typing, who, dur, muffle?, heart?}
    {t, kind: alert, text, sub?, dur?, mute?}                                  시스템 경고 자막
    {t, kind: scene, room, members, me?, title?}                               장면 전환(화면 비움)
  drop    : 반전 시각(0.45초 전 음악 끊고 폰크로)
  end     : {t, hold, series, next, ask?, cta, tiny, style?: drama}
python3 chat.py spec.json out.mp4 --tmp DIR
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx  # noqa: E402
import sound  # noqa: E402
import skia  # noqa: E402

THEME = {
    "dark": dict(bg="#121A17", head="#18221E", headfg="#F2EFE6", other="#26322D", otherfg="#F2EFE6", me="#D9A441",
                 mefg="#1B1508", sub="#A9B3AD", unread="#E9C46A", sys="#2B3833", sysfg="#C9D3CE", title_bg="#F2EFE6",
                 title_fg="#121A17", accent="#D9A441", endbg="#0E1412", file="#1F2B26"),
    "light": dict(bg="#DCE3EA", head="#F5F7F9", headfg="#141A21", other="#FFFFFF", otherfg="#141A21", me="#17395E",
                  mefg="#FFFFFF", sub="#5A6672", unread="#E8590C", sys="#C5CFD9", sysfg="#3C4752", title_bg="#141A21",
                  title_fg="#FFFFFF", accent="#E8590C", endbg="#0F1B2D", file="#EEF2F6"),
}
TOP = 420
BOTTOM = 1480
BUB_F = 52
NAME_F = 30
PAD = 26
MAXW = 700


def layout_msg(m):
    f = fx.font("medium", BUB_F)
    lines = fx.wrap(m["text"], f, MAXW)
    w = max(f.measureText(ln) for ln in lines) + PAD * 2 + (34 if m.get("quote") else 0)
    h = len(lines) * BUB_F * 1.32 + PAD * 1.4
    return lines, w, h


def render(spec, out, tmp):
    th = THEME[spec.get("theme", "light")]
    script = sorted(spec["script"], key=lambda e: e["t"])
    end = spec["end"]
    total = end["t"] + end.get("hold", 3.0)
    drop = spec.get("drop")
    seed = spec.get("seed", 1)
    cam = fx.Camera(seed)
    rng = np.random.default_rng(seed)
    people = spec["people"]

    # ---- 장면(방) 목록: 시작 장면 + scene 항목
    scenes = [dict(t=-1, room=spec["room"], members=spec["members"], me=spec["me"], title=spec["title"])]
    for e in script:
        if e.get("kind") == "scene":
            scenes.append(dict(t=e["t"], room=e["room"], members=e["members"], me=e.get("me", spec["me"]),
                               title=e.get("title", spec["title"])))

    def scene_at(t):
        cur = scenes[0]
        for s in scenes:
            if t >= s["t"]:
                cur = s
        return cur

    # ---- 메시지 목록
    msgs = []
    for e in script:
        if "who" in e and "kind" not in e:
            sc = scene_at(e["t"])
            mine = e["who"] == sc["me"]
            if "file" in e:
                msgs.append(dict(t=e["t"], who=e["who"], file=e["file"], size=e.get("size", ""), w=560, h=132, mine=mine,
                                 unread=e.get("unread", sc["members"] - 1), fx=e.get("fx"), deleted=None, read_t=None,
                                 react=e.get("react"), scene=sc["t"]))
            else:
                lines, w, h = layout_msg(e)
                msgs.append(dict(t=e["t"], who=e["who"], text=e["text"], lines=lines, w=w, h=h, mine=mine,
                                 unread=e.get("unread", sc["members"] - 1), fx=e.get("fx"), deleted=None, read_t=None,
                                 react=e.get("react"), quote=e.get("quote"), scene=sc["t"]))
        elif e.get("kind") == "system":
            msgs.append(dict(t=e["t"], sys=True, text=e["text"], h=86, w=0, deleted=None, read_t=None, fx=e.get("fx"),
                             react=e.get("react"), scene=scene_at(e["t"])["t"]))
    for e in script:
        if e.get("kind") == "read":
            for m in msgs:
                if m["t"] <= e["t"] and m.get("read_t") is None and not m.get("sys"):
                    m["read_t"] = e["t"]
        if e.get("kind") == "delete":
            for k, idx in enumerate(e["targets"]):
                msgs[idx]["deleted"] = e["t"] + k * 0.18

    # ---- 효과음과 카메라
    sfx_ev = []
    for m in msgs:
        if m.get("sys"):
            sfx_ev.append((m["t"], "pop", 0.4))
        elif m.get("file"):
            sfx_ev.append((m["t"], "slide_up", 0.5))
        else:
            sfx_ev.append((m["t"], "pop", 0.75 if not m["mine"] else 0.55))
        f_ = m.get("fx")
        if f_ == "boom":
            sfx_ev.append((m["t"], "boom", 0.95))
            cam.flash(m["t"], 0.16)
            cam.shake(m["t"], 0.45, 26)
            cam.punch(m["t"], 0.1, 0.45)
        elif f_ == "hit":
            sfx_ev.append((m["t"], "hit", 0.75))
            cam.punch(m["t"], 0.05, 0.3)
        elif f_ == "zoom":
            sfx_ev.append((m["t"], "hit", 0.6))
    alerts, typings = [], []
    for e in script:
        k = e.get("kind")
        if k == "alert":
            alerts.append(e)
            sfx_ev.append((e["t"], "glitch", 0.7))
            sfx_ev.append((e["t"] + 0.05, "hit", 0.8))
            cam.glitch(e["t"], 0.3)
            cam.shake(e["t"], 0.35, 18)
        elif k == "typing":
            typings.append(e)
            sfx_ev.append((e["t"], sound.sfx_typing(np.random.default_rng(3), min(1.4, e["dur"])), 0.6))
            if e.get("heart"):
                for hb in np.arange(e["t"] + 0.2, e["t"] + e["dur"], 0.75):
                    sfx_ev.append((hb, "heart", 0.7))
        elif k == "delete":
            sfx_ev.append((e["t"], "whoosh", 0.6))
        elif k == "read":
            sfx_ev.append((e["t"], "tick", 0.5))
        elif k == "scene":
            sfx_ev.append((e["t"], "whoosh", 0.7))
            cam.punch(e["t"], 0.04, 0.3)
    drama = end.get("style") == "drama"
    if drama:
        sfx_ev.append((end["t"] - 1.1, "timpani", 0.9))
        sfx_ev.append((end["t"] + 1.15, "orch", 0.8))
        cam.flash(end["t"] + 1.15, 0.2)
        cam.shake(end["t"] + 1.15, 0.4, 20)
    else:
        sfx_ev.append((end["t"], "whoosh", 0.5))

    # ---- 음악
    sk = sound.sneaky(total + 1, seed=seed + 3)
    ph = sound.phonk(total + 1, seed=seed + 5, bpm=spec.get("bpm", 140))
    parts = [(0, drop - 0.45, sk, 0.9), (drop, total, ph, 1.0)] if drop else [(0, total, sk, 1.0)]
    music = sound.bed(total + 0.1, parts)
    muffle = [(e["t"], e["t"] + e["dur"]) for e in typings if e.get("muffle")]
    mute = [(a["t"], a["t"] + a.get("mute", 0.9)) for a in alerts]
    if drama:
        mute.append((end["t"] - 1.1, total))
    audio = Path(tmp) / (Path(out).stem + ".wav")
    sound.mix(total, audio, music=music, events=sfx_ev, mute=mute, muffle=muffle, music_gain=0.5)

    # ---- 프레임
    vid = Path(tmp) / (Path(out).stem + "_v.mp4")
    wr = fx.Writer(vid)
    surf = fx.surface()
    scroll = 0.0
    nfr = int(total * fx.FPS)
    avatar_f = fx.font("black", 36)
    last_scene_t = -1
    for fi in range(nfr):
        t = fi / fx.FPS
        sc = scene_at(t)
        if sc["t"] != last_scene_t:
            scroll = 0.0
            last_scene_t = sc["t"]
        c = surf.getCanvas()
        c.clear(fx.col(th["bg"]))
        c.save()
        cam.apply(c, t)
        # 장면 전환 미끄러짐
        if sc["t"] > 0 and t - sc["t"] < 0.3:
            c.translate(1080 * (1 - fx.ease_out((t - sc["t"]) / 0.3)), 0)
        vis = [m for m in msgs if m["t"] <= t and m["scene"] == sc["t"]]
        heights = []
        prev_who = None
        for m in vis:
            m["h_now"] = 86 if (m.get("deleted") is not None and t >= m["deleted"]) else m["h"]
            name_h = 0
            if not m.get("sys") and not m["mine"] and m["who"] != prev_who:
                name_h = NAME_F + 12
            heights.append((m, name_h, 18))
            prev_who = None if m.get("sys") else m["who"]
        typing_now = [e for e in typings if e["t"] <= t < e["t"] + e["dur"]]
        total_h = sum(m["h_now"] + nh + g for m, nh, g in heights) + (110 if typing_now else 0)
        target = max(0.0, total_h - (BOTTOM - TOP))
        scroll += (target - scroll) * 0.25
        # 반전 말풍선 줌
        yy = TOP - scroll
        zc, zk, ze = None, 0.0, 0.0
        for m, name_h, gap in heights:
            if m.get("sys"):
                cxy, wz = (540, yy + 49), 500
                yy += m["h_now"] + gap
            else:
                bx_ = 1080 - 56 - m["w"] if m["mine"] else 160
                cxy, wz = (bx_ + m["w"] / 2, yy + name_h + m["h_now"] / 2), m["w"]
                yy += m["h_now"] + name_h + gap
            if m.get("fx") in ("boom", "zoom"):
                age = t - m["t"]
                if 0 <= age < 1.25:
                    if age < 0.16:
                        env_ = fx.ease_out(age / 0.16)
                    elif age < 0.95:
                        env_ = 1.0
                    else:
                        env_ = 1 - fx.ease_in_out((age - 0.95) / 0.3)
                    zmax = min(0.42 if m.get("fx") == "boom" else 0.12, 980 / max(1, wz) - 1)
                    zc, zk, ze = cxy, env_ * max(0.0, zmax), env_
        if zc:
            c.translate(zc[0] + (540 - zc[0]) * ze, zc[1])
            c.scale(1 + zk, 1 + zk)
            c.translate(-zc[0], -zc[1])
        y = TOP - scroll
        for m, name_h, gap in heights:
            age = t - m["t"]
            k = fx.ease_out_back(min(1, age / 0.22))
            if m.get("sys"):
                f_ = fx.font("medium", 32)
                w = f_.measureText(m["text"]) + 60
                cy = y + 20
                fx.rrect(c, 540 - w / 2, cy, w, 58, 29, th["sys"], 0.95)
                fx.text(c, m["text"], 540, cy + 40, f_, th["sysfg"])
                y += m["h_now"] + gap
                continue
            mine = m["mine"]
            col_ = people.get(m["who"], "#888888")
            bx = 1080 - 56 - m["w"] if mine else 160
            by = y + name_h
            if not mine and name_h:
                fx.text(c, m["who"], 160, y + NAME_F, fx.font("bold", NAME_F), th["sub"], align="left")
                c.drawCircle(92, y + 50, 42, fx.paint(col_))
                fx.text(c, m["who"][0], 92, y + 63, avatar_f, "#FFFFFF")
            c.save()
            ox = bx + (m["w"] if mine else 0)
            c.translate(ox, by + m["h"] / 2)
            c.scale(0.7 + 0.3 * k, 0.7 + 0.3 * k)
            c.translate(-ox, -(by + m["h"] / 2))
            deleted = m["deleted"] is not None and t >= m["deleted"]
            bcol = th["me"] if mine else th["other"]
            fcol = th["mefg"] if mine else th["otherfg"]
            if deleted:
                f_ = fx.font("regular", 38)
                txt = "삭제된 메시지입니다"
                w = f_.measureText(txt) + PAD * 2
                bx2 = 1080 - 56 - w if mine else 160
                fx.rrect(c, bx2, by, w, 86, 30, bcol, 0.45)
                fx.text(c, txt, bx2 + PAD, by + 56, f_, fcol, 0.8, align="left")
            elif m.get("file"):
                fx.rrect(c, bx, by, m["w"], m["h"], 24, bcol)
                fx.rrect(c, bx + 22, by + 24, 64, 84, 10, th["file"] if not mine else "#FFFFFF", 0.9)
                fx.text(c, "DOC", bx + 54, by + 76, fx.font("black", 20), "#17395E")
                fx.text(c, m["file"], bx + 108, by + 60, fx.font("bold", 34), fcol, align="left")
                fx.text(c, m["size"], bx + 108, by + 104, fx.font("regular", 28), fcol, 0.7, align="left")
            else:
                fx.rrect(c, bx, by, m["w"], m["h"], 30, bcol)
                f_ = fx.font("medium", BUB_F)
                tx = bx + PAD
                if m.get("quote"):
                    fx.rrect(c, bx + PAD, by + 20, 10, m["h"] - 40, 5, fcol, 0.55)
                    tx += 34
                for li, ln in enumerate(m["lines"]):
                    fx.text(c, ln, tx, by + PAD * 0.7 + BUB_F * (li + 1) * 1.18, f_, fcol, align="left")
            c.restore()
            if not deleted:
                un = m["unread"]
                if m["read_t"] is not None and t >= m["read_t"]:
                    kk = min(1, (t - m["read_t"]) / 0.5)
                    un = int(round(un * (1 - kk)))
                if un > 0:
                    ux = bx - 14 if mine else bx + m["w"] + 14
                    fx.text(c, str(un), ux, by + m["h"] - 8, fx.font("bold", 30), th["unread"],
                            align="right" if mine else "left")
            y += m["h_now"] + name_h + gap
        for e in typing_now:
            col_ = people.get(e["who"], "#888888")
            yy = y + 6
            c.drawCircle(92, yy + 50, 42, fx.paint(col_))
            fx.text(c, e["who"][0], 92, yy + 63, avatar_f, "#FFFFFF")
            fx.rrect(c, 160, yy + 10, 170, 86, 30, th["other"])
            for d in range(3):
                ph_ = (t * 3 - d * 0.33) % 1.0
                a_ = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(ph_ * 2 * math.pi))
                c.drawCircle(205 + d * 40, yy + 53, 11, fx.paint(th["sub"], a_))
        c.restore()

        # ---- 머리와 제목
        c.drawRect(skia.Rect.MakeXYWH(0, 300, 1080, 100), fx.paint(th["head"]))
        fx.text(c, "<", 60, 368, fx.font("bold", 46), th["headfg"], align="left")
        fx.text(c, sc["room"], 120, 368, fx.font("bold", 40), th["headfg"], align="left")
        rw = fx.font("bold", 40).measureText(sc["room"])
        if sc["members"] > 2:
            fx.text(c, str(sc["members"]), 120 + rw + 16, 368, fx.font("bold", 34), th["sub"], align="left")
        c.drawRect(skia.Rect.MakeXYWH(0, 0, 1080, 300), fx.paint(th["bg"]))
        f_t = fx.font("black", 60)
        tl = fx.wrap(sc["title"], f_t, 960)
        for li, ln in enumerate(tl):
            ty = 175 + li * 74 - (len(tl) - 1) * 30
            tw = f_t.measureText(ln) + 44
            fx.rrect(c, 540 - tw / 2, ty - 58, tw, 76, 14, th["title_bg"])
            fx.text(c, ln, 540, ty, f_t, th["title_fg"])
        # ---- 경고 자막(시스템 기록 느낌)
        for a in alerts:
            dt = t - a["t"]
            dur = a.get("dur", 1.4)
            if 0 <= dt < dur:
                k = fx.ease_out_back(min(1, dt / 0.18))
                a_ = min(1, (dur - dt) / 0.2)
                c.save()
                c.translate(540, 900)
                c.scale(0.7 + 0.3 * k, 0.7 + 0.3 * k)
                fx.rrect(c, -440, -120, 880, 240, 28, "#0B0B0B", 0.92 * a_)
                fx.rrect(c, -440, -120, 880, 240, 28, "#FF3B30", a_, stroke=6)
                path = skia.Path()
                path.moveTo(-370, 20)
                path.lineTo(-320, -70)
                path.lineTo(-270, 20)
                path.close()
                c.drawPath(path, fx.paint("#FF3B30", a_))
                c.drawLine(-320, -38, -320, -8, fx.paint("#0B0B0B", a_, stroke=9))
                c.drawCircle(-320, 7, 5.5, fx.paint("#0B0B0B", a_))
                fx.text(c, a["text"], -230, -18, fx.font("black", 58), "#FF3B30", a_, align="left")
                if a.get("sub"):
                    fx.text(c, a["sub"], -230, 56, fx.font("bold", 38), "#FFFFFF", a_, align="left")
                c.restore()
        # ---- 반응 자막
        for m in msgs:
            if not m.get("react"):
                continue
            dt = t - m["t"] - 0.12
            if 0 <= dt < 1.1:
                k = min(1, dt / 0.14)
                scl = 2.2 - 1.2 * fx.ease_out(k)
                a_ = min(1, (1.1 - dt) / 0.2) * min(1, k * 2)
                c.save()
                c.translate(540, 860)
                c.rotate(-6)
                c.scale(scl, scl)
                fx.text(c, m["react"], 0, 50, fx.font("black", 150), "#FFD54A", a_, stroke=18, stroke_color="#111111")
                c.restore()
        # ---- 끝 화면
        if t >= end["t"]:
            dt = t - end["t"]
            if drama:
                k = fx.ease_out(dt / 0.25)
                c.drawRect(skia.Rect.MakeWH(1080, 1920), fx.paint("#000000", 0.97 * k))
                if dt < 1.15:
                    # 떨리는 '다음 화에 계속'
                    jit = 3 * math.sin(dt * 90)
                    fx.text(c, "다음 화에", 540 + jit, 900, fx.font("serif", 110), "#FFFFFF", k)
                    fx.text(c, "계속", 540 - jit, 1040, fx.font("serif", 110), "#FFFFFF", k)
                else:
                    k2 = fx.ease_out((dt - 1.15) / 0.3)
                    fx.text(c, end["series"], 540, 740, fx.font("bold", 46), th["accent"], k2)
                    fl = fx.font("black", 84)
                    for li, ln in enumerate(fx.wrap(end["next"], fl, 960)):
                        fx.text(c, ln, 540, 880 + li * 104, fl, "#FFFFFF", k2, stroke=10)
                    if end.get("ask"):
                        fx.text(c, end["ask"], 540, 1140, fx.font("bold", 46), "#C9D3CE", k2)
                    fx.text(c, end["cta"], 540, 1640, fx.font("medium", 34), "#C9D3CE", 0.85 * k2)
                    fx.text(c, end["tiny"], 540, 1700, fx.font("regular", 17), "#8C9791", 0.6 * k2)
            else:
                k = fx.ease_out(dt / 0.35)
                c.drawRect(skia.Rect.MakeWH(1080, 1920), fx.paint(th["endbg"], 0.97 * k))
                fx.text(c, end["series"], 540, 760, fx.font("bold", 48), th["accent"], k)
                fl = fx.font("black", 84)
                for li, ln in enumerate(fx.wrap(end["next"], fl, 960)):
                    fx.text(c, ln, 540, 900 + li * 104, fl, "#FFFFFF", k, stroke=10)
                if end.get("ask"):
                    fx.text(c, end["ask"], 540, 1150, fx.font("bold", 46), "#C9D3CE", k)
                fx.text(c, end["cta"], 540, 1640, fx.font("medium", 34), "#C9D3CE", 0.85 * k)
                fx.text(c, end["tiny"], 540, 1700, fx.font("regular", 17), "#8C9791", 0.6 * k)
        cam.overlay(c, t)
        arr = fx.snapshot(surf)
        g = cam.glitch_amt(t)
        if g > 0:
            arr = fx.rgb_split(arr, g, rng)
        wr.put(arr)
    wr.close()
    fx.mux(vid, audio, out)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--tmp", default=".")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    print(render(spec, a.out, a.tmp))


if __name__ == "__main__":
    main()
