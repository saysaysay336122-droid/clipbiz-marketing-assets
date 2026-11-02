# 261103 새 형식 7편(2차)

| 파일 | 브랜드 | 형식 | 길이 | 만든 방법 |
|---|---|---|---|---|
| V-hcs-chat1.mp4 | 홍책사 | 동창 단톡방 1탄, 친구 남친 사주 험담을 그 친구한테(11초 재입장) | 31초 | tools/viral/chat.py V-hcs-chat1.json |
| V-hcs-chat2.mp4 | 홍책사 | 사주 과몰입 지수 1화, 소개팅 세 번째 메시지 | 31초 | tools/viral/chat.py V-hcs-chat2.json |
| V-hcs-battle1.mp4 | 홍책사 | 천간 배틀 로얄 1회전(탈락 유언 포함) | 24.5초 | tools/viral/battle.py render --seed 364 --ep 1 |
| V-hcs-rank1.mp4 | 홍책사 | 일간별 순위 1탄 | 19초 | tools/viral/kinetic.py V-hcs-rank1.json |
| V-b2b-chat1.mp4 | 클립비즈(안심클립) | 박 대리의 연말 1화, 속마음 메모 보고서 | 30초 | tools/viral/chat.py V-b2b-chat1.json |
| V-b2b-race1.mp4 | 클립비즈(클립마켓) | 창고 설비 레이스 1회(선두 중계 포함) | 28초 | tools/viral/race.py render --seed 272 |
| V-hic-chat1.mp4 | 하이클립 | 박 대리의 첫 채용 1화, 경사로 없다고 썼다가 | 29초 | tools/viral/chat.py V-hic-chat1.json |

음악과 효과음은 tools/viral/sound.py에서 직접 합성. 남의 음원과 샘플 없음. 끝은 드라마식 '다음 화에 계속'.
