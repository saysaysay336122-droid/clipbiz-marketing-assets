"""홍책사 7화 답장 무르기 편집. 설계서 v2 시간표 그대로.
사용: python3 build.py [샷id ...]  (샷 id를 주면 그 구간만 다시 만든다)
"""
import json, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
import sfx  # noqa: E402
import animatic as AN  # noqa: E402

D = "/home/claude/ep7/v"
SPEC = json.load(open("/home/claude/ep7/ep07_spec_v2.json", encoding="utf-8"))
ASR = json.load(open(f"{D}/asr.json", encoding="utf-8")) if os.path.exists(f"{D}/asr.json") else {}
MUSIC = "/home/claude/ep7/ep07_music_v2.wav"
COIN = "/home/claude/ep6/v4/stills/coin.png"
W, H, FPS, SR = 1080, 1920, 30, 48000
FD = "/usr/share/fonts/opentype/noto/"
os.makedirs(f"{D}/ov", exist_ok=True)
os.makedirs(f"{D}/seg", exist_ok=True)


def F(p, s):
    for i in range(10):
        f = ImageFont.truetype(FD + p, s, index=i)
        if "KR" in f.getname()[0]:
            return f
    return ImageFont.truetype(FD + p, s)


SUBF = F("NotoSansCJK-Bold.ttc", 60)
CAPF = F("NotoSansCJK-Bold.ttc", 66)
NOTEF = F("NotoSansCJK-Regular.ttc", 38)
TAGF = F("NotoSansCJK-Bold.ttc", 44)
SMALL = F("NotoSansCJK-Regular.ttc", 24)
BIGF = F("NotoSansCJK-Bold.ttc", 96)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:800])
        print(r.stderr[-2000:])
        raise SystemExit(1)
    return r


def canvas():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def center_lines(dr, lines, font, y, lh, stroke=5, fill=(255, 255, 255)):
    for i, l in enumerate(lines):
        w = dr.textlength(l, font=font)
        dr.text(((W - w) / 2, y + i * lh), l, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def wrap(t, n):
    return AN.wrap(t, n).split("\n")


def ov_sub(text):
    im = canvas()
    lines = wrap(text, 14)
    center_lines(ImageDraw.Draw(im), lines, SUBF, 1150 - (len(lines) - 1) * 42, 84)
    return im


def ov_caption(text, y=230):
    im = canvas()
    center_lines(ImageDraw.Draw(im), wrap(text, 13), CAPF, y, 90, stroke=6)
    return im


def ov_note(text):
    im = canvas()
    dr = ImageDraw.Draw(im)
    w = dr.textlength(text, font=NOTEF)
    dr.rounded_rectangle((40, 330, 40 + w + 44, 394), 14, fill=(0, 0, 0, 140))
    dr.text((62, 336), text, font=NOTEF, fill=(255, 255, 255, 240))
    return im


def ov_tag(text):
    im = canvas()
    dr = ImageDraw.Draw(im)
    w = dr.textlength(text, font=TAGF)
    x1 = 1040
    x0 = x1 - w - 48
    dr.rounded_rectangle((x0, 990, x1, 1062), 18, fill=(20, 20, 20, 200))
    dr.text((x0 + 24, 998), text, font=TAGF, fill=(255, 214, 80))
    return im


def ov_ai():
    im = canvas()
    dr = ImageDraw.Draw(im)
    t = "AI로 만든 가상인물"
    w = dr.textlength(t, font=SMALL)
    dr.rounded_rectangle((28, 44, 28 + w + 28, 84), 12, fill=(0, 0, 0, 120))
    dr.text((42, 48), t, font=SMALL, fill=(255, 255, 255, 200))
    return im


def save(im, name):
    p = f"{D}/ov/{name}.png"
    im.save(p)
    return p


def frame_at(clip, t):
    p = f"{D}/ov/frame_{os.path.basename(clip)}_{t:.2f}.png"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", clip, "-frames:v", "1", "-vf", f"scale={W}:{H}:flags=lanczos", p])
    return Image.open(p).convert("RGB")


SH = SPEC["shots"]
IDS = {s["id"]: s for s in SH}
TOTAL = SH[-1]["t"][1]


def clip_of(sh):
    return f"{D}/clips/{sh.get('reuse') or sh['id']}.mp4"


def sub_window(sh):
    """대사 자막이 보이는 구간(샷 안 시간). 음성 인식 구간이 있으면 그것을 쓴다."""
    u0, u1 = sh["use"]
    dur = sh["t"][1] - sh["t"][0]
    a = ASR.get(sh["id"], {})
    if a.get("span"):
        s, e = a["span"][0] - u0 - 0.08, a["span"][1] - u0 + 0.35
    else:
        s, e = sh.get("cue", 0.5) - u0, sh.get("cue", 0.5) - u0 + 1.8
    return max(0.0, s), min(dur, max(e, s + 1.0))


def video_seg(sh, out):
    a, b = sh["t"]
    dur = b - a
    u0, u1 = sh["use"]
    src = clip_of(sh)
    ins = ["-ss", f"{u0:.3f}", "-t", f"{dur + 0.2:.3f}", "-i", src]
    fl = [f"[0:v]fps={FPS},setsar=1,scale={W}:{H}:flags=lanczos,unsharp=5:5:0.4,tpad=stop_mode=clone:stop_duration=0.3,format=yuv420p[b0]"]
    ovs = []
    if sh.get("caption"):
        ovs.append((0.0, dur, ov_caption(sh["caption"])))
    if sh.get("note"):
        ovs.append((0.3, min(dur, 2.4), ov_note(sh["note"])))
    if sh.get("tag"):
        ovs.append((0.3, dur, ov_tag(sh["tag"])))
    if sh.get("line") and not sh.get("reuse"):
        s, e = sub_window(sh)
        ovs.append((s, e, ov_sub(sh.get("sub", sh["line"]))))
    last, k = "b0", 1
    for i, (s0, e0, im) in enumerate(ovs):
        p = save(im, f"{sh['id']}_{i}")
        ins += ["-framerate", str(FPS), "-loop", "1", "-t", f"{dur + 0.3:.3f}", "-i", p]
        fin = "" if (a == 0 and s0 == 0) else f"fade=in:st={s0:.3f}:d=0.12:alpha=1,"
        fl.append(f"[{k}:v]format=rgba,{fin}fade=out:st={max(s0, e0 - 0.12):.3f}:d=0.12:alpha=1[o{k}]")
        fl.append(f"[{last}][o{k}]overlay=0:0:eof_action=pass[b{k}]")
        last = f"b{k}"
        k += 1
    fl.append(f"[{last}]trim=duration={dur:.3f},setpts=PTS-STARTPTS[fin]")
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fl), "-map", "[fin]", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", out])


def prev_video(i):
    for j in range(i - 1, -1, -1):
        if SH[j]["kind"] == "video":
            return SH[j]
    return None


def chat_seg(i, sh, out):
    dur = sh["t"][1] - sh["t"][0]
    pv = prev_video(i)
    bg = frame_at(clip_of(pv), pv["use"][1] - 0.1) if pv else Image.new("RGB", (W, H), (40, 40, 40))
    frames = AN.chat_frames(sh["chat"], bg, sh.get("chat_title", "준"), sh.get("chat_me", "은서"))
    cap = ov_caption(sh["caption"], 200) if sh.get("caption") else None
    lst = f"{D}/ov/{sh['id']}_list.txt"
    with open(lst, "w") as fh:
        for k, fr in enumerate(frames):
            im = fr.convert("RGBA")
            if cap:
                im = Image.alpha_composite(im, cap)
            p = f"{D}/ov/{sh['id']}_c{k}.png"
            im.convert("RGB").save(p)
            fh.write(f"file '{p}'\nduration {dur / len(frames):.4f}\n")
        fh.write(f"file '{p}'\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"fps={FPS},format=yuv420p",
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", out])


def rewind_seg(i, sh, out):
    dur = sh["t"][1] - sh["t"][0]
    pv = prev_video(i)
    u0, u1 = pv["use"]
    span = u1 - u0
    im = canvas()
    dr = ImageDraw.Draw(im)
    for y in range(0, H, 22):
        dr.line((0, y, W, y), fill=(255, 255, 255, 46), width=2)
    center_lines(dr, [sh.get("caption", "")], BIGF, 860, 110, stroke=7, fill=(255, 226, 150))
    p = save(im, f"{sh['id']}_rw")
    fl = (f"[0:v]fps={FPS},setsar=1,scale={W}:{H}:flags=lanczos,reverse,setpts=PTS*{dur / span:.4f},"
          f"eq=saturation=0.6:brightness=0.03,gblur=sigma=1.2,format=yuv420p[b0];"
          f"[1:v]format=rgba[o];[b0][o]overlay=0:0,trim=duration={dur:.3f},setpts=PTS-STARTPTS[fin]")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{u0:.3f}", "-t", f"{span:.3f}", "-i", clip_of(pv),
         "-framerate", str(FPS), "-loop", "1", "-t", f"{dur + 0.3:.3f}", "-i", p, "-filter_complex", fl, "-map", "[fin]",
         "-r", str(FPS), "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", out])


def end_seg(sh, out):
    dur = sh["t"][1] - sh["t"][0]
    bg = AN.cover(Image.open(COIN)).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45))
    img = AN.coin_string(bg, sh["coins"]).convert("RGBA")
    dr = ImageDraw.Draw(img)
    n = len(sh["coins"])

    def c(t, f, y, fill):
        w = dr.textlength(t, font=f)
        dr.text(((W - w) / 2, y), t, font=f, fill=fill)
    c(f"{n}닢째", F("NotoSansCJK-Bold.ttc", 52), 1080, (255, 200, 60))
    c("그 사람과 잘될까 궁금할 땐", F("NotoSansCJK-Bold.ttc", 60), 1190, (255, 255, 255))
    f2 = F("NotoSansCJK-Bold.ttc", 40)
    w = dr.textlength("hongchaksa.kr", font=f2)
    dr.rounded_rectangle((540 - w / 2 - 30, 1310, 540 + w / 2 + 30, 1382), 36, outline=(210, 210, 210), width=2)
    c("hongchaksa.kr", f2, 1318, (240, 240, 240))
    p = save(img, "endcard")
    run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-loop", "1", "-t", f"{dur:.3f}", "-i", p,
         "-vf", "scale=1080:1920,setsar=1,fade=in:st=0:d=0.4,format=yuv420p", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", out])


only = sys.argv[1:]
segs = []
for i, sh in enumerate(SH):
    out = f"{D}/seg/{i:02d}_{sh['id']}.mp4"
    segs.append(out)
    if only and sh["id"] not in only and os.path.exists(out):
        continue
    if sh["kind"] == "video":
        video_seg(sh, out)
    elif sh.get("comp") == "chat":
        chat_seg(i, sh, out)
    elif sh.get("comp") == "rewind":
        rewind_seg(i, sh, out)
    else:
        end_seg(sh, out)
    print("seg", sh["id"])
with open(f"{D}/seg/list.txt", "w") as fh:
    for s in segs:
        fh.write(f"file '{s}'\n")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{D}/seg/list.txt", "-c", "copy", f"{D}/video_noai.mp4"])


# 오디오
def load(src, a, dur, ch=1):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", src, "-ac", str(ch), "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(r, np.int16).astype(float) / 32768


N = int(TOTAL * SR) + SR
dia = np.zeros(N)
duck = np.ones(N)
for sh in SH:
    if sh["kind"] != "video" or not sh.get("line") or sh.get("reuse"):
        continue
    a, b = sh["t"]
    x = load(clip_of(sh), sh["use"][0], b - a)
    if len(x) == 0:
        continue
    v = x[np.abs(x) > 0.02]
    rms = np.sqrt(np.mean(v ** 2)) if len(v) else 0.1
    x = x * min(4.0, 0.12 / max(rms, 1e-4))
    fd = int(0.02 * SR)
    x[:fd] *= np.linspace(0, 1, fd)
    x[-fd:] *= np.linspace(1, 0, fd)
    s0 = int(a * SR)
    dia[s0:s0 + len(x)] += x
    ss, se = sub_window(sh)
    i0, i1 = int((a + ss - 0.1) * SR), int((a + se) * SR)
    duck[i0:i1] = np.minimum(duck[i0:i1], 10 ** (-8 / 20))
r = int(0.15 * SR)
duck = np.convolve(duck, np.ones(r) / r, mode="same")
mus = load(MUSIC, 0, TOTAL)
mus = np.pad(mus, (0, max(0, N - len(mus))))[:N]
nz = mus[np.abs(mus) > 1e-4]
mus *= 0.07 / np.sqrt(np.mean(nz ** 2))
fxw = f"{D}/fx.wav"
events = [tuple(e) for sh in SH for e in sh.get("sfx", [])]
sfx.mix(TOTAL, fxw, events=events)
fx = load(fxw, 0, TOTAL)
fx = np.pad(fx, (0, max(0, N - len(fx))))[:N]
fx *= 0.5 / max(np.abs(fx).max(), 1e-6)
mix = dia + mus * duck + fx
e = int(TOTAL * SR)
fo = int(0.6 * SR)
mix[e - fo:e] *= np.linspace(1, 0, fo)
mix = np.clip(mix[:e], -1, 1)
st = np.stack([mix, mix], 1)
with wave.open(f"{D}/mix.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
rr = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{D}/mix.wav", "-af", "loudnorm=I=-14:TP=-2:LRA=11:print_format=json", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
js = json.loads(rr[rr.rfind("{"):rr.rfind("}") + 1])
ln = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
      f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
aip = save(ov_ai(), "ai")
OUT = f"{D}/hcs_ep07_mureugi.mp4"
run(["ffmpeg", "-v", "error", "-y", "-i", f"{D}/video_noai.mp4", "-framerate", "30", "-loop", "1", "-i", aip, "-i", f"{D}/mix.wav",
     "-filter_complex", f"[1:v]format=rgba[a];[0:v][a]overlay=0:0:shortest=1,format=yuv420p[v];[2:a]{ln},alimiter=limit=0.55:attack=1:release=50:level=disabled,aresample=48000[au]",
     "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", "30", "-c:a", "aac", "-b:a", "192k",
     "-movflags", "+faststart", "-t", f"{TOTAL:.3f}", OUT])
print("OUT", OUT, TOTAL)
