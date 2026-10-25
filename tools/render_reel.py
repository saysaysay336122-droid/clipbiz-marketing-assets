"""카드 이미지를 인스타그램 릴스 영상(1080x1920, 9:16)으로 만든다.

사용법: python3 render_reel.py <카드 폴더> <ID> <출력 mp4> [장당 초, 기본 3.6]
예: python3 render_reel.py w/261027 MK-261027-08 w/261027/MK-261027-08_reel.mp4

<카드 폴더>/manifest.json 에서 <ID>의 카드 목록을 읽는다.
각 장은 천천히 확대되고 다음 장으로 교차 전환된다. 카드 바탕색으로 위아래를 채운다.
소리는 저작권 문제가 없도록 프로그램이 직접 만든 잔잔한 화음 패드를 낮은 음량으로 넣는다.
"""
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

FPS = 30
W, H = 1080, 1920


def make_pad(seconds, path, seed=7):
    sr = 44100
    n = int(sr * seconds)
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)
    base = rng.choice([110.0, 123.47, 130.81, 146.83])  # A2, B2, C3, D3
    ratios = [1, 1.5, 2, 3, 2.5]  # 근음, 5도, 옥타브, 12도, 10도
    out = np.zeros(n)
    for i, r in enumerate(ratios):
        f = base * r
        lfo = 1 + 0.004 * np.sin(2 * math.pi * (0.05 + 0.02 * i) * t + i)
        amp = 0.5 / (i + 1)
        out += amp * np.sin(2 * math.pi * f * lfo * t)
        out += amp * 0.4 * np.sin(2 * math.pi * f * 1.003 * t + 0.7 * i)
    # 느린 숨쉬기
    out *= 0.75 + 0.25 * np.sin(2 * math.pi * 0.08 * t)
    # 페이드
    fade = int(sr * 1.5)
    env = np.ones(n)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    out *= env
    out = out / np.max(np.abs(out)) * 0.18
    data = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def main():
    folder = Path(sys.argv[1])
    cid = sys.argv[2]
    out = Path(sys.argv[3])
    per = float(sys.argv[4]) if len(sys.argv) > 4 else 3.6
    files = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))[cid]
    if len(files) == 1:
        per = max(per, 9.0)
    xfade = 0.6
    bg = Image.open(folder / files[0]).convert("RGB").getpixel((5, 5))
    color = "0x%02x%02x%02x" % bg
    total = per * len(files) - xfade * (len(files) - 1)
    pad = out.with_suffix(".wav")
    make_pad(total + 0.5, pad)

    inputs = []
    for f in files:
        inputs += ["-loop", "1", "-t", f"{per}", "-i", str(folder / f)]
    inputs += ["-i", str(pad)]
    chains = []
    for i in range(len(files)):
        zoom = f"zoompan=z='min(zoom+0.0006,1.08)':d={int(per * FPS)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1350:fps={FPS}"
        chains.append(f"[{i}:v]{zoom},pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={color},format=yuv420p[v{i}]")
    cur = "v0"
    offset = 0.0
    for i in range(1, len(files)):
        offset += per - xfade
        chains.append(f"[{cur}][v{i}]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[x{i}]")
        cur = f"x{i}"
    fc = ";".join(chains)
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", f"[{cur}]", "-map", f"{len(files)}:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    pad.unlink()
    print(out, round(total, 1), "s")


if __name__ == "__main__":
    main()
