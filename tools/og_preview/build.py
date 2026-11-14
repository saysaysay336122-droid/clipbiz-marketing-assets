# -*- coding: utf-8 -*-
"""링크 미리보기 이미지 빌더: HTML을 크롬으로 2배 렌더한 뒤 1200x600으로 줄인다.
쓰는 법은 같은 폴더 README.md."""
import asyncio, re, sys, random, base64, os, json
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image

B = Path(__file__).resolve().parent
A = B / 'assets'
OUT = B / 'out'
OUT.mkdir(exist_ok=True)
(B / 'img').mkdir(exist_ok=True)
W, H = 1200, 600

# ---------- 공식 심볼(실사판) 색 변형 ----------
SYM_SRC = (A / 'ansimclip_logo_0.svg').read_text()
PAL = {
    'blue':   dict(fg=['#5c82d4','#3564c9','#2457C5','#2150b7','#3967ca','#2355c1','#1e4aa9'], sg=['#3e568b','#143272','#0f2555'], dk='#102758'),
    'amber':  dict(fg=['#edb161','#e99e3b','#E8962A','#d78b27','#eaa03f','#e39329','#c78124'], sg=['#9b7541','#865718','#644112'], dk='#684312'),
    'orange': dict(fg=['#ff9372','#ff7950','#FF6E41','#ed663c','#ff7c54','#f96b3f','#db5e37'], sg=['#a6614c','#933f25','#6e2f1b'], dk='#72311d'),
    'green':  dict(fg=['#5cc29a','#2bad7a','#17A06B','#159363','#30b07e','#169b68','#128659'], sg=['#3f7f66','#0e5f40','#0a4730'], dk='#0c4f35'),
    'white':  dict(fg=['#ffffff','#f8fafc','#f0f3f7','#e6eaf0','#f5f7fa','#ebeff4','#dbe1e9'], sg=['#b9c2ce','#8f9aaa','#768193'], dk='#4a576b'),
}
_uid = [0]
def symbol(color, shadow=True):
    _uid[0] += 1
    u = f's{_uid[0]}'
    s = SYM_SRC
    p = PAL[color]
    base = PAL['blue']
    for a, b in zip(base['fg'], p['fg']): s = s.replace(f'stop-color="{a}"', f'stop-color="{b}"')
    for a, b in zip(base['sg'], p['sg']): s = s.replace(f'stop-color="{a}"', f'stop-color="{b}"')
    s = s.replace('flood-color="#102758"', f'flood-color="{p["dk"]}"')
    if not shadow:
        s = s.replace('flood-color="#1a0f0b" flood-opacity=".42"', 'flood-color="#1a0f0b" flood-opacity="0"')
    s = s.replace('cbs1', u)
    s = re.sub(r'style="[^"]*"', 'style="display:block;height:100%;width:auto;overflow:visible"', s, count=1)
    s = s.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    return s

def file_uri(p): return 'file://' + str(p)

def data_uri(path, mime):
    return f'data:{mime};base64,' + base64.b64encode(Path(path).read_bytes()).decode()

# 클립마켓 공식 로고(심볼+워드마크) 흰 글자판
cm_logo = (A / 'clipmarket_logo_0.svg').read_text().replace('#14202E', '#FFFFFF')
cm_logo = re.sub(r'\sdata-v-[0-9a-f]+=""', '', cm_logo).replace('cbs1', 'cmk')
(B / 'img' / 'clipmarket_logo_white.svg').write_text(cm_logo)
(B / 'img' / 'clipbiz_logo_white.svg').write_text((A / 'clipbiz_logo_white.svg').read_text())

FONTS = f"""
@font-face{{font-family:'Pretendard';src:url('{file_uri(B/'fonts/PretendardVariable.woff2')}') format('woff2');font-weight:45 920;font-style:normal}}
@font-face{{font-family:'NSerif';src:url('{file_uri(B/'fonts/noto-serif-kr-korean-600-normal.woff2')}') format('woff2');font-weight:600}}
@font-face{{font-family:'NSerif';src:url('{file_uri(B/'fonts/noto-serif-kr-korean-700-normal.woff2')}') format('woff2');font-weight:700}}
@font-face{{font-family:'NSerif';src:url('{file_uri(B/'fonts/noto-serif-kr-korean-900-normal.woff2')}') format('woff2');font-weight:900}}
@font-face{{font-family:'NSerif';src:url('{file_uri(B/'fonts/noto-serif-kr-korean-500-normal.woff2')}') format('woff2');font-weight:500}}
@font-face{{font-family:'Plex';src:url('{file_uri(B/'fonts/ibm-plex-sans-kr-korean-400-normal.woff2')}') format('woff2');font-weight:400}}
@font-face{{font-family:'Plex';src:url('{file_uri(B/'fonts/ibm-plex-sans-kr-korean-500-normal.woff2')}') format('woff2');font-weight:500}}
@font-face{{font-family:'Plex';src:url('{file_uri(B/'fonts/ibm-plex-sans-kr-korean-600-normal.woff2')}') format('woff2');font-weight:600}}
"""

GRAIN = "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.55 0'/></filter><rect width='300' height='300' filter='url(%23n)'/></svg>\")"

BASE_CSS = FONTS + f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;background:#000}}
.c{{width:{W}px;height:{H}px;position:relative;overflow:hidden;font-family:'Pretendard',sans-serif;color:#fff;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;word-break:keep-all}}
.bg,.glow,.glow2,.grain,.vig{{position:absolute;inset:0}}
.grain{{background-image:{GRAIN};mix-blend-mode:soft-light;opacity:.55}}
.vig{{background:radial-gradient(120% 120% at 30% 35%,rgba(0,0,0,0) 52%,rgba(0,0,0,.30) 100%)}}
.logo{{position:absolute;left:72px;top:54px;height:48px;display:flex;align-items:center;gap:13px}}
.logo .sym{{height:46px;display:block;flex:none}}
.logo .wm{{font-size:35px;font-weight:800;letter-spacing:-.035em;line-height:1;white-space:nowrap}}
.logo img{{display:block}}
.eyebrow{{position:absolute;left:74px;font-size:24px;font-weight:600;letter-spacing:-.012em;color:rgba(255,255,255,.80);white-space:nowrap}}
.h{{position:absolute;left:72px;font-weight:800;letter-spacing:-.042em;line-height:1.19;white-space:nowrap;text-shadow:0 2px 26px rgba(0,0,0,.16)}}
.foot{{position:absolute;left:72px;bottom:46px;font-size:23.5px;font-weight:500;letter-spacing:-.015em;color:rgba(255,255,255,.78);white-space:nowrap;padding-top:17px}}
.foot::before{{content:'';position:absolute;left:0;top:0;width:var(--fw,470px);height:1px;background:linear-gradient(90deg,rgba(255,255,255,.42),rgba(255,255,255,.10))}}
.card{{position:absolute;background:#fff;color:#0B1A2E;border-radius:22px;box-shadow:0 46px 90px -28px rgba(0,0,0,.55),0 18px 36px -14px rgba(0,0,0,.30),0 0 0 1px rgba(255,255,255,.14)}}
.sheet{{position:absolute;background:rgba(255,255,255,.16);border-radius:22px;border:1px solid rgba(255,255,255,.20)}}
/* 결재란 */
.lab{{font-size:15.5px;font-weight:700;letter-spacing:-.01em;color:#55667C}}
.tag{{font-size:12.5px;font-weight:700;color:#7A889B;border:1px solid #D5DEEA;border-radius:999px;padding:3px 9px;letter-spacing:0}}
.gy{{display:grid;border:1.5px solid #CFD9E6;border-radius:13px;overflow:hidden}}
.gy .hd{{background:#F1F5FA;color:#17395E;font-size:14.5px;font-weight:700;letter-spacing:-.03em;text-align:center;padding:10px 0 9px;border-right:1px solid #D9E2EC;border-bottom:1px solid #D9E2EC;white-space:nowrap}}
.gy .st{{display:grid;place-items:center;border-right:1px solid #E3E9F1;height:92px}}
.gy .cp{{font-size:11.6px;font-weight:500;color:#7A889B;text-align:center;padding:0 2px 11px;border-right:1px solid #E3E9F1;letter-spacing:-.04em;white-space:nowrap}}
.gy>*:nth-child(6n){{border-right:0}}
.gy .hd.now{{background:#FFF1E8;color:#B93C0A}}
.seal{{width:56px;height:56px;border-radius:50%;border:2.6px solid var(--ink,#1D4A85);color:var(--ink,#1D4A85);display:grid;place-items:center;font-size:15.5px;font-weight:800;letter-spacing:-.02em;position:relative}}
.seal::after{{content:'';position:absolute;inset:3.6px;border-radius:50%;border:1.1px solid currentColor;opacity:.5}}
.seal.now{{--ink:#C2410C;border-radius:13px;width:60px;height:42px;background:#FFF6F0}}
.seal.now::after{{border-radius:9px}}
.seal.wait{{border:2px dashed #C3CEDB;color:transparent}}
.seal.wait::after{{display:none}}
"""

def page(css, body):
    return f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><style>{BASE_CSS}{css}</style></head><body><div class='c'>{body}</div></body></html>"

def gyeoljae(heads, caps, states, now_label='지급'):
    """결재란: states는 done, now, wait"""
    rot = [-7, 5, -4, 6, 0, 0]
    h = ''.join(f"<div class='hd{' now' if s=='now' else ''}'>{t}</div>" for t, s in zip(heads, states))
    st = ''
    for i, s in enumerate(states):
        if s == 'done': st += f"<div class='st'><div class='seal' style='transform:rotate({rot[i]}deg)'>확인</div></div>"
        elif s == 'now': st += f"<div class='st'><div class='seal now'>{now_label}</div></div>"
        else: st += "<div class='st'><div class='seal wait'></div></div>"
    c = ''.join(f"<div class='cp'>{t}</div>" for t in caps)
    return f"<div class='gy' style='grid-template-columns:repeat(6,1fr)'>{h}{st}{c}</div>"

# ---------- 안심클립 ----------
def ansimclip():
    css = """
    .bg{background:linear-gradient(118deg,#083A32 0%,#0D5145 46%,#136657 100%)}
    .glow{background:radial-gradient(70% 90% at 12% -8%,rgba(150,255,220,.26) 0%,rgba(150,255,220,0) 62%)}
    .glow2{background:radial-gradient(52% 70% at 88% 108%,rgba(255,196,120,.16) 0%,rgba(255,196,120,0) 64%)}
    .h{top:204px;font-size:71px}
    .eyebrow{top:163px}
    .card{left:556px;top:140px;width:580px;padding:24px 24px 20px}
    .sheet{left:578px;top:126px;width:580px;height:312px;transform:rotate(3deg)}
    .card .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}
    .lab{font-size:17px}
    .gy .hd{font-size:16px;padding:11px 0 10px}
    .gy .st{height:106px}
    .seal{width:66px;height:66px;font-size:18px;border-width:3px}
    .seal::after{inset:4.2px;border-width:1.3px}
    .seal.now{width:70px;height:48px;border-radius:14px}
    .gy .cp{font-size:12.6px;padding-bottom:12px}
    .stt{display:flex;justify-content:space-between;align-items:center;margin-top:15px;font-size:14.5px;letter-spacing:-.02em;color:#55667C;font-weight:600}
    .stt span:first-child{display:flex;align-items:center;gap:8px}
    .stt u{display:block;width:8px;height:8px;border-radius:50%;background:#12A06B}
    .stt b{color:#B93C0A;font-weight:800}
    """
    heads = ['견적', '계약', '발주', '납품과 검수', '지급증빙', '연도마감']
    caps = ['견적 비교표', '계약서 직인본', '통합발주서', '납품, 검수 기록', '이체확인증', '감면 신청 자료']
    body = f"""
    <div class='bg'></div><div class='glow'></div><div class='glow2'></div><div class='vig'></div><div class='grain'></div>
    <div class='logo'><span class='sym'>{symbol('white')}</span><span class='wm'>안심클립</span></div>
    <div class='eyebrow'>장애인표준사업장 연계고용 거래 관리</div>
    <div class='h'>견적부터<br>지급증빙까지<br>한곳에서</div>
    <div class='foot'>표준사업장, 직업재활시설과 기업을 잇습니다</div>
    <div class='sheet'></div>
    <div class='card'><div class='top'><span class='lab'>거래 한 건이 남기는 자료</span></div>
    {gyeoljae(heads, caps, ['done','done','done','done','now','wait'])}
    <div class='stt'><span>견적, 계약, 발주, 납품과 검수 확인됨</span><b>지금 차례: 지급증빙</b></div></div>
    """
    return page(css, body)

# ---------- 클립마켓 ----------
def clipmarket():
    css = f"""
    .bg{{background:linear-gradient(118deg,#181040 0%,#271C5E 48%,#3A2B84 100%)}}
    .glow{{background:radial-gradient(70% 90% at 10% -10%,rgba(176,160,255,.30) 0%,rgba(176,160,255,0) 62%)}}
    .glow2{{background:radial-gradient(50% 70% at 92% 110%,rgba(232,150,42,.20) 0%,rgba(232,150,42,0) 64%)}}
    .logo img{{height:62px;margin-left:-2px;margin-top:2px}}
    .eyebrow{{top:160px}}
    .h{{top:201px;font-size:66px}}
    .photo{{position:absolute;left:652px;top:78px;width:484px;height:348px;border-radius:22px;overflow:hidden;box-shadow:0 46px 90px -28px rgba(0,0,0,.6),0 18px 36px -14px rgba(0,0,0,.34),0 0 0 1px rgba(255,255,255,.16)}}
    .photo img{{width:100%;height:100%;object-fit:cover;object-position:50% 62%;display:block}}
    .photo::after{{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(24,16,64,.16) 0%,rgba(24,16,64,0) 30%,rgba(24,16,64,.22) 100%)}}
    .ptag{{position:absolute;right:16px;top:16px;z-index:2;background:rgba(255,255,255,.94);color:#271C5E;font-size:14.5px;font-weight:800;border-radius:999px;padding:6px 13px;letter-spacing:-.02em}}
    .card{{left:622px;top:336px;width:300px;padding:15px 16px 16px;border-radius:20px}}
    .card .top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:11px}}
    .lab{{font-size:15px}}
    .gy .st{{height:82px}}
    .gy .hd{{font-size:15.5px;padding:9px 0 8px;color:#2B2063;background:#F3F1FB;border-color:#DEDAF0}}
    .gy>*:nth-child(3n){{border-right:0}}
    .seal{{--ink:#3B2C86;width:56px;height:56px;font-size:15.5px}}
    .gy{{border-color:#D3CEEA}} .gy .st{{border-color:#E7E4F4}}
    .gy .cp{{display:none}}
    """
    body = f"""
    <div class='bg'></div><div class='glow'></div><div class='glow2'></div><div class='vig'></div><div class='grain'></div>
    <div class='logo'><img src='{file_uri(B/'img/clipmarket_logo_white.svg')}'></div>
    <div class='eyebrow'>기업 간 중고 설비, 자재 거래</div>
    <div class='h'>세워 둔 설비와<br>남은 자재,<br>입찰을 받아 파세요</div>
    <div class='foot'>대금은 판매기업 계좌로 직접, 구매기업 이용료 없음</div>
    <div class='photo'><span class='ptag'>예시 매물</span><img src='{file_uri(A/'cm_forklift_s.jpg')}'></div>
    <div class='card'><div class='top'><span class='lab'>거래 한 건이 남기는 기록</span><span class='tag'>예시</span></div>
    <div class='gy' style='grid-template-columns:repeat(3,1fr)'><div class='hd'>입찰</div><div class='hd'>선정</div><div class='hd'>계약</div>
    <div class='st'><div class='seal' style='transform:rotate(-7deg)'>확인</div></div><div class='st'><div class='seal' style='transform:rotate(5deg)'>확인</div></div><div class='st'><div class='seal' style='transform:rotate(-4deg)'>확인</div></div></div></div>
    """
    return page(css, body)

# ---------- 클립비즈 ----------
def clipbiz(eyebrow='HD현대중공업 사내벤처로 출발한 클립비즈'):
    css = f"""
    .bg{{background:linear-gradient(118deg,#06162A 0%,#0D2642 48%,#17395E 100%)}}
    .glow{{background:radial-gradient(70% 90% at 10% -10%,rgba(120,175,255,.26) 0%,rgba(120,175,255,0) 62%)}}
    .glow2{{background:radial-gradient(50% 70% at 92% 110%,rgba(255,110,65,.20) 0%,rgba(255,110,65,0) 64%)}}
    .logo img{{height:60px;margin-left:-3px}}
    .eyebrow{{top:166px;color:#FFB59B}}
    .h{{top:206px;font-size:64px}}
    .card{{left:676px;top:112px;width:458px;padding:8px 24px}}
    .row{{display:flex;align-items:center;gap:16px;height:112px;border-bottom:1px solid #E3E9F1}}
    .row:last-child{{border-bottom:0}}
    .row .sy{{height:44px;width:54px;flex:none;display:flex;align-items:center}}
    .row .nm{{font-size:27px;font-weight:800;letter-spacing:-.04em;line-height:1.1}}
    .row .ds{{font-size:17px;font-weight:500;color:#55667C;letter-spacing:-.02em;margin-top:6px}}
    .row .on{{margin-left:auto;display:flex;align-items:center;gap:7px;font-size:14.5px;font-weight:700;color:#0E6B4F;background:#E6F4EE;border-radius:999px;padding:7px 14px;letter-spacing:-.02em;white-space:nowrap}}
    .row .on u{{display:block;width:8px;height:8px;border-radius:50%;background:#12A06B}}
    """
    rows = [('blue', '안심클립', '연계고용 거래'), ('amber', '클립마켓', '유휴자산 거래'), ('green', '하이클립', '장애인 채용정보')]
    r = ''.join(f"<div class='row'><span class='sy'>{symbol(c, shadow=False)}</span><div><div class='nm'>{n}</div><div class='ds'>{d}</div></div><span class='on'>운영 중</span></div>" for c, n, d in rows)
    body = f"""
    <div class='bg'></div><div class='glow'></div><div class='glow2'></div><div class='vig'></div><div class='grain'></div>
    <div class='logo'><img src='{file_uri(B/'img/clipbiz_logo_white.svg')}'></div>
    <div class='eyebrow'>{eyebrow}</div>
    <div class='h'>장애인 고용부담금,<br>구매와 채용으로<br>줄입니다</div>
    <div class='foot'>연계고용은 안심클립, 유휴자산은 클립마켓, 채용정보는 하이클립</div>
    <div class='card'>{r}</div>
    """
    return page(css, body)

# ---------- 하이클립 ----------
def hiclip():
    css = """
    .bg{background:linear-gradient(118deg,#8E2B06 0%,#B63C0B 46%,#D4561A 100%)}
    .glow{background:radial-gradient(70% 90% at 10% -10%,rgba(255,214,170,.34) 0%,rgba(255,214,170,0) 62%)}
    .glow2{background:radial-gradient(50% 70% at 94% 112%,rgba(90,20,0,.42) 0%,rgba(90,20,0,0) 66%)}
    .vig{background:radial-gradient(120% 120% at 30% 35%,rgba(0,0,0,0) 55%,rgba(60,12,0,.34) 100%)}
    .eyebrow{top:196px;color:rgba(255,255,255,.95)}
    .foot{color:rgba(255,255,255,.95)}
    .h{top:238px;font-size:62px;line-height:1.22}
    .card{left:690px;top:104px;width:444px;padding:24px 26px 22px}
    .sheet{left:712px;top:92px;width:444px;height:372px;transform:rotate(3deg)}
    .ct{font-size:23px;font-weight:800;letter-spacing:-.04em;margin:10px 0 14px}
    .r{display:flex;align-items:center;gap:12px;padding:15px 0;border-top:1px solid #E6EBF2}
    .r .k{font-size:18.5px;font-weight:800;letter-spacing:-.03em}
    .r .v{font-size:14.5px;font-weight:500;color:#5E6E83;letter-spacing:-.025em;margin-top:5px}
    .chip{margin-left:auto;font-size:15.5px;font-weight:800;letter-spacing:-.02em;border-radius:999px;padding:8px 16px;white-space:nowrap}
    .chip.ok{background:#E3F4EC;color:#0B6B4A}
    .chip.ask{background:#FFEBDD;color:#B93C0A}
    .chip svg{display:block}
    .sum{border-top:1px solid #E6EBF2;padding-top:15px;font-size:16px;font-weight:700;color:#17395E;letter-spacing:-.02em}
    """
    ok = "<svg width='16' height='16' viewBox='0 0 16 16'><path d='M3 8.4l3.2 3.1L13 4.8' fill='none' stroke='#0B6B4A' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    ask = "<svg width='16' height='16' viewBox='0 0 16 16'><circle cx='8' cy='8' r='4.2' fill='#D9571A'/></svg>"
    rows = [('이동 접근성', '엘리베이터, 단차 없는 출입구', 'ok', '맞음'), ('문자 소통', '업무 안내를 쪽지와 문자로', 'ok', '맞음'), ('시간 조정', '오전 4시간, 협의 가능', 'ask', '물어보기')]
    r = ''.join(f"<div class='r'><div><div class='k'>{k}</div><div class='v'>{v}</div></div><span class='chip {c}'>{t}</span></div>" for k, v, c, t in rows)
    body = f"""
    <div class='bg'></div><div class='glow'></div><div class='glow2'></div><div class='vig'></div><div class='grain'></div>
    <div class='logo'><span class='sym'>{symbol('white')}</span><span class='wm'>Hi-clip</span></div>
    <div class='eyebrow'>장애인 채용정보 서비스</div>
    <div class='h'>일할 수 있는 곳인지<br>지원하기 전에 봅니다</div>
    <div class='foot'>구직자 이용료 없음, 연락처 비공개</div>
    <div class='sheet'></div>
    <div class='card'><span class='lab'>조건 비교 예시</span><div class='ct'>문서 정리와 데이터 입력</div>{r}
    <div class='sum'>2개 맞음, 1개는 지원 전에 물어보기</div></div>
    """
    return page(css, body)

# ---------- 홍책사 ----------
def hongchaksa():
    rnd = random.Random(20261114)
    stars = ''
    for i in range(330):
        x = rnd.uniform(0, W); y = rnd.uniform(0, H)
        # 오른쪽 위에서 왼쪽 아래로 흐르는 은하수 띠에 별을 더 모은다
        band = abs((x - 250) * 0.50 + (y - 300) * 0.86) / 150.0
        if rnd.random() < min(.80, band * .55): continue
        r = rnd.choice([.55, .6, .7, .8, .9, 1.0, 1.15, 1.4])
        o = rnd.uniform(.18, .85)
        col = rnd.choice(['#FFFFFF', '#FFF4DE', '#DCE8FF', '#FFE9C4'])
        stars += f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{r}' fill='{col}' opacity='{o:.2f}'/>"
    for i in range(9):
        x = rnd.uniform(40, W - 40); y = rnd.uniform(30, H - 60)
        stars += f"<circle cx='{x:.1f}' cy='{y:.1f}' r='1.9' fill='#FFF6E2' opacity='.95' filter='url(#sg)'/>"
    css = f"""
    .c{{font-family:'Plex','Pretendard',sans-serif;color:#F3ECDC}}
    .bg{{background:linear-gradient(160deg,#0A1220 0%,#0E1626 38%,#131410 78%,#1A150E 100%)}}
    .milky{{position:absolute;inset:-20%;background:radial-gradient(38% 20% at 58% 46%,rgba(170,190,235,.20),rgba(170,190,235,0) 70%),radial-gradient(30% 16% at 36% 62%,rgba(214,176,128,.13),rgba(214,176,128,0) 70%),radial-gradient(26% 14% at 76% 30%,rgba(150,170,230,.14),rgba(150,170,230,0) 70%);transform:rotate(-28deg);filter:blur(22px)}}
    .glow{{background:radial-gradient(34% 62% at 79% 54%,rgba(255,170,84,.34) 0%,rgba(255,150,70,.10) 46%,rgba(255,150,70,0) 72%)}}
    .horizon{{position:absolute;left:0;right:0;bottom:0;height:210px;background:linear-gradient(180deg,rgba(26,21,14,0) 0%,rgba(40,26,12,.55) 60%,rgba(52,30,12,.82) 100%)}}
    .vig{{background:radial-gradient(120% 120% at 34% 40%,rgba(0,0,0,0) 50%,rgba(0,0,0,.50) 100%)}}
    .grain{{opacity:.42}}
    .logo{{gap:14px;top:52px}}
    .logo img{{height:50px;width:50px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,.45)}}
    .logo .wm{{font-family:'NSerif',serif;font-weight:700;font-size:36px;letter-spacing:-.03em;color:#F5EEDF}}
    .eyebrow{{top:167px;font-family:'Plex';font-weight:500;font-size:24px;color:#D8B56B;letter-spacing:.02em}}
    .h{{top:206px;font-family:'NSerif',serif;font-weight:700;font-size:69px;letter-spacing:-.045em;line-height:1.2;color:#FBF6EA;text-shadow:0 2px 30px rgba(0,0,0,.45)}}
    .h em{{font-style:normal;color:#F0B35A}}
    .chips{{position:absolute;left:72px;bottom:46px;display:flex;gap:10px}}
    .chips span{{font-family:'Plex';font-size:21px;font-weight:500;color:#EFE7D6;border:1.4px solid rgba(239,231,214,.42);background:rgba(255,255,255,.05);border-radius:999px;padding:8px 18px 9px;letter-spacing:-.01em}}
    .grid{{position:absolute;left:560px;top:-40px;width:760px;height:700px;opacity:.9;-webkit-mask-image:radial-gradient(46% 50% at 53% 52%,#000 0%,rgba(0,0,0,.55) 46%,rgba(0,0,0,0) 78%);transform:rotate(-9deg)}}
    .board{{position:absolute;left:770px;top:128px;width:338px;height:338px;transform:rotate(-9deg);filter:drop-shadow(0 44px 46px rgba(0,0,0,.62)) drop-shadow(0 10px 14px rgba(0,0,0,.45))}}
    .board img{{width:100%;height:100%;display:block}}
    .shine{{position:absolute;left:770px;top:128px;width:338px;height:338px;transform:rotate(-9deg);border-radius:76px;background:linear-gradient(135deg,rgba(255,255,255,.22) 0%,rgba(255,255,255,0) 38%);mix-blend-mode:soft-light}}
    """
    lines = ''
    for i in range(-6, 14):
        v = 56 + i * 112.6
        lines += f"<line x1='{v:.1f}' y1='0' x2='{v:.1f}' y2='700' stroke='#F1DFB8' stroke-opacity='.20' stroke-width='1.2'/>"
        lines += f"<line x1='0' y1='{v-30:.1f}' x2='760' y2='{v-30:.1f}' stroke='#F1DFB8' stroke-opacity='.20' stroke-width='1.2'/>"
    body = f"""
    <div class='bg'></div><div class='milky'></div>
    <svg style='position:absolute;inset:0' width='{W}' height='{H}' viewBox='0 0 {W} {H}'><defs><filter id='sg' x='-400%' y='-400%' width='900%' height='900%'><feGaussianBlur stdDeviation='1.6' result='b'/><feMerge><feMergeNode in='b'/><feMergeNode in='b'/><feMergeNode in='SourceGraphic'/></feMerge></filter></defs>{stars}</svg>
    <div class='horizon'></div><div class='glow'></div>
    <svg class='grid' viewBox='0 0 760 700'>{lines}</svg>
    <div class='vig'></div><div class='grain'></div>
    <div class='board'><img src='{file_uri(A/'hcs_icon512.png')}'></div><div class='shine'></div>
    <div class='logo'><img src='{file_uri(A/'hcs_icon512.png')}'><span class='wm'>홍책사</span></div>
    <div class='eyebrow'>사주, 주역, 타로</div>
    <div class='h'>내 고민엔<br>어떤 <em>한 수</em>가<br>나올까요</div>
    <div class='chips'><span>궁합</span><span>2027년 흐름</span><span>내 사주</span><span>타로</span></div>
    """
    return page(css, body)

BRANDS = {'ansimclip': ansimclip, 'clipmarket': clipmarket, 'clipbiz': clipbiz, 'hiclip': hiclip, 'hongchaksa': hongchaksa, 'clipbiz_b': lambda: clipbiz('안심클립, 클립마켓, 하이클립을 운영합니다')}

async def render(names):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome', headless=True, args=['--no-sandbox', '--font-render-hinting=none'])
        ctx = await b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=2)
        pg = await ctx.new_page()
        for n in names:
            html = BRANDS[n]()
            hp = OUT / f'{n}.html'
            hp.write_text(html, encoding='utf-8')
            await pg.goto(file_uri(hp))
            await pg.evaluate('document.fonts.ready')
            await pg.wait_for_timeout(500)
            await pg.screenshot(path=str(OUT / f'{n}@2x.png'), clip={'x': 0, 'y': 0, 'width': W, 'height': H})
            im = Image.open(OUT / f'{n}@2x.png').convert('RGB')
            im.resize((W, H), Image.LANCZOS).save(OUT / f'{n}.png', optimize=True)
            print(n, 'ok', os.path.getsize(OUT / f'{n}.png') // 1024, 'KB')
        await b.close()

if __name__ == '__main__':
    names = sys.argv[1:] or list(BRANDS)
    asyncio.run(render(names))
