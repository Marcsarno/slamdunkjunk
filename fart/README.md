# Fart Machine

A pocket fart machine you can install on your phone: one big random button (a whoopee cushion) and five
presets: The Classic, The Squeaker, The Thunder, The Wet One and The Machine Gun.

There are no sound files. Every fart is synthesized on the spot in `index.html` (a buzzing pulse wave plus
breathy noise, shaped by flutter and sputters, muffled by a low-pass filter, with bubble pops for the wet
ones), so each press sounds a little different and the random button never repeats.

## Run it
`python3 -m http.server 8765` in this folder, then open http://127.0.0.1:8765/.

## Install it on a phone
Host this folder anywhere with HTTPS (GitHub Pages, Vercel, Netlify), open it on the phone, then
"Add to Home Screen" (Safari share menu) or "Install app" (Chrome menu). After the first visit it works
offline (`sw.js` caches it).

## Files
- `index.html` the whole app
- `manifest.webmanifest`, `sw.js` what makes it installable and offline
- `icons/` home-screen icons, drawn by `make_icons.py`
