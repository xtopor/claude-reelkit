---
name: reel-capcut
description: Finish a built reel in CapCut — upload the picture (everything baked in), the voice and music stems, place CapCut library sound effects on every effect and transition, push an editable CapCut Web draft, and let the creator swap music and sounds by ear before exporting. Optional route; the engine already mixes local sound effects into the MP4. Use when asked for "sound effects from CapCut", "put it into CapCut", "editable draft", "change the music in CapCut", "капкат", "в CapCut".
---

# Reel → CapCut draft (optional)

The default deliverable is the engine's MP4 with local sound effects (`sfx` in reel.json). Use this route only when the creator wants to pick library music and sounds by ear inside CapCut.

Needs: a built reel (`reelkit build <dir> --capcut`), the CapCut MCP server (add it once: `claude mcp add --transport http capcut https://www.capcut.com/api/external_mcp`, then sign in via `/mcp`), and CapCut's own plugin bundle on disk for the uploader and draft builder (see `$(reelkit root)/docs/capcut.md`, env `CAPCUT_PLUGIN_DIR`, default `~/capcut-plugin`).

## Steps
1. `"sfx"` in reel.json is shared with the local mix — one entry per on-screen event:
   ```json
   "sfx": [{"name": "whoosh", "t": 6.9, "vol": 0.5}, {"name": "click", "t": 30.62, "vol": 0.5},
           {"name": "typing", "t": 2.5, "vol": 0.35, "dur": 1.4}, {"name": "my_sounds/rip.mp3", "t": 15.36}]
   ```
   Library names that exist in CapCut: `whoosh`, `whoosh-short`, `pop`, `typing`, `click`, `sparkle`, `coin`, `chime`, `impact`, `shutter`, `ding` (ids in `engine/capcut.py`). Anything else = a local audio file you own, uploaded with the stems.
2. `reelkit capcut stems <dir>` → `out/capcut/{video.mp4, voice.wav, music.wav}` + `files.json`. Voice and music share one gain (sum = −14 LUFS) and a limiter; music is already ducked under the voice.
3. Upload: call `capcut_asset_upload_credential` with `version: 2` and every file's exact `file_name` + `size_bytes` (re-check sizes right before; a mismatch fails with `upload_files_mismatch`). Then
   `printf '%s' <ticket> | node "${CAPCUT_PLUGIN_DIR:-$HOME/capcut-plugin}"/x/plugins/codex/skills/capcut-upload/scripts/capcut-upload.mjs --files "$(cat out/capcut/files.json)" --upload-ticket-stdin --json > out/capcut/upload.json`
   (PowerShell: `Get-Content ticket.txt -Raw | node … --files (Get-Content out/capcut/files.json -Raw) --upload-ticket-stdin --json > out/capcut/upload.json`).
4. `reelkit capcut draft <dir>` → `out/capcut/draft.json` (validated).
5. `start_stdraft_session` → `push_stdraft_snapshot` with `base_package_id: ""` and the draft JSON. Give the creator the `web_editor_url`.
6. Before pushing again, `get_stdraft_snapshot` and build on it — the creator may have edited the draft (read-back is lossy; never overwrite their changes blindly). For small fixes (trim the music tail, volume) prefer doing them in the editor through the browser.

## What to tell the creator
- Listen first: CapCut library sounds have been reported to sit on the timeline but play silent. If so, replace them in Audio → Sound effects, or use local files.
- Music: mute the placeholder stem and pick a library track by ear; trim it to the video length (a longer track adds a black tail to the export).
- Export (top right → Download, 1080p / 30 fps / MP4) saves to their CapCut cloud first: if the cloud space is full, the export fails with "Couldn't save" — free space in their CapCut space or keep the engine's MP4.
- The connector's own sound search (`search_capcut_material`) is a poor title search without previews; the full sound library is only in the CapCut app.
