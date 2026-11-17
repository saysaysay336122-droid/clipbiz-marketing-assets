import json, sys, re, subprocess
sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import hcs_music, sfx_cine
spec = json.load(open(sys.argv[1], encoding="utf-8"))
tag = sys.argv[2]
T = spec["target_sec"]
mus = f"ep08_music_{tag}.wav"
hcs_music.make(T, [tuple(x) for x in spec["music"]], mus, room=spec.get("music_room", 0.0))
events, duck, silence = [], [], []
for sh in spec["shots"]:
    a = sh["t"][0]
    for at, n, g in sh.get("sfx", []):
        events.append((at, n, g))
    if sh.get("mute"):
        silence.append(tuple(sh["mute"]))
    if sh.get("line"):
        st = a + sh.get("cue", 0.5) - (sh.get("use") or [0, 0])[0]
        syl = len(re.findall(r"[가-힣]", sh["line"]))
        duck.append((st - 0.05, st + syl / 3.3 + 0.35))
    if sh.get("voice_from"):
        duck.append((a + 0.25, a + 1.0))
wav = f"ep08_sfx_cue_{tag}.wav"
sfx_cine.mix(T, wav, music=mus, music_gain=0.95, events=events, duck=duck, silence=silence)
mp3 = "홍책사_8화_효과음큐_미리듣기.mp3"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "highpass=f=30,lowshelf=f=90:g=-3,alimiter=limit=0.7:level=false,loudnorm=I=-14:TP=-2.5:LRA=11,alimiter=limit=0.74:level=false", "-ar", "48000",
                "-c:a", "libmp3lame", "-b:a", "192k", mp3], check=True)
r = subprocess.run(["ffmpeg", "-i", mp3, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
print(wav, mp3, [l.strip() for l in r.splitlines() if "I:" in l or "Peak:" in l][-2:])
print("events", len(events), "duck", duck, "silence", silence)
