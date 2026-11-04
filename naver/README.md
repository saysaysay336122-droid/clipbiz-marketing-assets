# 네이버 블로그 원고 묶음

blog.naver.com/clipbiz 원고를 붙여넣기 페이지 하나로 만든다. 대표는 페이지에서 제목 복사, 본문 복사 두 번 누르고 네이버에서 예약 발행만 한다.

만들기: python3 tools/naver_pack.py naver/YYMM/spec.json 출력폴더
spec 형식은 tools/naver_pack.py 머리말. 카드는 1080x1080 직접 렌더(로고, 주소 워터마크, 사진 소재 없음), 페이지 안에 data URI로 들어가 본문 복사 때 함께 복사된다. 본문 끝 #태그는 네이버가 태그로 자동 등록한다.
사진이 빠지는 경우를 대비해 글마다 사진 n 복사 버튼(PNG)이 있다.

폴더: naver/YYMM/spec.json 이 그 묶음의 원문이다. 새 글을 쓰기 전에 지난 묶음 spec과 문장이 겹치지 않는지 대조한다.
