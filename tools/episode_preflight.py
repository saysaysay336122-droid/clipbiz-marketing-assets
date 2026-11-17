"""회차 설계서(JSON)를 생성 전에 점검하고, 드롭샷 지시문과 크레딧 견적을 만든다.

사용: python3 episode_preflight.py 설계서.json [출력.md]
점검 항목(하나라도 '실패'면 생성하지 않는다)
  1. 시간표가 0초부터 빈틈없이 이어지고 목표 길이와 맞는가
  2. 영상 샷의 생성 길이(4~15초)와 사용 구간이 맞는가, 재사용 클립은 원본이 있는가
  3. 대사 속도: 초당 4음절 이하, 한 샷 한 사람, 말하는 사람이 샷 인물에 있는가
  4. 대사 없는 샷은 오디오 끔(엉뚱한 말 방지), 대사 있는 샷은 오디오 켬
  5. 첫 대사나 첫 소리가 0.5초 안에 나오는가
  6. 같은 음절이 낱말 경계에서 겹치는 대사(예: 말 말고) 경고
  7. 자막과 대사의 금지 기호와 금지 표현
  8. 처음 3초 자막에 주소, 로고, 제도 용어가 없는가
  9. 모든 영상 샷에 시작 사진과 얼굴 참고 이미지가 있는가
 10. 크레딧 견적(사진 장당 단가, 영상 초당 단가, 재사용은 한 번만)
"""
import json
import re
import sys

BANNED_CHARS = ["·", "・", "‧", "∙", "•", "!", "…", "—", "–", "→", "←", "※"]
BANNED_WORDS = ["결론부터", "핵심은", "단순히", "특히 주목할", "종합적으로", "시사점", "매우 중요", "효과적으로", "혁신", "획기적",
                "최적", "강력한", "한 단계 더", "솔루션", "시너지", "인사이트", "지금 바로", "놓치지 마세요", "보장", "최초", "실화", "합격 확정"]
EARLY_BANNED = ["hongchaksa", ".kr", "부담금", "연계고용", "안심클립", "클립비즈"]
PRICE = {"nano-banana-pro": 75, "seedream-5-lite": 17.5}
VIDEO_PER_SEC = 75


def syllables(s):
    return len(re.findall(r"[가-힣]", s))


def boundary_repeat(s):
    words = re.findall(r"[가-힣]+", s)
    hits = []
    for a, b in zip(words, words[1:]):
        if a[-1] == b[0]:
            hits.append(f"{a} {b}")
    return hits


def build_prompts(spec):
    ch = spec["characters"]
    sets = spec["sets"]
    still_suffix = spec["style"]["still"]
    video_suffix = spec["style"]["video"]
    neg = spec["style"]["negative"]
    out = []
    set_prompts = {}
    for k, s in sets.items():
        set_prompts[k] = f"9:16 세로, 사람 없는 빈 장소 기준 사진. {s['desc']} {still_suffix}"
    for sh in spec["shots"]:
        if sh["kind"] == "still":
            people = " ".join(ch[c]["fixed"] for c in sh.get("chars", []))
            refs = [ch[c]["face"] for c in sh.get("chars", [])] + [f"[장소 {sh['set']} 기준 사진]"] + sh.get("refs_extra", [])
            still = f"9:16 세로. {sh['framing']} {people} 장소: {sets[sh['set']]['desc']} 순간: {sh['still']} {still_suffix}"
            out.append(dict(id=sh["id"], refs=refs, still=still, video=None, sec=0, audio=False,
                            still_url=sh.get("still_url"), still_only=True))
            continue
        if sh["kind"] != "video" or sh.get("reuse"):
            continue
        people = " ".join(ch[c]["fixed"] for c in sh["chars"])
        refs = [ch[c]["face"] for c in sh["chars"]] + [f"[장소 {sh['set']} 기준 사진]"] + sh.get("refs_extra", [])
        still = f"9:16 세로. {sh['framing']} {people} 장소: {sets[sh['set']]['desc']} 순간: {sh['still']} {still_suffix}"
        if sh.get("line"):
            sp = ch[sh["speaker"]]
            sound = (f"대사: {sp['name']}만 {sp['voice']} 목소리로 {sh.get('cue', 0.5)}초쯤 한 번 말한다. \"{sh['line']}\" "
                     f"다른 인물은 말하지 않는다. 말 뒤에는 숨소리와 작은 현장음만.")
        else:
            sound = "대사 없음. 사람 목소리와 말소리 없음, 작은 현장음만."
        video = (f"시작 사진에서 이어지는 한 컷, 장면 전환 없음. 카메라: {sh['camera']} 동작: {sh['action']} {sound} "
                 f"시작 사진과 같은 얼굴, 머리, 옷, 소품, 빛을 끝까지 유지. {video_suffix}")
        video = f"{video} 넣지 말 것: {neg}."
        out.append(dict(id=sh["id"], refs=refs, still=still, video=video, sec=sh["gen_sec"], audio=bool(sh.get("line")),
                        still_url=sh.get("still_url")))
    return set_prompts, out, neg


def check(spec):
    errs, warns = [], []
    shots = spec["shots"]
    target = spec["target_sec"]
    t0 = 0.0
    for sh in shots:
        a, b = sh["t"]
        if abs(a - t0) > 0.01:
            errs.append(f"{sh['id']}: 시작 {a}초, 앞 샷 끝 {t0}초와 어긋남")
        if b <= a:
            errs.append(f"{sh['id']}: 길이 0 이하")
        t0 = b
    if abs(t0 - target) > 0.5:
        errs.append(f"전체 {t0}초, 목표 {target}초와 0.5초 넘게 다름")
    ids = {s["id"]: s for s in shots}
    first_sound = None
    for sh in shots:
        a, b = sh["t"]
        dur = b - a
        texts = [sh.get("line", ""), sh.get("caption", ""), sh.get("sub", ""), sh.get("tag", ""), sh.get("note", ""), sh.get("chat_title", "")] + [m for m in sh.get("chat", [])]
        texts += sh.get("coins", [])
        for tx in texts:
            for c in BANNED_CHARS:
                if c in tx:
                    errs.append(f"{sh['id']}: 금지 기호 U+{ord(c):04X} '{tx}'")
            for w in BANNED_WORDS:
                if w in tx:
                    errs.append(f"{sh['id']}: 금지 표현 '{w}'")
        if a < 3.0:
            for w in EARLY_BANNED:
                if w in sh.get("caption", ""):
                    errs.append(f"{sh['id']}: 처음 3초 자막에 '{w}'")
        for at, name, g in sh.get("sfx", []):
            if first_sound is None or at < first_sound:
                first_sound = at
        if sh["kind"] == "still":
            if not sh.get("still") or not sh.get("set"):
                errs.append(f"{sh['id']}: 사진 전용 샷에 시작 사진 설명이나 장소 없음")
            if sh.get("line"):
                errs.append(f"{sh['id']}: 사진 전용 샷에는 대사를 넣을 수 없음")
        if sh["kind"] == "video":
            src = ids.get(sh["reuse"]) if sh.get("reuse") else sh
            if sh.get("reuse") and src is None:
                errs.append(f"{sh['id']}: 재사용 원본 {sh['reuse']} 없음")
                continue
            g = src["gen_sec"]
            if not 4 <= g <= 15:
                errs.append(f"{src['id']}: 생성 길이 {g}초(4~15초만 가능)")
            u0, u1 = sh["use"]
            if abs((u1 - u0) - dur) > 0.05:
                errs.append(f"{sh['id']}: 사용 구간 {u1-u0:.2f}초와 화면 길이 {dur:.2f}초 다름")
            if u1 > g + 0.01:
                errs.append(f"{sh['id']}: 사용 구간 끝 {u1}초가 생성 길이 {g}초를 넘음")
            if not sh.get("reuse"):
                if not sh.get("still") or not sh.get("chars"):
                    errs.append(f"{sh['id']}: 시작 사진 설명이나 인물 없음")
                line = sh.get("line", "")
                if line:
                    sp = sh.get("speaker")
                    if sp not in sh["chars"]:
                        errs.append(f"{sh['id']}: 말하는 사람 {sp}가 샷 인물에 없음")
                    rate = syllables(line) / max(0.5, dur - 0.6)
                    if rate > 4.0:
                        errs.append(f"{sh['id']}: 대사 속도 초당 {rate:.1f}음절(4.0 이하)")
                    for h in boundary_repeat(line):
                        warns.append(f"{sh['id']}: 낱말 경계 같은 음절 '{h}', 발음이 뭉개질 수 있음")
                    if first_sound is None or a + sh.get("cue", 0.5) < first_sound:
                        first_sound = a + sh.get("cue", 0.5)
                if sh.get("audio") is not None and sh["audio"] != bool(line):
                    errs.append(f"{sh['id']}: 오디오 설정이 대사 유무와 다름")
    if first_sound is None or first_sound > 0.5:
        errs.append(f"첫 소리 {first_sound}초(0.5초 안이어야 함)")
    return errs, warns


def estimate(spec, video_prompts):
    stills = sum(PRICE[s.get("model", "nano-banana-pro")] for s in spec["sets"].values() if not s.get("url"))
    stills += 75 * sum(1 for p in video_prompts if not p.get("still_url"))
    stills += sum(PRICE[p.get("model", "nano-banana-pro")] for p in spec.get("props", {}).values() if not p.get("url"))
    vids = sum(p["sec"] for p in video_prompts if not p.get("still_only")) * VIDEO_PER_SEC
    reserve = round((stills + vids) * spec.get("reserve_ratio", 0.25))
    return stills, vids, reserve


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else None
    errs, warns = check(spec)
    set_p, vp, neg = build_prompts(spec)
    stills, vids, reserve = estimate(spec, vp)
    lines = [f"# {spec['title']} 사전 점검과 드롭샷 지시문", ""]
    lines.append(f"점검: 실패 {len(errs)}건, 경고 {len(warns)}건")
    lines += [f"- 실패: {e}" for e in errs] + [f"- 경고: {w}" for w in warns]
    lines += ["", f"크레딧 견적: 사진 {stills:g}, 영상 {vids:g}, 다시 만들기 예비 {reserve:g}, 상한 {stills + vids + reserve:g}", ""]
    lines.append("## 장소 기준 사진")
    for k, p in set_p.items():
        lines += [f"{k} ({spec['sets'][k].get('model', 'nano-banana-pro')}): {p}", ""]
    if spec.get("props"):
        lines.append("## 합성용 소품 사진")
        for k, p in spec["props"].items():
            lines += [f"{k} ({p.get('model', 'nano-banana-pro')}): 9:16 세로. {p['desc']} 실사 제품 사진, 화면에 글자와 로고 없음.", ""]
    lines.append(f"## 샷별 지시문 (부정 지시 공통: {neg})")
    model = spec.get("video_model", "bytedance/seedance-2.0")
    for p in vp:
        if p.get("still_only"):
            lines += [f"### {p['id']} 사진 전용(편집 효과용)", f"참고 이미지: {', '.join(p['refs'])}", f"사진: {p['still']}", ""]
            continue
        lines += [f"### {p['id']} 영상 {p['sec']}초, 오디오 {'켬' if p['audio'] else '끔'}",
                  f"참고 이미지: {', '.join(p['refs'])}", f"시작 사진: {p.get('still_url') or '(아직 없음) ' + p['still']}", f"영상: {p['video']}"]
        if p.get("still_url"):
            cmd = dict(model=model, options=dict(prompt=p["video"], start_frame=p["still_url"], generation_mode="frame", duration=p["sec"],
                                                 resolution="720p", aspect_ratio="9:16", generate_audio=p["audio"]))
            lines += ["드롭샷 명령:", "```json", json.dumps(cmd, ensure_ascii=False, indent=1), "```"]
        lines.append("")
    text = "\n".join(lines)
    if out:
        open(out, "w", encoding="utf-8").write(text)
    print(text[:3000])
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
