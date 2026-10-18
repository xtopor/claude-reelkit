"""Build a voice-over reel from <job>/reel.json in one command.

voice (vo/vo.mp3: your recording, `reelkit tts`, or ElevenLabs) -> timed voice (offset + breathing gaps)
-> word timings (from the TTS, else faster-whisper) -> subtitles from the script (<em> = accent words, auto-chunked
to 5-7 words, 1-2 lines) -> punch-ins on accent words -> footage frames -> page render (template.html, Playwright)
-> music shaped by the structure -> sound effects from the local bank -> mix to -14 LUFS -> safe-zone QA sheet,
cover, caption.

Usage:
  reelkit build <reel-dir> [--stills] [--capcut]
  --stills  only resolve + frames + QA sheet (fast preview, no video)
  --capcut  also render a no-subtitles video and a music track without SFX for the CapCut draft
reel.json format: skills/reel-builder/SKILL.md
Ported from claude-reelsmith (MIT, lalimi) to run on Windows / Linux / macOS."""
import difflib, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
import numpy as np

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent                                   # plugin root
RENDER = ROOT / "tools" / "render.mjs"
WIN = sys.platform == "win32"
DATA = Path(os.environ.get("REELKIT_DATA") or (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "reelkit" if WIN else Path.home() / ".local/share/reelkit"))
SFX_DIR = DATA / "sfx"
FFMPEG = os.environ.get("REELKIT_FFMPEG", "ffmpeg")
NODE = "node.exe" if WIN else "node"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ROOT / "skills/talking-head-edit/prep"))
from common import load_wav, snap                       # noqa: E402
import music                                            # noqa: E402

FPS, W, H = 30, 1080, 1920


def sh(*a, **k):
    return subprocess.run([str(x) for x in a], check=True, **k)


def resolve(job, p):
    p = os.path.expanduser(str(p))
    cands = [Path(p)] if os.path.isabs(p) else [job / p, Path.cwd() / p, ROOT / p]
    for q in cands:
        if q.exists(): return q
    sys.exit(f"file not found: {p}")


def fresh(out, key):
    """True when `out` was built from exactly this `key` (cache)."""
    k = out.with_name(out.name + ".key")
    return out.exists() and k.exists() and k.read_text(encoding="utf8") == key


def mark(out, key):
    out.with_name(out.name + ".key").write_text(key, encoding="utf8")


def jload(p):
    return json.load(open(p, encoding="utf8"))


def jdump(o, p, **k):
    json.dump(o, open(p, "w", encoding="utf8"), ensure_ascii=False, **k)


# ---------------------------------------------------------------- voice
def time_voice(job, vo):
    """Place the voice at `offset`, insert breathing gaps [[vo_time, extra_s]] at the quietest point nearby.
    Returns (wav, parts) where parts = [(from, to, shift)] on the sped-up voice, so TTS word times can be remapped."""
    src = resolve(job, vo["file"]); out = job / "out/vo_timed.wav"
    key = json.dumps(vo, sort_keys=True) + str(src.stat().st_mtime)
    parts_f = out.with_suffix(".parts.json")
    if fresh(out, key) and parts_f.exists(): return out, jload(parts_f)
    raw = job / "out/vo_raw.wav"                     # speed: atempo first, so gap times are on the sped-up voice
    sh(FFMPEG, "-v", "error", "-y", "-i", src, *(["-af", f"atempo={vo['speed']}"] if vo.get("speed") else []), "-ar", "48000", "-ac", "1", raw)
    a, sr = load_wav(raw); raw.unlink()
    shift, prev, parts = vo.get("offset", 0.3), 0.0, []
    for t, extra in sorted(vo.get("gaps", [])):
        c = snap(a, sr, t, t - 0.25, t + 0.25)
        parts.append((prev, c, shift)); shift += extra; prev = c
    parts.append((prev, len(a) / sr, shift))
    buf = np.zeros(int((parts[-1][1] + parts[-1][2] + 0.1) * sr)); f = np.linspace(0, 1, int(0.02 * sr))
    for s, e, d in parts:
        seg = a[int(s * sr):int(e * sr)].copy()
        if len(seg) > 2 * len(f): seg[:len(f)] *= f; seg[-len(f):] *= f[::-1]
        i = int((s + d) * sr); buf[i:i + len(seg)] += seg[:len(buf) - i]
    import wave
    with wave.open(str(out), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    jdump(parts, parts_f); mark(out, key)
    return out, parts


def tts_words(job, vo, parts):
    """Word timings written by `reelkit tts` next to the voice file, remapped through speed / offset / gaps."""
    src = resolve(job, vo["file"]); wf = src.with_suffix(".words.json")
    if not wf.exists() or wf.stat().st_mtime < src.stat().st_mtime - 2: return None
    d = jload(wf); words = d["words"] if isinstance(d, dict) else d
    sp = vo.get("speed") or 1.0

    def remap(t):
        t = t / sp
        for s, e, d_ in parts:
            if s <= t < e or (s, e) == (parts[-1][0], parts[-1][1]): return round(t + d_, 3)
        return round(t + parts[-1][2], 3)
    return [{"w": w["w"], "s": remap(w["s"]), "e": remap(w["e"])} for w in words if w["w"].strip()]


def transcribe(wav, lang=None):
    out = wav.with_name("words.json"); key = str(wav.stat().st_mtime) + str(lang)
    if fresh(out, key): return jload(out)
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    words = []
    for vad in (True, False):                          # word alignment occasionally crashes with VAD on
        try:
            segs, _ = m.transcribe(str(wav), language=lang, word_timestamps=True, vad_filter=vad)
            words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words if w.word.strip()]
            break
        except IndexError:
            continue
    jdump(words, out); mark(out, key)
    return words


# ---------------------------------------------------------------- subtitles
norm = lambda w: re.sub(r"[^\w']", "", w.lower().replace("’", "'")).replace("_", "")


def display_script(script):
    """{shown|said} -> shown (what subtitles print; the voice says the other half)."""
    return re.sub(r"\{([^{}|]*)\|([^{}]*)\}", r"\1", script)


def script_tokens(script):
    toks, em, glued = [], False, False
    for part in re.split(r"(<em>|</em>)", display_script(script)):
        if part in ("<em>", "</em>"): em = part == "<em>"; continue
        words = part.split()
        if words and toks and glued and not part[:1].isspace():   # "…</em>." : punctuation sticks to the accent word
            toks[-1]["t"] += words.pop(0)
        toks += [{"t": w, "em": em} for w in words]
        glued = bool(part) and not part[-1:].isspace()
    return toks


def align(toks, words):
    sm = difflib.SequenceMatcher(None, [norm(t["t"]) for t in toks], [norm(w["w"]) for w in words], autojunk=False)
    for b in sm.get_matching_blocks():
        for k in range(b.size):
            toks[b.a + k].update(s=words[b.b + k]["s"], e=words[b.b + k]["e"])
    known = [i for i, t in enumerate(toks) if "s" in t]
    for i, t in enumerate(toks):                       # unmatched words (numbers, names): spread between neighbours
        if "s" in t: continue
        p = max((j for j in known if j < i), default=None); n = min((j for j in known if j > i), default=None)
        lo = toks[p]["e"] if p is not None else (toks[n]["s"] - 0.3 if n is not None else 0)
        hi = toks[n]["s"] if n is not None else lo + 0.3 * (i - (p or 0) + 1)
        a0, b0 = (p if p is not None else -1), (n if n is not None else len(toks))
        t["s"] = lo + (hi - lo) * (i - a0) / (b0 - a0); t["e"] = t["s"] + 0.2
    return toks, sum(b.size for b in sm.get_matching_blocks()) / max(1, len(toks))


WEAK = set(("і й та а але в у з із зі до від на по за для про що як де бо чи не ні ж же "     # uk
             "и а но в на с к о у за для про что как где не ни же "                              # ru
             "and a an the of to in on at for with or but by from as that so not").split())        # en
TIME_KEYS = {"at", "to", "from", "out", "lines_at", "sub_at", "handle_at", "t"}


def anchor(toks, v):
    """'@thousand' -> start of the first script word equal to (else beginning with) 'thousand'; '@again#2+0.2' = 2nd hit, +0.2 s."""
    if not (isinstance(v, str) and v.startswith("@")): return v
    m = re.fullmatch(r"@(.+?)(?:#(\d+))?([+-][\d.]+)?", v)
    w = norm(m[1]); hits = [t for t in toks if norm(t["t"]) == w] or [t for t in toks if norm(t["t"]).startswith(w)]
    if len(hits) < int(m[2] or 1): sys.exit(f"anchor {v}: no such word in the script")
    return round(hits[int(m[2] or 1) - 1]["s"] + float(m[3] or 0), 3)


def anchors(toks, o, key=None):
    if isinstance(o, dict): return {k: anchors(toks, v, k) for k, v in o.items()}
    if isinstance(o, list): return [anchors(toks, v, key) for v in o]
    return anchor(toks, o) if key in TIME_KEYS else o


def make_subs(toks, lo, hi, lower_first=True, maxw=7, maxc=46, skip=()):
    chunks, cur = [], []
    for t in toks:
        if t["s"] < lo - 0.05 or t["s"] >= hi or any(a <= t["s"] < b for a, b in skip):
            if cur: chunks.append(cur); cur = []
            continue
        if cur:
            p = cur[-1]; chars = sum(len(x["t"]) + 1 for x in cur) + len(t["t"])
            in_accent = t["em"] and p["em"] and len(cur) < maxw + 3      # never split an accent phrase
            if (re.search(r"[.!?…]$", p["t"]) or (re.search(r"[,;:]$", p["t"]) and len(cur) >= 4)
                    or (not in_accent and (len(cur) >= maxw or chars > maxc)) or t["s"] - p["e"] > 0.5):
                chunks.append(cur); cur = []
        cur.append(t)
    if cur: chunks.append(cur)
    for a, b in zip(chunks, chunks[1:]):              # "… for 99 and | then a discount": a line never ends on "and", "in", "of"
        while len(a) > 2 and norm(a[-1]["t"]) in WEAK and not re.search(r"[.!?…,;:]$", a[-1]["t"]) and b[0]["s"] - a[-1]["e"] < 0.5:
            b.insert(0, a.pop())
    merged, carry = [], []                             # no orphan 1-2 word subtitles
    for i, c in enumerate(chunks):
        c = carry + c; carry = []
        if len(c) <= 2 and i + 1 < len(chunks) and not re.search(r"[.!?…,;:]$", c[-1]["t"]):
            carry = c; continue                        # "but" belongs to what follows
        if len(c) <= 2 and merged and not re.search(r"[.!?…]$", merged[-1][-1]["t"]) and len(merged[-1]) + len(c) <= maxw + 1:
            merged[-1] = merged[-1] + c; continue
        merged.append(c)
    if carry: merged.append(carry)
    subs = []
    for i, c in enumerate(merged):
        words = [x["t"] for x in c]; total = len(" ".join(words)); brk = None
        if total > 24:
            best = None
            for k in range(1, len(words)):
                score = abs(len(" ".join(words[:k])) - total / 2) - (8 if words[k - 1].endswith(",") else 0)
                if best is None or score < best: best, brk = score, k
        s, inem = "", False
        for k, x in enumerate(c):
            w = x["t"]
            if k == 0 and lower_first and w[:1].isupper() and not (len(w) > 1 and w[1:2].isupper()): w = w[0].lower() + w[1:]
            if k == len(c) - 1: w = w.rstrip(".,;:")        # subtitles end without a dot or comma
            if inem and not x["em"]: s += "</em>"; inem = False
            if k: s += "<br>" if k == brk else " "
            if x["em"] and not inem: s += "<em>"; inem = True
            s += w
        if inem: s += "</em>"
        st = max(lo, c[0]["s"] - 0.08)
        nxt = merged[i + 1][0]["s"] - 0.08 if i + 1 < len(merged) else hi
        en = min(nxt - 0.02, max(c[-1]["e"] + 0.35, st + 0.6), hi)
        if en - st < 0.45: continue                    # would only flash (e.g. runs into the end card)
        subs.append([round(st, 2), round(en, 2), s])
    return subs


def auto_punch(toks, segs, max_n=4, gap=3.0):
    starts = [float(t["s"]) for i, t in enumerate(toks) if t["em"] and (i == 0 or not toks[i - 1]["em"])]
    out = []
    for t in starts:
        if out and t - out[-1][0] < gap: continue
        k = next((j for j, s in enumerate(segs) if s["t0"] <= t < s["t0"] + s["dur"]), None)
        if k is None: continue
        until = segs[k]["t0"] + segs[k]["dur"]                       # hold to the cut ...
        if until - t < 0.8 and k + 1 < len(segs):                    # ... unless the cut is too close
            until = min(t + 1.2, segs[k + 1]["t0"] + segs[k + 1]["dur"])
        out.append([round(t, 2), round(min(until, t + 2.5), 2)])
        if len(out) == max_n: break
    return out


# ---------------------------------------------------------------- footage
def to_jpeg(src, dst):
    """Any photo (HEIC included) -> JPEG: Pillow (+pillow-heif when installed), ffmpeg as the fallback."""
    try:
        from PIL import Image, ImageOps
        try:
            import pillow_heif; pillow_heif.register_heif_opener()
        except ImportError:
            pass
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB"); im.save(dst, quality=95); return
    except Exception:
        sh(FFMPEG, "-v", "error", "-y", "-i", src, "-q:v", "2", dst)


def frames(job, seg):
    out = job / "frames" / seg["id"]
    key = json.dumps({k: seg.get(k) for k in ("clip", "img", "ss", "dur", "crop", "pos", "rate")}, sort_keys=True)
    if (out / ".key").exists() and (out / ".key").read_text(encoding="utf8") == key:
        return len(list(out.glob("*.jpg")))
    shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}:(iw-{W})*{seg.get('pos', 0.5)}:(ih-{H})/2"
    if seg.get("crop"):
        x, y, z = seg["crop"]; fit = f"crop=iw*{z}:ih*{z}:iw*{x}:ih*{y}," + fit
    if seg.get("img"):
        src = resolve(job, seg["img"]); tmp = out / "_src.jpg"
        to_jpeg(src, tmp)
        sh(FFMPEG, "-v", "error", "-y", "-i", tmp, "-vf", fit, "-q:v", "2", out / "0001.jpg"); tmp.unlink()
    else:
        sh(FFMPEG, "-v", "error", "-y", "-ss", seg.get("ss", 0), "-i", resolve(job, seg["clip"]), "-frames:v", round(seg["dur"] * FPS) + 2,
           "-vf", (f"setpts=PTS/{seg['rate']}," if seg.get("rate") else "") + f"fps={FPS}," + fit, "-q:v", "3", out / "%04d.jpg")
    (out / ".key").write_text(key, encoding="utf8")
    return len(list(out.glob("*.jpg")))


def masks(job, seg):
    """Person masks for a segment's frames (alpha PNGs, rembg) + head positions, cached with the frames."""
    src, out = job / "frames" / seg["id"], job / "frames" / (seg["id"] + "_m")
    key = (src / ".key").read_text(encoding="utf8")
    if (out / ".key").exists() and (out / ".key").read_text(encoding="utf8") == key:
        return jload(out / "meta.json")
    shutil.rmtree(out, ignore_errors=True)
    sh(sys.executable, "-I", "-X", "utf8", ENGINE / "masks.py", src, out)
    (out / ".key").write_text(key, encoding="utf8")
    return jload(out / "meta.json")


# ---------------------------------------------------------------- audio out
def sfx_track(job, spec, dur):
    """Sound effects from the local bank (or files you own) placed on the timeline -> out/sfx.wav (stereo 48 kHz)."""
    events = spec.get("sfx") or []
    if not events: return None
    out = job / "out/sfx.wav"; key = json.dumps(events, sort_keys=True) + str(dur)
    if fresh(out, key): return out
    import wave
    sr = 48000; buf = np.zeros((int((dur + 0.5) * sr), 2), np.float32)
    for e in events:
        name = e["name"]
        p = SFX_DIR / f"{name}.wav"
        if not p.exists():
            q = next((c for c in (job / name, ROOT / name, Path(name)) if c.exists()), None)
            if not q: sys.exit(f"sound not found: {name} (bank: {', '.join(sorted(x.stem for x in SFX_DIR.glob('*.wav')))})")
            p = job / "out" / f"_sfx_{q.stem}.wav"; sh(FFMPEG, "-v", "error", "-y", "-i", q, "-ar", sr, "-ac", 2, p)
        with wave.open(str(p)) as w:
            ch = w.getnchannels(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            a = a.reshape(-1, ch); a = a if ch == 2 else np.repeat(a, 2, 1)
        if e.get("dur"):
            a = a[:int(e["dur"] * sr)].copy()
            if len(a) > sr // 20: a[-sr // 20:] *= np.linspace(1, 0, sr // 20)[:, None]
        i = int(float(e["t"]) * sr); a = a[:len(buf) - i] * float(e.get("vol", 0.4))
        if i >= 0 and len(a): buf[i:i + len(a)] += a
    with wave.open(str(out), "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    mark(out, key); return out


def mix(job, video, voice, music_wav, sfx_wav, out, dur, music_gain=0.16, sfx_gain=0.9):
    ins = ["-i", video, "-i", voice] + (["-i", music_wav] if music_wav else []) + (["-i", sfx_wav] if sfx_wav else [])
    mi, si = (2, 3) if music_wav else (None, 2)
    parts = ["[1:a]highpass=f=70,aformat=channel_layouts=stereo,asplit=2[v][sc]"]
    mixin = ["[v]"]
    if music_wav:
        parts.append(f"[{mi}:a]volume={music_gain}[m];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=380[md]"); mixin.append("[md]")
    else:
        parts.append("[sc]anullsink")
    if sfx_wav:
        parts.append(f"[{si}:a]volume={sfx_gain},aformat=channel_layouts=stereo[fx]"); mixin.append("[fx]")
    fc = ";".join(parts) + ";" + "".join(mixin) + (f"amix=inputs={len(mixin)}:normalize=0:duration=longest" if len(mixin) > 1 else "apad")
    j = subprocess.run([FFMPEG, "-hide_banner", *map(str, ins), "-filter_complex", fc + ",loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-t", str(dur), "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf8", errors="replace").stderr
    m = json.loads(j[j.rindex("{"):j.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    # a brick-wall limiter after loudnorm at -3 dBTP: AAC encoding overshoots peaks by ~1.2 dB, so the file lands ≤ -1.5 dBTP
    sh(FFMPEG, "-v", "error", "-y", *ins, "-filter_complex", f"{fc},{ln},alimiter=limit=0.7:attack=3:release=60:level=false,aresample=48000[a]", "-map", "0:v", "-map", "[a]",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", dur, "-movflags", "+faststart", out)


def loudness(f):
    e = subprocess.run([FFMPEG, "-hide_banner", "-i", str(f), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, encoding="utf8", errors="replace").stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1]), float((re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e) or ["0"])[-1])


def link_fonts(job):
    """The page needs fonts/ next to it: a symlink where allowed, a copy on Windows."""
    dst = job / "fonts"
    if dst.is_symlink() or (dst.exists() and (dst / "fonts.css").exists()): return
    try:
        dst.symlink_to(ENGINE / "fonts", target_is_directory=True)
    except OSError:
        shutil.copytree(ENGINE / "fonts", dst, dirs_exist_ok=True)


# ---------------------------------------------------------------- main
def main():
    job = Path(sys.argv[1]).expanduser().resolve(); flags = set(sys.argv[2:])
    spec = jload(job / "reel.json"); (job / "out").mkdir(exist_ok=True)
    warn = []

    # footage timeline
    segs, t0 = [], 0.0
    for s in spec["segments"]:
        s = dict(s); s["t0"] = round(t0, 4); s["n"] = frames(job, s); t0 += s["dur"]; segs.append(s)
        if s.get("cut"): s["head"] = masks(job, s)
    dur = round(t0, 3)
    print(f"frames: {len(segs)} segments, {dur} s")

    # voice -> words -> subtitles / punch
    voice, toks = None, []
    if spec.get("vo"):
        voice, parts = time_voice(job, spec["vo"])
        words = tts_words(job, spec["vo"], parts)
        if words: print("word timings: from the TTS")
        else: words = transcribe(voice, spec.get("lang") or os.environ.get("REELKIT_LANG") or None)   # None = auto-detect
        vo_end = words[-1]["e"] if words else 0
        if vo_end > dur - 0.8: warn.append(f"the voice ends at {vo_end:.1f} s but the video at {dur:.1f} s: make the last segment longer")
        if spec.get("script"):
            toks, ratio = align(script_tokens(spec["script"]), words)
            print(f"script ↔ voice: {ratio:.0%} of words matched")
            if ratio < 0.7: warn.append("the script differs a lot from the voice-over: check the text (or set \"lang\")")
    for k in ("hook", "end", "doodles", "glass", "checklist", "cover", "wall", "orbit", "sfx"):   # "@word" times -> seconds
        if spec.get(k): spec[k] = anchors(toks, spec[k], k if k in ("doodles", "sfx") else None)
    for k in ("subs_skip", "punch", "subs_from", "subs_until"):
        if isinstance(spec.get(k), (list, str)): spec[k] = anchors(toks, spec[k], "at")
    hook, end = spec.get("hook"), spec.get("end")
    lo = spec.get("subs_from", hook.get("out", 0) + 0.15 if hook and hook.get("out") else 0)
    hi = spec.get("subs_until", end["from"] - 0.1 if end else dur)
    skip = [list(w) for w in spec.get("subs_skip", [])]                 # no subtitles under glass titles / checklists
    if spec.get("glass"): skip.append([spec["glass"]["from"] - 0.05, spec["glass"]["to"]])
    if spec.get("checklist"): skip.append([spec["checklist"]["from"] - 0.05, spec["checklist"]["to"]])
    subs = spec.get("subs") if spec.get("subs") not in (None, "auto") else (make_subs(toks, lo, hi, skip=skip) if toks else [])
    punch = spec.get("punch") if spec.get("punch") not in (None, "auto") else (auto_punch(toks, segs) if toks else [])
    stamps = []
    for st in spec.get("stamps", []):
        if isinstance(st, dict):
            ids = st["seg"] if isinstance(st["seg"], list) else [st["seg"]]
            ss = [s for s in segs if s["id"] in ids]
            stamps.append([ss[0]["t0"], round(ss[-1]["t0"] + ss[-1]["dur"], 3), st["text"]])
        else:
            stamps.append(st)

    # page
    page = {"fps": FPS, "duration": dur, "segments": [{k: s.get(k) for k in ("id", "dur", "n", "look", "move", "date", "t0", "in", "cut", "head")} for s in segs],
            "subs": subs, "punch": punch, "stamps": stamps, "hook": hook, "end": end, "colors": spec.get("colors"),
            "doodles": spec.get("doodles"), "glass": spec.get("glass"), "checklist": spec.get("checklist"),
            "cover": spec.get("cover"), "wall": spec.get("wall"), "orbit": spec.get("orbit")}
    (job / "spec.js").write_text("window.SPEC = " + json.dumps(page, ensure_ascii=False) + ";\n", encoding="utf8")
    shutil.copy(ENGINE / "template.html", job / "index.html")
    link_fonts(job)
    jdump(page, job / "out/resolved.json", indent=1)
    for a, b, s in subs: print(f"  {a:6.2f}–{b:6.2f}  {re.sub('<[^>]+>', ' ', s)}")
    print("punch-ins:", [[round(float(a), 2), round(float(b), 2)] for a, b in punch])

    # QA sheet: hook, a few subtitles, ending — with the Reels safe zone in red
    extra = [round(d["at"] + 0.5, 2) for d in spec.get("doodles") or [] if d["kind"] == "text"][:3]
    if spec.get("glass"): extra.append(round(spec["glass"]["to"] - 0.4, 2))
    if spec.get("checklist"): extra.append(round(spec["checklist"]["to"] - 0.4, 2))
    for k in ("cover", "orbit"):
        if spec.get(k): extra.append(round(min(spec[k]["from"] + 1.5, spec[k]["to"] - 0.3), 2))
    if spec.get("wall"): extra.append(round(spec["wall"]["from"] + 0.6, 2))
    times = sorted(set(([0.5] if hook else []) + [round((a + b) / 2, 2) for a, b, _ in subs][::max(1, len(subs) // 5)] + extra
                       + ([round(end["from"] + 2, 2)] if end else [round(dur - 0.5, 2)])))
    times = [t for t in times if 0 <= t < dur] or [min(0.5, dur / 2)]
    shutil.rmtree(job / "stills", ignore_errors=True); (job / "stills").mkdir()
    env = dict(os.environ, W=str(W), H=str(H))
    sh(NODE, RENDER, job, "stills", ",".join(map(str, times)), env=env)
    zone = "drawbox=x=0:y=0:w=1080:h=280:color=red@0.22:t=fill,drawbox=x=0:y=1500:w=1080:h=420:color=red@0.22:t=fill,drawbox=x=910:y=900:w=170:h=600:color=red@0.22:t=fill"
    imgs = [job / "stills" / f"t_{t:.2f}.jpg" for t in times]
    fc = ";".join(f"[{i}:v]{zone},scale=270:-2[s{i}]" for i in range(len(imgs))) + ";" + "".join(f"[s{i}]" for i in range(len(imgs))) + f"hstack={len(imgs)}" if len(imgs) > 1 else f"{zone},scale=270:-2"
    sh(FFMPEG, "-v", "error", "-y", *sum([["-i", p] for p in imgs], []), "-filter_complex", fc, job / "out/qa_sheet.jpg")
    print("safe-zone check:", job / "out/qa_sheet.jpg")
    if "--stills" in flags:
        for w in warn: print("WARNING:", w)
        return

    # video
    sh(NODE, RENDER, job, "video", job / "out/silent.mp4", FPS, env=env)
    if "--capcut" in flags:
        sh(NODE, RENDER, job, "video", job / "out/silent_nosubs.mp4", FPS, env=dict(env, PAGE="index.html?nosubs=1"))

    # music shaped by the structure
    bw = [s for s in segs if s.get("look") == "bw"]; burst = [s for s in segs if s.get("look") == "burst"]
    muffle = (bw[0]["t0"], bw[-1]["t0"] + bw[-1]["dur"]) if bw else None
    open_at = burst[0]["t0"] if burst else (muffle[1] if muffle else (hook.get("out", 0) if hook else 0))
    margs = dict(dur=dur, shutters=[s["t0"] for s in segs if s.get("look") == "memory"], muffle=muffle,
                 open_at=open_at, end_at=end["from"] if end else dur - 3, chime=bool(burst))
    mus = spec.get("music", "synth")
    if mus == "synth":
        music.make(job / "out/music.wav", **margs); mwav = job / "out/music.wav"
        if "--capcut" in flags: music.make(job / "out/music_nofx.wav", fx=False, **margs)
    elif mus:
        mwav = resolve(job, mus)
    else:
        mwav = None
    fx = sfx_track(job, spec, dur)

    if voice:
        mix(job, job / "out/silent.mp4", voice, mwav, fx, job / "out/reel.mp4", dur, spec.get("music_gain", 0.16), spec.get("sfx_gain", 0.9))
        mix(job, job / "out/silent.mp4", voice, None, fx, job / "out/reel_nomusic.mp4", dur, sfx_gain=spec.get("sfx_gain", 0.9))
        sh(FFMPEG, "-v", "error", "-y", "-ss", spec.get("cover_t", 0.5), "-i", job / "out/reel.mp4", "-frames:v", 1, "-q:v", 2, job / "out/cover.jpg")
        for f in ("reel.mp4", "reel_nomusic.mp4"):
            i, p = loudness(job / "out" / f)
            print(f"{f}: {i:.1f} LUFS, peak {p:.1f} dB")
            if not -15 <= i <= -13 or p > -1: warn.append(f"{f}: loudness out of range (-14 LUFS ±1, peak ≤ -1 dB)")
    if not voice:                                          # no voice-over: picture (+ music / sfx if any) is the reel
        auds = [a for a in (mwav, fx) if a]
        if auds:
            ins = sum([["-i", a] for a in auds], [])
            fc = "".join(f"[{i + 1}:a]" for i in range(len(auds))) + f"amix=inputs={len(auds)}:normalize=0[a]" if len(auds) > 1 else "[1:a]anull[a]"
            sh(FFMPEG, "-v", "error", "-y", "-i", job / "out/silent.mp4", *ins, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", job / "out/reel.mp4")
        else:
            shutil.copy(job / "out/silent.mp4", job / "out/reel.mp4")
        sh(FFMPEG, "-v", "error", "-y", "-ss", min(spec.get("cover_t", 0.5), dur - 0.05), "-i", job / "out/reel.mp4", "-frames:v", 1, "-q:v", 2, job / "out/cover.jpg")
    if spec.get("caption"): (job / "out/caption.txt").write_text(spec["caption"].strip() + "\n", encoding="utf8")
    for w in warn: print("WARNING:", w)
    print("done:", job / "out/reel.mp4")


if __name__ == "__main__":
    main()
