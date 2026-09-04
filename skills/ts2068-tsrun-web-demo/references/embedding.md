# Embed TSRun with automatic cartridge loading

## Working architecture and source map

Source: https://github.com/jon0x0/speech2ay/tree/main/web
Upstream: https://github.com/josef-jelinek/TSRun
Live modules: https://josef-jelinek.github.io/TSRun/
The Audio Lab adapter was initially checked against upstream revision
`390ecb5d6b0dd26bf0fd1e958b25e4237369dc38`; the deployed page follows the live site.
This is recorded experience, not a pinned compatibility guarantee.

| File in speech2ay | Responsibility |
|---|---|
| `web/index.html`, `style.css`, `app.js` | Page, same-origin iframe, start overlay, controls, errors, download and repository links |
| `web/emulator/index.html`, `adapter.js` | Canvas/keyboard and module integration; automatically fetch/insert DCK |
| `web/emulator/sound.worklet.js` | Same-origin shim importing the live upstream worklet |
| `web/assets/` | DCK, flat ROM download, preview and manifest/hash metadata |
| `tests/verify_tsrun.mjs` | Headless engine exercise with actual emulated key presses |
| `.github/workflows/pages.yml` | Build static documentation and deploy `web/` |
| `scripts/render_web_docs.mjs` | Markdown article/guide conversion; keep generated pages synchronized |

Reuse/adapt these files rather than recreating the integration from memory.
There is no need to bundle a TSRun source archive or system ROM in the page repo.
Check upstream terms/provenance when distribution choices change.

## Why an adapter rather than just a remote iframe

Embedding the upstream page can show its UI, but the browser's same-origin rule
prevents the parent from controlling its DOM or silently selecting a local DCK.
The reference hosts a small iframe page on the demo's own origin and imports
TSRun's public ES modules from upstream. It therefore follows upstream updates
while retaining control of loading and UI. This depends on upstream CORS,
module paths and APIs. Check those responses when diagnosing a failure; do not
assume arbitrary remote archives can be executed directly or invent a URL option.

## Startup sequence to preserve

1. Import `machine.js`, `screen.js`, `sound.js`, `keyboard.js`, `joystick.js`.
2. Initialize keyboard and joystick arrays using upstream helpers, then call
   `createMachine`. Fetch upstream shaders and ROMs, plus the local DCK.
3. Check 16384-byte HOME and 8192-byte EXROM images, assign them, call
   `insertDock` and check its returned error, then reset the machine.
4. Initialize WebGL screen and sound, use the actual AudioContext sample rate
   with `setSoundRate`, enable audio, and use mono for the Audio Lab comparison.
5. Pace `runFrame` by emulated frame duration, not blindly once per browser
   animation callback: the reference uses 58688 / 3528000 seconds per frame,
   capped catch-up, and bounded sound-queue refill. Feed `takeAudio` to the
   sound queue and draw `machine.pixels`.
6. Resume audio from a user gesture. Automatic cartridge loading does not
   bypass browser restrictions on audible autoplay. Release emulated keys on
   blur; pair programmatic key-down with key-up. Clear sound/key state on reset.

The upstream sound helper requests `sound.worklet.js` relative to the document.
Keep a local file at that path containing:

```javascript
import 'https://josef-jelinek.github.io/TSRun/sound.worklet.js';
```

Check the upstream helper again if its worklet-loading behavior changes.
The parent uses the iframe's same-origin API for controls and checks both
`event.origin` and `event.source` on readiness/error messages. Show startup
errors and retain a downloadable DCK when upstream is unavailable.

## Validate and publish when requested

Serve over HTTP locally, not file URLs. Test real browser startup, gesture-based
audio activation, keyboard focus/release, reset and error display. On different
refresh-rate displays, check pacing and sound underruns. For Audio Lab, exercise
O/P samples, Q/A codecs, Space playback and S spectra; keep the cartridge hash
and download links aligned with the embedded asset. Headless engine checks can
verify menu/playback progression, but cannot replace browser integration or
listening checks.

GitHub Pages supports this static layout. Keep project-relative resource URLs
working under `/repository-name/`, build documentation, deploy the `web/` artifact,
and check the successful workflow and public page before claiming publication.
The source README links to the demo; the demo links back to the repository.
Do not schedule upstream monitoring or vendor a frozen copy merely to make
live imports reliable unless the user requests that different update policy.
