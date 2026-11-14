# 링크 미리보기 이미지 만들기

카카오톡, 문자, 메신저에 주소를 보냈을 때 뜨는 미리보기 이미지(1200x600, 가로 2 대 세로 1)를 다섯 사이트 것으로 만든다.

## 준비

1. 크롬과 파이썬 playwright, Pillow가 있어야 한다.
2. 글꼴은 저장소에 넣지 않았다. 아래로 받아 fonts 폴더에 둔다.

```
npm install pretendard @fontsource/noto-serif-kr @fontsource/ibm-plex-sans-kr
mkdir -p fonts
cp node_modules/pretendard/dist/web/variable/woff2/PretendardVariable.woff2 fonts/
cp node_modules/@fontsource/noto-serif-kr/files/noto-serif-kr-korean-{500,600,700,900}-normal.woff2 fonts/
cp node_modules/@fontsource/ibm-plex-sans-kr/files/ibm-plex-sans-kr-korean-{400,500,600}-normal.woff2 fonts/
```

## 만들기

```
python3 build.py                 # 다섯 장 모두, out 폴더에 PNG
python3 build.py hiclip          # 한 장만
python3 sim.py                   # 카카오톡 크기 전후 비교(before 폴더에 지금 이미지, copy.json에 문구)
```

문구와 배치는 build.py의 브랜드별 함수에서 고친다. 고친 뒤에는 카카오톡 크기(폭 232px)로 줄여 제목이 읽히는지 본다.

## 지킬 것

1. 크기는 1200x600. 카카오가 2 대 1에 맞춰 보여 준다.
2. 이미지 안 문구는 사이트 첫 화면과 기준정보에 있는 말만 쓴다.
3. 심볼과 로고는 assets 폴더의 공식 파일을 색만 바꿔 쓴다.
4. 사진은 클립마켓 사이트의 예시 매물 사진을 쓴다. 사람 얼굴이 나오는 사진과 AI로 만든 사진은 쓰지 않는다.
5. 이미지를 바꾸면 파일 이름을 바꿔 올린다. 카카오가 이미지 주소로 캐시를 잡는다.
