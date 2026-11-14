"""네이버 블로그 붙여넣기 묶음 만들기.

사용법: python3 tools/naver_pack.py 원고.json 출력폴더
출력: 출력폴더/img/*.jpg(글마다 고유 이미지), 출력폴더/네이버원고.html(붙여넣기 페이지)

원고.json 형식:
{"title": "11월 네이버 원고", "posts": [
  {"id": "NB-261105", "when": "2026년 11월 5일(목) 오전 8시 40분", "category": "연계고용 감면제도",
   "title": "제목", "tags": ["태그", ...],
   "blocks": [
     {"p": "문단. **굵게** 가능, [링크 글](https://...) 가능"},
     {"h": "질문형 소제목"},
     {"table": [["머리1", "머리2"], ["값", "값"]]},
     {"ol": ["순서 1", "순서 2"]},
     {"img": {"kind": "cover|rows|steps|formula", ...}, "alt": "대체 텍스트", "cap": "사진 아래 한 줄"}
   ]}
]}
이미지 kind:
  cover   {"kicker", "title"}                       제목 카드
  rows    {"kicker", "title", "rows": [[왼쪽, 오른쪽], ...]}   두 칸 표 카드
  steps   {"kicker", "title", "steps": ["...", ...]}  번호 순서 카드
  formula {"kicker", "title", "lines": ["식", ...], "note": "설명"}  산식 카드
이미지는 1080x1080 JPEG. 미리보기에는 data URI로 넣고, spec에 img_base(공개 https 주소)가 있으면 본문 복사 때 그 주소의 사진을 함께 담는다.
네이버가 붙여넣기 HTML의 data URI 사진은 받지 않는다(2026-11-04 확인). https 사진이 들어오지 않으면 사진 n 복사 버튼으로 붙인다.
글마다 theme(b2b 기본, hic 하이클립)를 줄 수 있다. cover에는 big(큰 숫자나 날짜 한 줄)을 줄 수 있다.
글자는 직접 만든 카드뿐이다. 로고, 주소 워터마크, 사진 소재를 쓰지 않는다.
"""
import base64
import html
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

NAVY, ORANGE, INK, PAPER, SUB = "#17395E", "#E8590C", "#14202E", "#F6F4EF", "#5A6878"
FONT = "'Noto Sans CJK KR'"


def esc(s):
    return html.escape(s or "").replace("\n", "<br>")


THEMES = {
    # b2b: 클립비즈 계정 남색, hic: 하이클립 화면색(밝은 바탕)
    "b2b": dict(cbg=NAVY, cfg="#FFFFFF", csub="#C9D6E3", acc=ORANGE, bg=PAPER, ink=INK, sub=SUB, line="#CFCAC0", dot=NAVY),
    "hic": dict(cbg="#F5F6F3", cfg="#14202E", csub="#485868", acc="#C64016", bg="#FFFFFF", ink="#14202E", sub="#485868", line="#D9DDD6", dot="#14202E"),
}


def _title_px(title, big):
    longest = max(len(x) for x in title.split("\n"))
    if big:
        return 96 if longest <= 10 else 84 if longest <= 12 else 74
    return 128 if longest <= 7 else 112 if longest <= 9 else 98 if longest <= 11 else 86


def card_html(c, theme="b2b"):
    t = THEMES.get(theme, THEMES["b2b"])
    kind = c.get("kind", "cover")
    base = f"""*{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1080px;font-family:{FONT};word-break:keep-all;overflow:hidden;position:relative}}
    .k{{font-size:40px;font-weight:500;letter-spacing:1px}}
    .bar{{width:72px;height:10px;background:{t['acc']};margin:30px 0 40px}}
    .brand{{position:absolute;left:96px;bottom:70px;font-size:30px;font-weight:500;letter-spacing:1px}}"""
    if kind == "cover":
        big = c.get("big", "")
        bightml = f"<div class='big'>{esc(big)}</div>" if big else ""
        return f"""<html><head><meta charset='utf-8'><style>{base}
        body{{background:{t['cbg']};color:{t['cfg']}}}
        .w{{position:absolute;left:96px;right:80px;top:70px;bottom:150px;display:flex;flex-direction:column;justify-content:center}}
        .k,.brand{{color:{t['csub']}}}
        .big{{font-size:200px;line-height:1;font-weight:800;letter-spacing:-6px;color:{t['acc']};margin:-6px 0 34px}}
        .t{{font-size:{_title_px(c['title'], big)}px;line-height:1.2;font-weight:800;letter-spacing:-3px}}
        </style></head><body><div class='w'><div class='k'>{esc(c.get('kicker'))}</div><div class='bar'></div>
        {bightml}<div class='t'>{esc(c['title'])}</div></div><div class='brand'>클립비즈 실무 노트</div></body></html>"""
    head = f"<div class='k'>{esc(c.get('kicker'))}</div><div class='bar'></div><div class='t'>{esc(c['title'])}</div>"
    css = f"""{base}
    body{{background:{t['bg']};color:{t['ink']}}}
    .w{{position:absolute;left:90px;right:90px;top:70px;bottom:130px;display:flex;flex-direction:column;justify-content:center}}
    .k,.brand{{color:{t['sub']}}} .t{{font-size:66px;line-height:1.24;font-weight:800;letter-spacing:-1.5px;margin-bottom:46px}}
    .rows{{border-top:4px solid {t['ink']}}}
    .r{{display:flex;justify-content:space-between;align-items:baseline;gap:30px;padding:24px 4px;border-bottom:1.5px solid {t['line']};font-size:40px}}
    .r span:first-child{{color:{t['sub']};flex:0 0 46%}} .r span:last-child{{font-weight:700;text-align:right}}
    .s{{display:flex;gap:28px;align-items:flex-start;margin-bottom:30px;font-size:42px;line-height:1.4}}
    .n{{flex:0 0 66px;height:66px;border-radius:50%;background:{t['dot']};color:#fff;font-size:34px;font-weight:700;display:flex;align-items:center;justify-content:center;margin-top:-2px}}
    .f{{background:{'#fff' if theme == 'b2b' else '#F5F6F3'};border-left:12px solid {t['acc']};padding:34px 38px;font-size:44px;line-height:1.55;font-weight:700;margin-bottom:34px}}
    .note{{font-size:36px;line-height:1.5;color:{t['sub']}}}"""
    if kind == "rows":
        inner = "<div class='rows'>" + "".join(
            f"<div class='r'><span>{esc(a)}</span><span>{esc(b)}</span></div>" for a, b in c["rows"]) + "</div>"
    elif kind == "steps":
        inner = "".join(f"<div class='s'><div class='n'>{i}</div><div>{esc(x)}</div></div>"
                        for i, x in enumerate(c["steps"], 1))
    elif kind == "formula":
        inner = "<div class='f'>" + "<br>".join(esc(x) for x in c["lines"]) + "</div>"
        if c.get("note"):
            inner += f"<div class='note'>{esc(c['note'])}</div>"
    else:
        raise ValueError(kind)
    return f"<html><head><meta charset='utf-8'><style>{css}</style></head><body><div class='w'>{head}{inner}</div><div class='brand'>클립비즈 실무 노트</div></body></html>"


INLINE = re.compile(r"\*\*(.+?)\*\*|\[(.+?)\]\((https?://[^)\s]+)\)")


def inline(s):
    out, pos = [], 0
    for m in INLINE.finditer(s):
        out.append(html.escape(s[pos:m.start()]))
        if m.group(1):
            out.append(f"<b>{html.escape(m.group(1))}</b>")
        else:
            out.append(f"<a href='{html.escape(m.group(3))}'>{html.escape(m.group(2))}</a>")
        pos = m.end()
    out.append(html.escape(s[pos:]))
    return "".join(out)


def body_html(post, imgs):
    parts, k = [], 0
    for b in post["blocks"]:
        if "p" in b:
            parts.append(f"<p>{inline(b['p'])}</p>")
        elif "h" in b:
            parts.append(f"<p><br></p><p><b><span style='font-size:20px'>{inline(b['h'])}</span></b></p>")
        elif "ol" in b:
            parts.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in b["ol"]) + "</ol>")
        elif "table" in b:
            rows = b["table"]
            th = "".join(f"<td style='border:1px solid #999;padding:8px;background:#EEF1F5'><b>{inline(x)}</b></td>" for x in rows[0])
            tb = "".join("<tr>" + "".join(f"<td style='border:1px solid #999;padding:8px'>{inline(x)}</td>" for x in r) + "</tr>" for r in rows[1:])
            parts.append(f"<table style='border-collapse:collapse;width:100%'><tr>{th}</tr>{tb}</table>")
        elif "img" in b:
            data = imgs[k]
            k += 1
            remote = f" data-src='{html.escape(post['_img_base'])}{post['id']}_{k}.jpg'" if post.get('_img_base') else ''
            parts.append(f"<p class='imgp' style='text-align:center'><img src='data:image/jpeg;base64,{data}'{remote} alt='{html.escape(b['alt'])}' width='720'><br><button class='imgbtn' onclick=\"copyImg(this,'{post['_bid']}',{k - 1})\">사진 {k} 복사</button></p>")
            if b.get("cap"):
                parts.append(f"<p style='text-align:center'><span style='color:#777;font-size:13px'>{inline(b['cap'])}</span></p>")
    if post.get("tags"):
        parts.append("<p><br></p><p>" + html.escape(" ".join("#" + t for t in post["tags"])) + "</p>")
    return "\n".join(parts)


def plain_len(post):
    t = []
    for b in post["blocks"]:
        for key in ("p", "h"):
            if key in b:
                t.append(re.sub(r"\[(.+?)\]\(.+?\)", r"\1", b[key]).replace("**", ""))
        if "ol" in b:
            t += b["ol"]
        if "table" in b:
            t += [" ".join(r) for r in b["table"]]
    return len("".join(t).replace(" ", ""))


PAGE_CSS = """
:root{--paper:#fff;--paperink:#222;--bg:#F1F3F5;--card:#fff;--ink:#14202E;--sub:#5A6878;--line:#DDD8CC;--acc:#E8590C;--navy:#17395E}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#11161C;--card:#1A222B;--ink:#E9EDF1;--sub:#9AA7B4;--line:#2C3743;color-scheme:dark}}
:root[data-theme=dark]{--bg:#11161C;--card:#1A222B;--ink:#E9EDF1;--sub:#9AA7B4;--line:#2C3743;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:'Pretendard','Noto Sans KR','Apple SD Gothic Neo',sans-serif;line-height:1.6}
.top{max-width:860px;margin:0 auto;padding-block:28px 8px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}.top h1{font-size:22px;margin:0 0 6px}.top p{margin:4px 0;color:var(--sub);font-size:14px}
.how{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0 4px;font-size:14px}.how ol{margin:6px 0 0 18px;padding:0}
.nav{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.nav a{font-size:13px;padding:5px 9px;border:1px solid var(--line);border-radius:999px;color:var(--ink);text-decoration:none;background:var(--card)}
.nav a.done{opacity:.45;text-decoration:line-through}
section{max-width:860px;margin:18px auto;padding-block:0;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.box{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.meta{padding:14px 16px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.meta .n{font-weight:700;color:var(--acc)}.meta .w{font-weight:700}.meta .c{color:var(--sub);font-size:14px}
.btns{display:flex;flex-wrap:wrap;gap:8px;padding:12px 16px;border-bottom:1px solid var(--line)}
button{font:inherit;font-size:14px;padding:9px 14px;border-radius:8px;border:1px solid var(--navy);background:var(--navy);color:#fff;cursor:pointer}
button.o{background:transparent;color:var(--ink);border-color:var(--line)}button:focus-visible{outline:2px solid var(--acc);outline-offset:2px}button.ok{background:#2F7D4F;border-color:#2F7D4F}
.ttl{padding:12px 16px 0;font-size:19px;font-weight:700}
.post{padding:8px 16px 18px;background:var(--paper);color:var(--paperink);font-size:16px;min-width:0;overflow-x:auto}
.post img{max-width:100%;height:auto}.imgbtn{margin-top:6px;font-size:13px;padding:6px 12px}.post table{font-size:14px}.post a{color:#1a5fb4}
.tags{padding:10px 16px 14px;color:var(--sub);font-size:13px;border-top:1px solid var(--line)}
.dl{font-size:12px;color:var(--sub);padding:0 16px 14px;display:flex;flex-wrap:wrap;gap:6px 4px;align-items:center}.dl a{color:var(--sub);margin-right:12px;font-size:12px}button.s{font-size:12px;padding:5px 9px}
"""

PAGE_JS = """
function sel(el){const r=document.createRange();r.selectNodeContents(el);const s=getSelection();s.removeAllRanges();s.addRange(r);return s}
function flash(b,t){const o=b.dataset.l||b.textContent;b.dataset.l=o;b.textContent=t;b.classList.add('ok');setTimeout(()=>{b.textContent=o;b.classList.remove('ok')},1800)}
async function copyText(b,txt){try{await navigator.clipboard.writeText(txt);flash(b,'복사됨')}catch(e){const t=document.createElement('textarea');t.value=txt;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();flash(b,'복사됨')}}
async function copyBody(b,id){const src=document.getElementById(id);const el=src.cloneNode(true);el.removeAttribute('id');el.querySelectorAll('.imgp').forEach(x=>{const im=x.querySelector('img');const u=im&&im.dataset.src;if(u){const q=document.createElement('p');q.style.textAlign='center';const n=document.createElement('img');n.src=u;n.alt=im.alt;n.width=720;q.appendChild(n);x.replaceWith(q)}else{x.remove()}});el.style.position='fixed';el.style.left='-9999px';document.body.appendChild(el);let ok=false;try{sel(el);ok=document.execCommand('copy');getSelection().removeAllRanges()}catch(e){}el.remove();
 if(!ok){try{await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([el.innerHTML],{type:'text/html'}),'text/plain':new Blob([el.innerText],{type:'text/plain'})})]);ok=true}catch(e){}}
 if(ok){flash(b,'본문 복사됨');mark(id)}else{sel(src);flash(b,'선택됨, Ctrl+C')}}
async function copyImg(b,id,i){const im=document.querySelectorAll('#'+id+' img')[i];try{const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;c.getContext('2d').drawImage(im,0,0);const blob=await new Promise(r=>c.toBlob(r,'image/png'));await navigator.clipboard.write([new ClipboardItem({'image/png':blob})]);flash(b,'사진 복사됨')}catch(e){flash(b,'복사가 막혔어요. html 파일로 열어 주세요')}}
function mark(id){try{const d=JSON.parse(localStorage.getItem('nb_done')||'{}');d[id]=1;localStorage.setItem('nb_done',JSON.stringify(d))}catch(e){}paint()}
function paint(){let d={};try{d=JSON.parse(localStorage.getItem('nb_done')||'{}')}catch(e){}document.querySelectorAll('.nav a').forEach(a=>{a.classList.toggle('done',!!d[a.dataset.id])})}
paint();
"""


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    (out / "img").mkdir(parents=True, exist_ok=True)
    rendered = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 1080, "height": 1080})
        for post in spec["posts"]:
            k = 0
            for b in post["blocks"]:
                if "img" in b:
                    k += 1
                    pg.set_content(card_html(b["img"], post.get("theme", "b2b")))
                    pg.wait_for_timeout(120)
                    f = out / "img" / f"{post['id']}_{k}.jpg"
                    pg.screenshot(path=str(f), type="jpeg", quality=86)
                    rendered.setdefault(post["id"], []).append(f)
        br.close()
    secs, nav, report = [], [], []
    for i, post in enumerate(spec["posts"], 1):
        files = rendered.get(post["id"], [])
        imgs = [base64.b64encode(f.read_bytes()).decode() for f in files]
        bid = f"b{i}"
        post['_bid'] = bid
        post['_img_base'] = spec.get('img_base', '')
        tags = " ".join(post["tags"])
        nav.append(f"<a href='#s{i}' data-id='{bid}'>{i}. {html.escape(post['when'].split('(')[0].replace('2026년 ', '').replace('2027년 ', ''))}</a>")
        dls = "<span>사진만 따로</span>" + "".join(f"<button class='o s' onclick=\"copyImg(this,'{bid}',{j - 1})\">사진 {j} 복사</button>" for j in range(1, len(imgs) + 1))
        secs.append(f"""<section id='s{i}'><div class='box'>
<div class='meta'><span class='n'>{i}</span><span class='w'>예약 {html.escape(post['when'])}</span><span class='c'>카테고리 {html.escape(post['category'])}</span></div>
<div class='btns'><button onclick="copyText(this,{html.escape(json.dumps(post['title'], ensure_ascii=False))})">제목 복사</button>
<button onclick="copyBody(this,'{bid}')">본문 복사</button>
<button class='o' onclick="copyText(this,{html.escape(json.dumps(' '.join('#' + t for t in post['tags']), ensure_ascii=False))})">태그만 복사</button></div>
<div class='ttl'>{html.escape(post['title'])}</div>
<div class='post' id='{bid}'>{body_html(post, imgs)}</div>
<div class='dl'>{dls}</div></div></section>""")
        report.append({"id": post["id"], "title": post["title"], "title_len": len(post["title"]), "chars": plain_len(post), "imgs": len(files)})
    page = f"""<title>{html.escape(spec.get('name', spec['title']))}</title><meta name="claude:viewport-fit-sides" content="cover"><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'><style>{PAGE_CSS}</style>
<div class='top'><h1>{html.escape(spec['title'])}</h1><p>{html.escape(spec.get('sub', ''))}</p>
<div class='how'><b>한 편 붙여 넣는 순서</b><ol>
<li>네이버 블로그 글쓰기를 엽니다.</li>
<li>제목 복사를 누르고 제목 칸에 붙여 넣습니다.</li>
<li>본문 복사를 누르고 본문 첫 줄에 붙여 넣습니다. 글, 표, 링크, 맨 끝 #태그가 들어갑니다. 본문의 #태그는 네이버가 태그로 자동 등록합니다.</li>
<li>사진이 본문과 함께 들어왔으면 그대로 둡니다. 들어오지 않았으면 이 페이지에서 사진 1 복사를 누르고, 네이버 본문의 회색 사진 설명 줄 바로 위 빈 줄에 붙여 넣습니다. 사진 2부터 4까지 같은 방법입니다.</li>
<li>발행 창에서 카테고리를 고르고 태그 칸에 태그가 들어왔는지 봅니다.</li>
<li>발행 시간을 예약으로 바꿔 위에 적힌 날짜와 시각을 넣고 발행합니다.</li></ol>
사진 복사 버튼은 페이지 미리보기의 각 사진 바로 아래와 글 맨 아래에 있습니다. 이 화면에서 복사 버튼이 막히면 함께 받은 html 파일을 크롬으로 열어 같은 버튼을 쓰면 됩니다.</div>
<div class='nav'>{''.join(nav)}</div></div>
{''.join(secs)}<script>{PAGE_JS}</script>"""
    (out / "네이버원고.html").write_text(page, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
