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
theme: "b2b"(남색, clipbiz2026 계정의 안심클립 하이클립 클립마켓), "hic"(밝은 바탕, 하이클립 전용 계정) 또는 "hcs"(먹색, 홍책사)
선택 키: "hexagram": [아래에서 위로 6개, "yang" 또는 "yin"] 를 넣으면 오른쪽 아래에 괘를 그린다.
사진 장(캐러셀에 영상 장면을 넣을 때):
  "frame": {"src": "<영상 주소나 경로>", "t": 초} 영상의 그 시각 장면을 배경으로 깐다(ffmpeg로 뽑음).
  "image": "<이미지 주소나 경로>" 이미지를 배경으로 깐다.
  "pos": "center 22%" 4:5로 자를 때 보일 위치(CSS background-position, 기본 center 22%. 9:16 영상 맨 위의 원래 표시와 아래쪽 자막이 잘리고 그 사이가 보인다. 원래 표시가 남으면 값을 키운다).
  "label": "AI로 만든 가상인물" 왼쪽 위 표시(32px, 어두운 바탕 흰 글씨). AI 영상 장면이면 반드시 넣는다.
  사진 장은 아래쪽에 테마 색 그러데이션을 깔고 그 위에 kicker, title, body를 얹는다.
출력: 1080x1350 PNG, 파일명 <ID>_<번호>.png, manifest.json(폴더에 이미 있으면 합친다)
"""
import json
import sys
import html
import base64
import hashlib
import subprocess
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

THEMES = {
    "b2b": dict(bg="#17395E", fg="#FFFFFF", sub="#C9D6E3", accent="#E8590C", font="'Noto Sans CJK KR'"),
    "hcs": dict(bg="#16201C", fg="#F2EFE6", sub="#A9B3AD", accent="#B5342A", font="'Noto Serif CJK KR'"),
    # 하이클립 화면 색(hiclip.kr :root). 글자 대비 #14202E/#F5F6F3 약 15:1, #485868/#F5F6F3 약 7:1
    "hic": dict(bg="#F5F6F3", fg="#14202E", sub="#485868", accent="#C64016", font="'Noto Sans CJK KR'"),
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


def media_uri(src, t=None):
    key = hashlib.md5(f"{src}|{t}".encode()).hexdigest()[:16]
    out = Path(tempfile.gettempdir()) / f"rc_media_{key}.jpg"
    if not out.exists():
        cmd = ["ffmpeg", "-v", "error", "-y"]
        if t is not None:
            cmd += ["-ss", str(t)]
        cmd += ["-i", src, "-frames:v", "1", "-q:v", "2", str(out)]
        subprocess.run(cmd, check=True, timeout=300)
    return "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()


def photo_page(slide, idx, total):
    t = THEMES[slide.get("theme", "b2b")]
    if slide.get("frame"):
        uri = media_uri(slide["frame"]["src"], slide["frame"].get("t", 0))
    else:
        uri = media_uri(slide["image"])
    pos = html.escape(slide.get("pos", "center 22%"))
    count = f"{idx}/{total}" if total > 1 else ""
    body = f"<div class='body'>{esc(slide.get('body'))}</div>" if slide.get("body") else ""
    kicker = f"<div class='kicker'>{esc(slide.get('kicker'))}</div><div class='bar'></div>" if slide.get("kicker") else ""
    label = f"<div class='label'>{esc(slide.get('label'))}</div>" if slide.get("label") else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{width:1080px;height:1350px;background:{t['bg']};color:{t['fg']};font-family:{t['font']};position:relative;overflow:hidden}}
    .ph{{position:absolute;inset:0;background-image:url('{uri}');background-size:cover;background-position:{pos}}}
    .shade{{position:absolute;left:0;right:0;bottom:0;height:64%;background:linear-gradient(to top,{t['bg']} 0%,{t['bg']}F0 42%,{t['bg']}00 100%)}}
    .label{{position:absolute;left:48px;top:48px;background:rgba(0,0,0,.72);color:#fff;font-family:'Noto Sans CJK KR';font-size:32px;font-weight:500;padding:10px 20px;border-radius:10px}}
    .wrap{{position:absolute;left:96px;right:96px;bottom:190px}}
    .kicker{{font-size:32px;letter-spacing:2px;color:{t['sub']};font-family:'Noto Sans CJK KR';font-weight:500}}
    .bar{{width:64px;height:7px;background:{t['accent']};margin:24px 0 30px}}
    .title{{font-size:64px;line-height:1.3;font-weight:700;letter-spacing:-1px;word-break:keep-all}}
    .body{{margin-top:26px;font-size:38px;line-height:1.5;color:{t['sub']};font-family:'Noto Sans CJK KR';font-weight:400;word-break:keep-all}}
    .foot{{position:absolute;left:96px;right:96px;bottom:84px;display:flex;justify-content:space-between;font-family:'Noto Sans CJK KR';font-size:30px;color:{t['sub']}}}
    .foot b{{color:{t['fg']};font-weight:700}}
    </style></head><body><div class='ph'></div><div class='shade'></div>{label}
    <div class='wrap'>{kicker}<div class='title'>{esc(slide.get('title'))}</div>{body}</div>
    <div class='foot'><span>{slide.get('foot', '')}</span><span>{count}</span></div></body></html>"""


def page(slide, idx, total):
    if slide.get("frame") or slide.get("image"):
        return photo_page(slide, idx, total)
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
    mf = out / "manifest.json"
    manifest = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for cid, slides in spec.items():
            files = []
            for i, s in enumerate(slides, 1):
                pg.set_content(page(s, i, len(slides)))
                pg.wait_for_timeout(400 if (s.get("frame") or s.get("image")) else 150)
                f = out / f"{cid}_{i}.png"
                pg.screenshot(path=str(f))
                files.append(f.name)
            manifest[cid] = files
        b.close()
    mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in spec}, ensure_ascii=False))


if __name__ == "__main__":
    main()
