"""Word timings for the renderer: faster-whisper with word_timestamps -> words.json {"lang", "words": [{"w","s","e"}]}.
Usage: reelkit th transcribe <audio.wav> <words.json> [model]      default model: small
Language from REELKIT_LANG (uk / en / pl …; unset = auto-detect)."""
import json, os, sys
if len(sys.argv) < 3: sys.exit("usage: transcribe.py <audio.wav> <words.json> [model]")
from faster_whisper import WhisperModel
src, out, size = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "small")
m = WhisperModel(size, device="cpu", compute_type="int8")
segs, info = m.transcribe(src, language=os.environ.get("REELKIT_LANG") or None, word_timestamps=True, vad_filter=True)
words = []
for s in segs:
    for w in s.words:
        words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
json.dump({"lang": info.language, "words": words}, open(out, "w", encoding="utf8"), ensure_ascii=False, indent=0)
print(" ".join(f"{w['w']}[{w['s']}]" for w in words))
