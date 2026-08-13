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
  html,body{height:100%}
  html{scroll-behavior:auto}
  body{
    background:#000;
    -webkit-font-smoothing:antialiased;
    overflow-x:hidden;
  }

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
    let lastPost = 0;

    // Scroll distance: 7x viewport height = a slow, luxurious scrub through
    // all 250 frames (more scroll distance = slower frame advance).
    wrap.style.height = (window.innerHeight * 7) + "px";

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: wrap,
        start: "top top",
        end: "bottom bottom",
        scrub: 1.2,                 // heavier smoothing = slow, graceful, no stutter
        pin: stage,                 // pin the canvas stage while scrubbing
        anticipatePin: 1,
        invalidateOnRefresh: true,
        onUpdate: function () {
          const f = Math.min(FRAME_COUNT - 1, Math.max(0, Math.round(frameObj.frame)));
          if (f !== lastDrawn) { lastDrawn = f; currentFrame = f; draw(f); }
          // Tell the parent page (e.g. Wix) how far the sequence has played,
          // so it can lock its own scroll while the embed is centered and
          // release it once the sequence finishes. postMessage is the only
          // cross-origin-safe channel from inside an iframe. Throttled.
          var self = this;
          var now = (typeof performance !== "undefined" ? performance.now() : Date.now());
          if (now - lastPost > 90) {
            lastPost = now;
            var p = Math.max(0, Math.min(1, self.progress));
            try { window.parent.postMessage({ seqProgress: p }, "*"); } catch (e) {}
          }
        }
      }
    });

    // When the sequence finishes (or scrolls back before start), tell the parent
    // so it can release its scroll lock. onLeaveBack also releases on scroll-up.
    tl.eventCallback("onComplete", function () {
      try { window.parent.postMessage({ seqProgress: 1 }, "*"); } catch (e) {}
    });
    tl.to(frameObj, { frame: FRAME_COUNT - 1, ease: "none" });

    // Re-measure on resize (debounced) and redraw.
    let rT;
    window.addEventListener("resize", function () {
      clearTimeout(rT);
      rT = setTimeout(function () {
        wrap.style.height = (window.innerHeight * 7) + "px";
        setupCanvas();
        ScrollTrigger.refresh();
      }, 150);
    });

    // First paint.
    setupCanvas();
    draw(0);
  }

  /* ---------------- Embedded mode (driven by parent via postMessage) -------
     When this page is loaded inside an <iframe> (e.g. on a Wix site), the
     parent page owns the scroll. The iframe's own window scroll never moves,
     so ScrollTrigger's progress would be stuck at 0. Instead we listen for a
     "seq:progress" message carrying a 0..1 progress value from the parent,
     and render the matching frame directly. The stage stays pinned/fixed in
     the iframe box, and the parent keeps the box fixed on screen while it
     drives the scroll distance. */
  function buildEmbeddedMode() {
    // No big wrap height needed inside the iframe; the box is sized by parent.
    wrap.style.height = "100%";
    // Make the stage fill the iframe box and pin via simple fixed positioning.
    stage.style.position = "fixed";
    stage.style.inset = "0";
    stage.style.height = "100%";
    stage.style.width = "100%";

    // Smooth (scrubbed) frame chasing. The parent posts a target progress on
    // every scroll; we ease the *displayed* frame toward it over ~0.6s, exactly
    // like GSAP's `scrub: 0.6`. This is what gives the Apple AirPods feel —
    // scroll position is followed, but never snapped, so there's no stutter
    // and no abrupt first→last jump when the parent advances in coarse steps.
    var SCRUB = 1.2;           // seconds to catch up to the target (tune up = lazier)
    var target = 0;            // target frame index (float)
    var shown = 0;             // currently rendered frame index (float)
    var lastDrawn = -1;
    var rafId = null;
    var lastT = 0;

    function clampFrame(v) { return Math.min(FRAME_COUNT - 1, Math.max(0, v)); }
    function targetFromP(p) { return clampFrame(p * (FRAME_COUNT - 1)); }

    function frame(now) {
      rafId = null;
      if (!lastT) lastT = now;
      var dt = (now - lastT) / 1000;
      lastT = now;
      if (dt > 0.1) dt = 0.1;  // clamp tab-switch gaps

      // Exponential approach: each frame moves a fraction of the remaining gap.
      // k chosen so the catch-up is ~SCRUB seconds for a full-range move.
      var k = 1 - Math.pow(0.0001, dt / SCRUB);
      shown += (target - shown) * k;

      var f = Math.round(shown);
      if (f !== lastDrawn) {
        lastDrawn = f;
        currentFrame = f;
        draw(f);
      }
      if (Math.abs(target - shown) > 0.01) {
        rafId = requestAnimationFrame(frame);
      } else {
        // Snap exactly when close enough; redraw the precise target frame.
        shown = target;
        f = Math.round(shown);
        if (f !== lastDrawn) { lastDrawn = f; currentFrame = f; draw(f); }
      }
    }
    function chase() {
      if (rafId === null) { lastT = 0; rafId = requestAnimationFrame(frame); }
    }
    function renderProgress(p) {
      var nt = targetFromP(p);
      if (nt !== target) { target = nt; chase(); }
    }

    window.addEventListener("message", function (ev) {
      if (!ev || !ev.data) return;
      var d = ev.data;
      if (typeof d === "string") { try { d = JSON.parse(d); } catch (e) { return; } }
      if (d && d.type === "seq:progress" && typeof d.p === "number") {
        renderProgress(d.p);
      }
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
    // Choose the scroll driver. We NO LONGER auto-switch on "am I in an iframe?",
    // because a plain scrollable iframe (the simple embed) must run its own
    // ScrollTrigger on its own document — that's what makes it scrub when you
    // scroll the wheel over it. Only the explicit ?embed=1 flag selects the
    // postMessage-driven embedded mode (used by the parent-driver variant).
    var embedFlag = /[?&]embed=1\b/.test(window.location.search);
    if (embedFlag) {
      buildEmbeddedMode();
    } else {
      buildScrollAnimation();
    }
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
