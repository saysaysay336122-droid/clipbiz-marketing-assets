"""메신저 대화 형식의 짧은 이야기(상황극)를 세로 영상(1080x1920)과 카드(1080x1350)로 만든다.

사용법
  python3 tools/render_chat.py <spec.json> <출력 mp4>                 영상
  python3 tools/render_chat.py <spec.json> <출력 mp4> --cards <폴더>   영상과 함께 카드도(파일명 <ID>_1.png ...)

spec.json 예
{
  "id": "MK-261109-05",
  "theme": "b2b",                      # b2b(클립비즈 계정), hic(하이클립), hcs(홍책사)
  "room": "인사팀",                      # 대화방 이름(화면 위)
  "when": "12월 28일 오후 5:47",          # 첫 화면 위 시각 한 줄(갈등이 시작되는 순간)
  "me": "박 대리",                        # 오른쪽 말풍선 주인
  "messages": [
    {"from": "팀장", "text": "부담금 신고 자료 언제까지 돼?"},
    {"from": "박 대리", "text": "1월 31일까지라서요..."},
    {"from": "팀장", "text": "작년에 얼마 냈더라", "pause": 1.0},
    {"note": "다음 날 아침"},                      # 가운데 회색 줄(장면 전환)
    ...
  ],
  "pages": [4, 8],                      # 카드로 나눌 때 각 장의 마지막 메시지 번호(선택, 없으면 4개씩)
  "end": {"title": "감면은 부담금의 90%와\\n도급액의 50% 중 작은 금액", "body": "예상 참고액, 최종 인정은 한국장애인고용공단", "foot": "ansimclip.kr"},
  "music": true,
  "bg": [{"pexels": "6100897", "start": 1}, {"pexels": "7710418"}],   # 선택. 넣으면 실사 영상 위에 대화가 뜬다
  "hook": "박 대리의 연말 1화"                                            # 선택. bg가 있을 때 첫 1.8초 큰 글씨
}
영상 모드(bg가 있을 때): 첫 1.8초는 선명한 실사 영상 위에 when과 hook을 크게 보여 주고, 대화가 시작되면 배경을 흐리게 한다.
'note'가 나오면 다음 bg 영상으로 넘어가며 1.5초 동안 선명한 화면에 그 문장을 크게 보여 준다(장면 전환). 끝 화면은 흐린 영상 위에 글.

규칙
1. 등장인물은 모두 가상 인물이다. 화면 위에 '등장인물은 가상 인물입니다'를 작게 넣는다(지우지 않는다).
2. 메시지는 한 말풍선에 30자 안. 길면 두 개로 나눈다.
3. 쇼츠 화면 단추와 겹치지 않게 아래 340px, 오른쪽 150px에는 말풍선을 두지 않는다.
4. 메시지 하나가 보이는 시간은 0.9초 + 글자 수 x 0.05초(pause로 더할 수 있다). 앞에 입력 중 표시가 0.4초 나온다. 첫 메시지는 0.3초 만에 뜬다(첫 1초 안에 상황이 보이게). 전체 20초에서 35초를 권한다.
5. 전체 60초 이하. 출력은 H.264 30fps yuv420p faststart, 자체 생성 음향(render_reel.make_pad).
"""
import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_reel import make_pad  # noqa: E402

THEMES = {
    "b2b": dict(bg="#EEF1F4", head="#17395E", headfg="#FFFFFF", other="#FFFFFF", otherfg="#17222E",
                me="#17395E", mefg="#FFFFFF", sub="#5C6773", accent="#E8590C", endbg="#17395E", endfg="#FFFFFF", endsub="#C9D6E3"),
    "hic": dict(bg="#F5F6F3", head="#14202E", headfg="#F5F6F3", other="#FFFFFF", otherfg="#14202E",
                me="#C64016", mefg="#FFFFFF", sub="#485868", accent="#C64016", endbg="#14202E", endfg="#F5F6F3", endsub="#C9D1DA"),
    "hcs": dict(bg="#1D2824", head="#16201C", headfg="#F2EFE6", other="#2B3833", otherfg="#F2EFE6",
                me="#B5342A", mefg="#F7F1EA", sub="#A9B3AD", accent="#D9A441", endbg="#16201C", endfg="#F2EFE6", endsub="#A9B3AD"),
}
FONT = "'Noto Sans CJK KR', sans-serif"


def esc(s):
    return html.escape(s or "").replace("\n", "<br>")


AVATAR = ["#7C9CBF", "#C49A6C", "#8DAA91", "#B48EAD", "#D08770", "#88A0A8"]


def bubbles(t, spec, msgs, typing_from=None):
    """같은 사람이 이어 보낸 말은 묶어서 이름과 얼굴 표시를 한 번만 둔다."""
    me = spec.get("me")
    items = list(msgs) + ([{"from": typing_from, "typing": True}] if typing_from is not None else [])
    out, prev = [], None
    for m in items:
        if m.get("note"):
            out.append(f"<div class='note'>{esc(m['note'])}</div>")
            prev = None
            continue
        who = m.get("from")
        mine = who == me
        first = who != prev
        prev = who
        body = "<span class='dots'><i></i><i></i><i></i></span>" if m.get("typing") else esc(m.get("text"))
        cls = "b typing" if m.get("typing") else "b"
        if mine:
            out.append(f"<div class='row me{' gap' if first else ''}'><div class='{cls}'>{body}</div></div>")
        else:
            color = AVATAR[sum(map(ord, who or "")) % len(AVATAR)]
            av = f"<div class='av' style='background:{color}'>{esc((who or ' ')[0])}</div>" if first else "<div class='av ghost'></div>"
            name = f"<div class='name'>{esc(who)}</div>" if first else ""
            out.append(f"<div class='row other{' gap' if first else ''}'>{av}<div class='col'>{name}<div class='{cls}'>{body}</div></div></div>")
    return "".join(out)


def chat_html(t, spec, msgs, typing_from=None, w=1080, h=1920, card=False, video=False):
    bottom = 120 if card else 340
    right = 72 if card else 150
    when = f"<div class='when'>{esc(spec.get('when'))}</div>" if spec.get("when") else ""
    bg = "transparent" if video else t["bg"]
    head = "rgba(10,14,20,.42)" if video else t["head"]
    sub = "#FFFFFF" if video else t["sub"]
    shadow = "text-shadow:0 1px 6px rgba(0,0,0,.6);" if video else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:{w}px;height:{h}px;background:{bg};font-family:{FONT};position:relative;overflow:hidden}}
    .head{{position:absolute;left:0;right:0;top:0;height:{200 if card else 250}px;background:{head};color:{t['headfg'] if not video else '#FFFFFF'};
      display:flex;flex-direction:column;justify-content:flex-end;padding:0 72px 28px}}
    .room{{font-size:44px;font-weight:700;letter-spacing:-0.5px}}
    .fic{{font-size:24px;opacity:.6;margin-top:6px}}
    .when{{position:absolute;left:0;right:0;top:{230 if card else 290}px;text-align:center;font-size:32px;color:{sub};font-weight:500;{shadow}}}
    .area{{position:absolute;left:56px;right:{right}px;top:{300 if card else 370}px;bottom:{bottom}px;display:flex;flex-direction:column;justify-content:flex-end;gap:10px;overflow:hidden}}
    .row{{display:flex;max-width:84%}}
    .row.gap{{margin-top:18px}}
    .row.other{{align-self:flex-start;align-items:flex-start;gap:16px}}
    .row.me{{align-self:flex-end;justify-content:flex-end}}
    .col{{display:flex;flex-direction:column;align-items:flex-start;min-width:0}}
    .av{{flex:0 0 76px;width:76px;height:76px;border-radius:30px;color:#FFFFFF;font-size:34px;font-weight:700;display:flex;align-items:center;justify-content:center}}
    .av.ghost{{visibility:hidden}}
    .name{{font-size:29px;color:{sub};margin:0 0 8px 6px;font-weight:500;{shadow}}}
    .b{{font-size:42px;line-height:1.38;padding:22px 30px;border-radius:34px;word-break:keep-all;letter-spacing:-0.3px}}
    .other .b{{background:{'rgba(255,255,255,.96)' if video else t['other']};color:{'#17222E' if video else t['otherfg']};border-top-left-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,{'.25' if video else '.06'})}}
    .me .b{{background:{t['me']};color:{t['mefg']};border-top-right-radius:12px}}
    .note{{align-self:center;font-size:30px;color:{sub};padding:8px 24px;border-radius:999px;border:2px solid {sub};opacity:.9;{shadow}}}
    .dots{{display:flex;gap:12px;align-items:center;height:58px}}
    .dots i{{width:15px;height:15px;border-radius:50%;background:currentColor;opacity:.45;display:block}}
    </style></head><body>
    <div class='head'><div class='room'>{esc(spec.get('room'))}</div><div class='fic'>등장인물은 가상 인물입니다</div></div>
    {when}<div class='area'>{bubbles(t, spec, msgs, typing_from)}</div></body></html>"""


def end_html(t, e):
    body = f"<div class='body'>{esc(e.get('body'))}</div>" if e.get("body") else ""
    foot = f"<div class='foot'>{esc(e.get('foot'))}</div>" if e.get("foot") else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1920px;background:{t['endbg']};color:{t['endfg']};font-family:{FONT};
      display:flex;flex-direction:column;justify-content:center;padding:0 160px 160px 110px}}
    .title{{font-size:80px;line-height:1.3;font-weight:700;letter-spacing:-1px;word-break:keep-all}}
    .body{{margin-top:34px;font-size:40px;line-height:1.5;color:{t['endsub']}}}
    .foot{{margin-top:56px;font-size:42px;font-weight:700;color:{t['accent']}}}
    .fic{{position:absolute;left:110px;bottom:150px;font-size:26px;color:{t['endsub']}}}
    </style></head><body><div class='title'>{esc(e.get('title'))}</div>{body}{foot}
    <div class='fic'>등장인물은 가상 인물입니다</div></body></html>"""


def caption_html(t, kicker, title):
    """영상이 선명하게 보이는 장면(시작과 장면 전환) 위의 큰 글씨. 아래 어두운 띠."""
    k = f"<div class='k'>{esc(kicker)}</div>" if kicker else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1920px;background:transparent;font-family:{FONT};position:relative;overflow:hidden}}
    .band{{position:absolute;left:0;right:0;bottom:0;height:1150px;background:linear-gradient(to top, rgba(8,12,18,.92) 0%, rgba(8,12,18,.75) 45%, rgba(8,12,18,0) 100%)}}
    .box{{position:absolute;left:96px;right:160px;bottom:380px;color:#FFFFFF}}
    .k{{font-size:34px;font-weight:500;color:rgba(255,255,255,.82);margin-bottom:18px;letter-spacing:0.5px}}
    .t{{font-size:80px;line-height:1.28;font-weight:700;letter-spacing:-1px;word-break:keep-all;text-shadow:0 2px 14px rgba(0,0,0,.45)}}
    .fic{{position:absolute;right:160px;top:120px;font-size:24px;color:#FFFFFF;background:rgba(0,0,0,.38);padding:6px 16px;border-radius:999px}}
    </style></head><body><div class='band'></div><div class='fic'>등장인물은 가상 인물입니다</div>
    <div class='box'>{k}<div class='t'>{esc(title)}</div></div></body></html>"""


def end_video_html(t, e):
    body = f"<div class='body'>{esc(e.get('body'))}</div>" if e.get("body") else ""
    foot = f"<div class='foot'>{esc(e.get('foot'))}</div>" if e.get("foot") else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1920px;background:rgba(8,12,18,.62);color:#FFFFFF;font-family:{FONT};
      display:flex;flex-direction:column;justify-content:center;padding:0 160px 160px 110px}}
    .title{{font-size:80px;line-height:1.3;font-weight:700;letter-spacing:-1px;word-break:keep-all}}
    .body{{margin-top:34px;font-size:40px;line-height:1.5;color:#E3E8EE}}
    .foot{{margin-top:56px;font-size:42px;font-weight:700;color:{t['accent']}}}
    .fic{{position:absolute;left:110px;bottom:150px;font-size:26px;color:#E3E8EE}}
    </style></head><body><div class='title'>{esc(e.get('title'))}</div>{body}{foot}
    <div class='fic'>등장인물은 가상 인물입니다</div></body></html>"""


def shoot(pages, size, transparent=False):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": size[0], "height": size[1]})
        for html_text, path in pages:
            p.set_content(html_text)
            p.wait_for_timeout(120)
            p.screenshot(path=str(path), omit_background=transparent)
        b.close()


def resolve_bg(items):
    """bg 항목을 로컬 영상 파일로. {"pexels": "번호"} 는 stock/에 내려받는다."""
    import fetch_stock
    root = Path(__file__).resolve().parent.parent
    stock = root / "stock"
    stock.mkdir(exist_ok=True)
    out = []
    for it in items:
        if it.get("pexels"):
            vid = "".join(ch for ch in str(it["pexels"]) if ch.isdigit())
            fetch_stock.cmd_get([f"video:{vid}"], stock)
            out.append((stock / f"pexels_{vid}.mp4", float(it.get("start", 0))))
        else:
            src = Path(it["src"])
            out.append((src if src.is_absolute() else root / src, float(it.get("start", 0))))
    return out


def main():
    spec_path = Path(sys.argv[1])
    out = Path(sys.argv[2])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    t = THEMES[spec.get("theme", "b2b")]
    msgs = spec["messages"]
    work = Path(tempfile.mkdtemp(prefix="chat_"))

    video = bool(spec.get("bg"))
    frames = []  # (html, seconds, segment, clear)
    shown = []
    seg = 0
    if video:
        frames.append((caption_html(t, spec.get("when"), spec.get("hook") or spec.get("room")), 1.8, 0, True))
    else:
        frames.append((chat_html(t, spec, []), 0.3, 0, False))
    for m in msgs:
        if m.get("note"):
            if video:
                seg += 1
                frames.append((caption_html(t, "", m["note"]), 1.5 + float(m.get("pause", 0)), seg, True))
                shown = []
            else:
                shown.append(m)
                frames.append((chat_html(t, spec, shown), 1.2 + float(m.get("pause", 0)), seg, False))
            continue
        frames.append((chat_html(t, spec, shown, typing_from=m.get("from"), video=video), 0.4, seg, False))
        shown.append(m)
        frames.append((chat_html(t, spec, shown, video=video), 0.9 + 0.05 * len(m.get("text", "")) + float(m.get("pause", 0)), seg, False))
    end = spec.get("end")
    if end:
        frames.append(((end_video_html(t, end) if video else end_html(t, end)), float(end.get("dur", 3.4)), seg, False))
    total = sum(f[1] for f in frames)
    if total > 60:
        sys.exit(f"길이 {total:.1f}초. 60초를 넘는다.")

    pngs = [(f[0], work / f"f{i:03d}.png") for i, f in enumerate(frames)]
    shoot(pngs, (1080, 1920), transparent=video)
    concat = work / "list.txt"
    with open(concat, "w") as f:
        for (h, p), fr in zip(pngs, frames):
            f.write(f"file '{p}'\nduration {fr[1]:.3f}\n")
        f.write(f"file '{pngs[-1][1]}'\n")
    music = None
    if spec.get("music", True):
        music = work / "music.wav"
        make_pad(total + 0.5, music, seed=spec.get("seed", 11),
                 style=spec.get("music_style") or {"hcs": "playful"}.get(spec.get("theme", "b2b"), "bright"))

    if not video:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat)]
        if music:
            cmd += ["-i", str(music), "-c:a", "aac", "-b:a", "128k", "-shortest"]
        cmd += ["-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)]
    else:
        bgs = resolve_bg(spec["bg"])
        nseg = seg + 1
        seg_dur = [sum(f[1] for f in frames if f[2] == k) for k in range(nseg)]
        clear_until = [sum(f[1] for f in frames if f[2] == k and f[3]) for k in range(nseg)]
        cmd = ["ffmpeg", "-y", "-v", "error"]
        chains = []
        for k in range(nseg):
            src, start = bgs[k % len(bgs)]
            cmd += ["-stream_loop", "-1", "-ss", f"{start}", "-t", f"{seg_dur[k] + 0.3:.3f}", "-i", str(src)]
            c = clear_until[k]
            chains.append(f"[{k}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,"
                          f"trim=duration={seg_dur[k]:.3f},setpts=PTS-STARTPTS,"
                          f"gblur=sigma=16:enable='gte(t,{c:.3f})',eq=brightness=-0.05:saturation=0.9:enable='gte(t,{c:.3f})'[b{k}]")
        cmd += ["-f", "concat", "-safe", "0", "-i", str(concat)]
        ov = nseg
        if music:
            cmd += ["-i", str(music)]
        chains.append("".join(f"[b{k}]" for k in range(nseg)) + f"concat=n={nseg}:v=1:a=0[bg]")
        chains.append(f"[{ov}:v]fps=30,format=rgba[ov]")
        chains.append("[bg][ov]overlay=0:0:shortest=1,format=yuv420p[v]")
        cmd += ["-filter_complex", ";".join(chains), "-map", "[v]"]
        if music:
            cmd += ["-map", f"{ov + 1}:a", "-c:a", "aac", "-b:a", "128k"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-r", "30",
                "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr[-2000:])
    print(f"{out} {total:.1f}s")

    if "--cards" in sys.argv:
        cdir = Path(sys.argv[sys.argv.index("--cards") + 1])
        cdir.mkdir(parents=True, exist_ok=True)
        real = [i for i, m in enumerate(msgs) if not m.get("note")]
        cuts = spec.get("pages") or [n for n in range(4, len(real) + 1, 4)]
        if not cuts or cuts[-1] != len(real):
            cuts = list(cuts) + [len(real)]
        pages, start = [], 0
        for c in cuts:
            last = real[c - 1] + 1
            pages.append(msgs[start:last])
            start = last
        cid = spec.get("id", out.stem.replace("_reel", ""))
        shots = [(chat_html(t, spec, pg, w=1080, h=1350, card=True), cdir / f"{cid}_{i}.png") for i, pg in enumerate(pages, 1)]
        shoot(shots, (1080, 1350))
        mf = cdir / "manifest.json"
        manifest = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
        manifest[cid] = [p.name for _, p in shots]
        mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        print("카드", len(shots), "장")


if __name__ == "__main__":
    main()
