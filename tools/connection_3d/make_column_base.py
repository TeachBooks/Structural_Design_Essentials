"""Generate the 3D 'column base' connection viewer for the steel chapter.

The existing 3D details in book/_static/Connection_Steel_*.html were exported
from Rhino with the Iris plug-in. Each file is a self-contained three.js viewer
whose model lives in a single `<script id="data">var irisdata = {...}</script>`
block (three.js Object/Scene JSON). This script builds a new model in code and
injects it into a copy of an existing viewer, so the viewer itself (layer menu,
views, orbit controls) is identical to the other details.

Model: HEB 200 column welded to a base plate, two M20 anchor bolts with
washers and nuts, a grout layer and a concrete foundation block
(cf. book/design/steel/Images/Column_Support1.jpg). Units: cm, Z up.

Usage (from the repository root):
    python tools/connection_3d/make_column_base.py
"""

import json
import math
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "book" / "_static" / "Connection_Steel_Standard.html"
OUTPUT = ROOT / "book" / "_static" / "Connection_Steel_Column_Base.html"

# ---------------------------------------------------------------- dimensions (cm)
H, B, TW, TF, R = 20.0, 20.0, 0.9, 1.5, 1.8   # HEB 200
COL_TOP = 60.0                                # column length shown above plate
PL_X, PL_Y, PL_T = 36.0, 30.0, 2.5            # base plate (x along web)
GROUT_T = 3.0                                 # grout layer under plate
GROUT_FLARE = 4.0                             # grout spreads out towards bottom
FDN_X, FDN_Y, FDN_D = 70.0, 60.0, 40.0        # concrete foundation block
WELD_A = 0.7                                  # fillet weld leg length
BOLT_D, BOLT_Y = 2.0, 5.5                     # anchor bolt diameter, offset from web
BOLT_TOP = PL_T + 0.4 + 1.6 + 1.2             # plate + washer + nut + protrusion
BOLT_BOT = -GROUT_T - 30.0                    # embedment depth
NUT_S, NUT_H = 3.0, 1.6                       # M20 nut: across flats, height
WASHER_D, WASHER_T = 3.7, 0.4
ANCHOR_PL, ANCHOR_T = 7.0, 1.0                # anchor plate at bolt end

# ---------------------------------------------------------------- scene building
geometries, children = [], []
layers = {}


def uid():
    return str(uuid.uuid4())


MATERIALS = {
    # names/colours re-used from the existing Rhino exports where possible
    "steel": {"color": 11053224, "name": "Paint - Light Gray"},
    "weld": {"color": 5000268, "name": "Lasnaden"},
    "bolt": {"color": 9013641, "name": "Bouten"},
    "nut": {"color": 8289918, "name": "Koppen"},
    "grout": {"color": 0xB9B2A3, "name": "Grout"},
    "concrete": {"color": 0xC9C9C4, "name": "Concrete"},
}
materials = []
for key, m in MATERIALS.items():
    m.update({"roughness": 1.0, "metalness": 0.25, "opacity": 1.0, "uuid": uid(),
              "type": "MeshStandardMaterial"})
    materials.append(m)
LINE_MAT = {"color": 0, "uuid": uid(), "type": "LineBasicMaterial"}
materials.append(LINE_MAT)


class Mesh:
    def __init__(self):
        self.pos, self.idx = [], []

    def add_vertex(self, p):
        self.pos.extend(round(c, 5) for c in p)
        return len(self.pos) // 3 - 1

    def add_polygon(self, pts):
        """Flat (planar, convex or concave) polygon, own vertices -> sharp edges."""
        base = [self.add_vertex(p) for p in pts]
        for a, b, c in triangulate(pts):
            self.idx.extend((base[a], base[b], base[c]))

    def add_quad_strip(self, ring_a, ring_b, closed=True, smooth=False):
        """Surface between two rings of equal length."""
        n = len(ring_a)
        segs = n if closed else n - 1
        if smooth:
            ia = [self.add_vertex(p) for p in ring_a]
            ib = [self.add_vertex(p) for p in ring_b]
            for i in range(segs):
                j = (i + 1) % n
                self.idx.extend((ia[i], ia[j], ib[j], ia[i], ib[j], ib[i]))
        else:
            for i in range(segs):
                j = (i + 1) % n
                self.add_polygon([ring_a[i], ring_a[j], ring_b[j], ring_b[i]])


def add_mesh(mesh, mat, layer):
    gid = uid()
    n_vert = len(mesh.pos) // 3
    geometries.append({
        "data": {
            "attributes": {"position": {"itemSize": 3, "array": mesh.pos, "type": "Float32Array"}},
            "index": {"array": mesh.idx, "type": "Uint16Array" if n_vert < 65535 else "Uint32Array"},
        },
        "uuid": gid, "type": "BufferGeometry"})
    children.append(scene_object("Mesh", gid, MATERIALS[mat]["uuid"], layer))


def add_polyline(pts, layer, closed=False):
    if closed:
        pts = list(pts) + [pts[0]]
    gid = uid()
    arr = [round(c, 5) for p in pts for c in p]
    geometries.append({
        "data": {"attributes": {"position": {"itemSize": 3, "array": arr, "type": "Float32Array"}},
                 "boundingSphere": {}},
        "uuid": gid, "type": "BufferGeometry"})
    children.append(scene_object("Line", gid, LINE_MAT["uuid"], layer))


def scene_object(kind, gid, mid, layer):
    layers.setdefault(layer, {"sortIndex": len(layers) + 1, "visible": True})
    return {"geometry": gid, "material": mid,
            "userData": {"scene": {"layer": layer, "selected": False, "bBoxId": None, "url": ""}},
            "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
            "uuid": uid(), "type": kind}


# ---------------------------------------------------------------- geometry helpers
def triangulate(pts):
    """Ear clipping for a simple planar polygon given in 3D."""
    # project on the dominant plane of the polygon normal
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        x1, y1, z1 = pts[i]
        x2, y2, z2 = pts[(i + 1) % len(pts)]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    ax = max(range(3), key=lambda k: abs((nx, ny, nz)[k]))
    keep = [k for k in range(3) if k != ax]
    p2 = [(p[keep[0]], p[keep[1]]) for p in pts]
    area = sum(p2[i][0] * p2[(i + 1) % len(p2)][1] - p2[(i + 1) % len(p2)][0] * p2[i][1]
               for i in range(len(p2)))
    sign = 1.0 if area > 0 else -1.0

    def cross(o, a, b):
        return ((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])) * sign

    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-12 and cross(b, c, p) >= -1e-12 and cross(c, a, p) >= -1e-12

    idx = list(range(len(pts)))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = p2[i0], p2[i1], p2[i2]
            if cross(a, b, c) <= 1e-12:
                continue
            if any(inside(p2[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:  # degenerate remainder: fan it
            break
    for k in range(1, len(idx) - 1):
        tris.append((idx[0], idx[k], idx[k + 1]))
    # keep the original winding (normal direction) of the polygon
    return tris


def at_z(poly2d, z):
    return [(x, y, z) for x, y in poly2d]


def reverse(p):
    return list(reversed(p))


def prism(poly2d, z0, z1, mat, layer, outline=True, edges=None):
    """Vertical extrusion of a CCW 2D polygon."""
    m = Mesh()
    m.add_polygon(reverse(at_z(poly2d, z0)))      # bottom, facing down
    m.add_polygon(at_z(poly2d, z1))               # top, facing up
    m.add_quad_strip(at_z(poly2d, z0), at_z(poly2d, z1))
    add_mesh(m, mat, layer)
    if outline:
        add_polyline(at_z(poly2d, z0), layer, closed=True)
        add_polyline(at_z(poly2d, z1), layer, closed=True)
        for i in (edges if edges is not None else range(len(poly2d))):
            x, y = poly2d[i]
            add_polyline([(x, y, z0), (x, y, z1)], layer)


def rect(cx, cy, dx, dy):
    return [(cx - dx / 2, cy - dy / 2), (cx + dx / 2, cy - dy / 2),
            (cx + dx / 2, cy + dy / 2), (cx - dx / 2, cy + dy / 2)]


def circle(cx, cy, r, n=32, phase=0.0):
    return [(cx + r * math.cos(phase + 2 * math.pi * i / n),
             cy + r * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]


def cylinder(cx, cy, r, z0, z1, mat, layer, n=32, outline=True):
    ring = circle(cx, cy, r, n)
    m = Mesh()
    m.add_polygon(reverse(at_z(ring, z0)))
    m.add_polygon(at_z(ring, z1))
    m.add_quad_strip(at_z(ring, z0), at_z(ring, z1), smooth=True)
    add_mesh(m, mat, layer)
    if outline:
        add_polyline(at_z(ring, z0), layer, closed=True)
        add_polyline(at_z(ring, z1), layer, closed=True)


def h_section():
    """CCW outline of an H-section with root fillets; web along x, flanges parallel to y."""
    hx, by, tw, tf = H / 2, B / 2, TW / 2, TF
    xi = hx - tf          # inner face of flange
    pts = []

    def arc(cx, cy, a0, a1, n=8):
        return [(cx + R * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
                 cy + R * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]

    # start at right flange, bottom outer corner, go CCW
    pts += [(hx, -by), (hx, by), (xi, by)]
    pts += [(xi, tw + R)]
    pts += arc(xi - R, tw + R, 0, -90)[1:]                    # right/top fillet -> web top face
    pts += [(-xi + R, tw)]
    pts += arc(-xi + R, tw + R, -90, -180)[1:]                # left/top fillet
    pts += [(-xi, by), (-hx, by), (-hx, -by), (-xi, -by)]
    pts += [(-xi, -tw - R)]
    pts += arc(-xi + R, -tw - R, 180, 90)[1:]                 # left/bottom fillet
    pts += [(xi - R, -tw)]
    pts += arc(xi - R, -tw - R, 90, 0)[1:]                    # right/bottom fillet
    pts += [(xi, -by)]
    # remove duplicates
    clean = []
    for p in pts:
        if not clean or math.dist(p, clean[-1]) > 1e-6:
            clean.append(p)
    if math.dist(clean[0], clean[-1]) < 1e-6:
        clean.pop()
    return clean


def offset_polygon(poly, d):
    """Miter offset of a CCW polygon (outwards for d > 0)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]

        def normal(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            return (dy / length, -dx / length)   # right-hand normal = outward for CCW

        n1, n2 = normal(p0, p1), normal(p1, p2)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        bl = math.hypot(bx, by)
        bx, by = bx / bl, by / bl
        cos_half = bx * n1[0] + by * n1[1]
        s = d / max(cos_half, 0.2)
        out.append((p1[0] + bx * s, p1[1] + by * s))
    return out


# ---------------------------------------------------------------- the model
z_plate_top = PL_T
z_grout_bot = -GROUT_T
z_fdn_bot = z_grout_bot - FDN_D

# Column: HEB 200
sec = h_section()
corner_ids = [i for i, (x, y) in enumerate(sec)
              if abs(abs(x) - H / 2) < 1e-6 or (abs(abs(x) - (H / 2 - TF)) < 1e-6 and abs(abs(y) - B / 2) < 1e-6)]
prism(sec, z_plate_top, COL_TOP, "steel", "Column", edges=corner_ids)

# Fillet welds all around the column (sloped weld face)
inner = sec
outer = offset_polygon(sec, WELD_A)
weld = Mesh()
weld.add_quad_strip(at_z(outer, z_plate_top + 0.01), at_z(inner, z_plate_top + WELD_A), smooth=False)
add_mesh(weld, "weld", "Welds")

# Base plate
plate = rect(0, 0, PL_X, PL_Y)
prism(plate, 0.0, PL_T, "steel", "Base plate")

# Anchor bolts with washer + nut on top and an anchor plate at the bottom
for by in (-BOLT_Y, BOLT_Y):
    cylinder(0, by, BOLT_D / 2, BOLT_BOT, BOLT_TOP, "bolt", "Anchor bolts", n=24, outline=False)
    z = PL_T
    cylinder(0, by, WASHER_D / 2, z, z + WASHER_T, "nut", "Anchor bolts", n=32)
    z += WASHER_T
    hexagon = circle(0, by, NUT_S / math.sqrt(3), n=6, phase=math.pi / 6)
    prism(hexagon, z, z + NUT_H, "nut", "Anchor bolts")
    # anchor plate + nut at the embedded end
    prism(rect(0, by, ANCHOR_PL, ANCHOR_PL), BOLT_BOT + NUT_H, BOLT_BOT + NUT_H + ANCHOR_T, "nut", "Anchor bolts")
    prism(hexagon, BOLT_BOT + 0.2, BOLT_BOT + NUT_H, "nut", "Anchor bolts")

# Grout layer: tapered from plate size at the top to wider at the bottom
g_top = rect(0, 0, PL_X + 1.0, PL_Y + 1.0)
g_bot = rect(0, 0, PL_X + 1.0 + 2 * GROUT_FLARE, PL_Y + 1.0 + 2 * GROUT_FLARE)
grout = Mesh()
grout.add_polygon(at_z(g_top, 0.0))
grout.add_polygon(reverse(at_z(g_bot, z_grout_bot)))
grout.add_quad_strip(at_z(g_bot, z_grout_bot), at_z(g_top, 0.0))
add_mesh(grout, "grout", "Grout")
add_polyline(at_z(g_top, 0.0), "Grout", closed=True)
add_polyline(at_z(g_bot, z_grout_bot + 0.02), "Grout", closed=True)
for a, b in zip(g_bot, g_top):
    add_polyline([(a[0], a[1], z_grout_bot), (b[0], b[1], 0.0)], "Grout")

# Concrete foundation
prism(rect(0, 0, FDN_X, FDN_Y), z_fdn_bot, z_grout_bot, "concrete", "Foundation")

# ---------------------------------------------------------------- cameras & scene
target = (0.0, 0.0, 5.0)
cam_pos = (175.0, -250.0, 150.0)


def look_at_matrix(eye, tgt, up=(0, 0, 1)):
    f = [t - e for t, e in zip(tgt, eye)]
    fl = math.sqrt(sum(c * c for c in f))
    zc = [-c / fl for c in f]                                   # camera looks along -z
    xc = [up[1] * zc[2] - up[2] * zc[1], up[2] * zc[0] - up[0] * zc[2], up[0] * zc[1] - up[1] * zc[0]]
    xl = math.sqrt(sum(c * c for c in xc))
    xc = [c / xl for c in xc]
    yc = [zc[1] * xc[2] - zc[2] * xc[1], zc[2] * xc[0] - zc[0] * xc[2], zc[0] * xc[1] - zc[1] * xc[0]]
    return [xc[0], xc[1], xc[2], 0, yc[0], yc[1], yc[2], 0, zc[0], zc[1], zc[2], 0, eye[0], eye[1], eye[2], 1]


persp_id = uid()
tgt = {"tX": target[0], "tY": target[1], "tZ": target[2]}
cameras = [
    {"aspect": 2.0, "fov": 27.0, "userData": {"Target": tgt},
     "matrix": look_at_matrix(cam_pos, target), "uuid": persp_id, "name": "Perspective",
     "type": "PerspectiveCamera"},
]
for name, eye in (("Top", (0, 0, 400.0)), ("Front", (0, -400.0, 5.0)), ("Right", (400.0, 0, 5.0))):
    up = (0, 1, 0) if name == "Top" else (0, 0, 1)
    cameras.append({"bottom": -80.0, "left": -80.0, "right": 80.0, "top": 80.0,
                    "userData": {"Target": tgt}, "matrix": look_at_matrix(eye, target, up),
                    "uuid": uid(), "name": name, "type": "OrthographicCamera"})

irisdata = {
    "metadata": {"version": 4.5, "type": "Object", "generator": "ThreeLib-Object3D.toJSON"},
    "geometries": geometries, "images": [], "textures": [], "materials": materials,
    "object": {
        "background": 10331050,
        "userData": {"activeCamera": {"id": persp_id, "name": "Perspective"}, "planes": {},
                     "analytics": {"appName": "RhinoJSON", "appId": "com.mcneel.com",
                                   "appVersion": "0.7.1.0", "rhinoVersion": "7.37"},
                     "layers": layers},
        "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        "uuid": uid(), "type": "Scene", "children": children + cameras},
    "fonts": [],
}

# ---------------------------------------------------------------- write viewer
html = TEMPLATE.read_text(encoding="utf-8")
start = html.index('<script id="data">')
end = html.index("</script>", start)
data = '<script id="data">var irisdata = ' + json.dumps(irisdata, separators=(",", ":")) + ";\n"
html = html[:start] + data + html[end:]
html = re.sub(r"<title>.*?</title>", "<title>Iris Connection_Steel_Column_Base</title>", html, count=1)
OUTPUT.write_text(html, encoding="utf-8")
print(f"wrote {OUTPUT.relative_to(ROOT)}: {len(children)} objects, layers: {list(layers)}")
