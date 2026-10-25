"""클립비즈 홍보 카드 렌더러.

사용법: python3 render_cards.py spec.json 출력폴더
spec.json 형식:
{
  "MK-261103-01": [
    {"theme": "b2b", "kicker": "장애인고용부담금", "title": "첫 줄\n둘째 줄", "body": "설명", "foot": "<b>안심클립</b> ansimclip.kr"},
    ...
  ],
  ...
}
theme: "b2b"(남색, 안심클립 하이클립 클립마켓) 또는 "hcs"(먹색, 홍책사)
선택 키: "hexagram": [아래에서 위로 6개, "yang" 또는 "yin"] 를 넣으면 오른쪽 아래에 괘를 그린다.
출력: 1080x1350 PNG, 파일명 <ID>_<번호>.png, manifest.json
"""
import json
import sys
import html
from pathlib import Path
from playwright.sync_api import sync_playwright

THEMES = {
    "b2b": dict(bg="#17395E", fg="#FFFFFF", sub="#C9D6E3", accent="#E8590C", font="'Noto Sans CJK KR'"),
    "hcs": dict(bg="#16201C", fg="#F2EFE6", sub="#A9B3AD", accent="#B5342A", font="'Noto Serif CJK KR'"),
}


def esc(s):
    return html.escape(s or "").replace("\n", "<br>")


def hexagram(lines_bottom_up, color):
    rows = []
    for l in reversed(lines_bottom_up):
        if l == "yang":
            rows.append(f"<div class='hx'><span style='width:100%;background:{color}'></span></div>")
        else:
            rows.append(f"<div class='hx'><span style='width:44%;background:{color}'></span>"
                        f"<span style='width:44%;background:{color}'></span></div>")
    return "<div class='hexa'>" + "".join(rows) + "</div>"


def page(slide, idx, total):
    t = THEMES[slide.get("theme", "b2b")]
    count = f"{idx}/{total}" if total > 1 else ""
    body = f"<div class='body'>{esc(slide.get('body'))}</div>" if slide.get("body") else ""
    hx = hexagram(slide["hexagram"], t["accent"]) if slide.get("hexagram") else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1350px;background:{t['bg']};color:{t['fg']};font-family:{t['font']};position:relative;overflow:hidden}}
    .wrap{{position:absolute;left:96px;right:96px;top:0;bottom:230px;display:flex;flex-direction:column;justify-content:center}}
    .kicker{{font-size:34px;letter-spacing:2px;color:{t['sub']};font-family:'Noto Sans CJK KR';font-weight:500}}
    .bar{{width:72px;height:8px;background:{t['accent']};margin:34px 0 46px}}
    .title{{font-size:78px;line-height:1.32;font-weight:700;letter-spacing:-1px;word-break:keep-all}}
    .body{{margin-top:44px;font-size:42px;line-height:1.55;color:{t['sub']};font-family:'Noto Sans CJK KR';font-weight:400;word-break:keep-all}}
    .foot{{position:absolute;left:96px;right:96px;bottom:84px;display:flex;justify-content:space-between;font-family:'Noto Sans CJK KR';font-size:30px;color:{t['sub']}}}
    .foot b{{color:{t['fg']};font-weight:700}}
    .hexa{{position:absolute;right:96px;bottom:250px;width:220px}}
    .hx{{display:flex;justify-content:space-between;margin-bottom:26px}}
    .hx span{{display:block;height:26px}}
    </style></head><body><div class='wrap'>
    <div class='kicker'>{esc(slide.get('kicker'))}</div><div class='bar'></div>
    <div class='title'>{esc(slide.get('title'))}</div>{body}
    </div>{hx}<div class='foot'><span>{slide.get('foot', '')}</span><span>{count}</span></div></body></html>"""


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for cid, slides in spec.items():
            files = []
            for i, s in enumerate(slides, 1):
                pg.set_content(page(s, i, len(slides)))
                pg.wait_for_timeout(150)
                f = out / f"{cid}_{i}.png"
                pg.screenshot(path=str(f))
                files.append(f.name)
            manifest[cid] = files
        b.close()
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
