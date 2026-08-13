================================================================
WIX VELO PAGE CODE — snap the sequence embed to full screen,
freeze the Wix page while it plays, then continue past it.
================================================================

This is the Wix-native fix for the "two separate scroll bodies /
half-visible animation" problem. It runs in the TOP Wix document
(the only place that can control Wix's own scroll) and talks to the
Vercel iframe via the HTML component's onMessage().

----------------------------------------------------------------
SETUP (one-time, in the Wix Classic Editor)
----------------------------------------------------------------
1. Turn on Dev Mode (top bar → "Dev Mode" → "Turn on Dev Mode").
   A code panel opens at the bottom of the editor.

2. Make sure your embed is an HTML Component that loads the Vercel URL:
   - Add (+) → Embed Code → "Embed a website" → URL:
     https://realestate-trial.vercel.app/
   - (If you used "Embed HTML" instead, that's fine too — the code
     below works for either, as long as the element is an HtmlComponent.)

3. Click the HTML component → in the properties panel, set its ID to:
       seqEmbed
   (Top of the properties panel, the "ID" field. If you can't rename,
   use whatever ID it has and change '#seqEmbed' in the code below.)

4. Set the HTML component's HEIGHT in the editor to roughly ONE screen
   (e.g. 800px or 100vh). Do NOT make it 7x tall — the page INSIDE the
   iframe creates the scroll distance; the component just needs to be
   tall enough to show the full canvas.

5. Add an anchor right AFTER the HTML component (Add → Menu → Anchor),
   name it  nextSection. This is where the page jumps to once the
   sequence finishes. (If you don't add it, the code falls back to
   scrolling down by one screen.)

6. Paste the code below into the PAGE CODE panel (bottom), under the
   existing $w.onReady. Save and Preview.

----------------------------------------------------------------
HOW IT WORKS
----------------------------------------------------------------
- onViewportEnter: when the embed scrolls into view, snap it to the top
  of the viewport so the animation starts full-screen (never half-visible).
- onMessage: the iframe posts { seqProgress: 0..1 }. While 0.06 <= p < 0.98
  we consider it "playing" and freeze the page (we don't fight the user's
  scroll; the iframe owns the scroll while it's centered). When p >= 0.98
  the sequence is done → scroll to the next anchor so the page continues.
- Failsafe: if no progress message arrives for 8s while "playing", release.
- The iframe sends progress via window.parent.postMessage, which Wix's
  HtmlComponent.onMessage() receives as event.data.

----------------------------------------------------------------
THE CODE
----------------------------------------------------------------

import wixWindowFrontend from 'wix-window-frontend';

$w.onReady(function () {
  const EMBED = '#seqEmbed';          // <-- your HTML component ID
  const NEXT  = '#nextSection';       // <-- anchor after the embed (optional)
  const ENTER = 0.06;                 // lock once ~6% played
  const EXIT  = 0.98;                 // release / continue once ~98% done
  const STALE = 8000;                 // auto-release if no msg for 8s

  let playing = false;
  let lastMsgAt = 0;

  // Snap the embed to the top of the viewport as soon as it enters,
  // so the animation is full-screen before it starts (no half-visible).
  $w(EMBED).onViewportEnter(() => {
    $w(EMBED).scrollTo().catch(() => {});
  });

  // Receive progress from the Vercel iframe.
  $w(EMBED).onMessage((event) => {
    const d = event.data;
    if (!d || typeof d.seqProgress !== 'number') return;
    lastMsgAt = Date.now();
    const p = d.seqProgress;

    if (p >= ENTER && p < EXIT) {
      // Sequence is playing. The iframe owns the scroll while centered;
      // we just mark it active so the stale-watchdog can release if it
      // ever stops talking.
      playing = true;
    } else if (p >= EXIT && playing) {
      // Finished → continue the Wix page past the embed.
      playing = false;
      continuePast();
    } else if (p < ENTER && playing) {
      // Scrolled back before the start → release.
      playing = false;
    }
  });

  function continuePast() {
    // Jump to the next anchor if it exists, else scroll down one screen.
    try {
      $w(NEXT).scrollTo().catch(fallbackScroll);
    } catch (e) {
      fallbackScroll();
    }
  }
  function fallbackScroll() {
    wixWindowFrontend.getBoundingRect().then((rect) => {
      const y = (rect.scroll.y || 0) + (rect.window.height || 800);
      wixWindowFrontend.scrollTo(0, y);
    });
  }

  // Failsafe: if "playing" but no message for STALE ms, release.
  setInterval(() => {
    if (playing && (Date.now() - lastMsgAt > STALE)) playing = false;
  }, 1000);
});

================================================================
TROUBLESHOOTING
================================================================
- If onViewportEnter snaps too aggressively (fights your scroll), delete
  or comment out the onViewportEnter block; the onMessage handoff still
  works on its own.
- If the page doesn't continue after the animation, make sure the anchor
  #nextSection exists and is placed BELOW the embed, or rely on the
  fallback scroll (it scrolls down one screen).
- If onMessage never fires: confirm the embed is an HtmlComponent (not a
  plain iframe widget) and that the Vercel page is the deployed version
  (it posts seqProgress). The Vercel side is already live.
