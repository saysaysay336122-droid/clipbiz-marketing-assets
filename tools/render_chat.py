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
  "music": true
}

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


def bubbles(t, spec, msgs, typing_from=None):
    me = spec.get("me")
    out = []
    for m in msgs:
        if m.get("note"):
            out.append(f"<div class='note'>{esc(m['note'])}</div>")
            continue
        mine = m.get("from") == me
        name = "" if mine else f"<div class='name'>{esc(m.get('from'))}</div>"
        out.append(f"<div class='row {'me' if mine else 'other'}'>{name}<div class='b'>{esc(m.get('text'))}</div></div>")
    if typing_from is not None:
        mine = typing_from == me
        name = "" if mine else f"<div class='name'>{esc(typing_from)}</div>"
        out.append(f"<div class='row {'me' if mine else 'other'}'>{name}<div class='b typing'><i></i><i></i><i></i></div></div>")
    return "".join(out)


def chat_html(t, spec, msgs, typing_from=None, w=1080, h=1920, card=False):
    bottom = 120 if card else 340
    right = 72 if card else 150
    when = f"<div class='when'>{esc(spec.get('when'))}</div>" if spec.get("when") else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:{w}px;height:{h}px;background:{t['bg']};font-family:{FONT};position:relative;overflow:hidden}}
    .head{{position:absolute;left:0;right:0;top:0;height:{200 if card else 250}px;background:{t['head']};color:{t['headfg']};
      display:flex;flex-direction:column;justify-content:flex-end;padding:0 72px 28px}}
    .room{{font-size:46px;font-weight:700}}
    .fic{{font-size:26px;opacity:.75;margin-top:6px}}
    .when{{position:absolute;left:0;right:0;top:{230 if card else 290}px;text-align:center;font-size:32px;color:{t['sub']};font-weight:500}}
    .area{{position:absolute;left:72px;right:{right}px;top:{300 if card else 370}px;bottom:{bottom}px;display:flex;flex-direction:column;justify-content:flex-end;gap:22px;overflow:hidden}}
    .row{{display:flex;flex-direction:column;max-width:82%}}
    .row.other{{align-self:flex-start;align-items:flex-start}}
    .row.me{{align-self:flex-end;align-items:flex-end}}
    .name{{font-size:28px;color:{t['sub']};margin:0 0 8px 6px;font-weight:500}}
    .b{{font-size:44px;line-height:1.42;padding:24px 30px;border-radius:30px;word-break:keep-all}}
    .other .b{{background:{t['other']};color:{t['otherfg']};border-top-left-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.06)}}
    .me .b{{background:{t['me']};color:{t['mefg']};border-top-right-radius:8px}}
    .note{{align-self:center;font-size:30px;color:{t['sub']};padding:8px 24px;border-radius:999px;border:2px solid {t['sub']};opacity:.85}}
    .typing{{display:flex;gap:12px;align-items:center;height:110px}}
    .typing i{{width:16px;height:16px;border-radius:50%;background:currentColor;opacity:.5;display:block}}
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


def shoot(pages, size):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": size[0], "height": size[1]})
        for html_text, path in pages:
            p.set_content(html_text)
            p.wait_for_timeout(120)
            p.screenshot(path=str(path))
        b.close()


def main():
    spec_path = Path(sys.argv[1])
    out = Path(sys.argv[2])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    t = THEMES[spec.get("theme", "b2b")]
    msgs = spec["messages"]
    work = Path(tempfile.mkdtemp(prefix="chat_"))

    frames = []  # (html, seconds)
    shown = []
    frames.append((chat_html(t, spec, []), 0.3))
    for m in msgs:
        if m.get("note"):
            shown.append(m)
            frames.append((chat_html(t, spec, shown), 1.2 + float(m.get("pause", 0))))
            continue
        frames.append((chat_html(t, spec, shown, typing_from=m.get("from")), 0.4))
        shown.append(m)
        frames.append((chat_html(t, spec, shown), 0.9 + 0.05 * len(m.get("text", "")) + float(m.get("pause", 0))))
    end = spec.get("end")
    if end:
        frames.append((end_html(t, end), float(end.get("dur", 3.4))))
    total = sum(d for _, d in frames)
    if total > 60:
        sys.exit(f"길이 {total:.1f}초. 60초를 넘는다.")

    pngs = [(h, work / f"f{i:03d}.png") for i, (h, _) in enumerate(frames)]
    shoot(pngs, (1080, 1920))
    concat = work / "list.txt"
    with open(concat, "w") as f:
        for (h, p), (_, d) in zip(pngs, frames):
            f.write(f"file '{p}'\nduration {d:.3f}\n")
        f.write(f"file '{pngs[-1][1]}'\n")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat)]
    if spec.get("music", True):
        pad = work / "pad.wav"
        make_pad(total + 0.5, pad, seed=spec.get("seed", 11))
        cmd += ["-i", str(pad), "-c:a", "aac", "-b:a", "96k", "-shortest"]
    cmd += ["-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
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
