"""Small geometry library that writes models for the Iris (three.js) connection viewer.

The 3D details in book/_static were originally exported from Rhino with the Iris
plug-in. The viewer reads one three.js scene (`irisdata`) with meshes, outline
lines, cameras and a layer list. This module builds such scenes in code.

Conventions: units cm, Z up. All materials are double sided, so the winding of
faces does not matter.
"""

import json
import math
import uuid

# ----------------------------------------------------------------------------- vectors


def add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def mul(v, s):
    return tuple(c * s for c in v)


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(v):
    n = math.sqrt(dot(v, v))
    return tuple(c / n for c in v)


def frame_from_axis(w):
    """Two unit vectors u, v perpendicular to w (u x v = w)."""
    w = unit(w)
    ref = (0, 0, 1) if abs(w[2]) < 0.9 else (1, 0, 0)
    u = unit(cross(ref, w))
    v = cross(w, u)
    return u, v, w


AXES = {  # extrusion axis -> (u, v, w) so that 2D (u, v) maps onto the other two axes
    "x": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    "y": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "z": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
}

# ----------------------------------------------------------------------------- 2D sections


def rect(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def circle(r, n=32, phase=0.0, cu=0.0, cv=0.0):
    return [(cu + r * math.cos(phase + 2 * math.pi * i / n),
             cv + r * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]


def hexagon(across_flats, cu=0.0, cv=0.0):
    return circle(across_flats / math.sqrt(3), 6, math.pi / 6, cu, cv)


def _arc(cu, cv, r, a0, a1, n=6):
    return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cv + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(1, n + 1)]


def i_section(p):
    """CCW outline of an I/H section: width along u, depth along v, centred.

    Returns (points, sharp_corner_indices)."""
    h, b, tw, tf, r = p["h"], p["b"], p["tw"], p["tf"], p["r"]
    hh, hb, ht = h / 2, b / 2, tw / 2
    pts, corners = [], []

    def c(pt):
        corners.append(len(pts))
        pts.append(pt)

    c((-hb, -hh)); c((hb, -hh)); c((hb, -hh + tf))
    pts.append((ht + r, -hh + tf)); pts += _arc(ht + r, -hh + tf + r, r, -90, -180)
    pts.append((ht, hh - tf - r)); pts += _arc(ht + r, hh - tf - r, r, 180, 90)
    c((hb, hh - tf)); c((hb, hh)); c((-hb, hh)); c((-hb, hh - tf))
    pts.append((-ht - r, hh - tf)); pts += _arc(-ht - r, hh - tf - r, r, 90, 0)
    pts.append((-ht, -hh + tf + r)); pts += _arc(-ht - r, -hh + tf + r, r, 0, -90)
    c((-hb, -hh + tf))
    return _dedupe(pts, corners)


def angle_section(a, b, t, r):
    """L-section with the heel at the origin, legs along +u (length a) and +v (length b)."""
    pts, corners = [], []

    def c(pt):
        corners.append(len(pts))
        pts.append(pt)

    c((0, 0)); c((a, 0)); c((a, t))
    pts.append((t + r, t)); pts += _arc(t + r, t + r, r, -90, -180)
    c((t, b)); c((0, b))
    return _dedupe(pts, corners)


def chamfered_rect(u0, u1, v0, v1, chamfer_u0=0.0, chamfer_u1=0.0):
    """Rectangle with the two corners at v0 cut off (for stiffeners clear of the root fillet)."""
    pts = []
    if chamfer_u0:
        pts += [(u0, v0 + chamfer_u0), (u0 + chamfer_u0, v0)]
    else:
        pts += [(u0, v0)]
    if chamfer_u1:
        pts += [(u1 - chamfer_u1, v0), (u1, v0 + chamfer_u1)]
    else:
        pts += [(u1, v0)]
    pts += [(u1, v1), (u0, v1)]
    return pts


def _dedupe(pts, corners):
    keep, remap = [], {}
    for i, p in enumerate(pts):
        if keep and math.dist(p, keep[-1]) < 1e-9:
            remap[i] = len(keep) - 1
            continue
        remap[i] = len(keep)
        keep.append(p)
    if math.dist(keep[0], keep[-1]) < 1e-9:
        keep.pop()
    return keep, sorted({remap[i] % len(keep) for i in corners})


def offset_polygon(poly, d):
    """Miter offset of a CCW polygon (outwards for d > 0)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]

        def normal(a, b):
            du, dv = b[0] - a[0], b[1] - a[1]
            length = math.hypot(du, dv)
            return (dv / length, -du / length)

        n1, n2 = normal(p0, p1), normal(p1, p2)
        bu, bv = n1[0] + n2[0], n1[1] + n2[1]
        bl = math.hypot(bu, bv) or 1.0
        bu, bv = bu / bl, bv / bl
        s = d / max(bu * n1[0] + bv * n1[1], 0.3)
        out.append((p1[0] + bu * s, p1[1] + bv * s))
    return out


def triangulate(p2):
    """Ear clipping of a simple 2D polygon; returns index triples."""
    area = sum(p2[i][0] * p2[(i + 1) % len(p2)][1] - p2[(i + 1) % len(p2)][0] * p2[i][1]
               for i in range(len(p2)))
    sign = 1.0 if area > 0 else -1.0

    def cr(o, a, b):
        return ((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])) * sign

    def inside(p, a, b, c):
        return cr(a, b, p) >= -1e-12 and cr(b, c, p) >= -1e-12 and cr(c, a, p) >= -1e-12

    idx, tris = list(range(len(p2))), []
    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = p2[i0], p2[i1], p2[i2]
            if cr(a, b, c) <= 1e-12:
                continue
            if any(inside(p2[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    for k in range(1, len(idx) - 1):
        tris.append((idx[0], idx[k], idx[k + 1]))
    return tris


# ----------------------------------------------------------------------------- profiles (cm)

PROFILES = {
    "IPE300": {"h": 30.0, "b": 15.0, "tw": 0.71, "tf": 1.07, "r": 1.5},
    "IPE240": {"h": 24.0, "b": 12.0, "tw": 0.62, "tf": 0.98, "r": 1.5},
    "HEA240": {"h": 23.0, "b": 24.0, "tw": 0.75, "tf": 1.2, "r": 2.1},
    "HEB200": {"h": 20.0, "b": 20.0, "tw": 0.9, "tf": 1.5, "r": 1.8},
}

BOLTS = {  # d, head/nut across flats, head height, nut height, washer diameter, washer thickness
    "M16": {"d": 1.6, "s": 2.4, "k": 1.0, "m": 1.3, "dw": 3.0, "tw": 0.3},
    "M20": {"d": 2.0, "s": 3.0, "k": 1.25, "m": 1.6, "dw": 3.7, "tw": 0.4},
    "M24": {"d": 2.4, "s": 3.6, "k": 1.5, "m": 1.9, "dw": 4.4, "tw": 0.4},
}

MATERIALS = {
    # names/colours re-used from the existing Rhino exports where possible
    "steel": (11053224, "Paint - Light Gray"),
    "plate": (12500670, "Plates"),
    "weld": (5000268, "Lasnaden"),
    "bolt": (9013641, "Bouten"),
    "nut": (8289918, "Koppen"),
    "grout": (0xB9B2A3, "Grout"),
    "concrete": (0xC9C9C4, "Concrete"),
    "elastomer": (0x3A3A3A, "Elastomer"),
}


def _uid():
    return str(uuid.uuid4())


class Mesh:
    def __init__(self):
        self.pos, self.idx = [], []

    def vertex(self, p):
        self.pos.append(p)
        return len(self.pos) - 1

    def polygon(self, pts3, pts2):
        """Planar polygon (3D points + their 2D coordinates for triangulation)."""
        base = [self.vertex(p) for p in pts3]
        for a, b, c in triangulate(pts2):
            self.idx += [base[a], base[b], base[c]]

    def quad_strip(self, ring_a, ring_b, closed=True, smooth=False):
        n = len(ring_a)
        segs = n if closed else n - 1
        if smooth:
            ia = [self.vertex(p) for p in ring_a]
            ib = [self.vertex(p) for p in ring_b]
            for i in range(segs):
                j = (i + 1) % n
                self.idx += [ia[i], ia[j], ib[j], ia[i], ib[j], ib[i]]
        else:
            for i in range(segs):
                j = (i + 1) % n
                quad = [ring_a[i], ring_a[j], ring_b[j], ring_b[i]]
                base = [self.vertex(p) for p in quad]
                self.idx += [base[0], base[1], base[2], base[0], base[2], base[3]]


class Scene:
    def __init__(self, title):
        self.title = title
        self.meshes = []      # (Mesh, material, layer)
        self.lines = []       # (points, layer)
        self.layer_order = []
        self.view_dir = (0.62, -0.8, 0.5)
        self.zoom = 1.0

    def _layer(self, layer):
        if layer not in self.layer_order:
            self.layer_order.append(layer)

    def add_mesh(self, mesh, mat, layer):
        self._layer(layer)
        self.meshes.append((mesh, mat, layer))

    def add_line(self, pts, layer, closed=False):
        self._layer(layer)
        self.lines.append((list(pts) + ([pts[0]] if closed else []), layer))

    # ------------------------------------------------------------------ primitives
    def extrude(self, poly, origin, u, v, w, length, mat, layer, corners=None, outline=True,
                smooth=False):
        """Extrude a 2D polygon (in the u, v plane at origin) along w over `length`."""
        def P(pt, t):
            return add(origin, mul(u, pt[0]), mul(v, pt[1]), mul(w, t))

        bot = [P(p, 0) for p in poly]
        top = [P(p, length) for p in poly]
        m = Mesh()
        m.polygon(bot, poly)
        m.polygon(top, poly)
        m.quad_strip(bot, top, smooth=smooth)
        self.add_mesh(m, mat, layer)
        if outline:
            self.add_line(bot, layer, closed=True)
            self.add_line(top, layer, closed=True)
            for i in (corners if corners is not None else range(len(poly))):
                self.add_line([bot[i], top[i]], layer)

    def prism(self, poly, axis, t0, t1, mat, layer, outline=True):
        """Extrude a 2D polygon along a global axis ('x', 'y' or 'z') from t0 to t1."""
        u, v, w = AXES[axis]
        self.extrude(poly, mul(w, t0), u, v, w, t1 - t0, mat, layer, outline=outline)

    def box(self, x0, x1, y0, y1, z0, z1, mat, layer, outline=True):
        self.prism(rect(x0, x1, y0, y1), "z", z0, z1, mat, layer, outline)

    def cylinder(self, centre, axis, r, length, mat, layer, n=24, outline=False):
        u, v, w = frame_from_axis(axis)
        self.extrude(circle(r, n), centre, u, v, w, length, mat, layer, outline=False, smooth=True)
        if outline:
            ring = [add(centre, mul(u, p[0]), mul(v, p[1])) for p in circle(r, n)]
            self.add_line(ring, layer, closed=True)
            self.add_line([add(p, mul(w, length)) for p in ring], layer, closed=True)

    def member(self, prof, origin, u, v, w, length, layer="Members", mat="steel"):
        pts, corners = i_section(PROFILES[prof])
        self.extrude(pts, origin, u, v, w, length, mat, layer, corners=corners)

    def column(self, prof, z0, z1, x=0.0, y=0.0, layer="Column"):
        """Vertical I/H member; flanges perpendicular to x (beams connect along x)."""
        self.member(prof, (x, y, z0), (0, -1, 0), (1, 0, 0), (0, 0, 1), z1 - z0, layer)

    def beam_x(self, prof, x0, x1, z_top, y=0.0, layer="Beam"):
        """Horizontal I member along x with its top flange at z_top."""
        h = PROFILES[prof]["h"]
        self.member(prof, (x0, y, z_top - h / 2), (0, 1, 0), (0, 0, 1), (1, 0, 0), x1 - x0, layer)

    def beam_y(self, prof, y0, y1, z_top, x=0.0, layer="Beam"):
        h = PROFILES[prof]["h"]
        self.member(prof, (x, y0, z_top - h / 2), (-1, 0, 0), (0, 0, 1), (0, 1, 0), y1 - y0, layer)

    def profile_weld(self, prof, origin, u, v, w, a=0.5, layer="Welds"):
        """Fillet weld all round an I-profile end that meets a plate.

        origin/u/v: the profile's section frame on the plate surface; w points into the member."""
        pts, _ = i_section(PROFILES[prof])
        self.contour_weld(pts, origin, u, v, w, a, layer)

    def contour_weld(self, pts, origin, u, v, w, a=0.5, layer="Welds"):
        outer = offset_polygon(pts, a)

        def P(pt, t):
            return add(origin, mul(u, pt[0]), mul(v, pt[1]), mul(w, t))

        m = Mesh()
        m.quad_strip([P(p, 0.01) for p in outer], [P(p, a) for p in pts])
        self.add_mesh(m, "weld", layer)

    def line_weld(self, p0, p1, d1, d2, a=0.5, layer="Welds"):
        """Fillet weld along the corner line p0-p1 with legs along unit vectors d1 and d2."""
        tri = [(0, 0), (a, 0), (0, a)]
        w = sub(p1, p0)
        length = math.sqrt(dot(w, w))
        self.extrude(tri, p0, d1, d2, unit(w), length, "weld", layer, outline=False)

    def bolt(self, centre, axis, grip, size="M20", layer="Bolts", head=True, protrude=1.0):
        """Bolt along `axis`: head (or nut) before `centre`, clamped length `grip`, washer + nut after.

        centre is where the head side of the clamped package starts."""
        b = BOLTS[size]
        u, v, w = frame_from_axis(axis)
        hexa = hexagon(b["s"])
        if head:
            self.extrude(hexa, add(centre, mul(w, -b["k"])), u, v, w, b["k"], "bolt", layer, outline=False)
        else:   # nut + washer on the "head" side as well (anchor or threaded rod)
            self.extrude(circle(b["dw"] / 2), add(centre, mul(w, -b["tw"])), u, v, w, b["tw"], "nut",
                         layer, outline=False)
            self.extrude(hexa, add(centre, mul(w, -b["tw"] - b["m"])), u, v, w, b["m"], "nut", layer,
                         outline=False)
        end = add(centre, mul(w, grip))
        self.extrude(circle(b["dw"] / 2), end, u, v, w, b["tw"], "nut", layer, outline=False)
        self.extrude(hexa, add(end, mul(w, b["tw"])), u, v, w, b["m"], "nut", layer, outline=False)
        start = -b["k"] if head else -b["tw"] - b["m"] - protrude
        total = grip + b["tw"] + b["m"] + protrude - start
        self.cylinder(add(centre, mul(w, start)), w, b["d"] / 2, total, "bolt", layer, n=20)

    # ------------------------------------------------------------------ export
    def to_irisdata(self):
        # centre the model on the origin (the viewer orbits around the origin)
        allp = [p for m, _, _ in self.meshes for p in m.pos]
        lo = [min(p[k] for p in allp) for k in range(3)]
        hi = [max(p[k] for p in allp) for k in range(3)]
        c = tuple((a + b) / 2 for a, b in zip(lo, hi))
        radius = 0.5 * math.dist(lo, hi)

        materials, mat_ids = [], {}
        for key, (color, name) in MATERIALS.items():
            mat_ids[key] = _uid()
            materials.append({"color": color, "roughness": 1.0, "metalness": 0.25, "opacity": 1.0,
                              "side": 2, "uuid": mat_ids[key], "name": name,
                              "type": "MeshStandardMaterial"})
        line_mat = _uid()
        materials.append({"color": 0, "uuid": line_mat, "type": "LineBasicMaterial"})

        def flat(points):
            return [round(x - c[k], 4) for p in points for k, x in enumerate(p)]

        geometries, children = [], []
        identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

        def obj(kind, gid, mid, layer):
            return {"geometry": gid, "material": mid,
                    "userData": {"scene": {"layer": layer, "selected": False, "bBoxId": None, "url": ""}},
                    "matrix": identity, "uuid": _uid(), "type": kind}

        for m, mat, layer in self.meshes:
            gid = _uid()
            geometries.append({"data": {
                "attributes": {"position": {"itemSize": 3, "array": flat(m.pos), "type": "Float32Array"}},
                "index": {"array": m.idx, "type": "Uint16Array" if len(m.pos) < 65535 else "Uint32Array"}},
                "uuid": gid, "type": "BufferGeometry"})
            children.append(obj("Mesh", gid, mat_ids[mat], layer))
        for pts, layer in self.lines:
            gid = _uid()
            geometries.append({"data": {
                "attributes": {"position": {"itemSize": 3, "array": flat(pts), "type": "Float32Array"}},
                "boundingSphere": {}}, "uuid": gid, "type": "BufferGeometry"})
            children.append(obj("Line", gid, line_mat, layer))

        target = (0.0, 0.0, 0.0)
        dist = self.zoom * 1.15 * radius / math.sin(math.radians(27 / 2))
        eye = mul(unit(self.view_dir), dist)
        persp = _uid()
        tgt = {"tX": 0.0, "tY": 0.0, "tZ": 0.0}
        cams = [{"aspect": 1.3, "fov": 27.0, "userData": {"Target": tgt},
                 "matrix": _look_at(eye, target), "uuid": persp, "name": "Perspective",
                 "type": "PerspectiveCamera"}]
        ext = 1.2 * radius
        for name, e, up in (("Top", (0, 0, 4 * radius), (0, 1, 0)), ("Front", (0, -4 * radius, 0), (0, 0, 1)),
                            ("Right", (4 * radius, 0, 0), (0, 0, 1))):
            cams.append({"bottom": -ext, "left": -ext, "right": ext, "top": ext, "userData": {"Target": tgt},
                         "matrix": _look_at(e, target, up), "uuid": _uid(), "name": name,
                         "type": "OrthographicCamera"})

        layers = {name: {"sortIndex": i + 1, "visible": True} for i, name in enumerate(self.layer_order)}
        return {
            "metadata": {"version": 4.5, "type": "Object", "generator": "ThreeLib-Object3D.toJSON"},
            "geometries": geometries, "images": [], "textures": [], "materials": materials,
            "object": {"background": 10331050,
                       "userData": {"activeCamera": {"id": persp, "name": "Perspective"}, "planes": {},
                                    "analytics": {"appName": "RhinoJSON", "appId": "com.mcneel.com",
                                                  "appVersion": "0.7.1.0", "rhinoVersion": "7.37"},
                                    "layers": layers},
                       "matrix": identity, "uuid": _uid(), "type": "Scene", "children": children + cams},
            "fonts": [],
        }

    def to_js(self):
        return ("var irisdata = " + json.dumps(self.to_irisdata(), separators=(",", ":")) + ";\n"
                + "document.title = " + json.dumps(self.title) + ";\n")


def _look_at(eye, tgt, up=(0, 0, 1)):
    z = unit(sub(eye, tgt))
    x = unit(cross(up, z))
    y = cross(z, x)
    return [x[0], x[1], x[2], 0, y[0], y[1], y[2], 0, z[0], z[1], z[2], 0, eye[0], eye[1], eye[2], 1]
