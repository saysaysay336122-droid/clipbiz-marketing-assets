"""무료 실사 소재(Pexels 영상과 사진)를 내려받고 확인한다.

사용법
1. 주소 목록으로 받기(Apify memo23/pexels-scraper 결과의 downloadUrl 또는 Pexels 영상 번호):
   python3 tools/fetch_stock.py get <항목>... [--out stock]
   <항목>은 https://...mp4 주소, https://images.pexels.com/... 사진 주소, 또는 'video:5739810'처럼 Pexels 영상 번호.
   영상 번호는 https://www.pexels.com/download/video/<번호>/ 로 받는다(키 없이 됨, 2026-10-27 확인).
2. Pexels API로 찾기(환경변수 PEXELS_API_KEY가 있을 때만):
   python3 tools/fetch_stock.py search "<검색어>" [--type videos|photos] [--n 8] [--out stock]
   운영설정 '소재 API 키'가 비어 있으면 이 방식은 쓰지 않고 Apify 결과 주소로 1번을 쓴다.

하는 일
1. stock/ 아래에 pexels_<번호>.mp4 또는 pexels_<번호>.jpg로 저장한다(이미 있으면 다시 받지 않는다).
2. ffprobe로 폭, 높이, 길이를 확인하고 첫 장면(1초 지점)을 stock/frames/<이름>.jpg로 뽑는다.
   작업자는 이 그림을 열어 실사 촬영본인지, 글자나 로고나 다른 회사 표시가 없는지, 홍보에 어울리는지 본다.
3. 결과를 stock/<이름>.json(출처 번호, 주소, 촬영자, 길이, 해상도)으로 남긴다. 이 json을 모아 영상 옆 _credits.json에 적는다.

stock/ 폴더는 저장소에 올리지 않는다(.gitignore). 완성한 영상(mp4)만 w/YYMMDD에 올린다.
Pexels 이용 조건(2026-10-27 확인): 무료, 상업 이용과 편집 허용, 출처 표시 의무 없음. 사람이 나오는 소재를 보증이나 후기처럼 쓰지 않는다.
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def fetch(url, dest, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,duration,r_frame_rate", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"]), float(s.get("duration") or 0)


def frame(path, dest, at=1.0):
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at}", "-i", str(path), "-frames:v", "1",
                    "-vf", "scale=360:-2", str(dest)], check=True, capture_output=True)


def save(out, name, url, meta):
    dest = out / name
    if not dest.exists():
        fetch(url, dest)
    info = dict(meta)
    info.update(file=str(dest), url=url)
    if dest.suffix == ".mp4":
        w, h, d = probe(dest)
        info.update(width=w, height=h, duration=round(d, 2))
        frame(dest, out / "frames" / (dest.stem + ".jpg"))
    else:
        w, h, _ = probe(dest)
        info.update(width=w, height=h)
    (out / (dest.stem + ".json")).write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{dest.name} {info.get('width')}x{info.get('height')} {info.get('duration', '')} {info.get('photographer', '')}")
    return info


def cmd_get(items, out):
    for it in items:
        if it.startswith("video:"):
            vid = it.split(":", 1)[1]
            save(out, f"pexels_{vid}.mp4", f"https://www.pexels.com/download/video/{vid}/",
                 {"source": "Pexels", "id": vid, "page": f"https://www.pexels.com/video/{vid}/"})
        elif "videos.pexels.com" in it or it.endswith(".mp4"):
            m = re.search(r"video-files/(\d+)/", it)
            vid = m.group(1) if m else re.sub(r"\W", "", it[-24:])
            save(out, f"pexels_{vid}.mp4", it, {"source": "Pexels", "id": vid, "page": f"https://www.pexels.com/video/{vid}/"})
        elif "images.pexels.com" in it:
            m = re.search(r"photos/(\d+)/", it)
            pid = m.group(1) if m else re.sub(r"\W", "", it[-24:])
            save(out, f"pexels_{pid}.jpg", it, {"source": "Pexels", "id": pid, "page": f"https://www.pexels.com/photo/{pid}/"})
        else:
            print("모르는 주소 형식:", it, file=sys.stderr)


def cmd_search(query, kind, n, out):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        sys.exit("PEXELS_API_KEY가 없다. Apify memo23/pexels-scraper 결과 주소로 get을 쓴다.")
    if kind == "videos":
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&orientation=portrait&size=medium&per_page={n}"
    else:
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&orientation=portrait&size=large&per_page={n}"
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if kind == "videos":
        for v in data.get("videos", []):
            files = [f for f in v.get("video_files", []) if f.get("height", 0) >= 1920 and f.get("width", 0) < f.get("height", 0)]
            files.sort(key=lambda f: f.get("height", 0))
            if not files:
                continue
            save(out, f"pexels_{v['id']}.mp4", files[0]["link"],
                 {"source": "Pexels", "id": str(v["id"]), "page": v.get("url"), "photographer": v.get("user", {}).get("name"),
                  "pexels_duration": v.get("duration")})
    else:
        for p in data.get("photos", []):
            save(out, f"pexels_{p['id']}.jpg", p["src"]["large2x"],
                 {"source": "Pexels", "id": str(p["id"]), "page": p.get("url"), "photographer": p.get("photographer"), "alt": p.get("alt")})


def main():
    args = sys.argv[1:]
    out = Path("stock")
    if "--out" in args:
        i = args.index("--out")
        out = Path(args[i + 1])
        del args[i:i + 2]
    out.mkdir(parents=True, exist_ok=True)
    if not args:
        sys.exit(__doc__)
    if args[0] == "get":
        cmd_get(args[1:], out)
    elif args[0] == "search":
        kind, n = "videos", 8
        if "--type" in args:
            i = args.index("--type"); kind = args[i + 1]; del args[i:i + 2]
        if "--n" in args:
            i = args.index("--n"); n = int(args[i + 1]); del args[i:i + 2]
        cmd_search(args[1], kind, n, out)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
