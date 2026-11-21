python3 - <<'PY'
h=open('/home/claude/ep11/_v11_head.py',encoding='utf-8').read()
hp=open('/home/claude/ep10/_v20_helpers.py',encoding='utf-8').read()
m=open('/home/claude/ep11/_v11_main.py',encoding='utf-8').read()
open('/home/claude/ep11/build11.py','w',encoding='utf-8').write(h+'\n'+m.replace('"""HELPERS"""',hp))
PY
