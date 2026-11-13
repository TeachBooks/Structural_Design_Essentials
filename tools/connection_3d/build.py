"""Build the 3D connection gallery.

Writes, from the registry in details.py:
  book/_static/connections_3d/viewer.html        shared Iris viewer (loads ?model=<id>)
  book/_static/connections_3d/models/<id>.js     one model per connection
  book/_static/connections_3d/thumbs/<id>.jpg    thumbnails (headless Edge/Chrome screenshot; preview only)
  book/design/steel/S05_3d_connections.ipynb     the gallery page (compact grid)
  book/design/steel/S05_3d_connections_old.ipynb the previous page (large viewers, not in the TOC)

Usage (from the repository root):
    python tools/connection_3d/build.py              # everything
    python tools/connection_3d/build.py --no-thumbs  # skip the screenshots
Thumbnails need Pillow and Microsoft Edge or Google Chrome (set BROWSER=<path> to override).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from details import DETAILS  # noqa: E402
from details_new import NEW_DETAILS  # noqa: E402  (compact page only)

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "book" / "_static"
OUT = STATIC / "connections_3d"
PAGE = ROOT / "book" / "design" / "steel" / "S05_3d_connections_old.ipynb"
TEMPLATE = STATIC / "Connection_Steel_Standard.html"

GROUP_ORDER = ["Cont. column-beam", "Beam-beam", "Beam-wall", "Center-column-beam",
               "Column-support", "End column-beam"]

# Details exported from Rhino (standalone files, left unchanged)
RHINO = [
    ("Connection_Steel_Standard", "Standard connection"),
    ("Connection_Steel_Corner", "Corner connection"),
    ("Connection_Steel_Truss", "Truss connection"),
]

LOADER = """<script id="data">(function () {
  var q = window.location.search;
  var m = (q.match(/[?&]model=([A-Za-z0-9_-]+)/) || [])[1] || "column_support_1";
  document.write('<script src="models/' + m + '.js"><\\/script>');
  if (/[?&]thumb=1/.test(q)) document.write('<style>#MainMenu{display:none !important}</style>');
})();
"""

BG = (157, 163, 170)  # viewer background 0x9DA3AA


def build_viewer():
    html = TEMPLATE.read_text(encoding="utf-8")
    start = html.index('<script id="data">')
    end = html.index("</script>", start)
    html = html[:start] + LOADER + html[end:]
    html = html.replace("<title>Iris Connection_Steel_Standard</title>", "<title>3D connection</title>", 1)
    (OUT / "viewer.html").write_text(html, encoding="utf-8")


def build_models():
    (OUT / "models").mkdir(parents=True, exist_ok=True)
    for key, (fn, *_rest) in {**DETAILS, **NEW_DETAILS}.items():
        js = fn().to_js()
        (OUT / "models" / f"{key}.js").write_text(js, encoding="utf-8")
        print(f"  model {key}: {len(js) / 1024:.0f} kB")


def find_browser():
    if os.environ.get("BROWSER"):
        return os.environ["BROWSER"]
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if Path(p).exists():
            return p
    for name in ("msedge", "google-chrome", "chromium", "chromium-browser", "chrome"):
        if shutil.which(name):
            return shutil.which(name)
    raise SystemExit("No Edge/Chrome found for thumbnails; set BROWSER or use --no-thumbs")


def screenshot(browser, url, png):
    subprocess.run([browser, "--headless", "--disable-gpu", "--enable-unsafe-swiftshader",
                    "--use-angle=swiftshader", "--hide-scrollbars", "--timeout=7000",
                    "--window-size=1000,750", f"--screenshot={png}", url],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)


def crop_thumbnail(png, jpg, size=(480, 360)):
    from PIL import Image, ImageChops
    im = Image.open(png).convert("RGB")
    diff = ImageChops.difference(im, Image.new("RGB", im.size, BG)).convert("L")
    bbox = diff.point(lambda p: 255 if p > 14 else 0).getbbox() or (0, 0, *im.size)
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    pad = 0.08 * max(w, h)
    w, h = w + 2 * pad, h + 2 * pad
    aspect = size[0] / size[1]
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    box = (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))
    canvas = Image.new("RGB", (box[2] - box[0], box[3] - box[1]), BG)
    canvas.paste(im.crop((max(box[0], 0), max(box[1], 0), min(box[2], im.width), min(box[3], im.height))),
                 (max(-box[0], 0), max(-box[1], 0)))
    canvas.resize(size, Image.LANCZOS).save(jpg, quality=85, optimize=True)


def build_thumbnails(only=None):
    browser = find_browser()
    thumbs = OUT / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for key in DETAILS:
            if only and key not in only:
                continue
            png = tmp / f"{key}.png"
            screenshot(browser, (OUT / "viewer.html").as_uri() + f"?model={key}&thumb=1", png)
            crop_thumbnail(png, thumbs / f"{key}.jpg")
            print(f"  thumb {key}")
        for name, _ in RHINO:
            if only and name not in only:
                continue
            html = (STATIC / f"{name}.html").read_text(encoding="utf-8")
            html = html.replace("</head>", "<style>#MainMenu{display:none !important}</style></head>", 1)
            page = tmp / f"{name}.html"
            page.write_text(html, encoding="utf-8")
            png = tmp / f"{name}.png"
            screenshot(browser, page.as_uri(), png)
            crop_thumbnail(png, thumbs / f"{name}.jpg")
            print(f"  thumb {name}")


# ----------------------------------------------------------------------------- page
STYLE = """<style>
.c3d-frame {display: block; width: 100%; height: 560px; border: 1px solid rgba(128,128,128,0.35);}
.c3d-link {margin: 0.35rem 0 2rem; font-size: 0.9em;}
</style>"""


def embed(src, caption):
    """Interactive viewer inline on the page, as on the timber 3D connections page.

    loading="lazy" so the WebGL viewers only start when scrolled into view."""
    return (f"### {caption.rstrip('.')}\n\n"
            f'<iframe class="c3d-frame" src="{src}" title="3D view: {caption}" loading="lazy" '
            f'frameborder="0"></iframe>\n'
            f'<div class="c3d-link"><a href="{src}" target="_blank" rel="noopener">'
            f"Open this 3D model in a new tab</a></div>\n")


def build_page():
    base = "../../_static/connections_3d"
    groups = {}
    for key, (_fn, group, caption, _drawing) in DETAILS.items():
        groups.setdefault(group, []).append(embed(f"{base}/viewer.html?model={key}", caption))
    md = ["# 3D Connections (old version)\n",
          "Previous version of the 3D connections page, kept for reference; it is not in the table of "
          "contents. The current page is [3D Connections](S05_3d_connections.ipynb).\n",
          "Explore the structural connections of steel through interactive 3D visualisations. "
          "The details follow the drawings on the [connections](S04_connections.ipynb) page.\n",
          "Drag with the left mouse button to rotate, with the right mouse button to pan, and scroll to "
          "zoom. Use the menu at the top left of each model to switch layers (for example bolts or welds) "
          "on and off.\n",
          STYLE + "\n"]
    for group in GROUP_ORDER + sorted(set(groups) - set(GROUP_ORDER)):
        if group in groups:
            md.append(f"## {group}\n")
            md.extend(groups[group])
    md.append("## Other connections\n")
    md.extend(embed(f"../../_static/{name}.html", caption) for name, caption in RHINO)
    write_notebook(PAGE, md)


def write_notebook(path, md):
    """Write the markdown blocks `md` as the single cell of notebook `path` (metadata from PAGE)."""
    text = "\n".join(md)
    lines = text.splitlines(keepends=True)
    if lines and lines[-1].endswith("\n"):
        lines[-1] = lines[-1].rstrip("\n")

    nb = json.loads(PAGE.read_text(encoding="utf-8"))
    nb["cells"] = [{"cell_type": "markdown", "metadata": {}, "source": lines}]
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# ----------------------------------------------------------------------------- compact page (the gallery)
PAGE_GRID = ROOT / "book" / "design" / "steel" / "S05_3d_connections.ipynb"

GRID_STYLE = """<style>
.c3d-grid {display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 0.9rem; margin: 0.5rem 0 1.8rem;}
.c3d-tile {border: 1px solid rgba(128,128,128,0.35); border-radius: 4px; overflow: hidden;}
.c3d-tile iframe {display: block; width: 100%; height: 210px; border: 0;}
.c3d-tile div {padding: 0.4rem 0.55rem 0.5rem; font-size: 0.85em; line-height: 1.3;}
.c3d-tile a {font-size: 0.95em; white-space: nowrap;}
</style>"""


def tile(src, caption, hide_menu=True):
    """Small live viewer (menu hidden) with caption and a link to the full-size viewer.

    The iframe only gets its src from GRID_SCRIPT while it is near the screen, so the page
    never holds more live 3D views than browsers allow (about 16)."""
    frame_src = src + ("&thumb=1" if hide_menu and "?" in src else "")
    return (f'<div class="c3d-tile"><iframe class="c3d-live" data-src="{frame_src}" title="3D view: {caption}" '
            f'frameborder="0"></iframe>'
            f'<div>{caption.rstrip(".")}<br><a href="{src}" target="_blank" rel="noopener">'
            f"Open full size &#8599;</a></div></div>")


# Load a tile's viewer when it comes near the screen and release it (about:blank) when it
# scrolls away. One HTML block: no blank lines inside.
GRID_SCRIPT = """<script>
(function () {
  var frames = Array.prototype.slice.call(document.querySelectorAll("iframe.c3d-live"));
  function load(f) { if (f.getAttribute("src") !== f.dataset.src) { f.setAttribute("src", f.dataset.src); } }
  function unload(f) { if (f.getAttribute("src") && f.getAttribute("src") !== "about:blank") { f.setAttribute("src", "about:blank"); } }
  frames.forEach(function (f) { var r = f.getBoundingClientRect(); if (r.top < window.innerHeight + 150 && r.bottom > -150) { load(f); } });
  if (!("IntersectionObserver" in window)) { frames.slice(0, 12).forEach(load); return; }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { load(e.target); } else { unload(e.target); } });
  }, {rootMargin: "150px 0px"});
  frames.forEach(function (f) { io.observe(f); });
})();
</script>"""


def build_page_grid():
    base = "../../_static/connections_3d"
    groups = {}
    for key, (_fn, group, caption, _drawing) in {**DETAILS, **NEW_DETAILS}.items():
        groups.setdefault(group, []).append(tile(f"{base}/viewer.html?model={key}", caption))
    md = ["# 3D Connections\n",
          "Overview of the steel connections as small interactive 3D models. The details follow the "
          "drawings on the [connections](S04_connections.ipynb) page.\n",
          "Drag to rotate, right-drag to pan and scroll to zoom. Use *Open full size* for a large view "
          "with the layer menu (for example to switch bolts or welds on and off).\n",
          GRID_STYLE + "\n"]
    for group in GROUP_ORDER + sorted(set(groups) - set(GROUP_ORDER)):
        if group in groups:
            md.append(f"## {group}\n")
            md.append('<div class="c3d-grid">\n' + "\n".join(groups[group]) + "\n</div>\n")
    md.append("## Other connections\n")
    md.append('<div class="c3d-grid">\n' + "\n".join(
        tile(f"../../_static/{name}.html", caption) for name, caption in RHINO) + "\n</div>\n")
    md.append(GRID_SCRIPT + "\n")
    write_notebook(PAGE_GRID, md)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_viewer()
    build_models()
    if "--no-thumbs" not in sys.argv:
        only = [a for a in sys.argv[1:] if not a.startswith("--")] or None
        build_thumbnails(only)
    build_page()
    build_page_grid()
    print("done")
