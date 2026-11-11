"""Make the Rhino/Iris exports orbit around their connection instead of the drawing origin.

The Iris viewer always orbits around (0, 0, 0). In the Rhino exports the origin lies away
from the joint, so dragging makes the model swing across the screen. This moves every mesh
and line (via its object matrix) so that the centre of the bolts is at the origin, and puts
the cameras at a matching distance. The geometry itself is unchanged. Running it again
only resets the camera distance.

Usage (from the repository root):
    python tools/connection_3d/recentre_rhino.py
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = ["Connection_Steel_Standard", "Connection_Steel_Corner", "Connection_Steel_Truss"]
PREFIX = "var irisdata = "
ZOOM = 0.75          # < 1 brings the camera closer


def main():
    for name in FILES:
        path = ROOT / "book" / "_static" / f"{name}.html"
        html = path.read_text(encoding="utf-8")
        i = html.index(PREFIX) + len(PREFIX)
        j = html.index("</script>", i)
        data = json.loads(html[i:j].rstrip().rstrip(";"))
        geo = {g["uuid"]: g["data"]["attributes"]["position"]["array"] for g in data["geometries"]}
        children = data["object"]["children"]

        def world_points(objs):
            for o in objs:
                t = o["matrix"][12:15]
                a = geo[o["geometry"]]
                for k in range(0, len(a), 3):
                    yield (a[k] + t[0], a[k + 1] + t[1], a[k + 2] + t[2])

        meshes = [o for o in children if o["type"] in ("Mesh", "Line")]
        bolts = [o for o in meshes if o["type"] == "Mesh" and "bolt" in o["userData"]["scene"]["layer"].lower()]
        pts = list(world_points(meshes))
        lo = [min(p[k] for p in pts) for k in range(3)]
        hi = [max(p[k] for p in pts) for k in range(3)]
        bp = list(world_points(bolts)) or pts
        c = [(min(p[k] for p in bp) + max(p[k] for p in bp)) / 2 for k in range(3)]
        if max(abs(x) for x in c) < 1e-6:
            c = [0.0, 0.0, 0.0]          # already centred: only (re)set the camera distance

        for o in meshes:
            for k in range(3):
                o["matrix"][12 + k] -= c[k]
        lo = [x - y for x, y in zip(lo, c)]
        hi = [x - y for x, y in zip(hi, c)]
        corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        radius = 0.5 * (0.5 * math.dist(lo, hi) + max(math.dist((0, 0, 0), q) for q in corners))
        for o in children:
            if o["type"] == "PerspectiveCamera":
                # the viewer looks at the origin, so keep the direction from the origin to the camera
                d = list(o["matrix"][12:15])
                n = math.sqrt(sum(x * x for x in d))
                if n < 1e-6:
                    d, n = [0.62, -0.8, 0.5], math.sqrt(0.62 ** 2 + 0.8 ** 2 + 0.5 ** 2)
                dist = ZOOM * 1.15 * radius / math.sin(math.radians(o.get("fov", 27) / 2))
                o["matrix"][12:15] = [x / n * dist for x in d]
                o["userData"]["Target"] = {"tX": 0.0, "tY": 0.0, "tZ": 0.0}
            elif o["type"] == "OrthographicCamera":
                for k, key in enumerate(("tX", "tY", "tZ")):
                    o["matrix"][12 + k] -= c[k]
                    o["userData"]["Target"][key] -= c[k]

        html = html[:i] + json.dumps(data, separators=(",", ":")) + ";\n" + html[j:]
        path.write_text(html, encoding="utf-8")
        print(f"{name}: moved by {[-round(x, 2) for x in c]}, camera distance {dist:.0f}")


if __name__ == "__main__":
    main()
