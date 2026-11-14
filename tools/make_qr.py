"""우편 안내문에 붙일 QR 이미지를 만든다.

사용법: python3 make_qr.py "<주소>" <출력 png>
필요 패키지: pip install qrcode pillow (--break-system-packages)
"""
import sys
import qrcode

img = qrcode.make(sys.argv[1], box_size=10, border=2)
img.save(sys.argv[2])
print(sys.argv[2])
