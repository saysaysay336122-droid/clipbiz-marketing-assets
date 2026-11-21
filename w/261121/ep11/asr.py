import sys, json, subprocess, numpy as np
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
out = {}
for k in sys.argv[1:]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f"/home/claude/ep11/clips/{k}.mp4", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    segs, _ = m.transcribe(a, language="ko", word_timestamps=True, vad_filter=False)
    ws = []
    for s in segs:
        for w in s.words:
            ws.append((round(w.start, 2), round(w.end, 2), w.word))
    out[k] = ws
    print(k, ws)
json.dump(out, open("/home/claude/ep11/asr.json", "w"), ensure_ascii=False)
