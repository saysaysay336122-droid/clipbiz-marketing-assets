import sys, subprocess, numpy as np
for k in sys.argv[1:]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f"clips/{k}.mp4", "-af", "highpass=f=120,lowpass=f=5000", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    fr = 160
    e = np.array([np.sqrt(np.mean(a[i:i+fr]**2)) for i in range(0, len(a)-fr, fr)])
    db = 20*np.log10(e+1e-9)
    thr = db.max() - 25
    act = np.where(db > thr)[0]
    segs = []
    if len(act):
        s = act[0]; p = act[0]
        for i in act[1:]:
            if i - p > 25:
                segs.append((s*0.01, p*0.01)); s = i
            p = i
        segs.append((s*0.01, p*0.01))
    print(k, f"max {db.max():.1f}dB", [(round(x,2), round(y,2)) for x,y in segs])
