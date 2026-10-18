# claude-reelkit 🎬

**Reels and TikToks from your own footage, directed and edited by Claude Code.**
You approve an idea and a script. Claude writes it, voices it with a free TTS voice, picks fresh shots from your camera roll, cuts them to the words, adds motion effects and subtitles, mixes sound, and hands you a post-ready MP4, a cover and a caption. Your time: about 10 minutes per reel.

Runs on **Windows, Linux and macOS**. Voice: free Microsoft neural voices (70+ languages). Person cut-outs for the effects: rembg, no Apple Vision. Sound effects: a synthesised, licence-free bank mixed locally, no CapCut required.

[Українська](README.md)

## What's inside

| Skill | What it does |
|---|---|
| 🎬 **reel-director** | Runs the job end to end, picks the story structure, decides which 3–5 effects go on which beat, plans transitions and sound, then reviews the cut like a critic. |
| ✍️ **reel-script** | Scripts from 4 structures reverse-engineered from viral reels (contrarian hook, series with cliffhanger, list of factors, "the scenario of…"). Analyses reels you paste, writes in your language. |
| 🎞 **footage-scout** | Picks fresh clips from a folder, files sent in chat or a shared iCloud album in your browser; contact sheets; privacy pass; used-footage log. |
| ✂️ **reel-builder** | One `reel.json` → finished 1080×1920 MP4 with subtitles, cards, effects, music, sound effects and a −14 LUFS mix. |
| 🗣 **talking-head-edit** | For talking-to-camera videos: audio cleanup, filler cutting, word-by-word captions, layouts, UI cards. |
| 🔊 **reel-capcut** | Optional: an editable CapCut draft with library sound effects on every transition. |

Engine effects (keys in `reel.json`, see [docs/effects.md](docs/effects.md)): cover story + frame break · orbit text around the head · doodle boil · glass type · headline wall · checklist · black-and-white → colour burst · photo montage with camera date stamp · punch-ins on accent words · zoom-through and whip transitions · hook and end cards · stamps · subtitles with accent words · Reels/TikTok safe-zone QA sheet.

## Install

Requirements: [Claude Code](https://claude.com/claude-code), `ffmpeg`, `node` ≥ 20, `python` ≥ 3.10.
Windows: `winget install Gyan.FFmpeg OpenJS.NodeJS.LTS Python.Python.3.12` · macOS: `brew install ffmpeg node python` · Linux: `apt install ffmpeg nodejs python3-venv`.

**As a Claude Code plugin** (recommended):
```
/plugin marketplace add xtopor/claude-reelkit
/plugin install reelkit@xtopor
```
Then once: `/reelkit:setup` (or `reelkit setup` in a terminal; 3–6 min: python venv with faster-whisper, edge-tts and rembg, Playwright Chromium, the sound bank, the `reelkit` command).

**Or manually:**
```bash
git clone https://github.com/xtopor/claude-reelkit && cd claude-reelkit
node bin/reelkit.mjs setup
```
Check anytime with `reelkit doctor`. Heavy dependencies live outside the plugin folder (`%LOCALAPPDATA%\reelkit` on Windows, `~/.local/share/reelkit` elsewhere), so plugin updates do not touch them.

### Connectors (all optional)
- **A browser connector** (Claude in Chrome or the chrome-devtools MCP) lets Claude browse your shared photo album in your logged-in browser. Claude never types your passwords.
- **ElevenLabs** if you prefer their voices to the free ones → [docs/voice.md](docs/voice.md).
- **CapCut MCP** only for the CapCut route → [docs/capcut.md](docs/capcut.md).

## Quick start

Open Claude Code in a folder for your reels and say:

> Make me a 45-second reel for my Instagram about why people never launch their course. My clips are in the "video" folder, use only new ones. Voice: Polina.

The director asks a few questions, shows you a script to approve, then builds. Or drive the engine yourself:

```bash
reelkit new reels/launch            # folder + template reel.json
reelkit sheet reels/launch/src/*    # contact sheets to pick moments
reelkit tts reels/launch            # free voice-over from the script + word timings
reelkit build reels/launch --stills # fast preview + safe-zone QA sheet
reelkit build reels/launch          # final MP4, cover.jpg, caption.txt in reels/launch/out/
```

## How it works

```
idea ─► reel-script ─► approved script ─► voice (reelkit tts / your recording / ElevenLabs) ─► word timings
                                                                                                │
footage-scout ─► fresh clips ─► reel.json (beats, effects, transitions, sfx) ◄──────────────────┘
                                     │
reel-builder: HTML page per frame (Playwright) ─► ffmpeg ─► MP4 + cover + caption ─► director's critic pass
                                     │
                         (optional) reel-capcut ─► editable CapCut draft
```
Every frame is an HTML page rendered by headless Chromium, so effects are plain CSS/SVG/JS in `engine/template.html`.

## Privacy
Your footage, voice and renders stay on your machine (`.gitignore` excludes `src/`, `out/`, `frames/`). The TTS sends only the script text to Microsoft's voice service. Nothing else is uploaded unless you use the CapCut route.

## Credits & license
MIT — see [LICENSE](LICENSE). Grown from [lalimi/claude-reelsmith](https://github.com/lalimi/claude-reelsmith) (MIT): the engine, script structures and workflow come from there, ported to Windows/Linux with a free voice, rembg masks and local sound effects. Talking-head prep scripts from [nicolapocock/claude-reel-editor](https://github.com/nicolapocock/claude-reel-editor) (MIT). Fonts under SIL OFL 1.1. Full list: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
