"""Sound bank synthesised from scratch (no samples, no licenses): whoosh, whoosh-short, pop, click, typing, impact,
shutter, sparkle, coin, chime, ding, paper, snip, stamp, swell. 48 kHz stereo WAV, named like the CapCut library
ids in capcut.py so the same reel.json "sfx" list works for both routes.

  reelkit sfx                 -> <data>/sfx/*.wav   (done once by `reelkit setup`)
  python sfx.py <out-dir>
"""
import os, sys, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def save(name, x, out):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x], 1) if x.ndim == 1 else x
    with wave.open(os.path.join(out, name + ".wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def env(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-np.maximum(t - a, 0) / r)


def lowpass(x, cut):
    """One-pole low-pass with a variable cutoff (cut: number or array)."""
    cut = np.broadcast_to(np.asarray(cut, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * cut / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y


def tone(f, d, decay=4.0, harm=0.25):
    t = np.arange(int(SR * d)) / SR
    return (np.sin(2 * np.pi * f * t) + harm * np.sin(4 * np.pi * f * t)) * np.exp(-t * decay) * np.minimum(1, t / 0.004)


def whoosh(d=0.7):
    n = int(SR * d); t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    sweep = 200 + 2600 * np.sin(np.pi * t) ** 2
    x = lowpass(noise, sweep) - lowpass(noise, sweep * 0.25)
    return x * np.sin(np.pi * t) ** 1.5 * 0.9


def swell(d=0.9):
    n = int(SR * d); t = np.linspace(0, 1, n)
    noise = lowpass(rng.standard_normal(n), 400 + 3000 * t ** 2) * 0.5
    tn = np.sin(2 * np.pi * np.cumsum(180 + 260 * t ** 2) / SR) * 0.12
    return (noise + tn) * (t ** 2) * np.exp(-np.maximum(t - .85, 0) * 30) * 0.8


def paper(d=0.6):
    n = int(SR * d); t = np.linspace(0, 1, n)
    x = rng.standard_normal(n)
    x = lowpass(x, 5000) - lowpass(x, 900)
    flutter = 0.6 + 0.4 * np.sin(2 * np.pi * 18 * t * (1 - t))
    return x * np.sin(np.pi * t) ** 1.2 * flutter * 0.7


def pop(f0=520, d=0.16):
    n = int(SR * d); t = np.arange(n) / SR
    f = f0 * (1 + 1.2 * np.exp(-t * 40))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.045) * 0.8


def click(d=0.03):
    n = int(SR * d)
    return lowpass(rng.standard_normal(n), 6000) * env(n, 0.0005, 0.006) * 1.6


def snip():
    out = np.zeros(int(SR * 0.35))
    for at in (0.0, 0.14):
        c = click(0.05) * 1.2; i = int(at * SR); out[i:i + len(c)] += c
    n = len(out); out += (lowpass(rng.standard_normal(n), 3000) - lowpass(rng.standard_normal(n), 600)) * env(n, 0.01, 0.12) * 0.25
    return out


def stamp():
    n = int(SR * 0.35); t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * 70 * t * (1 + np.exp(-t * 30))) * env(n, 0.002, 0.08)
    return thump * 0.9 + click(0.35) * 0.5


def impact():
    n = int(SR * 0.9); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 90 * np.exp(-t * 18)) / SR) * np.exp(-t * 4.5)
    body = lowpass(rng.standard_normal(n), 900) * np.exp(-t * 14) * 0.6
    return (boom * 0.95 + body) * np.minimum(1, t / 0.003)


def typing(d=0.9):
    out = np.zeros(int(SR * d)); i = 0
    while i < len(out) - 2000:
        c = click(0.02) * rng.uniform(.4, .8); out[i:i + len(c)] += c
        i += int(SR * rng.uniform(0.07, 0.13))
    return out


def shutter():
    out = np.zeros(int(SR * 0.3))
    for at, g in ((0.0, 1.0), (0.09, 0.7)):
        c = click(0.04) * g; i = int(at * SR); out[i:i + len(c)] += c
    p = paper(0.25) * 0.35; out[int(0.02 * SR):int(0.02 * SR) + len(p)] += p
    return out


def sparkle():
    out = np.zeros(int(SR * 1.4))
    for k, m in enumerate([84, 88, 91, 96, 100]):
        f = 440 * 2 ** ((m - 69) / 12); s = tone(f, 0.9, 3.5, 0.15) * 0.35
        i = int((0.04 + k * 0.07) * SR); out[i:i + len(s)] += s[:len(out) - i]
    return out


def coin():
    out = np.zeros(int(SR * 0.6))
    for k, (f, d) in enumerate(((1975, 0.12), (2637, 0.5))):
        s = tone(f, d, 6 if k else 18, 0.1) * 0.5; i = int(k * 0.07 * SR); out[i:i + len(s)] += s[:len(out) - i]
    return out


def chime():
    out = np.zeros(int(SR * 1.6))
    for k, m in enumerate([76, 83, 88]):
        f = 440 * 2 ** ((m - 69) / 12); s = tone(f, 1.5, 2.2, 0.2) * 0.4
        i = int(k * 0.11 * SR); out[i:i + len(s)] += s[:len(out) - i]
    return out


def ding():
    out = tone(1318.5, 1.0, 3.0, 0.3) * 0.55
    hi = tone(2637, 0.6, 7, 0.0) * 0.2; out[:len(hi)] += hi
    return out


def bed(sec, bpm=84):
    """Quiet lo-fi bed: soft chords + kick + shaker; the voice sits on top."""
    n = int(SR * sec); t = np.arange(n) / SR; beat = 60 / bpm
    chords = [[220.0, 261.6, 329.6], [196.0, 246.9, 293.7], [174.6, 220.0, 261.6], [196.0, 246.9, 311.1]]
    pad = np.zeros(n)
    for k in range(int(sec / (beat * 4)) + 1):
        a, b = int(k * beat * 4 * SR), min(n, int((k + 1) * beat * 4 * SR))
        if a >= n: break
        tt = t[a:b] - t[a]
        e = np.minimum(tt / 0.25, 1) * np.minimum((beat * 4 - tt) / 0.3, 1)
        for f in chords[k % 4]:
            pad[a:b] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * e * 0.12
    pad = lowpass(pad, 1400)
    drum = np.zeros(n)
    kick = np.sin(2 * np.pi * 55 * np.arange(int(SR * .25)) / SR * (1 + 2 * np.exp(-np.arange(int(SR * .25)) / SR * 35))) * env(int(SR * .25), 0.002, 0.09)
    hat = (rng.standard_normal(int(SR * .05)) - lowpass(rng.standard_normal(int(SR * .05)), 5000)) * env(int(SR * .05), 0.001, 0.012)
    for s in range(int(sec / (beat / 2))):
        i = int(s * beat / 2 * SR)
        if s % 4 == 0 and i + len(kick) < n: drum[i:i + len(kick)] += kick * 0.7
        if i + len(hat) < n: drum[i:i + len(hat)] += hat * (0.25 if s % 2 else 0.12)
    x = pad + drum
    fade = np.minimum(np.minimum(t / 0.5, 1), np.minimum((sec - t) / 1.0, 1))
    return x * fade * 0.8


BANK = {"whoosh": whoosh, "whoosh-short": lambda: whoosh(0.35), "swell": swell, "paper": paper, "pop": pop, "snip": snip,
        "stamp": stamp, "impact": impact, "click": click, "typing": typing, "type": typing, "shutter": shutter,
        "sparkle": sparkle, "coin": coin, "chime": chime, "ding": ding}

if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for name, fn in BANK.items():
        save(name, fn(), out)
    save("bed", bed(float(sys.argv[2]) if len(sys.argv) > 2 else 34), out)
    print("sound bank:", len(BANK) + 1, "files in", out)
