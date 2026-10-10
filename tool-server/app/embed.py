"""Inline HTML embed that Open WebUI renders directly in the chat message.

Open WebUI shows an external tool's HTML response in an iframe when the response
carries `Content-Disposition: inline`. Using it means the image appears
regardless of whether the (small) LLM repeats a markdown link correctly.
The image is inlined as a data URI so it does not depend on any host/port
being reachable from the browser or on http/https mixed-content rules.
"""

import base64
from html import escape

# Header Open WebUI looks for to decide the response is an embed, not tool text.
EMBED_HEADERS = {"Content-Disposition": "inline"}

_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; background: transparent; }}
  figure {{ margin: 0; padding: 4px 0; font: 13px system-ui, sans-serif; color: #888; }}
  img {{ display: block; max-width: 100%; height: auto; border-radius: 8px; }}
  figcaption {{ margin-top: 6px; }}
  a {{ color: inherit; }}
</style>
</head>
<body>
<figure>
  <img id="img" alt="{alt}" src="data:image/png;base64,{b64}">
  <figcaption>{alt} &middot; seed {seed} &middot;
    <a href="data:image/png;base64,{b64}" download="image-{seed}.png">download</a></figcaption>
</figure>
<script>
  // Tell Open WebUI how tall the iframe should be (it cannot measure it itself).
  function report() {{
    parent.postMessage({{ type: "iframe:height", height: document.documentElement.scrollHeight }}, "*");
  }}
  document.getElementById("img").addEventListener("load", report);
  window.addEventListener("load", report);
  window.addEventListener("resize", report);
</script>
</body>
</html>
"""


def render_image_embed(png_bytes: bytes, alt: str, seed: int) -> str:
    return _TEMPLATE.format(
        alt=escape(alt, quote=True),
        b64=base64.b64encode(png_bytes).decode("ascii"),
        seed=seed,
    )
