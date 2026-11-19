"""10화 효과음 큐 미리 듣기(자체 음악 + 효과음, 대사 자리는 음악만 낮춤). python3 mk_audio10.py"""
import json, re, subprocess, sys
sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music, sfx_cine
spec = json.load(open("ep10_spec.json", encoding="utf-8"))
T = spec["target_sec"]
mus = "ep10_music_preview.wav"
hcs_music.make(T, [tuple(x) for x in spec["music"]], mus, room=0.15)
events, duck = [], []
for sh in spec["shots"]:
    a = sh["t"][0]
    events += [tuple(e) for e in sh.get("sfx", [])]
    if sh.get("line"):
        st = a + sh.get("cue", 0.5) - (sh.get("use") or [0, 0])[0]
        syl = len(re.findall(r"[가-힣]", sh["line"]))
        duck.append((st - 0.05, st + syl / 3.3 + 0.35))
# 끝 화면 잔향이 0초 불판 소리로 이어지게: 마지막 0.4초에 지글을 미리 깐다
events.append((T - 0.45, "sizzle", 0.35))
wav = "ep10_sfx_cue_preview.wav"
sfx_cine.mix(T, wav, music=mus, music_gain=0.9, events=events, duck=duck)
mp3 = "홍책사_10화_효과음큐_미리듣기.mp3"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af",
                "highpass=f=30,alimiter=limit=0.7:level=false,loudnorm=I=-14:TP=-2.5:LRA=11,alimiter=limit=0.74:level=false",
                "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "192k", mp3], check=True)
r = subprocess.run(["ffmpeg", "-i", mp3, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print(mp3, [l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:], "events", len(events))
