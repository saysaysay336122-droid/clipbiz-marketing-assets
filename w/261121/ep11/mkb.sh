python3 - <<'PY'
h=open('/home/claude/ep11/_v11_head.py',encoding='utf-8').read().replace('30.5초','v2 스릴러')
hp=open('/home/claude/ep10/_v20_helpers.py',encoding='utf-8').read()
cb=open('/home/claude/ep11/_chat_block2.py',encoding='utf-8').read()
m=open('/home/claude/ep11/_v11b_head_main.py',encoding='utf-8').read()
open('/home/claude/ep11/build11b.py','w',encoding='utf-8').write(h+'\n'+m.replace('"""HELPERS"""',hp).replace('"""CHAT"""',cb))
PY
