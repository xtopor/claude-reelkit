"""Person masks without Apple Vision: rembg (u2net_human_seg, runs on CPU anywhere) -> alpha PNG per frame +
meta.json with the head position, the same format the engine's cover / orbit effects expect.

  reelkit masks <frames-dir> <out-dir>
Writes <name>.png (white, alpha = person, 1080x1920) for every .jpg and meta.json: per frame [top, cx, width]
of the subject's top band, or null when no person was found. Alpha is smoothed over neighbouring frames so the
cut-out does not flicker."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
files = sorted(p for p in src.glob("*.jpg") if not p.name.startswith("_"))
if not files: sys.exit(f"no frames in {src}")

from rembg import new_session, remove
session = new_session("u2net_human_seg")

alphas = []
for i, f in enumerate(files):
    im = Image.open(f).convert("RGB")
    small = im.resize((im.width // 2, im.height // 2), Image.BILINEAR)          # masks are soft anyway; 2x faster
    m = remove(small, session=session, only_mask=True, post_process_mask=True)
    alphas.append(np.asarray(m.resize(im.size, Image.BILINEAR), dtype=np.float32) / 255)
    if i % 20 == 0: print(f"masks {i + 1}/{len(files)}", flush=True)

meta, missed = [], 0
for i, f in enumerate(files):
    a = 0.25 * alphas[max(i - 1, 0)] + 0.5 * alphas[i] + 0.25 * alphas[min(i + 1, len(files) - 1)]
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255
    h, w = a.shape
    hard = a > 0.5
    rows = np.where(hard.sum(axis=1) >= 3)[0]
    if len(rows) == 0 or hard.mean() < 0.01:
        missed += 1; meta.append(None)
        Image.new("RGBA", (w, h), (0, 0, 0, 0)).save(out / (f.stem + ".png")); continue
    top = int(rows[0])
    band = hard[top:min(h, top + 160)]
    cols = np.where(band.any(axis=0))[0]
    meta.append([top, int((cols[0] + cols[-1]) / 2), int(cols[-1] - cols[0])])
    rgba = np.zeros((h, w, 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = (a * 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(out / (f.stem + ".png"))
json.dump(meta, open(out / "meta.json", "w"))
print("masks:", len(files) - missed, "/", len(files), f"(no person in {missed})" if missed else "")
