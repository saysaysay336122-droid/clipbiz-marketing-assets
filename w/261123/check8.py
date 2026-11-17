import json, re, subprocess, sys
import numpy as np
SPEC = json.load(open('ep08_spec_v6.json', encoding='utf-8'))
SH = {s['id']: s for s in SPEC['shots']}
ids = sys.argv[1].split(',')
try: res = json.load(open('asr.json'))
except Exception: res = {}
from faster_whisper import WhisperModel
import librosa
model = WhisperModel('small', device='cpu', compute_type='int8')
def norm(t): return re.sub(r'[^가-힣]', '', t)
for k in ids:
    p = f'clips/{k}.mp4'; wav = f'clips/{k}.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-i',p,'-ac','1','-ar','16000',wav], check=True)
    y,_ = librosa.load(wav, sr=16000)
    segs,_ = model.transcribe(y.astype(np.float32), language='ko', word_timestamps=True, vad_filter=False, initial_prompt=SH[k].get('line',''))
    segs = list(segs)
    text = ' '.join(s.text.strip() for s in segs)
    words = [(w.start, w.end, w.word) for s in segs for w in (s.words or [])]
    line = SH[k].get('line','')
    r = {'asr': text, 'span': [words[0][0], words[-1][1]] if words else None, 'words': words,
         'match': norm(line) in norm(text) if line else None}
    if r['span']:
        a,b = int(r['span'][0]*16000), int(r['span'][1]*16000)
        f0,_,_ = librosa.pyin(y[a:b], fmin=70, fmax=400, sr=16000); f0 = f0[~np.isnan(f0)]
        r['f0'] = float(np.median(f0)) if len(f0) else None
    res[k] = r
    print(k, line, '|', text, r['span'], r.get('f0'), r['match'])
json.dump(res, open('asr.json','w'), ensure_ascii=False, indent=1)
