# Fart Machine

A pocket fart machine you can install on your phone: one big random button (a whoopee cushion) and five
presets: The Classic, The Squeaker, The Wet One, The Thunder and The Long Haul.

The farts are real recordings (`sounds/`, credits and licenses in `sounds/CREDITS.md`). The random button
picks any of the nine and bends its pitch a little, so no two presses match.

## Run it
`python3 -m http.server 8765` in this folder, then open http://127.0.0.1:8765/.

## Install it on a phone
Host this folder anywhere with HTTPS (GitHub Pages, Vercel, Netlify), open it on the phone, then
"Add to Home Screen" (Safari share menu) or "Install app" (Chrome menu). After the first visit it works
offline (`sw.js` caches it).

## Files
- `index.html` the whole app
- `sounds/` the nine recordings, with their credits and licenses
- `manifest.webmanifest`, `sw.js` what makes it installable and offline
- `icons/` home-screen icons, drawn by `make_icons.py`
