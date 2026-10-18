"""Beat grid + energy curve of a music track, so cuts can land on the beat.

  reelkit beats <audio> [out.json]
Writes {"bpm", "beats": [t...], "downbeats": [t...], "onsets": [t...], "energy": [[t, rms_db]...], "sections": [[t0, t1, "loud"|"quiet"]...]}
and prints a summary. Pure numpy: spectral-flux onsets, autocorrelation tempo, dynamic-programming beat tracking (Ellis 2007)."""
import json, subprocess, sys, tempfile, wave
from pathlib import Path
import numpy as np

SR, HOP, WIN = 22050, 256, 1024


def load(path):
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ac", "1", "-ar", str(SR), str(w)], check=True)
        with wave.open(str(w)) as f:
            return np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768


def onset_envelope(x):
    n = (len(x) - WIN) // HOP
    win = np.hanning(WIN)
    frames = np.lib.stride_tricks.as_strided(x, (n, WIN), (x.strides[0] * HOP, x.strides[0]))
    S = np.abs(np.fft.rfft(frames * win, axis=1))
    mel = np.log1p(S * 10)
    flux = np.diff(mel, axis=0, prepend=mel[:1]); flux[flux < 0] = 0
    env = flux.mean(axis=1)
    env -= np.convolve(env, np.ones(64) / 64, mode="same")           # local mean removal
    env[env < 0] = 0
    return env / (env.max() + 1e-9)


def tempo(env):
    fps = SR / HOP
    lo, hi = int(fps * 60 / 200), int(fps * 60 / 60)                 # 200..60 BPM
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    ac = ac[:hi + 1] / (ac[0] + 1e-9)
    lag = np.arange(len(ac)); w = np.exp(-0.5 * ((np.log2(lag[lo:hi + 1] * 60 / fps / 120)) / 0.9) ** 2)   # prefer ~120 BPM
    best = lo + int(np.argmax(ac[lo:hi + 1] * w))
    return 60 * fps / best, best


def track(env, period, tightness=400):
    """Ellis dynamic programming: beats maximise onset strength + regular spacing."""
    n = len(env); score = np.full(n, -1e9); back = np.full(n, -1, int)
    score[:1] = env[:1]
    lo, hi = int(period * 0.5), int(period * 2)
    for i in range(1, n):
        a, b = max(0, i - hi), max(0, i - lo)
        if b <= a: score[i] = env[i]; continue
        cands = np.arange(a, b)
        pen = -tightness * (np.log((i - cands) / period)) ** 2
        tot = score[a:b] + pen
        k = int(np.argmax(tot)); score[i] = env[i] + tot[k]; back[i] = a + k
    i = int(np.argmax(score[-int(period * 2):]) + n - int(period * 2))
    beats = []
    while i >= 0: beats.append(i); i = back[i]
    return np.array(beats[::-1])


def main():
    src = Path(sys.argv[1]); out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".beats.json")
    x = load(src); env = onset_envelope(x); fps = SR / HOP
    bpm, period = tempo(env)
    beats = track(env, period) / fps
    # downbeats: the phase (0..3) whose beats carry the most onset energy
    strength = np.array([env[int(b * fps)] if int(b * fps) < len(env) else 0 for b in beats])
    phase = max(range(4), key=lambda p: strength[p::4].sum())
    downbeats = beats[phase::4]
    onsets = [round(float(i / fps), 3) for i in np.where((env > 0.35) & (env >= np.roll(env, 1)) & (env >= np.roll(env, -1)))[0]]
    # energy per second and loud/quiet sections
    sec = int(SR); rms = [20 * np.log10(np.sqrt(np.mean(x[i:i + sec] ** 2)) + 1e-9) for i in range(0, len(x) - sec, sec)]
    rms = np.array(rms); thr = np.median(rms)
    sm = np.convolve(rms, np.ones(5) / 5, mode="same"); loud = sm > thr
    sections, start = [], 0
    for i in range(1, len(loud) + 1):
        if i == len(loud) or loud[i] != loud[start]:
            sections.append([start, i, "loud" if loud[start] else "quiet"]); start = i
    data = {"bpm": round(float(bpm), 1), "beats": [round(float(b), 3) for b in beats], "downbeats": [round(float(b), 3) for b in downbeats],
            "onsets": onsets, "energy": [[i, round(float(v), 1)] for i, v in enumerate(rms)], "sections": sections}
    json.dump(data, open(out, "w", encoding="utf8"))
    print(f"{src.name}: {len(x) / SR:.1f} s, {bpm:.1f} BPM, {len(beats)} beats, bar = {4 * 60 / bpm:.2f} s")
    print("sections:", ", ".join(f"{a}-{b}s {k}" for a, b, k in sections))
    print("downbeats:", " ".join(f"{t:.1f}" for t in downbeats[:48]), "…" if len(downbeats) > 48 else "")
    print("->", out)


if __name__ == "__main__":
    main()
