import subprocess, sys
sys.path.insert(0,'w/261127/cards')
from spec import ALL
FY={'read':0.24,'smile':0.27,'calm':0.28,'warm':0.30,'smirk':0.28,'mid':0.26,'mid2':0.24,'fan':0.27,'talk':0.23,'coin':0.22}
ZZ={'read':1.15,'smile':1.0,'calm':1.0,'warm':1.0,'smirk':1.0,'mid':1.1,'mid2':1.15,'fan':1.3,'talk':1.15,'coin':1.1}
JL={'jik01':('돈 안 모인 거,','운 탓 아니에요'),'jik02':('연락 기다리면','그건 성격이에요'),'jik03':('이직 고민 1년째','그건 습관이에요'),'jik04':('새해 계획 열 개','하나도 못 해요')}
EN={'rat':'RAT','ox':'OX','tiger':'TIGER','rabbit':'RABBIT','dragon':'DRAGON','snake':'SNAKE','horse':'HORSE','goat':'GOAT','monkey':'MONKEY','rooster':'ROOSTER','dog':'DOG','pig':'PIG'}
ids=sys.argv[1:]
for v in ALL:
    if ids and v['id'] not in ids: continue
    st=v['scenes'][0]['still'] if v['kind']=='tti' else v['src']['stills'][0]
    src=f'w/261127/cards/tmp/stills/{st}.png'
    out=f'w/261127/cards/cover/hcs_{v["id"]}_cover.jpg'
    if v['kind']=='tti':
        ep,l1,l2,en='홍책사 2027 띠별',f'2027 {v["name"]}띠','좋은 달은 언제',f'2027 ZODIAC {EN[v["en"]]}'
    else:
        ep='홍책사 직언'; l1,l2=JL[v['id']]; en='STRAIGHT TALK FOR 2027'
    subprocess.run(['python3','tools/make_cover.py',src,out,ep,l1,l2,'AI로 만든 가상인물',en,'hcs',str(FY[st]),str(ZZ[st]),'0.5'],check=True)
    print(out)
