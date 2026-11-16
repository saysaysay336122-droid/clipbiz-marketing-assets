"""7화 컷 검사: 대사 음성 인식, 목소리 높이, 프레임 묶음.
사용: python3 check.py gen.json   (gen.json = {"S1": "https://.../output_0.mp4", ...})
"""
import json, os, re, subprocess, sys
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open("/home/claude/ep7/ep07_spec_v2.json", encoding="utf-8"))
SH = {s["id"]: s for s in SPEC["shots"]}
gen = json.load(open(sys.argv[1]))
os.makedirs(f"{D}/clips", exist_ok=True)


def norm(t):
    return re.sub(r"[^가-힣]", "", t)


for k, url in gen.items():
    p = f"{D}/clips/{k}.mp4"
    if not os.path.exists(p) or os.path.getsize(p) < 10000:
        subprocess.run(["curl", "-s", "-o", p, url], check=True)

from faster_whisper import WhisperModel
import librosa

model = WhisperModel("small", device="cpu", compute_type="int8")
res = {}
for k in gen:
    p = f"{D}/clips/{k}.mp4"
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,duration", "-of", "json", p], capture_output=True, text=True).stdout
    info = json.loads(pr)
    r = {"streams": [(s.get("codec_type"), s.get("width"), s.get("height"), s.get("duration")) for s in info.get("streams", [])]}
    has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    line = SH[k].get("line", "")
    if has_audio:
        wav = f"{D}/clips/{k}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ac", "1", "-ar", "16000", wav], check=True)
        y16, _ = librosa.load(wav, sr=16000)
        segs, _ = model.transcribe(y16.astype(np.float32), language="ko", word_timestamps=True, vad_filter=False)
        segs = list(segs)
        text = " ".join(s.text.strip() for s in segs)
        words = [(w.start, w.end, w.word) for s in segs for w in (s.words or [])]
        r["asr"] = text
        r["span"] = [words[0][0], words[-1][1]] if words else None
        r["match"] = (norm(line) in norm(text)) if line else (norm(text) == "")
        y, sr = librosa.load(wav, sr=16000)
        if line and r["span"]:
            a, b = int(r["span"][0] * sr), int(r["span"][1] * sr)
            seg = y[a:b] if b > a else y
            f0, vf, _ = librosa.pyin(seg, fmin=70, fmax=400, sr=sr)
            f0 = f0[~np.isnan(f0)]
            r["f0"] = float(np.median(f0)) if len(f0) else None
        r["rms_db"] = float(20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9))
    else:
        r["asr"] = None
        r["match"] = not line
    res[k] = r
    print(k, json.dumps(r, ensure_ascii=False))
json.dump(res, open(f"{D}/asr.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 프레임 묶음: 컷마다 0.3초, 가운데, 끝 0.3초 전
from PIL import Image, ImageDraw, ImageFont
f = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 22)
rows = []
for k in gen:
    p = f"{D}/clips/{k}.mp4"
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout or 4)
    ims = []
    for t in (0.3, dur / 2, max(0.3, dur - 0.3)):
        o = f"{D}/clips/{k}_{t:.1f}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", p, "-frames:v", "1", "-vf", "scale=240:-2", o], check=True)
        ims.append(Image.open(o))
    rows.append((k, ims))
w, h = rows[0][1][0].size
sheet = Image.new("RGB", (w * 3 * 2, (h + 30) * ((len(rows) + 1) // 2)), (255, 255, 255))
for i, (k, ims) in enumerate(rows):
    x0 = (i % 2) * w * 3
    y0 = (i // 2) * (h + 30)
    ImageDraw.Draw(sheet).text((x0 + 6, y0 + 2), k, font=f, fill=(0, 0, 0))
    for j, im in enumerate(ims):
        sheet.paste(im, (x0 + j * w, y0 + 30))
sheet.save(f"{D}/clips_contact.jpg", quality=85)
print("sheet ok")
