# 261103 새 형식 6편

| 파일 | 브랜드 | 형식 | 길이 | 만든 방법 |
|---|---|---|---|---|
| V-hcs-battle1.mp4 | 홍책사 | 천간 배틀 로얄 1회전(물리 시뮬) | 24.5초 | tools/viral/battle.py render --seed 364 --ep 1 |
| V-hcs-chat1.mp4 | 홍책사 | 동창 단톡방 1탄(잘못 보낸 방) | 27.4초 | tools/viral/chat.py V-hcs-chat1.json |
| V-hcs-rank1.mp4 | 홍책사 | 일간별 순위 1탄 | 19.1초 | tools/viral/kinetic.py V-hcs-rank1.json |
| V-b2b-chat1.mp4 | 클립비즈(안심클립) | 박 대리의 연말 1화(잘못 보낸 방) | 27.0초 | tools/viral/chat.py V-b2b-chat1.json |
| V-b2b-race1.mp4 | 클립비즈(클립마켓) | 창고 설비 레이스 1회(마블 레이스) | 28.2초 | tools/viral/race.py render --seed 272 |
| V-hic-alert1.mp4 | 하이클립 | 박 대리의 첫 채용 1화(머릿속 알림) | 16.6초 | tools/viral/kinetic.py V-hic-alert1.json |

음악과 효과음은 tools/viral/sound.py에서 직접 합성(폰크, 피치카토, 시스템 GM 사운드폰트). 남의 음원과 샘플 없음.
