"""드롭샷 결과 내려받기. 사용: python3 gen9/dl.py jobs.json 폴더 확장자"""
import json, subprocess, sys, time
J = json.load(open(sys.argv[1])); out = sys.argv[2]; ext = sys.argv[3]
pending = dict(J)
for rnd in range(int(sys.argv[4]) if len(sys.argv) > 4 else 30):
    for s, j in list(pending.items()):
        u = f"https://cdn.aistudio.dropshot.io/public/jobs/prod/{j}/output/output_0.{ext}"
        code = subprocess.run(['curl', '-s', '-o', f'{out}/{s}.{ext}', '-w', '%{http_code}', u], capture_output=True, text=True).stdout
        if code == '200':
            pending.pop(s)
    if not pending:
        break
    time.sleep(10)
print('missing', list(pending))
