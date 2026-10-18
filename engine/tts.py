"""Free voice-over with word timings: Microsoft Edge neural voices via edge-tts (no key, 70+ languages,
Ukrainian: uk-UA-OstapNeural / uk-UA-PolinaNeural, English: en-US-AndrewMultilingualNeural, ...).

  reelkit tts <reel-dir> [--voice NAME] [--rate +5%] [--pitch +0Hz] [--text "..."] [--out vo/vo.mp3]
      text = --text, else reel.json "vo.text", else "script" with <em> tags stripped and {shown|said} -> said
      writes vo/vo.mp3 and vo/words.json ([{"w","s","e"}] in seconds; build.py uses them instead of Whisper)
  reelkit voices [lang]        list voices (e.g. "uk", "en", "pl")

Voice and rate can also live in reel.json: "vo": {"file": "vo/vo.mp3", "voice": "uk-UA-OstapNeural", "rate": "+5%"}.
"""
import asyncio, json, re, sys
from pathlib import Path


def tts_text(spec):
    """Script -> what the voice says: {shown|said} takes the spoken form, <em> tags go, digits stay (the voices read them)."""
    if spec.get("vo", {}).get("text"): return spec["vo"]["text"]
    s = spec.get("script", "")
    s = re.sub(r"\{([^{}|]*)\|([^{}]*)\}", r"\2", s)
    return re.sub(r"</?em>", "", s).strip()


async def speak(text, voice, rate, pitch, out):
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with open(out, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7
                words.append({"w": ch["text"].strip(), "s": round(s, 3), "e": round(s + ch["duration"] / 1e7, 3)})
    return [w for w in words if w["w"]]


async def list_voices(lang):
    import edge_tts
    vs = await edge_tts.list_voices()
    for v in sorted(vs, key=lambda v: (v["Locale"], v["ShortName"])):
        if lang and not v["Locale"].lower().startswith(lang.lower()): continue
        print(f"{v['ShortName']:40s} {v['Gender']:7s} {', '.join(v.get('VoiceTag', {}).get('VoicePersonalities', []))}")


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == "--list":
        asyncio.run(list_voices(a[1] if len(a) > 1 else "")); return
    job = Path(a[0]).expanduser().resolve()
    opts = {"voice": None, "rate": None, "pitch": "+0Hz", "text": None, "out": None}
    i = 1
    while i < len(a):
        k = a[i].lstrip("-")
        if k in opts and i + 1 < len(a): opts[k] = a[i + 1]; i += 2
        else: sys.exit(f"unknown option {a[i]}")
    spec = json.load(open(job / "reel.json", encoding="utf8")) if (job / "reel.json").exists() else {}
    vo = spec.get("vo", {})
    voice = opts["voice"] or vo.get("voice") or ("uk-UA-OstapNeural" if spec.get("lang", "uk") == "uk" else "en-US-AndrewMultilingualNeural")
    rate = opts["rate"] or vo.get("rate") or "+0%"
    text = opts["text"] or tts_text(spec)
    if not text: sys.exit("nothing to say: put the script into reel.json \"script\" or pass --text")
    out = job / (opts["out"] or vo.get("file") or "vo/vo.mp3"); out.parent.mkdir(parents=True, exist_ok=True)
    words = asyncio.run(speak(text, voice, rate, opts["pitch"], out))
    json.dump({"voice": voice, "rate": rate, "text": text, "words": words}, open(out.with_suffix(".words.json"), "w", encoding="utf8"), ensure_ascii=False, indent=0)
    json.dump(words, open(out.parent / "words.json", "w", encoding="utf8"), ensure_ascii=False)
    dur = words[-1]["e"] if words else 0
    print(f"{out}  {dur:.1f}s  {len(words)} words  voice {voice} rate {rate}")
    print("(~150 words ≈ 60 s; \"rate\": \"+8%\" tightens; set \"vo\": {\"speed\": 1.07} in reel.json for atempo instead)")


if __name__ == "__main__":
    main()
