# Project: realestate-trial

Scroll-linked image-sequence canvas (Apple AirPods technique) using GSAP +
ScrollTrigger, embedded into a Wix site via a simple scrollable iframe.

## Architecture
- `generate.py` — builds `index.html` by base64-embedding all JPG frames from
  `ezgif-8a62be381ea7d0f0-jpg.zip` into the `TEMPLATE`. Run after any logic
  change: `python3 generate.py` (regenerates `index.html`, ~9 MB).
- `index.html` — self-contained, deployed to Vercel (auto-deploys from
  `origin/main` on push). Has TWO runtime modes, selected ONLY by the
  `?embed=1` URL flag (NOT by "am I in an iframe?"):
  - **Standalone** (no `?embed=1`): uses GSAP ScrollTrigger with `scrub: 1.2` +
    `pin: stage`, scroll distance = 7× viewport height (slow, graceful scrub).
    This is what runs inside the simple Wix iframe — the iframe scrolls itself,
    which ScrollTrigger reads on its own document.
  - **Embedded** (`?embed=1`): `buildEmbeddedMode()` pins the canvas with
    `position: fixed` and listens for `seq:progress` postMessages from the
    parent, easing the displayed frame toward the target over ~1.2s. This is
    the parent-driver variant (kept as a fallback; the simple iframe does NOT
    use it).
- `wix-code.html` — the snippet the user pastes into Wix "Add Custom Code" →
  "Embed HTML". A plain `<iframe height:100vh>` pointing at the Vercel page
  (no `?embed=1`, no bridge, no pointer-events hacks). ~1.5 KB.

## Why embedded misbehaved while standalone worked
An iframe is its own scrolling context. The earlier postMessage bridge existed
to work around a NON-scrollable iframe (`scrolling="no"`, `position:fixed`
stage) — ScrollTrigger inside it never saw the parent's scroll. But a NORMAL
scrollable iframe scrolls ITSELF when the wheel/touch is over it, which is
exactly what ScrollTrigger needs. So the bridge, sticky host, and
pointer-events hacks were all unnecessary complexity that introduced the
stall-then-jump bug. The simple iframe runs the standalone ScrollTrigger on its
own document and scrubs correctly.

## Key gotchas (learned the hard way)
- **Mode selection must NOT key off "am I in an iframe?"** A plain iframe is
  the common embed case and must run standalone ScrollTrigger. Only the
  explicit `?embed=1` flag selects postMessage mode.
- **Iframe height = visible stage, NOT scroll distance.** Set the iframe to
  ~100vh; the page INSIDE it creates the 7× scroll distance. Making the iframe
  itself 7× tall makes the canvas render at 7× height (huge, wrong).
- **Slow scrub = more scroll distance + heavier scrub.** Distance 7× vh +
  `scrub: 1.2` gives the slow Apple feel. Bump distance to slow further.
- **Two-part deploy.** A code change needs BOTH: (1) push `index.html` to
  redeploy Vercel (iframe content), AND (2) the user re-pastes the updated
  `wix-code.html` into Wix.
- Wix embed char limit is 15,000; `wix-code.html` is ~1.5 KB.

## Local test harness
Serve with `python3 -m http.server 12000` (proxied at
`https://work-1-briloyymccwchcoy.prod-runtime.all-hands.dev/`). To test the
simple embed, build a parent page with `<iframe src=".../index.html">` at
height:100vh. Note: the browser scroll tool can be captured by the iframe, so
to drive intra-iframe scroll use `window.scrollTo` or test the standalone page
directly.

