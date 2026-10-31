"""한 주 게시물을 휴대폰에서 훑어볼 수 있는 미리보기 페이지(아티팩트용 HTML)를 만든다.

사용법: python3 tools/make_preview.py <posts.json> <출력 html>
posts.json 형식(목록)
  {"id": "MK-261109-22", "when": "2026-11-09T21:10", "brand": "홍책사"|"하이클립"|"클립비즈",
   "channel": "인스타그램"|"릴스"|"유튜브 쇼츠"|"스레드", "status": "자동 예약"|"승인 대기"|"승인 예약",
   "title": "(쇼츠 제목, 선택)", "text": "본문", "files": ["w/261109/MK-261109-22_1.png", ...],
   "video_url": "(영상 원본 주소, 선택)"}
이미지는 폭 320px JPEG로 줄여 페이지 안에 넣는다(아티팩트는 외부 이미지를 못 불러온다). 영상은 첫 장면을 넣고 원본 주소로 연결한다.
"""
import base64
import html
import io
import json
import subprocess
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DAYS = "월화수목금토일"
BRAND = {"홍책사": "hcs", "하이클립": "hic", "클립비즈": "b2b"}


def thumb(path, width=320):
    p = ROOT / path
    if p.suffix == ".mp4":
        tmp = Path(tempfile.mkdtemp()) / "f.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1.2", "-i", str(p), "-frames:v", "1", str(tmp)], check=True)
        p = tmp
    im = Image.open(p).convert("RGB")
    im = im.resize((width, int(im.height * width / im.width)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def esc(s):
    return html.escape(s or "")


def main():
    posts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    posts.sort(key=lambda p: (p["when"], p["brand"]))
    days = OrderedDict()
    for p in posts:
        d = datetime.fromisoformat(p["when"])
        days.setdefault(d.date(), []).append((d, p))
    first, last = min(days), max(days)
    counts = OrderedDict()
    for p in posts:
        counts[p["brand"]] = counts.get(p["brand"], 0) + 1
    waiting = [p for p in posts if p["status"] == "승인 대기"]

    secs = []
    for day, items in days.items():
        rows = []
        for d, p in items:
            media = ""
            if p.get("files"):
                imgs = []
                for f in p["files"]:
                    alt = "영상 첫 장면" if f.endswith(".mp4") else "카드"
                    imgs.append(f'<img src="{thumb(f)}" alt="{alt}" loading="lazy">')
                strip = "".join(imgs)
                if p.get("video_url"):
                    strip += f'<a class="play" href="{esc(p["video_url"])}" target="_blank" rel="noopener">영상 열기</a>'
                media = f'<div class="strip">{strip}</div>'
            title = f'<p class="yt">{esc(p["title"])}</p>' if p.get("title") else ""
            pid = p.get("id") or ""
            pick = (f'<label class="pick"><input type="checkbox" id="x-{esc(pid)}" data-id="{esc(pid)}"> 빼기</label>'
                    if pid else "")
            st = {"자동 예약": "auto", "승인 대기": "wait", "승인 예약": "ok"}.get(p["status"], "auto")
            rows.append(f"""
      <article class="post {BRAND.get(p['brand'], 'b2b')}">
        <div class="time">{d:%H:%M}</div>
        <div class="body">
          <header><span class="brand">{esc(p['brand'])}</span><span class="ch">{esc(p['channel'])}</span>
            <span class="st {st}">{esc(p['status'])}</span><span class="pid">{esc(pid)}</span>{pick}</header>
          {title}{media}
          <details><summary>{esc(p['text'].splitlines()[0] if p['text'] else '')}</summary><pre>{esc(p['text'])}</pre></details>
        </div>
      </article>""")
        secs.append(f'<section><h2>{day.month}월 {day.day}일 {DAYS[day.weekday()]}요일</h2>{"".join(rows)}</section>')

    summary = ", ".join(f"{k} {v}건" for k, v in counts.items())
    wait_line = (f'<p class="note">승인 대기 {len(waiting)}건은 승인해야 올라갑니다.</p>' if waiting else "")
    page = f"""<title>주간 게시 미리보기</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@500;600&family=Noto+Sans+KR:wght@400;500&family=IBM+Plex+Mono:wght@500&display=swap">
<style>
/* 날짜별 세로 타임라인. 왼쪽 시각, 오른쪽 게시물. 휴대폰 한 손 스크롤 기준 */
:root {{
  --bg:#F3F4F2; --panel:#FFFFFF; --fg:#18222C; --sub:#5A6672; --line:#DCE0E3;
  --navy:#17395E; --hcs:#2E4A3F; --hic:#C64016; --wait:#B26B00; --ok:#1F6F4A;
  --f-head:"IBM Plex Sans KR","Noto Sans KR",system-ui,sans-serif; --f-body:"Noto Sans KR",system-ui,sans-serif; --f-num:"IBM Plex Mono",ui-monospace,monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#12171C; --panel:#1B232B; --fg:#E8ECEF; --sub:#9AA6B1; --line:#2C3741;
  --navy:#8DB3DA; --hcs:#8FC2AC; --hic:#F08A63; --wait:#E3A63B; --ok:#6CC79C; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#12171C; --panel:#1B232B; --fg:#E8ECEF; --sub:#9AA6B1; --line:#2C3741;
  --navy:#8DB3DA; --hcs:#8FC2AC; --hic:#F08A63; --wait:#E3A63B; --ok:#6CC79C; color-scheme:dark }}
body {{ background:var(--bg); color:var(--fg); font-family:var(--f-body); line-height:1.55;
  padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); padding-block:20px 96px }}
.wrap {{ max-width:760px; margin:0 auto; display:flex; flex-direction:column; gap:24px }}
h1 {{ font-family:var(--f-head); font-weight:600; font-size:1.45rem; margin:0; text-wrap:balance }}
.lead {{ color:var(--sub); margin:6px 0 0 }}
.note {{ margin:8px 0 0; color:var(--wait); font-weight:500 }}
.how {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 14px; font-size:.92rem; color:var(--sub) }}
.how b {{ color:var(--fg) }}
section {{ display:flex; flex-direction:column; gap:10px }}
h2 {{ font-family:var(--f-head); font-weight:600; font-size:1.02rem; margin:0; padding-bottom:6px; border-bottom:1px solid var(--line) }}
.post {{ display:grid; grid-template-columns:52px minmax(0,1fr); gap:10px }}
.time {{ font-family:var(--f-num); font-variant-numeric:tabular-nums; color:var(--sub); padding-top:2px }}
.body {{ background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--navy); border-radius:8px; padding:10px 12px; display:flex; flex-direction:column; gap:8px; min-width:0 }}
.post.hcs .body {{ border-left-color:var(--hcs) }} .post.hic .body {{ border-left-color:var(--hic) }}
header {{ display:flex; flex-wrap:wrap; align-items:center; gap:6px 10px; font-size:.86rem }}
.brand {{ font-weight:600 }} .ch {{ color:var(--sub) }} .pid {{ font-family:var(--f-num); font-size:.78rem; color:var(--sub) }}
.st {{ font-size:.76rem; padding:1px 8px; border-radius:999px; border:1px solid currentColor }}
.st.auto {{ color:var(--navy) }} .st.wait {{ color:var(--wait) }} .st.ok {{ color:var(--ok) }}
.pick {{ margin-left:auto; display:flex; align-items:center; gap:4px; color:var(--sub); cursor:pointer }}
.yt {{ margin:0; font-weight:500 }}
.strip {{ display:flex; gap:6px; overflow-x:auto; padding-bottom:2px }}
.strip img {{ width:132px; flex:0 0 auto; border-radius:4px; border:1px solid var(--line); max-width:100% }}
.play {{ align-self:center; flex:0 0 auto; padding:8px 12px; border:1px solid var(--line); border-radius:6px; color:var(--fg); text-decoration:none; font-size:.86rem }}
details summary {{ cursor:pointer; color:var(--fg); overflow:hidden; text-overflow:ellipsis }}
details pre {{ white-space:pre-wrap; font-family:var(--f-body); font-size:.9rem; margin:8px 0 0; color:var(--fg) }}
.bar {{ position:fixed; left:0; right:0; bottom:0; background:var(--panel); border-top:1px solid var(--line);
  padding:10px max(16px, env(safe-area-inset-right, 0px)) calc(10px + env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px));
  display:flex; gap:10px; align-items:center }}
.bar textarea {{ flex:1; min-width:0; height:40px; resize:none; font:inherit; font-size:.86rem; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:8px }}
.bar button {{ font:inherit; font-weight:500; padding:9px 14px; border-radius:6px; border:0; background:var(--navy); color:var(--panel); cursor:pointer }}
button:focus-visible, summary:focus-visible, input:focus-visible {{ outline:2px solid var(--navy); outline-offset:2px }}
</style>
<div class="wrap">
  <div>
    <h1>{first.month}월 {first.day}일 ~ {last.month}월 {last.day}일 게시 예정</h1>
    <p class="lead">모두 {len(posts)}건. {summary}.</p>{wait_line}
  </div>
  <div class="how"><b>빼고 싶은 글</b>은 오른쪽 '빼기'를 누르면 아래 칸에 요청 문장이 만들어집니다. 복사해서 Claude 예약 작업 화면에 답장으로 보내면 그 글만 예약에서 내립니다. 전부 멈추려면 '홍책사 멈춰' 또는 '하이클립 멈춰'라고 보내면 됩니다.</div>
  {''.join(secs)}
</div>
<div class="bar"><textarea id="req" readonly placeholder="빼기를 누르면 요청 문장이 여기에 생깁니다"></textarea><button id="copy" type="button">복사</button></div>
<script>
const req=document.getElementById('req');
function update(){{const ids=[...document.querySelectorAll('.pick input:checked')].map(e=>e.dataset.id);req.value=ids.length?ids.join(', ')+' 빼 주세요':'';}}
document.querySelectorAll('.pick input').forEach(e=>e.addEventListener('change',update));
document.getElementById('copy').addEventListener('click',async()=>{{if(!req.value)return;try{{await navigator.clipboard.writeText(req.value);document.getElementById('copy').textContent='복사됨';setTimeout(()=>document.getElementById('copy').textContent='복사',1500);}}catch(e){{req.focus();req.select();}}}});
</script>
"""
    out.write_text(page, encoding="utf-8")
    print(out, f"{out.stat().st_size // 1024}KB", len(posts), "건")


if __name__ == "__main__":
    main()
