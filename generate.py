#!/usr/bin/env python3
"""Generate a single self-contained index.html containing a GSAP/ScrollTrigger
scroll-linked image-sequence canvas from a zip of JPG frames.

Each frame is base64-embedded as a data URI, so the resulting file works with
no external image hosting — just drop it on your site.
"""
import base64
import json
import re
import sys
import zipfile

ZIP_PATH = "ezgif-8a62be381ea7d0f0-jpg.zip"
OUT_PATH = "index.html"

FRAME_RE = re.compile(r"ezgif-frame-(\d+)\.jpg", re.IGNORECASE)


def frames_in_order(zip_path):
    z = zipfile.ZipFile(zip_path)
    items = []
    for info in z.infolist():
        m = FRAME_RE.match(info.filename)
        if m:
            items.append((int(m.group(1)), info.filename))
    items.sort()
    return [(name, z.read(name)) for _, name in items]


def main():
    frames = frames_in_order(ZIP_PATH)
    if not frames:
        sys.exit(f"No matching frames found in {ZIP_PATH}")
    print(f"Embedding {len(frames)} frames ...")

    # Build the JSON array of base64 data URIs. Using json.dumps guarantees
    # correct string escaping for every byte of the data URIs.
    uris = [
        "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        for _, data in frames
    ]
    frames_json = json.dumps(uris)

    html = TEMPLATE.replace("__FRAMES_JSON__", frames_json)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUT_PATH} ({len(html):,} bytes)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<title>Scroll Image Sequence</title>
<style>
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  html{scroll-behavior:auto}
  body{
    background:#0b0b0d;color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased;
  }

  /* ---------- Intro / outro sections (regular scroll) ---------- */
  section.intro,section.outro{
    min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;
    text-align:center;padding:2rem;position:relative;
  }
  section.intro h1{font-size:clamp(2rem,7vw,4.5rem);font-weight:700;letter-spacing:-.02em;line-height:1.05}
  section.intro p{margin-top:1rem;max-width:42ch;color:#a1a1aa;font-size:clamp(1rem,2.4vw,1.25rem)}
  section.outro h2{font-size:clamp(1.6rem,5vw,3rem);font-weight:700}
  section.outro p{margin-top:1rem;max-width:46ch;color:#a1a1aa;font-size:clamp(.95rem,2.2vw,1.15rem)}
  .scroll-hint{margin-top:2.5rem;color:#71717a;font-size:.9rem;letter-spacing:.18em;text-transform:uppercase;animation:bob 1.8s ease-in-out infinite}
  @keyframes bob{0%,100%{transform:translateY(0);opacity:.6}50%{transform:translateY(6px);opacity:1}}

  /* ---------- Pinned sequence stage ---------- */
  #sequence-wrap{
    position:relative;
    /* height is set in JS: scroll distance over which the sequence scrubs */
    background:#000;
  }
  #sequence-stage{
    position:relative;width:100%;
    /* fixed height that scales down on small screens */
    height:100vh;height:100dvh;
    overflow:hidden;
  }
  #sequence-canvas{
    position:absolute;top:50%;left:50%;
    transform:translate(-50%,-50%);
    display:block;
    width:auto;height:100%;
    max-width:100%;max-height:100%;
    /* keep crisp: avoid sub-pixel blur from CSS scaling */
    image-rendering:auto;
    background:#000;
  }

  /* ---------- Loading overlay (graceful fallback) ---------- */
  #loader{
    position:absolute;inset:0;z-index:5;display:flex;flex-direction:column;
    align-items:center;justify-content:center;gap:1.1rem;background:#0b0b0d;
    transition:opacity .6s ease;backdrop-filter:blur(2px);
  }
  #loader.hidden{opacity:0;pointer-events:none}
  #loader .ring{
    width:46px;height:46px;border-radius:50%;
    border:3px solid rgba(255,255,255,.15);border-top-color:#fff;
    animation:spin .9s linear infinite;
  }
  @keyframes spin{to{transform:rotate(360deg)}}
  #loader .bar{width:min(240px,60vw);height:4px;border-radius:99px;background:rgba(255,255,255,.15);overflow:hidden}
  #loader .bar > span{display:block;height:100%;width:0%;background:#fff;transition:width .2s ease}
  #loader .label{color:#a1a1aa;font-size:.8rem;letter-spacing:.12em;text-transform:uppercase}
  #loader .fallback{
    color:#71717a;font-size:.8rem;max-width:34ch;text-align:center;display:none;line-height:1.5;
  }
  #loader.show-fallback .fallback{display:block}
  #loader.show-fallback .ring,#loader.show-fallback .bar,#loader.show-fallback .pct{display:none}
  #loader .pct{color:#d4d4d8;font-variant-numeric:tabular-nums;font-size:.85rem}
</style>
</head>
<body>

<section class="intro">
  <h1>Scroll to animate</h1>
  <p>A frame-by-frame image sequence, scrubbed by your scroll position &mdash; the Apple AirPods technique.</p>
  <div class="scroll-hint">Scroll down</div>
</section>

<div id="sequence-wrap">
  <div id="sequence-stage">
    <canvas id="sequence-canvas"></canvas>
    <div id="loader" aria-live="polite">
      <div class="ring" aria-hidden="true"></div>
      <div class="bar" aria-hidden="true"><span></span></div>
      <div class="pct">0%</div>
      <div class="label">Preparing sequence</div>
      <div class="fallback">The sequence is still loading. Scroll to explore, or wait a moment for full quality.</div>
    </div>
  </div>
</div>

<section class="outro">
  <h2>That&rsquo;s the sequence</h2>
  <p>Keep scrolling for the rest of your page content.</p>
</section>

<!-- GSAP + ScrollTrigger -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
<script>
(function () {
  "use strict";

  // Frames are embedded as base64 data URIs at build time.
  const FRAMES = __FRAMES_JSON__;
  const FRAME_COUNT = FRAMES.length;

  const canvas = document.getElementById("sequence-canvas");
  const ctx = canvas.getContext("2d", { alpha: false });
  const stage = document.getElementById("sequence-stage");
  const wrap = document.getElementById("sequence-wrap");
  const loader = document.getElementById("loader");

  let images = new Array(FRAME_COUNT);
  let loadedCount = 0;
  let currentFrame = 0;
  let ctxReady = false;

  /* ---------------- Canvas sizing (DPR-sharp, centered, cover) ---------------- */
  function setupCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2); // cap DPR for perf
    const cssW = stage.clientWidth;
    const cssH = stage.clientHeight;
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    canvas.style.width = cssW + "px";
    canvas.style.height = cssH + "px";
    ctxReady = true;
    draw(currentFrame); // re-draw current frame at new size
  }

  /* Draw a frame as "cover": scaled to fill, centered, no distortion. */
  function draw(index) {
    if (!ctxReady) return;
    const img = images[index];
    const w = canvas.width, h = canvas.height;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, w, h);
    if (!img || !img.complete || img.naturalWidth === 0) return;

    const ir = img.naturalWidth / img.naturalHeight;
    const cr = w / h;
    let dw, dh;
    if (ir > cr) { dh = h; dw = h * ir; }      // image wider -> match height
    else         { dw = w; dh = w / ir; }      // image taller -> match width
    const dx = (w - dw) / 2;
    const dy = (h - dh) / 2;
    ctx.drawImage(img, dx, dy, dw, dh);
  }

  /* ---------------- Preload frames ---------------- */
  function preload() {
    return new Promise(function (resolve) {
      const fill = document.querySelector("#loader .bar > span");
      const pct = loader.querySelector(".pct");
      let resolved = false;

      function onLoad(i) {
        return function () {
          images[i] = this;
          loadedCount++;
          const p = Math.round((loadedCount / FRAME_COUNT) * 100);
          if (fill) fill.style.width = p + "%";
          if (pct) pct.textContent = p + "%";
          if (loadedCount === 1) draw(0);              // show first frame ASAP
          if (loadedCount >= FRAME_COUNT && !resolved) { resolved = true; resolve(true); }
        };
      }
      function onError(i) {
        return function () {
          loadedCount++;
          if (loadedCount >= FRAME_COUNT && !resolved) { resolved = true; resolve(false); }
        };
      }

      for (let i = 0; i < FRAME_COUNT; i++) {
        const img = new Image();
        img.decoding = "async";
        img.onload = onLoad(i);
        img.onerror = onError(i);
        img.src = FRAMES[i];
        images[i] = img; // keep ref even before load for draw() checks
      }

      // Timeout-based fallback: if not everything is loaded after 12s,
      // reveal the graceful-fallback message but keep the sequence usable
      // with whatever has loaded so far.
      setTimeout(function () {
        if (!resolved) {
          loader.classList.add("show-fallback");
        }
      }, 12000);
    });
  }

  /* ---------------- Scroll-linked animation ---------------- */
  function buildScrollAnimation() {
    gsap.registerPlugin(ScrollTrigger);

    const frameObj = { frame: 0 };
    let lastDrawn = -1;

    // Scroll distance: 4x the viewport height gives a comfortable scrub length.
    wrap.style.height = (window.innerHeight * 4) + "px";

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: wrap,
        start: "top top",
        end: "bottom bottom",
        scrub: 0.6,                 // smooth, no stutter; tune up for snappier scrub
        pin: stage,                 // pin the canvas stage while scrubbing
        anticipatePin: 1,
        invalidateOnRefresh: true,
        onUpdate: function () {
          const f = Math.min(FRAME_COUNT - 1, Math.max(0, Math.round(frameObj.frame)));
          if (f !== lastDrawn) { lastDrawn = f; currentFrame = f; draw(f); }
        }
      }
    });
    tl.to(frameObj, { frame: FRAME_COUNT - 1, ease: "none" });

    // Re-measure on resize (debounced) and redraw.
    let rT;
    window.addEventListener("resize", function () {
      clearTimeout(rT);
      rT = setTimeout(function () {
        wrap.style.height = (window.innerHeight * 4) + "px";
        setupCanvas();
        ScrollTrigger.refresh();
      }, 150);
    });

    // First paint.
    setupCanvas();
    draw(0);
  }

  /* ---------------- Boot ---------------- */
  function hideLoader() {
    loader.classList.add("hidden");
    setTimeout(function () { if (loader.parentNode) loader.parentNode.removeChild(loader); }, 700);
  }

  preload().then(function (allLoaded) {
    buildScrollAnimation();
    hideLoader();
    if (!allLoaded) {
      // Some frames failed; the timeline still works on the ones that loaded.
      console.warn("Scroll sequence: some frames failed to load; continuing with available frames.");
    }
  });
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
