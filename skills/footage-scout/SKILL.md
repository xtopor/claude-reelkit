---
name: footage-scout
description: Pick fresh clips and photos for a reel from the creator's own footage — a local folder, a phone dump, files sent in chat, or a shared iCloud Photos / Google Photos album opened in their browser (Claude in Chrome or the chrome-devtools MCP) — and copy only what the edit needs. Catalogues the footage, checks candidates at full size, makes contact sheets, picks in/out points per beat, skips private details, and keeps a used-footage log so no clip is reused. Use when asked to "find shots for this reel", "take new footage", "use my album", "бери тільки потрібне відео", "подбери кадры", "вот мои видео, выбери", or when the editor needs B-roll for a script.
---

# Footage scout

Input: an approved script / beat map (see `reel-director`). Output: `<reel-dir>/src/<what>_<id>.<ext>` files, contact sheets, and a list "beat → clip → ss/dur".

## Rules
- **Fresh only.** Read `used_footage.md` (in the reels workspace) first; never reuse a clip listed there unless the creator asks. Append every clip you use, with what is in it.
- **Copy only what you use.** Disks fill up: 4K HEVC is ~3 MB/s. Long clips can be trimmed later; copy, never move, the originals.
- **Privacy pass at full resolution** before a clip goes in: other people's faces (ask first), messages and DMs on screens, private dashboards / numbers, car plates, street names and house numbers, ID documents. Skip those seconds or reframe with `crop`.
- **Never type passwords** for the creator. If a browser asks them to sign in (Apple ID, Google), stop and let them do it themselves in their own browser — a sign-in from an automated browser can lock their account.

## From a local folder or files sent in chat
```bash
reelkit sheet path/to/clips/*.MOV -o sheets/   # 10 frames per clip, prints the timestamps
```
On Windows PowerShell expand the wildcard yourself: `reelkit sheet (Get-ChildItem clips\*.mp4).FullName -o sheets`. Read the strips, pick `ss` for each beat, copy the chosen files into `<reel-dir>/src/` with descriptive names (`phone_walk_1042.MOV`). Files that arrive in chat: move them from the uploads folder into `src/` the same way. HEIC photos are fine (`img` in a segment).

## From a shared iCloud Photos album (browser automation)
The creator opens the album in their own browser where they are logged in, and connects Claude in Chrome (or you drive the dedicated debug Chrome through the chrome-devtools MCP).
1. **Catalogue**: scroll the grid screen by screen and zoom into thumbnails; note duration badges and what each shows. The grid scrolls inside an iframe: `document.querySelector('iframe').contentDocument.querySelector('.grid-scroll').scrollTop = row * rowHeight` jumps to a row; item index = row × columns + column.
2. **Check**: double-click a candidate. The viewer header shows place, date and "N of total" — note N. Look at it large before choosing.
3. **Download**: the viewer's "Save" button sits right next to "Delete". Click it through its `aria-label` via JavaScript in the iframe, not by coordinates, then choose "Download". Files arrive in `~/Downloads` as `IMG_xxxx`; move each into `<reel-dir>/src/` with a descriptive name.
4. A name with " (1)" means a file with that name already existed — it is a different clip unless the dates match.
Arrow keys in the viewer are throttled; navigating by grid position is faster.

## Picking in/out points
- One beat = one clip section; match the picture to the words (literal where possible).
- Start a clip on movement, not on a still moment; avoid the first and last 0.3 s of phone clips (shake).
- Faces: keep eyes out of the zones where cards and subtitles will sit (top ~280 px, bottom ~420 px, card area ~1000–1450 px).
- For `cover` and `orbit` choose shots with one person, head clearly separated from the background (the rembg person mask works best on a single person, upper body visible).
- Short usable part? Use `rate` (slow motion) instead of including the bad seconds.
- iPhone HDR clips look washed out in some players; the engine's frames come through ffmpeg and look fine, but check the first still.
