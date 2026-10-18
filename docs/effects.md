# Effects catalogue

Every effect is a key in `reel.json`; exact fields are in `skills/reel-builder/SKILL.md`. All of them are plain CSS/SVG/JS in `engine/template.html`, rendered frame by frame by headless Chromium, so adding one is editing one HTML file.

| Effect | Key | What it does |
|---|---|---|
| Cover story + frame break | `cover` + segment `cut` | Magazine masthead, letters drop in, the person stands in front of the title (person mask from rembg) |
| Orbit | `orbit` | A phrase circling the head; the back half passes behind the person |
| Doodle boil | `doodles` | Handwritten notes written on stroke by stroke, circles, underlines, arrows, wobbling every 3 frames |
| Strike-through | `doodles` kind `strike` | Crossing out a price or a promise |
| Headline wall | `wall` | Tiles (file names, headlines, notifications) pile up |
| Glass type | `glass` | A title on frosted glass over the footage |
| Black & white + stamp | `look: "bw"` + `stamps` | "Someone else's story"; the synth music muffles |
| Colour burst | `look: "burst"` | Grey → colour bloom on the turn; music opens up |
| Checklist | `checklist` | Steps tick on as they are said; replaces subtitles while up |
| Photo montage | `look: "memory"` + `date` | Zoom-through fly-in of photos with an orange camera date stamp |
| Zoom-through / whip cut | segment `in: "zoom"` / `"whip"` | The outgoing shot rushes in, the next lands from a zoom; or a fast blurred slide |
| Hook card / end card | `hook` / `end` | Paper card on frame 0; question + CTA + handle over the final shot |
| Punch-ins | `punch` | Digital zoom on accent words (automatic from `<em>`) |
| Moves | segment `move` | Slow push (default), tilt-up, pull-out, none; `rate` for slow motion; `crop` for punch-in crops |
| Subtitles | automatic from `script` | 5–7 words, accent words in italic accent colour, safe-zone aware |
| Safe-zone QA sheet | `--stills` | Red overlay of the Reels/TikTok UI zones on key frames |

## Choosing effects
Use 3–5 per reel, each on the beat it explains — see the table in `skills/reel-director/SKILL.md`. Effects must read at phone size on the first watch.

## Not built yet (ideas welcome)
couch wall · UI world · phone mockup · green screen · paper cut · vertigo (dolly zoom) · chart grow as an engine key.
