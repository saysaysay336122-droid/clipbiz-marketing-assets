"""제작지시 시트를 읽어 카드 이미지, 실사 영상, 블로그 글 파일을 만든다.

GitHub Actions(.github/workflows/render.yml)가 돌린다. 토요일 정기 작업 세션은 저장소에 직접 올릴 수 없어서
만들 내용을 구글 시트 '클립비즈_제작지시'에 적고, 이 스크립트가 그 내용을 받아 렌더한 뒤 main에 올린다.

사용법
  python3 tools/build_week.py <시트 CSV 주소>            렌더하고 결과를 쓴다
  python3 tools/build_week.py <시트 CSV 주소> --check    렌더할 것이 있으면 need=true를 출력한다(설치 생략용)

시트 형식(첫 줄은 머리글)
  A 폴더   w/YYMMDD(그 주 월요일), m/YYMM(네이버 원고 카드), docs(인사이트 블로그 글)
  B ID     MK-YYMMDD-번호. docs는 파일 이름
  C 종류   cards, short, cardreel, chat, post
  D 내용   JSON
           cards: render_cards.py spec의 한 항목(장 목록)
           short: render_short.py spec. 장면의 src 대신 "pexels": "<영상 번호>" 또는 "photo": "<images.pexels.com 주소>"
           cardreel: {"from": "<같은 폴더 cards 항목 ID>", "sec": 3.6}  카드를 이어 붙인 영상(실사 소재를 못 구했을 때)
           chat:  render_chat.py spec(메신저 대화 상황극). 영상 <ID>_reel.mp4와 카드 <ID>_1.png...를 함께 만든다
           post:  {"path": "docs/_posts/YYYY-MM-DD-slug.md", "text": "마크다운 전체"}
  E 적은 시각(참고용)

결과
  폴더마다 _built.json: {"rev", "built_at", "items": {ID: [파일...]}, "errors": {ID: 사유}}
  rev는 그 폴더 지시 내용의 해시다. 같은 rev면 다시 만들지 않는다.
"""
import csv
import datetime
import hashlib
import io
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
KST = datetime.timezone(datetime.timedelta(hours=9))
FOLDER_RE = re.compile(r"^(w/\d{6}|m/\d{4}|docs)$")
POST_RE = re.compile(r"^docs/_posts/\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")


def load_rows(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 clipbiz-render"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    by = {}
    for r in rows[1:]:
        if len(r) < 4:
            continue
        folder, mid, kind, body = r[0].strip(), r[1].strip(), r[2].strip(), r[3]
        if not folder or not mid or not FOLDER_RE.match(folder) or kind not in ("cards", "short", "cardreel", "chat", "post"):
            continue
        by.setdefault(folder, []).append((mid, kind, body))
    return by


def rev_of(items):
    return hashlib.sha256(json.dumps(sorted(items), ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def pending(by):
    out = []
    for folder, items in sorted(by.items()):
        built = ROOT / folder / "_built.json"
        if built.exists():
            try:
                if json.loads(built.read_text(encoding="utf-8")).get("rev") == rev_of(items):
                    continue
            except Exception:
                pass
        out.append(folder)
    return out


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-800:])
    return r.stdout


def build_short(folder, mid, spec, stock):
    import fetch_stock
    credits = []
    for sc in spec.get("scenes", []):
        if sc.get("end"):
            continue
        if sc.get("pexels"):
            vid = re.sub(r"\D", "", str(sc.pop("pexels")))
            name = f"pexels_{vid}.mp4"
            fetch_stock.cmd_get([f"video:{vid}"], stock)
        elif sc.get("photo"):
            url = sc.pop("photo")
            m = re.search(r"photos/(\d+)/", url)
            name = f"pexels_{m.group(1) if m else 'photo'}.jpg"
            fetch_stock.cmd_get([url], stock)
        else:
            raise RuntimeError("장면에 pexels 또는 photo가 없다")
        sc["src"] = f"stock/{name}"
        meta = stock / (Path(name).stem + ".json")
        if meta.exists():
            info = json.loads(meta.read_text(encoding="utf-8"))
            credits.append({k: info.get(k) for k in ("source", "id", "page", "photographer", "width", "height", "duration")})
    spec_path = ROOT / folder / f"{mid}_short.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    mp4 = ROOT / folder / f"{mid}_reel.mp4"
    run([sys.executable, "tools/render_short.py", str(spec_path.relative_to(ROOT)), str(mp4.relative_to(ROOT))])
    (ROOT / folder / f"{mid}_credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
    return [mp4.name, spec_path.name, f"{mid}_credits.json"]


def build(folder, items):
    out = ROOT / folder
    out.mkdir(parents=True, exist_ok=True)
    stock = ROOT / "stock"
    stock.mkdir(exist_ok=True)
    result = {"rev": rev_of(items), "built_at": datetime.datetime.now(KST).isoformat(timespec="seconds"),
              "items": {}, "errors": {}}
    parsed = []
    for mid, kind, body in items:
        try:
            parsed.append((mid, kind, json.loads(body)))
        except Exception as e:
            result["errors"][mid] = f"JSON 오류: {e}"
    cards = {mid: data for mid, kind, data in parsed if kind == "cards"}
    if cards:
        spec_all = out / "spec.json"
        merged = json.loads(spec_all.read_text(encoding="utf-8")) if spec_all.exists() else {}
        merged.update(cards)
        spec_all.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp = out / "_spec_this_run.json"
        tmp.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            run([sys.executable, "tools/render_cards.py", str(tmp.relative_to(ROOT)), str(out.relative_to(ROOT))])
            for mid, slides in cards.items():
                result["items"][mid] = [f"{mid}_{i}.png" for i in range(1, len(slides) + 1)]
        except Exception as e:
            for mid in cards:
                result["errors"][mid] = str(e)[-500:]
        finally:
            tmp.unlink(missing_ok=True)
    for mid, kind, data in parsed:
        try:
            if kind == "short":
                result["items"][mid] = build_short(folder, mid, data, stock)
            elif kind == "chat":
                data["id"] = mid
                spec_path = out / f"{mid}_chat.json"
                spec_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
                mp4 = out / f"{mid}_reel.mp4"
                run([sys.executable, "tools/render_chat.py", str(spec_path.relative_to(ROOT)), str(mp4.relative_to(ROOT)),
                     "--cards", str(out.relative_to(ROOT))])
                mf = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
                result["items"][mid] = [mp4.name, spec_path.name] + mf.get(mid, [])
            elif kind == "cardreel":
                src = data["from"]
                if src not in result["items"]:
                    raise RuntimeError(f"카드 {src}가 이번 렌더에 없다")
                mp4 = out / f"{mid}_reel.mp4"
                run([sys.executable, "tools/render_reel.py", str(out.relative_to(ROOT)), src, str(mp4.relative_to(ROOT)),
                     str(data.get("sec", 3.6))])
                result["items"][mid] = [mp4.name]
            elif kind == "post":
                path = data.get("path", "")
                if folder != "docs" or not POST_RE.match(path):
                    raise RuntimeError("post는 docs 폴더, docs/_posts/YYYY-MM-DD-slug.md 경로만 쓴다")
                (ROOT / path).write_text(data["text"], encoding="utf-8")
                result["items"][mid] = [path]
        except Exception as e:
            result["errors"][mid] = str(e)[-500:]
    for wav in out.glob("*.wav"):
        wav.unlink()
    if folder != "docs":
        (out / "_built.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        (ROOT / "docs" / "_built_posts.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(folder, "완료", len(result["items"]), "건, 오류", len(result["errors"]), "건")
    return result


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    by = load_rows(sys.argv[1])
    todo = pending(by)
    if "--check" in sys.argv:
        print("need=" + ("true" if todo else "false"))
        print("folders=" + " ".join(todo))
        return
    for folder in todo:
        build(folder, by[folder])


if __name__ == "__main__":
    main()
