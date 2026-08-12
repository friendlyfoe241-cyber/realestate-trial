# Project: realestate-trial

Scroll-linked image-sequence canvas (Apple AirPods technique) using GSAP +
ScrollTrigger, embedded into a Wix site via an iframe + postMessage bridge.

## Architecture
- `generate.py` — builds `index.html` by base64-embedding all JPG frames from
  `ezgif-8a62be381ea7d0f0-jpg.zip` into the `TEMPLATE`. Run after any logic
  change: `python3 generate.py` (regenerates `index.html`, ~9 MB).
- `index.html` — self-contained, deployed to Vercel (auto-deploys from
  `origin/main` on push). Has TWO runtime modes:
  - **Standalone** (not framed, no `?embed=1`): uses GSAP ScrollTrigger with
    `scrub: 0.6` + `pin: stage`. This is the smooth reference implementation.
  - **Embedded** (`window.self !== window.top` OR `?embed=1`): `buildEmbeddedMode()`
    pins the canvas with `position: fixed` and listens for `seq:progress`
    postMessages from the parent, easing the displayed frame toward the target
    over ~0.6s (mirrors `scrub: 0.6`).
- `wix-code.html` — the snippet the user pastes into Wix "Add Custom Code" →
  "Embed HTML". Contains `#seq-embed-host` (sized to the scroll distance),
  `#seq-embed-stage` (sticky, 100vh), and an iframe pointing at the Vercel
  page with `?embed=1`. Computes parent scroll progress and posts it.

## Key gotchas (learned the hard way)
- **Iframe eats scroll events.** A fullscreen `position: fixed` iframe over the
  viewport captures wheel/touch, so the parent page stops scrolling while the
  canvas is pinned → progress stalls then jumps. Fix: `pointer-events: none`
  on `#seq-embed-stage` and `#seq-embed-frame` so events pass through to the
  parent. The canvas is display-only, so this is safe.
- **No smoothing = jump.** Mapping parent progress straight to a frame index
  snaps. Always ease the displayed frame toward the target (~0.6s) to match
  GSAP's `scrub: 0.6` Apple feel.
- **Two-part deploy.** A code change needs BOTH: (1) push `index.html` to
  redeploy Vercel (iframe content), AND (2) the user re-pastes the updated
  `wix-code.html` into Wix (parent driver).
- Wix embed char limit is 15,000; `wix-code.html` is ~6 KB.

## Local test harness
Serve with `python3 -m http.server 12000` (proxied at
`https://work-1-briloyymccwchcoy.prod-runtime.all-hands.dev/`). To test the
embed driver locally, build a parent page that includes `wix-code.html` with
the iframe src rewritten to the local `index.html?embed=1`, then drive scroll
with `window.scrollTo` (the browser scroll tool can get captured by the iframe).
