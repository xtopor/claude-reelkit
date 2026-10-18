# Third-party notices

claude-reelkit is MIT-licensed (see `LICENSE`). It builds on:

| Part | Where | Origin | License |
|---|---|---|---|
| Reel engine (`build.py`, `template.html`, `music.py`, `capcut.py`, `pull_vo.py`), contact sheets, plate/refine tools, the four script structures and the skill workflow, adapted and ported to Windows/Linux (rembg masks instead of Apple Vision, edge-tts voice, local sound effects, Node CLI) | `engine/`, `tools/`, `skills/` | [lalimi/claude-reelsmith](https://github.com/lalimi/claude-reelsmith) © 2026 lalimi | MIT |
| Talking-head prep scripts (`clean_audio.py`, `common.py`, `lines.py`, `tighten.py`, `cut.py`, `qa.py`), adapted | `skills/talking-head-edit/prep/` | [nicolapocock/claude-reel-editor](https://github.com/nicolapocock/claude-reel-editor) © 2026 Nicola Pocock, via claude-reelsmith | MIT — `skills/talking-head-edit/prep/LICENSE-claude-reel-editor` |
| Table of tested CapCut library sound ids | `engine/capcut.py` | same repository | MIT |
| Playfair Display, Manrope, JetBrains Mono (woff2 subsets) | `engine/fonts/` | Google Fonts / their authors | SIL Open Font License 1.1 — `engine/fonts/OFL.txt` |
| Playwright (installed by `reelkit setup`) | data folder | Microsoft | Apache-2.0 |
| faster-whisper, NumPy, OpenCV, Pillow (installed into the venv) | data folder | their authors | MIT / BSD / Apache-2.0 / HPND |
| edge-tts (installed into the venv) | data folder | rany2 | LGPL-3.0 (library); the Microsoft voices it reaches are a free online service, see `docs/voice.md` |
| rembg + onnxruntime + the `u2net_human_seg` model (downloaded on first use) | data folder | danielgatis / Microsoft / Xuebin Qin et al. | MIT / MIT / Apache-2.0 |

Sound effects in `engine/sfx.py` are synthesised from scratch (no samples, no licenses). The generated music bed in `engine/music.py` is synthesised too.

Not included, downloaded by the user if they want it: FFmpeg, CapCut's plugin bundle (uploader + draft builder, CapCut's own terms), ElevenLabs (their terms).
