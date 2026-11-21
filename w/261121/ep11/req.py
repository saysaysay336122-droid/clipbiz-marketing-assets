"""11화 드롭샷 요청문. python3 req.py home_url mn_url mil_url fil_url -> req.json"""
import json, sys
sys.path.insert(0, "/home/claude/clipbiz-marketing-assets/tools")
from episode_preflight import build_prompts
spec = json.load(open("/home/claude/clipbiz-marketing-assets/w/261121/ep11_spec.json", encoding="utf-8"))
args = dict(a.split("=", 1) for a in sys.argv[1:])
setp, shots, neg = build_prompts(spec)
NAME = {"mn": "며느리", "mil": "시어머니", "fil": "시아버지", "hong": "홍책사"}
SETN = {"cafe": "카페 창가", "home": "아파트 거실"}
face = {"hong": spec["characters"]["hong"]["face"], "mn": args.get("mn"), "mil": args.get("mil"), "fil": args.get("fil")}
seturl = {"cafe": spec["sets"]["cafe"]["url"], "home": args.get("home")}
byid = {s["id"]: s for s in spec["shots"]}
out = {"_set_home": {"prompt": setp["home"], "aspect_ratio": "9:16", "resolution": "2K"}}
for p in shots:
    sh = byid[p["id"]]
    urls, names = [], []
    for c in sh.get("chars", []):
        if face.get(c):
            urls.append(face[c]); names.append(f"{NAME[c]} 얼굴")
    if seturl.get(sh["set"]):
        urls.append(seturl[sh["set"]]); names.append(f"장소 {SETN[sh['set']]}")
    order = ", ".join(f"{i+1}번 {n}" for i, n in enumerate(names))
    pre = (f"참고 이미지 순서: {order}. 인물 얼굴은 해당 참고 이미지와 똑같이, 장소는 참고 이미지와 같은 공간으로. " if urls else "")
    out[p["id"]] = {"still": {"prompt": pre + p["still"], "input_image": urls, "aspect_ratio": "9:16", "resolution": "2K"},
                    "video": p["video"], "sec": p["sec"], "audio": p["audio"]}
json.dump(out, open("req.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print({k: len(v["still"]["input_image"]) if k[0] != "_" else 0 for k, v in out.items()})
