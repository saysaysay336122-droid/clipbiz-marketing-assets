"""홍책사네 댄스 영상용 자체 제작 비트(남의 곡 없음). 춤 동작 박자(약 131BPM)에 맞춘다."""
import sys, wave
import numpy as np
sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import music

music.STYLES["dance"] = {"bpm": (131, 131), "swing": 0.0, "kick": [0, 1, 2, 3], "clap": [1, 3],
                         "hat": 0.14, "pluck": 0.6, "mel": 0.55, "bass": 0.32}
TOTAL = 8.567
FIRST_BEAT = 0.5 + 0.32 - 60 / 131  # 영상 0.5초부터 춤, 동작이 멈추는 박(시각 박자) 위상 0.32초
pre = FIRST_BEAT  # 곡의 첫 박을 이 시각에 둔다
info = music.make_track(TOTAL - pre + 0.05, "v2/beat_raw.wav", "dance", seed=11)
print(info, "first beat", round(pre, 3))
with wave.open("v2/beat_raw.wav") as w:
    sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
pad = np.zeros(int(pre * sr))
y = np.concatenate([pad, x])[: int(TOTAL * sr)]
with wave.open("v2/beat.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.astype(np.int16).tobytes())
