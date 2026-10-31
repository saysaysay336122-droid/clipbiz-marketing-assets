# clipbiz-marketing-assets

클립비즈(홍책사, 안심클립, 하이클립, 클립마켓) 홍보 자료 보관소입니다.

w/YYMMDD/ 그 주 월요일 기준 카드 이미지, 릴스 영상, 원본 문안(spec.json)
tools/render_cards.py spec.json을 1080x1350 카드 이미지로 만든다
tools/render_reel.py 카드 이미지를 1080x1920 릴스 영상으로 만든다
tools/make_qr.py 우편 안내문용 QR 이미지를 만든다
tools/render_short.py 실사 영상 위에 글을 얹어 릴스와 쇼츠(1080x1920)를 만든다
tools/build_week.py 구글 시트 '클립비즈_제작지시'를 읽어 카드, 영상, 블로그 글 파일을 만든다
.github/workflows/render.yml 15분마다 제작지시 시트를 확인해 build_week.py를 돌리고 main에 올린다(시트 주소는 비밀값 SHEET_CSV)
docs/ 클립비즈 인사이트 블로그 https://insight.clipbiz.kr (GitHub Pages, Jekyll). 글은 docs/_posts/ 에 둔다

문의 clipbiz@naver.com
