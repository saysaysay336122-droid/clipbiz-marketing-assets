"""휴대폰 화면을 녹화한 것처럼 보이는 짧은 상황극(1080x1920). 효과음과 음악 끊기까지 넣는다.

사용법: python3 tools/render_skit.py <spec.json> <출력 mp4>

종류(mode)
  search : 최근 검색어가 하나씩 쌓이고, 검색창에 글자를 치다가 알림이 내려오며 반전.
  tier   : 티어표(S, A, B, C, F)에 물건을 하나씩 매기다가 맨 위에 새 칸이 생기며 반전.

공통 spec
  theme       끝 화면 색(b2b, hcs, hic). render_chat.THEMES
  hook        처음 HOOK_SEC초 동안 겹쳐 두는 큰 글씨 띠(두 줄 이하). 첫 검색어나 첫 물건은 0초에 이미 화면에 있다
              (2026-11-02 대표 승인: 빈 화면에 제목만 1.5초 세우지 않는다)
  cont        반전 뒤 '다음 화' 한 줄(선택)
  notify      [{"from": "팀장님", "text": "..."}] 반전 때 위에서 내려오는 알림(선택)
  end         {"title", "body", "foot"} 끝 화면
  music_style bright, playful, chill. seed로 곡을 바꾼다.

search spec: badge(화면 위 작은 빨간 표시, 반전의 단서), clock, history[{q, t}], typing{text, typo: [위치, 틀린 글자]}
tier spec  : title, tiers(["S","A","B","C","F"]), items[{img|draw, label, say, tier}], twist{tier, img, label, reveal, say}

원칙: 반전의 단서는 첫 화면부터 보이게 둔다(search의 badge, tier의 hook). 음악은 반전 0.45초 전에 끊고 효과음으로 친다.
등장인물은 가상 인물이라는 문구를 화면 아래에 작게 계속 둔다.
"""
import base64
import html
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from music import make_track  # noqa: E402
from render_chat import THEMES, end_html, shoot  # noqa: E402
import sfx  # noqa: E402

W, H = 1080, 1920
HOOK_SEC = 1.8
SHAKE = [(0, 0), (-10, 5), (8, -4), (0, 0)]
FONT = "'Noto Sans CJK KR', sans-serif"
ROOT = Path(__file__).resolve().parent.parent
TIER_COLORS = {"SSS": "#FFD54A", "S": "#FF7F7F", "A": "#FFBF7F", "B": "#FFDF7F", "C": "#FFFF7F", "D": "#BFFF7F", "F": "#7FBFFF"}


def esc(s):
    return html.escape(s or "").replace("\n", "<br>")


def img_uri(path, size=640):
    from PIL import Image
    import io
    p = Path(path)
    if not p.is_absolute():
        p = (Path.cwd() / p) if (Path.cwd() / p).exists() else ROOT / p
    if p.suffix == ".mp4":
        tmp = Path(tempfile.mkdtemp()) / "f.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "2", "-i", str(p), "-frames:v", "1", str(tmp)], check=True)
        p = tmp
    im = Image.open(p).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width - s) // 2 + s, (im.height - s) // 2 + s)).resize((size, size))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


BASE_CSS = f"""*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;font-family:{FONT};position:relative;overflow:hidden}}
.stage{{position:absolute;inset:0;transform-origin:50% 22%}}
.status{{position:absolute;left:0;right:0;top:0;height:86px;display:flex;align-items:center;justify-content:space-between;padding:0 54px;font-size:32px;font-weight:700}}
.icons{{display:flex;gap:14px;align-items:center}}
.bars{{display:flex;gap:4px;align-items:flex-end;height:26px}}.bars i{{display:block;width:7px;background:currentColor;border-radius:2px}}
.batt{{width:52px;height:26px;border:3px solid currentColor;border-radius:7px;position:relative;padding:3px}}.batt i{{display:block;height:100%;width:62%;background:currentColor;border-radius:2px}}
.fic{{position:absolute;left:0;right:0;bottom:250px;text-align:center;font-size:24px;opacity:.55}}
.hook{{position:absolute;left:60px;right:150px;top:1060px;text-align:center;z-index:40}}
.hook span{{display:inline;background:#111;color:#FFF;font-size:64px;font-weight:900;line-height:1.5;padding:4px 22px;border-radius:14px;letter-spacing:-1.2px;
  -webkit-box-decoration-break:clone;box-decoration-break:clone}}
.dim{{position:absolute;inset:0;background:rgba(0,0,0,.45)}}
.cont{{position:absolute;left:80px;right:80px;top:880px;text-align:center}}
.cont span{{background:#FFF;color:#111;font-size:56px;font-weight:900;padding:10px 30px;border-radius:14px;line-height:1.6;
  -webkit-box-decoration-break:clone;box-decoration-break:clone}}
.ban{{position:absolute;left:28px;right:28px;height:176px;background:rgba(250,250,252,.98);border-radius:40px;box-shadow:0 14px 40px rgba(0,0,0,.28);
  display:flex;align-items:center;gap:26px;padding:0 34px;color:#111}}
.app{{flex:0 0 92px;height:92px;border-radius:24px;background:#3A4250;position:relative}}
.app:after{{content:'';position:absolute;left:22px;top:24px;width:48px;height:38px;background:#FFF;border-radius:18px}}
.ban .who{{font-size:32px;font-weight:700;display:flex;justify-content:space-between;width:100%}}.ban .who em{{font-style:normal;font-weight:400;opacity:.5;font-size:28px}}
.ban .txt{{font-size:40px;margin-top:6px;letter-spacing:-0.5px}}
.ban .col{{flex:1;min-width:0}}
"""


def status_html(clock, color="#111"):
    bars = "".join(f"<i style='height:{h}px'></i>" for h in (8, 13, 18, 24))
    return (f"<div class='status' style='color:{color}'><div>{esc(clock)}</div>"
            f"<div class='icons'><div class='bars'>{bars}</div><div class='batt'><i></i></div></div></div>")


def banners_html(notes, shown, slide_y=None):
    out = []
    for k in range(shown):
        n = notes[k]
        target = 30 + k * 196
        y = target if (k < shown - 1 or slide_y is None) else target + (slide_y - 30)
        out.append(f"<div class='ban' style='top:{y}px;z-index:{10 + k}'><div class='app'></div>"
                   f"<div class='col'><div class='who'>{esc(n['from'])}<em>지금</em></div><div class='txt'>{esc(n['text'])}</div></div></div>")
    return "".join(out)


# ---------------- search ----------------
SEARCH_CSS = BASE_CSS + """
body{background:#FFFFFF;color:#111}
.badge{position:absolute;left:54px;top:100px;display:flex;align-items:center;gap:12px;font-size:32px;color:#C62828;font-weight:700}
.badge i{width:20px;height:20px;border-radius:50%;background:#E53935;display:block}
.badge em{font-style:normal;font-weight:400;color:#777}
.box{position:absolute;left:36px;right:36px;top:170px;height:150px;border:5px solid #222;border-radius:75px;display:flex;align-items:center;padding:0 42px;gap:28px}
.mag{width:52px;height:52px;border:7px solid #222;border-radius:50%;position:relative;flex:0 0 52px}
.mag:after{content:'';position:absolute;width:7px;height:26px;background:#222;right:-14px;bottom:-19px;transform:rotate(-45deg);border-radius:3px}
.q{font-size:54px;letter-spacing:-0.8px;white-space:nowrap;overflow:hidden;flex:1;display:flex;min-width:0}
.q.tail{justify-content:flex-end}
.q.ph{color:#9AA0A6}
.caret{display:inline-block;width:4px;height:50px;background:#1A73E8;vertical-align:-8px;margin-left:3px}
.sec{position:absolute;left:58px;right:58px;top:372px;display:flex;justify-content:space-between;font-size:36px}
.sec b{font-weight:700}.sec span{color:#9AA0A6}
.list{position:absolute;left:24px;right:24px;top:450px}
.row{display:flex;align-items:center;gap:26px;min-height:142px;padding:16px 28px;border-bottom:2px solid #F1F3F4;border-radius:18px}
.row.new{background:#FFF4C2}
.clk{flex:0 0 46px;height:46px;border:5px solid #9AA0A6;border-radius:50%;position:relative}
.clk:before{content:'';position:absolute;left:16px;top:6px;width:5px;height:14px;background:#9AA0A6}
.clk:after{content:'';position:absolute;left:16px;top:17px;width:12px;height:5px;background:#9AA0A6}
.row .t{flex:1;font-size:52px;line-height:1.3;letter-spacing:-1px;word-break:keep-all}
.row .tm{font-size:30px;color:#9AA0A6;white-space:nowrap}.row .x{font-size:40px;color:#BDC1C6;margin-left:4px}
"""


def search_page(spec, rows, newest=False, typed=None, hook=False, notes_shown=0, slide_y=None, zoom=1.0, dim=False, cont=False, shake=(0, 0)):
    items = []
    for k, r in enumerate(rows):
        items.append(f"<div class='row{' new' if newest and k == 0 else ''}'><div class='clk'></div><div class='t'>{esc(r['q'])}</div>"
                     f"<div class='tm'>{esc(r.get('t', ''))}</div><div class='x'>×</div></div>")
    if typed is None:
        q = "<div class='q ph'>검색어를 입력하세요</div>"
    else:
        q = f"<div class='q{' tail' if len(typed) > 13 else ''}'><span style='white-space:nowrap'>{esc(typed)}<span class='caret'></span></span></div>"
    badge = ""
    if spec.get("badge"):
        badge = f"<div class='badge'><i></i>{esc(spec['badge'])}<em>{esc(spec.get('badge_sub', ''))}</em></div>"
    hook_html = ""
    if hook:
        lines = [ln for ln in spec["hook"].split("\n") if ln.strip()]
        hook_html = f"<div class='hook' style='transform:translate({shake[0]}px,{shake[1]}px)'>" + "<br>".join(f"<span>{esc(ln)}</span>" for ln in lines) + "</div>"
    over = ""
    if dim:
        over += "<div class='dim'></div>"
    if cont and spec.get("cont"):
        over += f"<div class='cont'><span>{esc(spec['cont'])}</span></div>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{SEARCH_CSS}</style></head><body>
    <div class='stage' style='transform:scale({zoom})'>{status_html(spec.get('clock', '오후 11:41'))}{badge}
    <div class='box'><div class='mag'></div>{q}</div>
    <div class='sec'><b>최근 검색어</b><span>전체 삭제</span></div>
    <div class='list'>{''.join(items)}</div></div>
    <div class='fic'>등장인물은 가상 인물입니다</div>{hook_html}{over}{banners_html(spec.get('notify', []), notes_shown, slide_y)}</body></html>"""


def build_search(spec, rnd):
    frames, events, cuts = [], [], []
    t = 0.0

    def add(h, d, ev=()):
        nonlocal t
        frames.append((h, d))
        for off, name, g in ev:
            events.append((t + off, name, g))
        t += d

    # 훅: 첫 검색어가 이미 있는 화면 위에 큰 글씨 띠, 살짝 흔들림. 띠는 HOOK_SEC초까지 겹쳐 둔다
    hist = spec["history"]
    rows = [hist[0]]
    d0 = 0.62 + 0.032 * len(hist[0]["q"])
    for k, sh in enumerate(SHAKE):
        add(search_page(spec, rows, newest=True, hook=True, shake=sh), 0.05 if k < 3 else d0,
            [(0, "whoosh", 0.9), (0, "pop", 0.7)] if k == 0 else [])
    for r in hist[1:]:
        rows.insert(0, r)
        d = 0.62 + 0.032 * len(r["q"])
        add(search_page(spec, rows, newest=True, hook=t < HOOK_SEC), d * 0.55, [(0, "pop", 0.7)])
        add(search_page(spec, rows, hook=t < HOOK_SEC), d * 0.45)
    # 타이핑
    ty = spec.get("typing", {})
    text = ty.get("text", "")
    typo = ty.get("typo")
    seq = []
    for i in range(1, len(text) + 1):
        if typo and i - 1 == typo[0]:
            seq.append((text[:i - 1] + typo[1], rnd.uniform(0.09, 0.13)))
            seq.append((text[:i - 1] + typo[1], 0.28))
            seq.append((text[:i - 1], 0.12))
        seq.append((text[:i], rnd.uniform(0.07, 0.12) if text[i - 1] != " " else 0.05))
    add(search_page(spec, rows, typed=""), 0.35)
    for s, d in seq:
        add(search_page(spec, rows, typed=s), d, [(0, "click", 0.8)])
    # 반전: 음악 끊고, 정적, 알림
    notes = spec.get("notify", [])
    cut_start = t
    events.append((t, "scratch", 0.7))
    add(search_page(spec, rows, typed=text), 0.45)
    for k in range(len(notes)):
        add(search_page(spec, rows, typed=text, notes_shown=k + 1, slide_y=-220), 0.04, [(0, "ding", 1.0)])
        add(search_page(spec, rows, typed=text, notes_shown=k + 1, slide_y=-60), 0.04)
        if k == 0:
            add(search_page(spec, rows, typed=text, notes_shown=1), 0.55)
            add(search_page(spec, rows, typed=text, notes_shown=1, zoom=1.06), 0.06, [(0, "boom", 0.9)])
            add(search_page(spec, rows, typed=text, notes_shown=1, zoom=1.1), 1.25)
        else:
            add(search_page(spec, rows, typed=text, notes_shown=k + 1, zoom=1.1), 1.6)
    cuts.append((cut_start, t))
    if spec.get("cont"):
        add(search_page(spec, rows, typed=text, notes_shown=len(notes), zoom=1.1, dim=True, cont=True), 1.5, [(0, "whoosh", 0.6)])
    return frames, events, cuts, t


# ---------------- tier ----------------
TIER_CSS = BASE_CSS + """
body{background:#141518;color:#F5F5F5}
.ttl{position:absolute;left:0;right:0;top:110px;text-align:center;font-size:46px;font-weight:900;letter-spacing:-1px}
.board{position:absolute;left:30px;right:30px;top:200px;display:flex;flex-direction:column;gap:6px}
.trow{display:flex;height:168px;background:#22242A;border-radius:10px;overflow:hidden}
.tl{flex:0 0 150px;display:flex;align-items:center;justify-content:center;font-size:66px;font-weight:900;color:#111}
.ti{display:flex;gap:8px;align-items:center;padding:0 10px}
.th{width:150px;height:150px;border-radius:8px;overflow:hidden;position:relative;background:#333}
.th img,.card img{width:100%;height:100%;object-fit:cover;display:block}
.th b{position:absolute;left:0;right:0;bottom:0;font-size:20px;padding:4px 6px;background:linear-gradient(transparent,rgba(0,0,0,.85));font-weight:700;line-height:1.2}
.shade{position:absolute;inset:0;background:rgba(0,0,0,.55)}
.card{position:absolute;left:50%;width:600px;transform-origin:50% 50%}
.card .im{width:600px;height:600px;border-radius:26px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.5);background:#333}
.card .lb{margin-top:26px;text-align:center}
.card .lb span{background:#FFF;color:#111;font-size:54px;font-weight:900;padding:6px 24px;border-radius:14px;line-height:1.6;letter-spacing:-1px;
  -webkit-box-decoration-break:clone;box-decoration-break:clone}
.card .say{margin-top:22px;text-align:center;font-size:40px;font-weight:700;color:#FFE27A}
.cal{width:100%;height:100%;background:#FAFAF7;color:#222;display:flex;flex-direction:column;align-items:center;justify-content:center}
.cal .y{font-size:120px;font-weight:900;color:#C62828;line-height:1}.cal .m{font-size:90px;font-weight:900}.cal .g{font-size:30px;color:#888;margin-top:16px}
.th .cal .y{font-size:34px}.th .cal .m{font-size:28px}.th .cal .g{display:none}
"""


def item_visual(it, cache):
    if it.get("draw") == "calendar":
        y, m = it.get("draw_text", "2016\n3월").split("\n")
        return f"<div class='cal'><div class='y'>{esc(y)}</div><div class='m'>{esc(m)}</div><div class='g'>여기서 멈춤</div></div>"
    key = it["img"]
    if key not in cache:
        cache[key] = img_uri(key)
    return f"<img src='{cache[key]}'>"


def tier_page(spec, tiers, placed, cache, card=None, card_pos=None, hook=False, shake=(0, 0), notes_shown=0, slide_y=None, dim=False, cont=False, flash=None):
    rows = []
    for tr in tiers:
        ths = "".join(f"<div class='th'>{item_visual(it, cache)}<b>{esc(it.get('short', it['label'].split(chr(10))[0]))}</b></div>"
                      for it in placed.get(tr, []))
        hl = "outline:6px solid #FFF;" if flash == tr else ""
        rows.append(f"<div class='trow' style='{hl}'><div class='tl' style='background:{TIER_COLORS.get(tr, '#CCC')}'>{esc(tr)}</div><div class='ti'>{ths}</div></div>")
    card_html = ""
    if card is not None:
        x, y, s = card_pos or (0, 620, 1.0)
        say = f"<div class='say'>{esc(card.get('say_now'))}</div>" if card.get("say_now") else ""
        lab = "<br>".join(f"<span>{esc(ln)}</span>" for ln in card["label"].split("\n"))
        card_html = (f"<div class='shade'></div><div class='card' style='top:{y}px;transform:translateX(calc(-50% + {x}px)) scale({s})'>"
                     f"<div class='im'>{item_visual(card, cache)}</div><div class='lb'>{lab}</div>{say}</div>")
    hook_html = ""
    if hook:
        lines = [ln for ln in spec["hook"].split("\n") if ln.strip()]
        hook_html = (f"<div class='hook' style='top:215px;transform:translate({shake[0]}px,{shake[1]}px)'>"
                     + "<br>".join(f"<span style='background:#FFF;color:#111'>{esc(ln)}</span>" for ln in lines) + "</div>")
    over = "<div class='dim'></div>" if dim else ""
    if cont and spec.get("cont"):
        over += f"<div class='cont'><span>{esc(spec['cont'])}</span></div>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{TIER_CSS}</style></head><body>
    <div class='stage'>{status_html(spec.get('clock', '오후 3:12'), '#EEE')}<div class='ttl'>{esc(spec.get('title', '티어표'))}</div>
    <div class='board'>{''.join(rows)}</div></div>{card_html}{hook_html}
    <div class='fic' style='color:#DDD'>등장인물은 가상 인물입니다</div>{over}{banners_html(spec.get('notify', []), notes_shown, slide_y)}</body></html>"""


def build_tier(spec, rnd):
    frames, events, cuts = [], [], []
    t = 0.0
    cache = {}

    def add(h, d, ev=()):
        nonlocal t
        frames.append((h, d))
        for off, name, g in ev:
            events.append((t + off, name, g))
        t += d

    tiers = list(spec.get("tiers", ["S", "A", "B", "C", "F"]))
    placed = {k: [] for k in tiers}
    def hk():
        return t < HOOK_SEC

    def present(it, tiers_now, extra_wait=0.0, label=None, say=None, fx_in="whoosh", opening=False):
        c = dict(it)
        if label:
            c["label"] = label
        hold = 0.55 + 0.03 * len(c["label"]) + extra_wait
        if opening:
            # 첫 물건은 0초에 이미 카드로 떠 있고, hook 띠가 비어 있는 위쪽 칸 위에 겹친다
            for k, sh in enumerate(SHAKE):
                add(tier_page(spec, tiers_now, placed, cache, card=c, card_pos=(0, 640, 1.0), hook=True, shake=sh),
                    0.05 if k < 3 else hold, [(0, "whoosh", 0.9)] if k == 0 else [])
        else:
            add(tier_page(spec, tiers_now, placed, cache, card=c, card_pos=(0, 760, 0.6), hook=hk()), 0.05, [(0, fx_in, 0.7)])
            add(tier_page(spec, tiers_now, placed, cache, card=c, card_pos=(0, 640, 1.0), hook=hk()), hold)
        if say:
            c["say_now"] = say
            add(tier_page(spec, tiers_now, placed, cache, card=c, card_pos=(0, 640, 1.0), hook=hk()), 0.7 + 0.04 * len(say))
        return c

    def place(it, tiers_now):
        tr = it["tier"]
        idx = tiers_now.index(tr)
        ty = 200 + idx * 174 - 140
        add(tier_page(spec, tiers_now, placed, cache, card=dict(it, say_now=None), card_pos=(-260, ty, 0.3), hook=hk()), 0.06)
        placed.setdefault(tr, []).append(it)
        add(tier_page(spec, tiers_now, placed, cache, flash=tr, hook=hk()), 0.12, [(0, "thunk", 1.0)])
        add(tier_page(spec, tiers_now, placed, cache, hook=hk()), 0.25)

    for n, it in enumerate(spec["items"]):
        present(it, tiers, say=it.get("say"), opening=(n == 0))
        place(it, tiers)

    tw = spec.get("twist")
    if tw:
        cut_start = t
        events.append((t, "scratch", 0.7))
        new_tiers = [tw["tier"]] + tiers
        placed.setdefault(tw["tier"], [])
        add(tier_page(spec, tiers, placed, cache), 0.4)
        add(tier_page(spec, new_tiers, placed, cache, flash=tw["tier"]), 0.5, [(0, "boom", 0.9)])
        present(tw, new_tiers, label=tw["label"], fx_in="whoosh")
        add(tier_page(spec, new_tiers, placed, cache, card=dict(tw, label=tw["reveal"]), card_pos=(0, 640, 1.04)), 0.06, [(0, "boom", 0.8)])
        add(tier_page(spec, new_tiers, placed, cache, card=dict(tw, label=tw["reveal"]), card_pos=(0, 640, 1.0)), 1.1)
        place(dict(tw, label=tw["reveal"], short=tw.get("short", tw["reveal"])), new_tiers)
        tiers = new_tiers
        notes = spec.get("notify", [])
        for k in range(len(notes)):
            add(tier_page(spec, tiers, placed, cache, notes_shown=k + 1, slide_y=-220), 0.04, [(0, "ding", 1.0)])
            add(tier_page(spec, tiers, placed, cache, notes_shown=k + 1, slide_y=-60), 0.04)
            add(tier_page(spec, tiers, placed, cache, notes_shown=k + 1), 1.3 + 0.03 * len(notes[k]["text"]))
        cuts.append((cut_start, t))
        if spec.get("cont"):
            add(tier_page(spec, tiers, placed, cache, notes_shown=len(notes), dim=True, cont=True), 1.5, [(0, "whoosh", 0.6)])
    return frames, events, cuts, t


def main():
    spec_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    rnd = random.Random(spec.get("seed", 7))
    mode = spec.get("mode", "search")
    frames, events, cuts, t = (build_search if mode == "search" else build_tier)(spec, rnd)
    theme = THEMES[spec.get("theme", "b2b")]
    if spec.get("end"):
        frames.append((end_html(theme, spec["end"]), float(spec["end"].get("dur", 3.4))))
        events.append((t, "whoosh", 0.5))
        t += float(spec["end"].get("dur", 3.4))
    if t > 60:
        sys.exit(f"길이 {t:.1f}초. 60초를 넘는다.")
    work = Path(tempfile.mkdtemp(prefix="skit_"))
    pngs = [(h, work / f"f{i:04d}.png") for i, (h, _) in enumerate(frames)]
    shoot(pngs, (W, H))
    lst = work / "list.txt"
    with open(lst, "w") as f:
        for (h, p), (_, d) in zip(pngs, frames):
            f.write(f"file '{p}'\nduration {d:.3f}\n")
        f.write(f"file '{pngs[-1][1]}'\n")
    music = work / "music.wav"
    make_track(t + 0.5, music, style=spec.get("music_style", "bright"), seed=spec.get("seed", 7))
    audio = work / "mix.wav"
    sfx.mix(t, audio, music=music, music_gain=spec.get("music_gain", 0.45), events=events, cuts=cuts, seed=spec.get("seed", 7))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio),
           "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-t", f"{t:.3f}", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr[-2000:])
    print(f"{out} {t:.1f}s 프레임 {len(frames)}")


if __name__ == "__main__":
    main()
