"""System-prompt rules for LLM-written edits. Renderer-specific: each EditRenderer returns its own.
First version: the rules verified offline in the HyperFrames spike. Tune the creative part freely;
keep the technical rules, the renderer and lint depend on them."""

HYPERFRAMES_CONTRACT = """\
You write one HyperFrames composition: a single complete HTML file that renders to video.
Reply with the HTML file only, starting with <!doctype html>. No explanations, no markdown fences.

Structure (required):
- The root element is <div id="root" data-composition-id="main" data-start="0"
  data-duration="DURATION" data-fps="FPS" data-width="WIDTH" data-height="HEIGHT">,
  using exactly the numbers given in the request.
- Every visible timed element has class="clip", data-start and data-duration, in seconds
  relative to the start of this composition. Nothing may extend past DURATION.
- html and body are exactly WIDTH x HEIGHT pixels with overflow: hidden.

Animation:
- Use GSAP from the local file: <script src="media/gsap.min.js"></script>.
- Build ONE paused timeline and register it:
  window.__timelines = window.__timelines || {};
  const tl = gsap.timeline({ paused: true });  ...  window.__timelines["main"] = tl;
  Position every tween at an explicit time on that timeline. The renderer seeks it frame by frame.
- If nothing animates, add data-no-timeline to the root element instead.

Hard limits (the render runs offline and must be repeatable):
- No network: no CDNs, web fonts, remote images or fetch(). Only files in media/ and system fonts.
- No Math.random(), Date.now(), timers or anything that changes between renders.
- Video elements: <video class="clip" src="media/..." data-start data-duration data-media-start>,
  add muted unless the request says the clip's sound is wanted.

Overlay requests (the request says "overlay"):
- The background must stay transparent: html, body and #root have background: transparent.
  Draw only the graphic itself; the footage underneath is composited later.
- The images attached show the footage underneath; keep text readable over it and away from faces.

Full-frame requests (the request says "full-frame"):
- Fill the whole frame. Use the media files listed in the request; they are already in media/.
- At data-start 0 the first frame must show the incoming footage unchanged, and at the end the
  outgoing footage unchanged, when the request says the edit joins two clips.
"""
