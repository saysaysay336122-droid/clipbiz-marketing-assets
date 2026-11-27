import subprocess, sys
from PIL import Image
sys.path.insert(0,'.')
from spec import ALL
def sheet(vid, out, w=360):
    v=[x for x in ALL if x['id']==vid][0]
    t=0; ims=[]
    for i,sc in enumerate(v['scenes']):
        at = 0.0 if i==0 else t+sc['dur']*0.6
        p=f'tmp/{vid}_f{i}.png'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',f'{at:.2f}','-i',f'out/hcs_{vid}.mp4','-frames:v','1',p],check=True)
        im=Image.open(p); im=im.resize((w,int(w*1920/1080))); ims.append(im); t+=sc['dur']
    s=Image.new('RGB',(w*len(ims),ims[0].height))
    for i,im in enumerate(ims): s.paste(im,(i*w,0))
    s.save(out,quality=88)
if __name__=='__main__':
    for vid in sys.argv[1:]: sheet(vid, f'tmp/sheet_{vid}.jpg')
