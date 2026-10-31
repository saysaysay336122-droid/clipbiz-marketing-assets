"""실사 영상과 사진 위에 글을 얹어 세로 영상(1080x1920, 9:16)을 만든다. 릴스와 쇼츠 공용.

사용법: python3 tools/render_short.py <spec.json> <출력 mp4>
예: python3 tools/render_short.py w/261103/MK-261103-05_short.json w/261103/MK-261103-05_short.mp4

spec.json 예
{
  "theme": "hcs",                       # hcs(홍책사), hic(하이클립), b2b(clipbiz2026)
  "credit": "영상 Pexels",               # 끝 화면 아래 작은 글. 비우면 안 넣는다
  "music": true,                        # 프로그램이 만든 밝은 배경 음악(tools/music.py). false면 무음. music_style로 bright, playful, chill 지정 가능
  "scenes": [
    {"src": "stock/pexels_5739810.mp4", "start": 0, "dur": 4.2,
     "kicker": "일간", "title": "내 사주에서\n나를 나타내는 글자", "body": "태어난 날의 천간이 일간이에요."},
    {"src": "stock/photo.jpg", "dur": 4.0, "title": "..."},
    {"end": true, "dur": 3.2, "title": "무료 풀이로\n결과를 먼저 보세요", "body": "회원가입, 구독, 광고가 없어요", "foot": "hongchaksa.kr"}
  ]
}

규칙
1. 영상 장면은 start부터 dur만큼 잘라 화면을 가득 채우게 키우고 가운데를 자른다. 사진은 천천히 확대한다.
2. 글은 카드와 같은 글꼴(Noto Serif CJK KR, Noto Sans CJK KR)로 그려 아래쪽 어두운 띠 위에 얹는다.
   쇼츠 화면의 단추와 겹치지 않도록 아래 320px과 오른쪽 150px은 비운다.
3. 장면 사이는 0.5초 교차 전환. 끝 장면(end)은 테마 바탕색 전체 화면.
4. 전체 길이는 60초 이하여야 한다(넘으면 중단).
5. 출력은 H.264, 30fps, yuv420p, faststart. 같은 이름의 _credits.json이 있으면 그대로 둔다.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_reel import make_pad  # noqa: E402

W, H = 1080, 1920
FPS = 30
XFADE = 0.5
THEMES = {
    "b2b": dict(bg="#17395E", fg="#FFFFFF", sub="#C9D6E3", accent="#E8590C",
                font="'Noto Sans CJK KR'", band="23,57,94"),
    "hcs": dict(bg="#16201C", fg="#F2EFE6", sub="#A9B3AD", accent="#B5342A",
                font="'Noto Serif CJK KR'", band="22,32,28"),
    "hic": dict(bg="#14202E", fg="#F5F6F3", sub="#C9D1DA", accent="#C64016",
                font="'Noto Sans CJK KR'", band="20,32,46"),
}


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def overlay_html(t, sc, end=False):
    kicker = f"<div class='kicker'>{esc(sc.get('kicker'))}</div>" if sc.get("kicker") else ""
    body = f"<div class='body'>{esc(sc.get('body'))}</div>" if sc.get("body") else ""
    foot = f"<div class='foot'>{esc(sc.get('foot'))}</div>" if sc.get("foot") else ""
    credit = f"<div class='credit'>{esc(sc.get('credit'))}</div>" if sc.get("credit") else ""
    if end:
        bg = f"background:{t['bg']};"
        box = "top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;padding:0 110px 120px 110px;"
        band = ""
    else:
        bg = "background:transparent;"
        box = "bottom:330px;padding:0 160px 0 96px;"
        band = (f"<div style='position:absolute;left:0;right:0;bottom:0;height:1150px;"
                f"background:linear-gradient(to top, rgba({t['band']},0.94) 0%, rgba({t['band']},0.84) 45%, rgba({t['band']},0) 100%)'></div>")
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    html,body{{margin:0;padding:0}}
    body{{width:{W}px;height:{H}px;{bg}color:{t['fg']};font-family:{t['font']};position:relative;overflow:hidden}}
    .box{{position:absolute;left:0;right:0;{box}}}
    .kicker{{font-size:34px;letter-spacing:2px;color:{t['accent']};font-family:'Noto Sans CJK KR';font-weight:700;margin-bottom:18px}}
    .title{{font-size:{'84' if end else '74'}px;line-height:1.3;font-weight:700;letter-spacing:-1px;word-break:keep-all;text-shadow:0 2px 14px rgba(0,0,0,.35)}}
    .body{{margin-top:30px;font-size:40px;line-height:1.5;color:{t['sub']};font-family:'Noto Sans CJK KR';font-weight:400;word-break:keep-all}}
    .foot{{margin-top:56px;font-size:40px;color:{t['fg']};font-family:'Noto Sans CJK KR';font-weight:700}}
    .credit{{position:absolute;left:110px;bottom:150px;font-size:26px;color:{t['sub']};font-family:'Noto Sans CJK KR'}}
    </style></head><body>{band}<div class='box'>{kicker}<div class='title'>{esc(sc.get('title'))}</div>{body}{foot}</div>{credit}</body></html>"""


def render_pngs(theme, scenes, workdir):
    """장면마다 글 겹침용 PNG(투명)와 끝 화면 PNG를 Playwright로 그린다."""
    t = THEMES[theme]
    pages = []
    for i, sc in enumerate(scenes):
        html = overlay_html(t, sc, end=bool(sc.get("end")))
        hp = workdir / f"ov{i}.html"
        hp.write_text(html, encoding="utf-8")
        pages.append((str(hp), str(workdir / f"ov{i}.png"), bool(sc.get("end"))))
    # 카드 렌더러와 같은 파이썬 Playwright를 쓴다(GitHub Actions에서도 같은 결과가 나오게).
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": W, "height": H})
        for h, o, end in pages:
            p.goto("file://" + h)
            p.wait_for_timeout(250)
            p.screenshot(path=o, omit_background=not end)
        b.close()
    return [Path(o) for _, o, _ in pages]


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"]), float(s.get("duration") or 0)


def main():
    spec_path = Path(sys.argv[1])
    out = Path(sys.argv[2])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    theme = spec.get("theme", "hcs")
    scenes = spec["scenes"]
    if spec.get("credit"):
        for sc in scenes:
            if sc.get("end"):
                sc.setdefault("credit", spec["credit"])
    durs = [float(sc.get("dur", 4.0)) for sc in scenes]
    total = sum(durs) - XFADE * (len(scenes) - 1)
    if total > 60:
        sys.exit(f"길이 {total:.1f}초. 60초를 넘는다.")
    root = spec_path.resolve().parent.parent.parent if spec_path.resolve().parent.name.startswith(("w", "m")) else Path.cwd()
    workdir = Path(tempfile.mkdtemp(prefix="short_"))
    pngs = render_pngs(theme, scenes, workdir)

    inputs, chains = [], []
    n_in = 0
    for i, sc in enumerate(scenes):
        d = durs[i]
        frames = int(round(d * FPS))
        if sc.get("end"):
            inputs += ["-loop", "1", "-t", f"{d}", "-i", str(pngs[i])]
            chains.append(f"[{n_in}:v]scale={W}:{H},setsar=1,fps={FPS},format=yuv420p[v{i}]")
            n_in += 1
            continue
        src = Path(sc["src"])
        if not src.is_absolute():
            src = (Path.cwd() / src) if (Path.cwd() / src).exists() else (root / src)
        if src.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            inputs += ["-loop", "1", "-t", f"{d}", "-i", str(src)]
            base = (f"[{n_in}:v]scale={W * 1.12:.0f}:{H * 1.12:.0f}:force_original_aspect_ratio=increase,"
                    f"crop={W * 1.12:.0f}:{H * 1.12:.0f},"
                    f"zoompan=z='min(zoom+0.0008,1.10)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
                    f"setsar=1,format=rgba[b{i}]")
        else:
            start = float(sc.get("start", 0))
            w, h, vd = probe(src)
            if vd and start + d > vd + 0.05:
                sys.exit(f"{src.name}: 길이 {vd:.1f}초인데 {start}+{d}초를 요구한다.")
            inputs += ["-ss", f"{start}", "-t", f"{d + 0.2}", "-i", str(src)]
            base = (f"[{n_in}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"fps={FPS},setsar=1,trim=duration={d},setpts=PTS-STARTPTS,format=rgba[b{i}]")
        n_in += 1
        chains.append(base)
        inputs += ["-loop", "1", "-t", f"{d}", "-i", str(pngs[i])]
        chains.append(f"[{n_in}:v]format=rgba,fade=t=in:st=0.15:d=0.45:alpha=1[o{i}]")
        chains.append(f"[b{i}][o{i}]overlay=0:0:shortest=1,format=yuv420p[v{i}]")
        n_in += 1

    cur = "v0"
    offset = 0.0
    for i in range(1, len(scenes)):
        offset += durs[i - 1] - XFADE
        chains.append(f"[{cur}][v{i}]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[x{i}]")
        cur = f"x{i}"
    maps = ["-map", f"[{cur}]"]
    audio_idx = None
    if spec.get("music", True):
        pad = workdir / "pad.wav"
        make_pad(total + 0.5, pad, seed=spec.get("seed", 7), style=spec.get("music_style") or {"hcs": "playful"}.get(theme, "bright"))
        inputs += ["-i", str(pad)]
        audio_idx = n_in
        maps += ["-map", f"{audio_idx}:a"]
    fc = ";".join(chains)
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, *maps,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-r", str(FPS), "-pix_fmt", "yuv420p",
           "-t", f"{total:.3f}", "-movflags", "+faststart"]
    if audio_idx is not None:
        cmd += ["-c:a", "aac", "-b:a", "96k"]
    else:
        cmd += ["-an"]
    cmd.append(str(out))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr[-3000:])
    w, h, vd = probe(out)
    print(f"{out} {w}x{h} {vd:.1f}s")


if __name__ == "__main__":
    main()
