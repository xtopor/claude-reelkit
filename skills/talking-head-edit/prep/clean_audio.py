"""Clean a talking-head voice track: light noise removal + gate, de-essing, gentle EQ + compression,
two-pass loudness to -14 LUFS (what Instagram/TikTok expect). Mono 48 kHz WAV out.
Usage: reelkit th clean <clip> <out.wav> [--no-denoise]        (python -I prep/clean_audio.py <clip> <out.wav> [--no-denoise])
Denoise: DeepFilterNet (`deepFilter` on PATH, DENOISE_DB env caps it, default 30 dB) if available, else ffmpeg afftdn.
Env: REELKIT_FFMPEG (ffmpeg executable, default "ffmpeg").
Ported from github.com/nicolapocock/claude-reel-editor (MIT, see LICENSE-claude-reel-editor)."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import floor_db, load_wav

USAGE = "usage: clean_audio.py <clip> <out.wav> [--no-denoise]"
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
    print(USAGE, file=sys.stderr); sys.exit(2)
src_clip, out = Path(sys.argv[1]).expanduser().resolve(), Path(sys.argv[2]).expanduser().resolve()
flag = sys.argv[3] if len(sys.argv) > 3 else "--denoise"
if flag not in ("--denoise", "--no-denoise"):
    print(USAGE, file=sys.stderr); sys.exit(2)
denoise = flag == "--denoise"
if not src_clip.exists(): sys.exit(f"clip not found: {src_clip}")
FFMPEG = os.environ.get("REELKIT_FFMPEG") or "ffmpeg"

def run(args, **kw):
    """Run a tool without a shell; stdout/stderr decoded as UTF-8 (ffmpeg prints file names)."""
    return subprocess.run([str(a) for a in args], capture_output=True, encoding="utf8", errors="replace", **kw)

def ffmpeg(*args, check=True):
    r = run([FFMPEG, "-v", "error", "-y", *args])
    if check and r.returncode != 0: sys.exit(f"ffmpeg failed: {r.stderr.strip() or r.returncode}")
    return r

# Gate pulls leftover noise between words down ~12 dB; then rumble cut, less boxiness, more clarity and air,
# de-ess (the clarity boost exaggerates sibilants), light 3:1 compression.
GATE = "agate=threshold=0.015:ratio=3:range=0.25:attack=4:release=150," if denoise else ""
CHAIN = (f"{GATE}highpass=f=85,equalizer=f=220:t=q:w=1:g=-2.5,equalizer=f=3200:t=q:w=1:g=2.5,highshelf=f=9000:g=2,"
         "deesser=i=0.4:m=0.5:f=0.5,acompressor=ratio=3:threshold=-20dB:attack=5:release=80")
LN = "loudnorm=I=-14:TP=-1.5:LRA=7"

with tempfile.TemporaryDirectory(prefix="clean_audio_") as tmp:
    tmp = Path(tmp)
    src = tmp / "raw.wav"
    ffmpeg("-i", src_clip, "-vn", "-ac", "1", "-ar", "48000", src)

    if denoise:
        df = shutil.which("deepFilter")
        if df:
            dfn = tmp / "dfn"; dfn.mkdir()
            # capped at 30 dB: natural, no underwater artefacts
            r = run([df, "-a", os.environ.get("DENOISE_DB", "30"), src, "-o", dfn])
            got = sorted(dfn.glob("*.wav"))
            if r.returncode == 0 and got: src = got[0]
            else: print("deepFilter failed, falling back to ffmpeg afftdn", file=sys.stderr); df = None
        if not df:
            dn = tmp / "dn.wav"
            ffmpeg("-i", src, "-af", "afftdn=nf=-25", dn)        # built-in denoiser (weaker on birds/traffic)
            src = dn

    # pass 1: measure loudness through the whole chain (loudnorm prints a JSON block on stderr)
    r = run([FFMPEG, "-hide_banner", "-i", src, "-af", f"{CHAIN},{LN}:print_format=json", "-f", "null", "-"])
    m = re.search(r"^\{.*?^\}", r.stderr, re.S | re.M)
    if not m: sys.exit(f"loudnorm measurement failed: {r.stderr.strip()[-800:]}")
    J = json.loads(m.group(0))

    # pass 2: apply the measured values linearly, write the final mono 48 kHz WAV
    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", src, "-af",
           f"{CHAIN},{LN}:measured_I={J['input_i']}:measured_TP={J['input_tp']}:measured_LRA={J['input_lra']}"
           f":measured_thresh={J['input_thresh']}:offset={J['target_offset']}:linear=true",
           "-ar", "48000", out)

# The gaps between words must be quiet: 10th-percentile 50 ms level = the background.
a, sr = load_wav(out)
floor = round(floor_db(a, sr, 10))
print(f"noise between words: {floor} dB (want -45 or quieter)", file=sys.stderr)
if floor > -45:
    print("WARNING: still noisy, check the raw recording (wind and rustle cannot be fully removed)", file=sys.stderr)
print(out)
