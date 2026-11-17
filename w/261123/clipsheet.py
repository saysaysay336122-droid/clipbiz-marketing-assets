import sys,subprocess,json
from PIL import Image,ImageDraw,ImageFont
f=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',22)
ids=sys.argv[1].split(','); out=sys.argv[2]; n=int(sys.argv[3]) if len(sys.argv)>3 else 6
rows=[]
for k in ids:
    p=f'clips/{k}.mp4'
    info=json.loads(subprocess.run(['ffprobe','-v','error','-show_entries','stream=width,height,codec_type:format=duration','-of','json',p],capture_output=True,text=True).stdout)
    dur=float(info['format']['duration'])
    ims=[]
    for i in range(n):
        t=0.1+i*(dur-0.2)/(n-1)
        o=f'/tmp/fr_{k}_{i}.png'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',f'{t:.2f}','-i',p,'-frames:v','1','-vf','scale=200:-2',o])
        ims.append((t,Image.open(o)))
    rows.append((k,ims,info))
w,h=rows[0][1][0][1].size
sheet=Image.new('RGB',(w*n,(h+28)*len(rows)),'white');d=ImageDraw.Draw(sheet)
for r,(k,ims,info) in enumerate(rows):
    st=[s for s in info['streams']]
    d.text((4,r*(h+28)+2),f"{k} {st[0].get('width')}x{st[0].get('height')} {float(info['format']['duration']):.2f}s audio={'audio' in [s['codec_type'] for s in st]}",font=f,fill=(0,0,0))
    for i,(t,im) in enumerate(ims):
        sheet.paste(im,(i*w,r*(h+28)+28)); d.text((i*w+4,r*(h+28)+30),f'{t:.1f}',font=f,fill=(255,255,0))
sheet.save(out,quality=85)
