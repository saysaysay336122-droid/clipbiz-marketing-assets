# -*- coding: utf-8 -*-
"""카카오톡 PC 채팅방 미리보기 흉내: 폭 232px 카드, 제목 2줄, 설명 2줄."""
import asyncio, sys, json
from pathlib import Path
from playwright.async_api import async_playwright
B=Path(__file__).resolve().parent; AUD=B/'before'
def uri(p): return 'file://'+str(p)
BEFORE=[
 dict(img=AUD/'ansimclip.png', t='안심클립 | 연계고용 거래와 감면 신청 자료', d='장애인표준사업장, 직업재활시설과 기업, 공공기관이 견적, 계약, 발주, 지급증빙을 주고받고 연말에 귀속연도별 감면 신청 자료를 내려받습니다.', u='ansimclip.kr'),
 dict(img=AUD/'clipmarket.png', t='클립마켓 Clip-market, 기업 간 중고 설비와 남은 자재 거래', d='', u='clipmarket.kr'),
 dict(img=AUD/'clipbiz.png', t='클립비즈 | 장애인 고용부담금, 구매와 채용으로 줄입니다', d='HD현대중공업 사내벤처로 출발한 클립비즈. 연계고용 거래 관리 안심클립, 기업 유휴자산 거래 클립마켓, 장애인 채용정보 하이클립을 운영합니다.', u='clipbiz.kr'),
 dict(img=AUD/'hiclip.png', t='하이클립 Hi-clip, 근무조건과 지원환경으로 찾는 장애인 채용', d='근무조건과 지원환경을 먼저 보고 기업에 직접 지원하는 장애인 채용정보 서비스. 구직자 이용료 없음, 연락처 비공개.', u='hiclip.kr'),
 dict(img=AUD/'hongchaksa.png', t='홍책사 | 너의 삶에 필요한 한 수', d='사주와 주역, 타로로 고민에 한 수를 건네요. 계산 기준과 원문을 함께 보여 드려요.', u='hongchaksa.kr'),
]
AFTER=json.loads((B/'copy.json').read_text()) if (B/'copy.json').exists() else []
def cards(items, suffix=''):
    h=''
    for it in items:
        d=f"<div class='d'>{it['d']}</div>" if it.get('d') else ''
        h+=f"<div class='k'><img src='{uri(it['img'])}'><div class='tx'><div class='t'>{it['t']}</div>{d}<div class='u'>{it['u']}</div></div></div>"
    return h
def html(scale, w):
    after=[dict(img=B/'out'/(a['key']+'.png'), t=a['og_title'], d=a['og_desc'], u=a['domain']) for a in AFTER]
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#B2C7D9;font-family:'Noto Sans CJK KR','Pretendard',sans-serif;padding:14px;width:{(w*2+14*3+0)}px}}
    .wrap{{display:flex;gap:14px;align-items:flex-start}}
    .col{{width:{w}px}}
    .note{{font-size:11px;color:#3b4a5a;margin:0 0 10px 2px}}
    .cap{{font-size:11px;color:#3b4a5a;font-weight:700;margin:0 0 6px 2px}}
    .k{{width:{w}px;background:#fff;border-radius:6px;overflow:hidden;margin-bottom:8px;box-shadow:0 1px 1px rgba(0,0,0,.08)}}
    .k img{{width:{w}px;height:{w//2}px;object-fit:cover;display:block}}
    .tx{{padding:8px 10px 9px}}
    .t{{font-size:13px;font-weight:700;color:#191919;line-height:17px;max-height:34px;overflow:hidden;word-break:break-all}}
    .d{{font-size:12px;color:#8a8a8a;line-height:16px;margin-top:3px;max-height:32px;overflow:hidden;word-break:break-all}}
    .u{{font-size:12px;color:#2F6FDE;text-decoration:underline;margin-top:5px}}
    </style></head><body><div class='note'>카카오톡 PC 채팅방 크기(폭 232px)로 줄여 본 모습</div><div class='wrap'><div class='col'><div class='cap'>지금</div>{cards(BEFORE)}</div><div class='col'><div class='cap'>새 미리보기</div>{cards(after)}</div></div></body></html>"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel='chrome',headless=True,args=['--no-sandbox'])
        for name,scale,w in [('sim_pc_1x',1,232),('sim_pc_2x',2,232),('sim_mobile_2x',2,300)]:
            ctx=await b.new_context(viewport={'width':w*2+14*3,'height':900},device_scale_factor=scale)
            pg=await ctx.new_page(); hp=B/'out'/f'_{name}.html'; hp.write_text(html(scale,w),encoding='utf-8')
            await pg.goto(uri(hp)); await pg.wait_for_timeout(400)
            await pg.screenshot(path=str(B/'out'/f'_{name}.png'),full_page=True); await ctx.close()
        await b.close()
asyncio.run(main())
