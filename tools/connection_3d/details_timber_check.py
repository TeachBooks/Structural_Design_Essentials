"""Timber details of Figs. 12.7 - 12.37 (T02 page), first versions to be checked by the author.

Shown on book/design/timber/T04a_3d_connections_to_be_checked.ipynb. Once approved, a
detail moves to details_timber.py / the 3D connections page (T04).

Conventions as in details_timber.py: units cm, Z up. Most details are drawn in the x-z
plane (the elevation of the drawing) with the member width along y.
"""

import math

from details_new import frustum, lock_bolt
from details_timber import A, coach_screw
from iris3d import Mesh, Scene, add, circle, mul, rect

Y = (0, 1, 0)


# ----------------------------------------------------------------------------- 2D helpers (x, z)
def _add2(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _mul2(a, s):
    return (a[0] * s, a[1] * s)


def _unit2(a):
    n = math.hypot(*a)
    return (a[0] / n, a[1] / n)


def _intersect(p, d, q, e):
    """Intersection of the lines p + t d and q + s e."""
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return _add2(p, _mul2(d, t))


def band(p0, p1, h, cut0=None, cut1=None):
    """Quad of a straight member of depth h centred on the line p0 -> p1 (x, z).

    cut0 / cut1: optional (point, direction) lines that trim the ends (default square)."""
    d = _unit2((p1[0] - p0[0], p1[1] - p0[1]))
    n = (-d[1], d[0])
    edges = [_add2(p0, _mul2(n, -h / 2)), _add2(p0, _mul2(n, h / 2))]

    def end(e, cut, p):
        if cut is None:
            return _intersect(e, d, p, n)
        return _intersect(e, d, cut[0], cut[1])

    return [end(edges[0], cut0, p0), end(edges[0], cut1, p1), end(edges[1], cut1, p1), end(edges[1], cut0, p0)]


def along(p0, p1, s, t=0.0):
    """Point at distance s along p0 -> p1, shifted t to the left (x, z)."""
    d = _unit2((p1[0] - p0[0], p1[1] - p0[1]))
    return (p0[0] + d[0] * s - d[1] * t, p0[1] + d[1] * s + d[0] * t)


def hull(pts):
    """Convex hull (counter-clockwise) of 2D points."""
    pts = sorted(set((round(x, 6), round(z, 6)) for x, z in pts))

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


# ----------------------------------------------------------------------------- 3D helpers
def xz(s, poly, y0, y1, mat="timber", layer="Timber", outline=True):
    """Prism of the (x, z) polygon `poly` between y0 and y1."""
    s.extrude(poly, (0, y0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0), y1 - y0, mat, layer, outline=outline)


def plate_xz(s, poly, y0, y1, layer="Plates"):
    xz(s, poly, y0, y1, "plate", layer)


def tbox(s, x0, x1, y0, y1, z0, z1, layer="Timber"):
    s.box(x0, x1, y0, y1, z0, z1, "timber", layer)


def bolt_y(s, x, z, y0, y1, size="M16"):
    """Bolt along +y, head at y0, clamping y0..y1."""
    s.bolt((x, y0, z), Y, y1 - y0, size=size)


def dowel_y(s, x, z, y0, y1, d=1.2, layer="Dowels"):
    s.cylinder((x, y0, z), Y, d / 2, y1 - y0, "bolt", layer, n=14, outline=True)


def small_screw(s, head_at, axis, length=6.0, layer="Screws"):
    """Light-weight screw: hexagon head on the surface, short shank (few vertices)."""
    from iris3d import frame_from_axis, hexagon
    u, v, w = frame_from_axis(axis)
    s.extrude(hexagon(1.0), add(head_at, mul(w, -0.4)), u, v, w, 0.4, "bolt", layer, outline=False)
    s.extrude(circle(0.3, 6), head_at, u, v, w, length, "bolt", layer, outline=False)


def nail_heads(s, pts, y, sign, layer="Nails"):
    for x, z in pts:
        s.cylinder((x, y, z), (0, sign, 0), 0.3, 0.15, "nut", layer, n=8)


def grid(x0, x1, nx, z0, z1, nz):
    xs = [x0 + (x1 - x0) * i / (nx - 1) for i in range(nx)] if nx > 1 else [(x0 + x1) / 2]
    zs = [z0 + (z1 - z0) * j / (nz - 1) for j in range(nz)] if nz > 1 else [(z0 + z1) / 2]
    return [(x, z) for x in xs for z in zs]


def concrete(s, x0, x1, y0, y1, z0, z1, layer="Concrete"):
    s.box(x0, x1, y0, y1, z0, z1, "concrete", layer)


def merge(s, sub, angle=0.0, centre=(0.0, 0.0)):
    """Add the parts of scene `sub`, rotated by `angle` degrees about the y axis through
    centre (x, z); positive angles turn +x towards +z."""
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)

    def r(p):
        x, z = p[0] - centre[0], p[2] - centre[1]
        return (centre[0] + x * ca - z * sa, p[1], centre[1] + x * sa + z * ca)

    for m, mat, layer in sub.meshes:
        m.pos = [r(p) for p in m.pos]
        s.add_mesh(m, mat, layer)
    for pts, layer in sub.lines:
        s.add_line([r(p) for p in pts], layer)


def sloped_footing(s, angle, half=35.0, top=-2.0, depth=30.0, hy=25.0):
    """Concrete footing with a horizontal base whose top face is perpendicular to an arch
    leaning by `angle` (same rotation as merge): the local plane z = top, |x| <= half."""
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    pa = (-half * ca - top * sa, -half * sa + top * ca)
    pb = (half * ca - top * sa, half * sa + top * ca)
    zbot = min(pa[1], pb[1]) - depth
    xz(s, [pa, (pa[0], zbot), (pb[0], zbot), pb][::-1] if pb[1] > pa[1] else [pa, (pa[0], zbot), (pb[0], zbot), pb],
       -hy, hy, "concrete", "Footing")


def view(s, pivot, zoom=0.6, view_dir=(0.7, -0.85, 0.45)):
    s.pivot, s.zoom, s.view_dir = pivot, zoom, view_dir
    return s


# ============================================================================= Fig. 12.7
def cantilever_1():
    """Purlins on both sides of a main beam, each hung on a Z-profile."""
    s = Scene("Purlins on main beam with Z-profiles")
    hb, H = 6.0, 30.0                         # main beam 120 x 300 along x
    bp, hp = 7.5, 24.0                        # purlins 75 x 240 along y, tops flush
    t = 0.4
    tbox(s, -40, 40, -hb, hb, 0, H, "Main beam")
    for sy in (1, -1):
        y0 = sy * (hb + t)
        y1 = sy * 55.0
        tbox(s, -bp / 2, bp / 2, min(y0, y1), max(y0, y1), H - hp, H, "Purlins")
        # Z-profile (8 cm wide): top flange on the main beam, web against its side,
        # bottom flange under the purlin
        def yy(a, b):
            return min(sy * a, sy * b), max(sy * a, sy * b)
        s.box(-4, 4, *yy(1.0, hb + t), H, H + t, "plate", "Z-profiles")
        s.box(-4, 4, *yy(hb, hb + t), H - hp - t, H + t, "plate", "Z-profiles")
        s.box(-4, 4, *yy(hb, hb + 12.0), H - hp - t, H - hp, "plate", "Z-profiles")
        small_screw(s, (0, sy * 3.5, H + t), (0, 0, -1), 6.0)
        small_screw(s, (0, sy * (hb + 8.0), H - hp - t), (0, 0, 1), 6.0)
    return view(s, (0, 0, 18), 0.5)


def cantilever_2():
    """Double beam on a double column; a central filler between the halves, all bolted."""
    s = Scene("Double beam on double column (bolted)")
    tb, f = 8.0, 6.0                          # thickness of each half, filler
    for sy in (1, -1):
        y0, y1 = sorted((sy * f / 2, sy * (f / 2 + tb)))
        tbox(s, -7.5, 7.5, y0, y1, -60, 0, "Column")
        tbox(s, -45, 45, y0, y1, 0, 28, "Beam")
    tbox(s, -7.5, 7.5, -f / 2, f / 2, -30, 28, "Filler")
    yb = f / 2 + tb
    for x in (-4.0, 4.0):
        for z in (6.0, 14.0, 22.0):
            bolt_y(s, x, z, -yb, yb)
    for z in (-8.0, -20.0):
        bolt_y(s, 0, z, -yb, yb)
    return view(s, (0, 0, 2), 0.65)


def cantilever_3():
    """Beam on column, steel cross-shaped connector slotted into both, with dowels."""
    s = Scene("Beam on column with steel connector")
    b, t, tf = 12.0, 0.8, 1.0
    tbox(s, -7, 7, -b / 2, b / 2, -50, 0, "Column")
    tbox(s, -40, 40, -b / 2, b / 2, t, t + 32, "Beam")
    s.box(-8, 8, -7, 7, 0, t, "plate", "Plates")
    s.box(-7, 7, -tf / 2, tf / 2, t, t + 8, "plate", "Plates")
    s.box(-6, 6, -tf / 2, tf / 2, -10, 0, "plate", "Plates")
    for sy in (1, -1):
        y = sy * tf / 2
        s.line_weld((-7, y, t), (7, y, t), (0, sy, 0), (0, 0, 1), A)
        s.line_weld((-6, y, 0), (6, y, 0), (0, sy, 0), (0, 0, -1), A)
    for x in (-4.5, 0.0, 4.5):
        dowel_y(s, x, t + 4.5, -b / 2, b / 2)
    for x in (-3.0, 3.0):
        dowel_y(s, x, -5.5, -b / 2, b / 2)
    return view(s, (0, 0, 0), 0.6)


# ============================================================================= Fig. 12.10
def fork_shoe(s, x0, x1, b, plate_h, base_z, anchors_y, side_t=1.0, bolts=()):
    """Steel fork on a wall: base plate with anchors, pedestal, bottom plate and two side
    plates (welded), the beam end in between (beam bottom at z = 0)."""
    tb = 1.2
    xm = (x0 + x1) / 2
    s.box(xm - 10, xm + 10, -anchors_y - 4, anchors_y + 4, base_z, base_z + tb, "plate", "Plates")
    frustum(s, x0, x1, -b / 2 - side_t, b / 2 + side_t, base_z + tb, -1.0, 1.0, "plate", "Plates")
    s.box(x0, x1, -b / 2 - side_t, b / 2 + side_t, -1.0, 0, "plate", "Plates")
    for sy in (1, -1):
        y0, y1 = sorted((sy * b / 2, sy * (b / 2 + side_t)))
        s.box(x0, x1, y0, y1, 0, plate_h, "plate", "Plates")
        s.line_weld((x0, sy * (b / 2 + side_t), 0), (x1, sy * (b / 2 + side_t), 0), (0, sy, 0), (0, 0, 1), A)
    for y in (-anchors_y, anchors_y):
        lock_bolt(s, xm, y, base_z + tb, base_z - 22.0, layer="Anchors")
    for x, z in bolts:
        bolt_y(s, x, z, -b / 2 - side_t, b / 2 + side_t)


def saddle_inclined_1():
    """Beam end on a wall in a welded steel fork, two bolts."""
    s = Scene("Beam on wall, welded steel fork")
    b = 14.0
    concrete(s, -2, 24, -30, 30, -35, -4.7, "Wall")
    tbox(s, 4, 70, -b / 2, b / 2, 0, 36, "Beam")
    fork_shoe(s, 4, 14, b, 21.0, -4.7, 13.5, bolts=[(9.5, 7.0), (9.5, 15.0)])
    return view(s, (12, 0, 4), 0.6)


def saddle_inclined_2():
    """Beam between the two halves of a double column, four bolts."""
    s = Scene("Beam and double column (bolted)")
    b, tc = 14.0, 14.0
    for sy in (1, -1):
        y0, y1 = sorted((sy * b / 2, sy * (b / 2 + tc)))
        tbox(s, -11.5, 11.5, y0, y1, -60, 38.5, "Column")
    tbox(s, -20, 70, -b / 2, b / 2, 0, 36, "Beam")
    for x in (-6.0, 6.0):
        for z in (10.0, 27.0):
            bolt_y(s, x, z, -b / 2 - tc, b / 2 + tc)
    return view(s, (0, 0, 10), 0.65)


def saddle_inclined_3():
    """Gerber joint: oblique halved joint, steel side plates with one bolt in each part."""
    s = Scene("Beam-beam connection with steel connector plates (Gerber)")
    b, h, t = 18.0, 40.0, 1.0
    xz(s, [(-70, 0), (12, 0), (-12, h), (-70, h)], -b / 2, b / 2, layer="Beam left")
    xz(s, [(12, 0), (70, 0), (70, h), (-12, h)], -b / 2, b / 2, layer="Beam right")
    plate = [(0, 0), (24, 0), (0, h), (-24, h)]
    for sy in (1, -1):
        y0, y1 = sorted((sy * b / 2, sy * (b / 2 + t)))
        plate_xz(s, plate, y0, y1)
    for x, z in ((-16.0, 32.0), (16.0, 8.0)):
        bolt_y(s, x, z, -b / 2 - t, b / 2 + t)
    return view(s, (0, 0, 20), 0.75)


# ============================================================================= Fig. 12.13
def saddle_curved_1():
    """Beam over a column, nailed steel plates on both faces."""
    s = Scene("Beam-column connection with nailed plates")
    b, t = 14.0, 0.3
    tbox(s, 0, 17, -b / 2, b / 2, -50, 0, "Column")
    tbox(s, 0, 80, -b / 2, b / 2, 0, 35, "Beam")
    nails = grid(3.5, 14.5, 5, -14.5, 14.5, 12)
    for sy in (1, -1):
        y0, y1 = sorted((sy * b / 2, sy * (b / 2 + t)))
        s.box(2, 16, y0, y1, -16, 16, "plate", "Plates")
        nail_heads(s, nails, sy * (b / 2 + t), sy)
    return view(s, (9, 0, 0), 0.6)


def saddle_curved_2():
    """Beam end on a wall: steel fork with screwed side plates and a bolt in a slotted hole."""
    s = Scene("Support on wall, hinge with slotted hole")
    b = 14.0
    concrete(s, -4, 26, -30, 30, -35, -4.7, "Wall")
    tbox(s, 1, 70, -b / 2, b / 2, 0, 36, "Beam")
    fork_shoe(s, 1, 20, b, 19.0, -4.7, 13.5)
    xs, zb = 10.5, 8.0
    bolt_y(s, xs, zb, -b / 2 - 1, b / 2 + 1)
    # slotted hole outline on both side plates (horizontal slot)
    for sy in (1, -1):
        y = sy * (b / 2 + 1.01)
        slot = [(xs + 2.2 + 1.2 * math.cos(a), zb + 1.2 * math.sin(a)) for a in
                [math.radians(-90 + 15 * i) for i in range(13)]]
        slot += [(xs - 2.2 + 1.2 * math.cos(a), zb + 1.2 * math.sin(a)) for a in
                 [math.radians(90 + 15 * i) for i in range(13)]]
        s.add_line([(x, y, z) for x, z in slot], "Plates", closed=True)
        for x, z in [(x, 17.0) for x in (3.0, 6.5, 10.5, 14.5, 18.0)] + \
                    [(x, z) for x in (3.0, 18.0) for z in (4.0, 9.0, 13.0)]:
            small_screw(s, (x, y, z), (0, -sy, 0), 6.0)
    return view(s, (10, 0, 4), 0.6)


def saddle_curved_3():
    """Purlins on both sides of a main beam, hung with a steel saddle over the main beam."""
    s = Scene("Purlin-beam connection, connector over the main beam")
    hm, H = 7.0, 36.0                         # main beam 140 x 360 along y
    bp, hp = 9.0, 29.0                        # purlins along x, tops flush
    t = 0.5
    tbox(s, -hm, hm, -45, 45, 0, H, "Main beam")
    s.box(-hm, hm, -bp / 2 - t, bp / 2 + t, H, H + t, "plate", "Connector")        # over the top
    for sx in (1, -1):
        x0, x1 = sorted((sx * (hm + t), sx * 60.0))
        tbox(s, x0, x1, -bp / 2, bp / 2, H - hp, H, "Purlins")
        xa, xb = sorted((sx * hm, sx * (hm + t)))
        s.box(xa, xb, -bp / 2 - t, bp / 2 + t, H - hp - t, H + t, "plate", "Connector")   # down the face
        tri = [(sx * hm, H + t), (sx * hm, H - hp - t), (sx * (hm + 17), H - hp - t)]
        if sx < 0:
            tri.reverse()
        for sy in (1, -1):
            y0, y1 = sorted((sy * bp / 2, sy * (bp / 2 + t)))
            plate_xz(s, tri, y0, y1, "Connector")
            small_screw(s, (sx * (hm + 11), sy * (bp / 2 + t), H - hp + 6), (0, -sy, 0), 6.0)
        xa, xb = sorted((sx * hm, sx * (hm + 17)))
        s.box(xa, xb, -bp / 2 - t, bp / 2 + t, H - hp - t, H - hp, "plate", "Connector")  # under the purlin
    return view(s, (0, 0, 20), 0.7)


# ============================================================================= Fig. 12.16
def continuous_1():
    """Gerber joint with a slotted-in steel plate and a seat under the suspended beam."""
    s = Scene("Beam-beam connection with slotted-in steel plate")
    b, h, tf = 17.0, 40.0, 1.0
    tbox(s, -80, 0, -b / 2, b / 2, 0, h, "Beam left")
    tbox(s, 0.3, 80, -b / 2, b / 2, 0, h, "Beam right")
    plate = [(-27, 27.6), (0, 0), (27, 0), (27, 11), (0, 38), (-28.5, 38)]
    plate_xz(s, plate, -tf / 2, tf / 2)
    s.box(0, 27, -b / 2, b / 2, -1.0, 0, "plate", "Plates")
    for sy in (1, -1):
        s.line_weld((0, sy * tf / 2, 0), (27, sy * tf / 2, 0), (0, sy, 0), (0, 0, 1), A)
    for x in (-22.5, -14.0, -6.0):
        for z in (33.0, 26.0):
            dowel_y(s, x, z, -b / 2, b / 2)
    dowel_y(s, 10.5, 9.6, -b / 2, b / 2)
    return view(s, (0, 0, 18), 0.7)


def continuous_2():
    """Heavy support: welded steel saddle on a bearing, beam screwed to its top plate."""
    s = Scene("Heavy support (welded saddle)")
    b, h = 18.0, 48.0
    concrete(s, -24, 24, -22, 22, -60, -26, "Pier")
    s.box(-14, 14, -14, 14, -26, -23.5, "elastomer", "Bearing")
    tbox(s, -70, 70, -b / 2, b / 2, 0, h, "Beam")
    s.box(-31, 31, -b / 2, b / 2, -1.5, 0, "plate", "Saddle")
    s.box(-16, 16, -12, 12, -23.5, -21.5, "plate", "Saddle")
    web = [(-16, -21.5), (16, -21.5), (31, -1.5), (-31, -1.5)]
    for sy in (1, -1):
        y0, y1 = sorted((sy * (b / 2 - 1.5), sy * (b / 2 - 0.5)))
        plate_xz(s, web, y0, y1, "Saddle")
    for x in (-5.5, 5.5):
        s.box(x - 0.5, x + 0.5, -b / 2 + 1.5, b / 2 - 1.5, -21.5, -1.5, "plate", "Saddle")
    for x in (-16.0, 16.0):
        for y in (-4.0, 4.0):
            coach_screw(s, (x, y, -1.5), (0, 0, 1), 13.5)
    return view(s, (0, 0, -6), 0.65)


def continuous_3():
    """Truss node at a column: slotted-in steel plate through chord, members and column, dowels."""
    s = Scene("Truss connection with slotted-in plate and dowels")
    b, tf, r2 = 12.0, 1.0, math.sqrt(0.5)
    hb = b / 2
    tbox(s, -60, -0.2, -hb, hb, 0, 20, "Chord")
    tbox(s, 0.2, 60, -hb, hb, 0, 20, "Chord")
    tbox(s, -10, 10, -hb, hb, 20, 70, "Vertical")
    tbox(s, -10, 10, -hb, hb, -60, 0, "Column")
    diag = {}
    for sx in (1, -1):
        p0 = (sx * 23.0, 20.0)
        p1 = (p0[0] + sx * 45, 65.0)
        poly = band(p0, p1, 18, cut0=((0, 20), (1, 0)))
        if sx > 0:
            poly.reverse()
        xz(s, poly, -hb, hb, layer="Diagonals")
        diag[sx] = (p0, p1)
    # slotted-in plate (separate pieces in one plane)
    for poly in (rect(-38, 38, 2, 18), rect(-8, 8, 18, 45), rect(-8, 8, -17, 2)):
        plate_xz(s, poly, -tf / 2, tf / 2)
    for sx, (p0, p1) in diag.items():
        poly = band(p0, p1, 14, cut0=((0, 18), (1, 0)), cut1=(along(p0, p1, 30), (-(p1[1] - p0[1]), p1[0] - p0[0])))
        if sx > 0:
            poly.reverse()
        plate_xz(s, poly, -tf / 2, tf / 2)
    pts = [(x, z) for x in (-33, -27, -21, -15, 15, 21, 27, 33) for z in (5, 10, 15)]
    pts += [(x, z) for x in (-6, -2, 2, 6) for z in (27, 33, 39)]
    pts += [(x, -9.0) for x in (-4, 4)]
    for sx, (p0, p1) in diag.items():
        pts += [along(p0, p1, sd, t) for sd in (12, 18, 24) for t in (-4, 0, 4)]
    for x, z in pts:
        dowel_y(s, x, z, -hb, hb)
    return view(s, (0, 0, 15), 0.75)


# ----------------------------------------------------------------------------- rods (tension bars)
def rod_with_fork(s, pin, direction, length=50.0, d=2.4, lug_t=1.5, fork_t=1.0, layer="Tension rods"):
    """Round bar from a pin outwards along `direction` (x, z), with a welded fork (two
    plates either side of the lug) around the pin."""
    dx, dz = _unit2(direction)
    p0 = (pin[0] - 2.5 * dx, pin[1] - 2.5 * dz)
    p1 = (pin[0] + 8 * dx, pin[1] + 8 * dz)
    for sy in (1, -1):
        y0, y1 = sorted((sy * lug_t / 2, sy * (lug_t / 2 + fork_t)))
        xz(s, band(p0, p1, 5.0), y0, y1, "plate", layer)
    s.cylinder((p1[0], 0, p1[1]), (dx, 0, dz), d / 2, length, "bolt", layer, n=16, outline=True)
    bolt_y(s, pin[0], pin[1], -lug_t / 2 - fork_t, lug_t / 2 + fork_t, size="M16")


# ============================================================================= Fig. 12.19
def straight_truss_1():
    """Steel strip diagonals pinned to a slotted-in plate in chord and strut."""
    s = Scene("Steel strips to bottom chord and strut (slotted-in plate)")
    hb, tf = 5.5, 1.0
    tbox(s, -55, 55, -hb, hb, 0, 20, "Chord")
    tbox(s, -7, 7, -hb, hb, 20, 60, "Strut")
    plate_xz(s, rect(-22, 22, 3, 17), -tf / 2, tf / 2)
    plate_xz(s, rect(-5, 5, 17, 35), -tf / 2, tf / 2)
    for sx in (1, -1):
        cx, cz = sx * 14.0, 27.0
        ear = hull([(cx, cz + 6), (cx + 6, cz), (cx - 6, cz), (sx * 9, 17), (sx * 19, 17)])
        plate_xz(s, ear, -tf / 2, tf / 2)
        strip = band(along((cx, cz), (cx + sx, cz + 1), -4), along((cx, cz), (cx + sx, cz + 1), 45), 6.0)
        for sy in (1, -1):
            y0, y1 = sorted((sy * tf / 2, sy * (tf / 2 + 0.8)))
            xz(s, strip, y0, y1, "plate", "Steel strips")
        bolt_y(s, cx, cz, -tf / 2 - 0.8, tf / 2 + 0.8)
    for x, z in grid(-16, 16, 5, 6, 14, 3) + grid(-2.5, 2.5, 2, 23, 33, 3):
        dowel_y(s, x, z, -hb, hb)
    return view(s, (0, 0, 18), 0.7)


def _diag_pair(z_base, x_base, width=18.0, length=50.0, cut=None):
    """Two diagonals rising outwards at 45 degrees from (+-x_base, z_base)."""
    out = {}
    for sx in (1, -1):
        p0 = (sx * x_base, z_base)
        p1 = (p0[0] + sx * length * math.sqrt(0.5), z_base + length * math.sqrt(0.5))
        c = cut(sx) if cut else ((0, z_base), (1, 0))
        out[sx] = (p0, p1, band(p0, p1, width, cut0=c))
    return out


def straight_truss_2():
    """Diagonals on a chord; screwed steel plates on all members, joined by one central axle."""
    s = Scene("Chord and diagonals, screwed plates and central axle")
    hc, hd, t = 6.0, 6.8, 0.8                 # chord / diagonals half widths, plate thickness
    tbox(s, -60, 60, -hc, hc, 0, 22, "Chord")
    diags = _diag_pair(22.0, 13.0)
    axle = (0.0, 11.0)
    for sx, (p0, p1, poly) in diags.items():
        xz(s, poly, -hd, hd, layer="Diagonals")
    for sy in (1, -1):
        y0, y1 = sorted((sy * hc, sy * (hc + t)))
        s.box(-9, 9, y0, y1, 2, 20, "plate", "Plates")
        for x, z in grid(-7, 7, 4, 4, 18, 4):
            if not (abs(x) < 3 and 6 < z < 16):
                small_screw(s, (x, sy * (hc + t), z), (0, -sy, 0))
        for sx, (p0, p1, _poly) in diags.items():
            pts = [along(p0, p1, sd, tt) for sd in (10, 28) for tt in (-7.5, 7.5)]
            tip = [(axle[0], axle[1] + 3), (axle[0], axle[1] - 3), (axle[0] + sx * 3, axle[1])]
            y0, y1 = sorted((sy * hd, sy * (hd + t)))
            plate_xz(s, hull(pts + tip), y0, y1)
            for sd in (15, 21, 27):
                for tt in (-5, 0, 5):
                    x, z = along(p0, p1, sd, tt)
                    small_screw(s, (x, sy * (hd + t), z), (0, -sy, 0))
    bolt_y(s, axle[0], axle[1], -hd - t, hd + t, size="M20")
    return view(s, (0, 0, 20), 0.75)


def straight_truss_3():
    """Diagonals between the halves of a double chord; screwed plates and central axle."""
    s = Scene("Double chord and diagonals, screwed plates and central axle")
    hd, t, hc = 6.8, 0.8, 8.0
    for sy in (1, -1):
        y0, y1 = sorted((sy * (hd + t), sy * (hd + t + hc)))
        tbox(s, -60, 60, y0, y1, 0, 22, "Chord")
    axle = (0.0, 11.0)
    diags = _diag_pair(30.0, 14.0, cut=lambda sx: ((sx * 1.0, 0), (0, 1)))
    pts = [(axle[0] + 3 * math.cos(a), axle[1] + 3 * math.sin(a)) for a in [i * math.pi / 6 for i in range(12)]]
    for sx, (p0, p1, poly) in diags.items():
        xz(s, poly, -hd, hd, layer="Diagonals")
        pts += [along(p0, p1, sd, tt) for sd in (-6, 14) for tt in (-7.5, 7.5)]
    node = hull(pts)
    for sy in (1, -1):
        y0, y1 = sorted((sy * hd, sy * (hd + t)))
        plate_xz(s, node, y0, y1)
        for sx, (p0, p1, _poly) in diags.items():
            for sd in (4, 10):
                for tt in (-4.5, 0, 4.5):
                    x, z = along(p0, p1, sd, tt)
                    if z > 24:
                        small_screw(s, (x, sy * (hd + t), z), (0, -sy, 0))
    bolt_y(s, axle[0], axle[1], -hd - t - hc, hd + t + hc, size="M20")
    return view(s, (0, 0, 20), 0.75)


# ============================================================================= Fig. 12.22
def triangular_truss_1():
    """Ridge: upper chords, vertical and diagonals, one slotted-in plate with dowels."""
    s = Scene("Upper chords, diagonals and vertical with slotted-in plate")
    hb, h, tf = 6.0, 16.0, 1.0
    ta = math.tan(math.radians(8))
    zb0 = 40 - h / math.cos(math.radians(8))
    for sx in (1, -1):
        poly = [(0, 40), (sx * 60, 40 - 60 * ta), (sx * 60, zb0 - 60 * ta), (0, zb0)]
        xz(s, poly if sx < 0 else poly[::-1], -hb, hb, layer="Upper chords")
    xz(s, [(-7, -40), (7, -40), (7, zb0 - 7 * ta), (0, zb0), (-7, zb0 - 7 * ta)], -hb, hb, layer="Vertical")
    diags = {}
    for sx in (1, -1):
        p0 = (sx * 20.0, 20.0)
        d = (sx * math.cos(math.radians(50)), -math.sin(math.radians(50)))
        p1 = (p0[0] + 50 * d[0], p0[1] + 50 * d[1])
        cut = ((0, zb0), (sx, -ta))
        xz(s, band(p0, p1, 14, cut0=cut), -hb, hb, layer="Diagonals")
        diags[sx] = (p0, p1)
    # slotted-in plate, in pieces in one plane
    for sx in (1, -1):
        piece = [(0, 38), (sx * 28, 38 - 28 * ta), (sx * 28, zb0 + 2 - 28 * ta), (0, zb0 + 2)]
        plate_xz(s, piece, -tf / 2, tf / 2)
        p0, p1 = diags[sx]
        plate_xz(s, band(p0, along(p0, p1, 25), 10, cut0=((0, zb0 + 2), (sx, -ta))), -tf / 2, tf / 2)
    plate_xz(s, [(-5, 0), (5, 0), (5, zb0 + 2 - 5 * ta), (0, zb0 + 2), (-5, zb0 + 2 - 5 * ta)], -tf / 2, tf / 2)
    pts = [(sx * x, 40 - x * ta - dz) for sx in (1, -1) for x in (10, 17, 24) for dz in (4, 10)]
    pts += [(x, z) for x in (-2.5, 2.5) for z in (6, 14)]
    for sx, (p0, p1) in diags.items():
        pts += [along(p0, p1, sd, tt) for sd in (6, 13, 20) for tt in (-3, 3)]
    for x, z in pts:
        dowel_y(s, x, z, -hb, hb)
    return view(s, (0, 0, 15), 0.75)


def triangular_truss_2():
    """Bottom chord, vertical and diagonals joined by toothed (punched metal) plates."""
    s = Scene("Bottom chord, diagonals and vertical with toothed plates")
    hb, t = 2.25, 0.15
    tbox(s, -45, 45, -hb, hb, 0, 10, "Chord")
    tbox(s, -4, 4, -hb, hb, 10, 55, "Vertical")
    for sx, (p0, p1, poly) in _diag_pair(10.0, 10.2, width=8.0, length=48.0).items():
        xz(s, poly, -hb, hb, layer="Diagonals")
    for sy in (1, -1):
        y0, y1 = sorted((sy * hb, sy * (hb + t)))
        s.box(-11.5, 11.5, y0, y1, 5, 16.4, "plate", "Toothed plates")
        y = sy * (hb + t + 0.01)
        for x0 in [-10.6 + 1.5 * i for i in range(15)]:
            for z0 in [6.0 + 1.2 * j for j in range(9)]:
                s.add_line([(x0 - 0.35, y, z0), (x0 + 0.35, y, z0)], "Toothed plates")
    return view(s, (0, 0, 12), 0.6)


def triangular_truss_3():
    """Upper chords notched against a continuous post with a wider head; one through bolt."""
    s = Scene("Upper chords and vertical, carpentry joint")
    hb, h = 5.0, 14.0
    ta = math.tan(math.radians(20))
    xz(s, [(-4.5, -50), (4.5, -50), (4.5, 18), (6.5, 22), (6.5, 40), (-6.5, 40), (-6.5, 22), (-4.5, 18)],
       -hb, hb, layer="Post")
    hv = h / math.cos(math.radians(20))
    for sx in (1, -1):
        zt = 19.0
        poly = [(sx * 4.5, zt), (sx * 60, zt - 55.5 * ta), (sx * 60, zt - 55.5 * ta - hv), (sx * 4.5, zt - hv)]
        xz(s, poly if sx < 0 else poly[::-1], -hb, hb, layer="Upper chords")
    s.bolt((-24, 0, 12), (1, 0, 0), 48, size="M16")
    return view(s, (0, 0, 15), 0.7)


# ============================================================================= Fig. 12.25
def under_stressed_1():
    """Beam end on a column: end plate, inclined side plates with a pin for the tension rod."""
    s = Scene("Tension rod at the support")
    hb = 8.0
    tbox(s, 0, 24, -hb, hb, -50, -1, "Column")
    s.box(0, 24, -hb, hb, -1, 0, "plate", "Plates")
    tbox(s, 0, 80, -hb, hb, 0, 40, "Beam")
    s.box(-1, 0, -hb, hb, -13, 40, "plate", "Plates")
    for z in (6.0, 15.0, 24.0, 33.0, -8.0):
        coach_screw(s, (-1, 0, z), (1, 0, 0), 10.0)
    p0, pin = (5.7, 18.6), (50.0, -5.7)
    L = math.dist(p0, pin)
    side = band(p0, along(p0, pin, L + 4), 9.0)
    for sy in (1, -1):
        y0, y1 = sorted((sy * hb, sy * (hb + 1)))
        plate_xz(s, side, y0, y1)
    bolt_y(s, 11.4, 12.3, -hb - 1, hb + 1, size="M20")
    d = _unit2((pin[0] - p0[0], pin[1] - p0[1]))
    xz(s, band(along(p0, pin, L - 3), along(p0, pin, L + 6), 6.0), -1.5, 1.5, "plate", "Tension rod")
    s.cylinder((pin[0] + 6 * d[0], 0, pin[1] + 6 * d[1]), (d[0], 0, d[1]), 1.5, 60, "bolt", "Tension rod",
               n=16, outline=True)
    bolt_y(s, pin[0], pin[1], -hb - 1, hb + 1, size="M20")
    return view(s, (20, 0, 5), 0.75)


def under_stressed_2():
    """Strut on a welded steel shoe; lug plate below with pins for two tension rods."""
    s = Scene("Tension rods and strut, welded plates")
    tbox(s, -8, 8, -6, 6, 0, 60, "Strut")
    s.box(-9, 9, -7, 7, -1, 0, "plate", "Plates")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 6, sy * 7))
        s.box(-8, 8, y0, y1, 0, 12, "plate", "Plates")
        s.line_weld((-8, sy * 7, 0), (8, sy * 7, 0), (0, sy, 0), (0, 0, 1), A)
    for x in (-4.0, 4.0):
        for z in (4.0, 9.0):
            bolt_y(s, x, z, -7, 7)
    s.box(-13, 13, -0.75, 0.75, -8, -1, "plate", "Plates")
    for sy in (1, -1):
        s.line_weld((-13, sy * 0.75, -1), (13, sy * 0.75, -1), (0, sy, 0), (0, 0, -1), A)
    for sx in (1, -1):
        rod_with_fork(s, (sx * 10.0, -4.5), (sx * math.cos(math.radians(10)), math.sin(math.radians(10))))
    return view(s, (0, 0, 5), 0.75)


def under_stressed_3():
    """Two diagonals and two tension rods on one slotted-in steel node, dowels."""
    s = Scene("Tension rods and diagonals with dowels")
    hb, tf = 6.0, 1.0
    diags = {}
    for sx in (1, -1):
        p0 = (sx * 9.5, 0.0)
        p1 = (p0[0] + sx * 30, 52.0)
        xz(s, band(p0, p1, 14, cut0=((0, 0), (1, 0))), -hb, hb, layer="Diagonals")
        plate_xz(s, band(p0, along(p0, p1, 26), 10, cut0=((0, 0), (1, 0))), -tf / 2, tf / 2)
        diags[sx] = (p0, p1)
    plate_xz(s, rect(-15, 15, -9, 0), -tf / 2, tf / 2)
    for sx, (p0, p1) in diags.items():
        for sd in (8, 15, 22):
            for tt in (-3, 3):
                x, z = along(p0, p1, sd, tt)
                dowel_y(s, x, z, -hb, hb)
        rod_with_fork(s, (sx * 10.0, -5.0), (sx * math.cos(math.radians(10)), math.sin(math.radians(10))),
                      lug_t=tf)
    return view(s, (0, 0, 8), 0.75)


# ============================================================================= Fig. 12.28
def rigid_frame_1():
    """Column on a floor: base plate with two welded angles, bolted through the column."""
    s = Scene("Column-floor support with angles and base plate")
    concrete(s, -40, 40, -35, 35, -20, 0, "Floor")
    s.box(-21, 21, -20, 20, 0, 1.5, "plate", "Plates")
    tbox(s, -19, 19, -7, 7, 1.5, 80, "Column")
    for sy in (1, -1):
        y_a, y_b = sorted((sy * 7, sy * 8))
        s.box(-15, 15, y_a, y_b, 1.5, 16.5, "plate", "Angles")
        y_a, y_b = sorted((sy * 8, sy * 17))
        s.box(-15, 15, y_a, y_b, 1.5, 2.5, "plate", "Angles")
        s.line_weld((-15, sy * 17, 1.5), (15, sy * 17, 1.5), (0, sy, 0), (0, 0, 1), A)
        lock_bolt(s, 0, sy * 14, 2.5, -16.0, layer="Anchors")
    for x in (-10.0, 0.0, 10.0):
        bolt_y(s, x, 10.0, -8, 8)
    return view(s, (0, 0, 8), 0.7)


def rigid_frame_2():
    """Beam between the halves of a double column, a circle of dowels."""
    s = Scene("Moment joint double column - beam (dowels)")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 7, sy * 21))
        tbox(s, -23.5, 23.5, y0, y1, -100, 25, "Column")
    tbox(s, -35, 90, -7, 7, -25, 25, "Beam")
    for i in range(16):
        a = 2 * math.pi * i / 16
        dowel_y(s, 16 * math.cos(a), 16 * math.sin(a), -21, 21, d=1.6)
    return view(s, (0, 0, -5), 0.75)


def rigid_frame_3():
    """Column on a floor, four cast-in flat bars bolted through the column."""
    s = Scene("Column-floor support with cast-in plates")
    concrete(s, -45, 45, -30, 30, -30, 0, "Floor")
    tbox(s, -22, 22, -7, 7, 0, 70, "Column")
    for x0 in (-13.0, 13.0):
        for sy in (1, -1):
            y0, y1 = sorted((sy * 7, sy * 8))
            s.box(x0 - 2.5, x0 + 2.5, y0, y1, -25, 18, "plate", "Cast-in plates")
        bolt_y(s, x0, 12.0, -8, 8)
        for z in (-8.0, -18.0):
            bolt_y(s, x0, z, -8, 8)
    return view(s, (0, 0, 8), 0.7)


# ============================================================================= Fig. 12.31
def three_hinged_frame_1():
    """Inclined column foot in a concrete fork on an elastomeric bearing, pin through."""
    s = Scene("Column foot on elastomeric bearing in concrete footing")
    a = math.radians(20)
    concrete(s, -30, 14, -15, 15, -60, -24, "Footing")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 7.5, sy * 15))
        concrete(s, -30, 14, y0, y1, -24, 0, "Footing")
    s.box(-25, 1, -7, 7, -24, -23, "elastomer", "Bearing")
    p0 = (-12.0, -23.0)
    p1 = (p0[0] + 90 * math.sin(a), p0[1] + 90 * math.cos(a))
    xz(s, band(p0, p1, 24, cut0=((0, -23), (1, 0))), -7, 7, layer="Column")
    bolt_y(s, -12 + 11 * math.tan(a), -12.0, -15, 15, size="M20")
    return view(s, (-6, 0, -8), 0.7)


def three_hinged_frame_2():
    """Rafter end between the halves of a double column; double tie bar on a pin."""
    s = Scene("Double tie bar to double column")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 7, sy * 16))
        tbox(s, -11, 11, y0, y1, -60, 30, "Column")
        y0, y1 = sorted((sy * 16, sy * 17))
        s.box(-14, 80, y0, y1, 19, 25, "plate", "Tie bars")
    tbox(s, -11, 11, -7, 7, -60, 0, "Filler")
    tbox(s, -12, 80, -7, 7, 0, 36, "Rafter")
    for x in (-6.0, 0.0, 6.0):
        bolt_y(s, x, -10.0, -16, 16)
    bolt_y(s, 6.0, 9.0, -16, 16)
    bolt_y(s, -5.0, 22.0, -17, 17, size="M20")
    return view(s, (5, 0, 5), 0.75)


def three_hinged_frame_3():
    """Column on a footing, two cast-in plates screwed to the column faces, one bolt."""
    s = Scene("Column support with cast-in plates (screwed)")
    concrete(s, -35, 35, -25, 25, -40, 0, "Footing")
    tbox(s, -12, 12, -7, 7, 0, 70, "Column")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 7, sy * 8))
        s.box(-9, 9, y0, y1, -20, 24, "plate", "Cast-in plates")
        for x, z in grid(-6, 6, 3, 4, 22, 5):
            if not (x == 0 and 9 < z < 19):
                small_screw(s, (x, sy * 8, z), (0, -sy, 0))
    bolt_y(s, 0, 14.0, -8, 8, size="M20")
    return view(s, (0, 0, 15), 0.8)


# ============================================================================= Fig. 12.34
def kinked_1():
    """Ridge: rafter ends against a shaped steel I-section, tension plates on both faces."""
    s = Scene("Ridge with tension plates and shaped I-profile")
    hb, ta = 7.0, math.tan(math.radians(5))

    def zb(x):
        return -abs(x) * ta

    def zt(x):
        return 40 - abs(x) * ta

    for sx in (1, -1):
        poly = [(sx * 0.6, zb(0.6)), (sx * 70, zb(70)), (sx * 70, zt(70)), (sx * 0.6, zt(0.6))]
        xz(s, poly if sx > 0 else poly[::-1], -hb, hb, layer="Rafters")
    i_prof = [(-9, zb(9) - 1.2), (0, -1.2), (9, zb(9) - 1.2), (9, zb(9)), (0.6, zb(0.6)), (0.6, zt(0.6)),
              (9, zt(9)), (9, zt(9) + 1.2), (0, 41.2), (-9, zt(9) + 1.2), (-9, zt(9)), (-0.6, zt(0.6)),
              (-0.6, zb(0.6)), (-9, zb(9))]
    xz(s, i_prof, -hb, hb, "plate", "I-profile")
    for sy in (1, -1):
        y0, y1 = sorted((sy * hb, sy * (hb + 1)))
        plate_xz(s, rect(-29, 29, 16, 22), y0, y1, "Tension plates")
    for x in (-25.0, -12.5, 12.5, 25.0):
        bolt_y(s, x, 19.0, -hb - 1, hb + 1)
    return view(s, (0, 0, 18), 0.75)


def kinked_2():
    """Ridge: steel shoes on both rafter ends, lugs joined by one pin."""
    s = Scene("Ridge connection (bolted)")
    hb, ta = 7.0, math.tan(math.radians(5))
    for sx in (1, -1):
        poly = [(sx * 5, 0), (sx * 70, -65 * ta), (sx * 70, 40 - 65 * ta), (sx * 5, 40)]
        xz(s, poly if sx > 0 else poly[::-1], -hb, hb, layer="Rafters")
        xa, xb = sorted((sx * 4, sx * 5))
        s.box(xa, xb, -hb - 1, hb + 1, 2, 38, "plate", "Plates")
        xa, xb = sorted((sx * 5, sx * 16))
        for sy in (1, -1):
            y0, y1 = sorted((sy * hb, sy * (hb + 1)))
            s.box(xa, xb, y0, y1, 3, 37, "plate", "Plates")
        for z in (8.0, 16.0, 24.0, 32.0):
            bolt_y(s, sx * 10.5, z, -hb - 1, hb + 1)
        lug = [(sx * 4, 10), (sx * 4, 30), (-sx * 2.5, 22.5), (-sx * 2.5, 17.5)]
        y0, y1 = (0, 1.5) if sx < 0 else (-1.5, 0)
        plate_xz(s, lug if sx < 0 else lug[::-1], y0, y1)
    bolt_y(s, 0, 20.0, -1.5, 1.5, size="M20")
    return view(s, (0, 0, 18), 0.7)


def kinked_3():
    """Column on a footing: base plate with welded-on studs and two side bars, one bolt."""
    s = Scene("Support on footing with welded steel plate")
    concrete(s, -35, 30, -25, 25, -30, 0, "Footing")
    s.box(-15, 15, -12, 12, 0, 1.5, "plate", "Plates")
    tbox(s, -16, 16, -7, 7, 1.5, 70, "Column")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 7, sy * 8))
        s.box(-3, 3, y0, y1, 1.5, 16, "plate", "Plates")
        s.line_weld((-3, sy * 8, 1.5), (3, sy * 8, 1.5), (0, sy, 0), (0, 0, 1), A)
        for x in (-11.0, 11.0):
            s.cylinder((x, sy * 9, -10), (0, 0, 1), 1.0, 10, "bolt", "Studs", n=16)
    bolt_y(s, 0, 9.0, -8, 8)
    return view(s, (0, 0, 12), 0.8)


# ============================================================================= Fig. 12.37
def arch_1():
    """Arch crown: slotted-in plates with end plates and a central hinge bar, straps on both faces."""
    s = Scene("Ridge connection with steel connectors (dowels)")
    hb, tf = 7.0, 1.0
    for sx in (1, -1):
        xa, xb = sorted((sx * 1.5, sx * 70))
        tbox(s, xa, xb, -hb, hb, 0, 40, "Arch")
        xa, xb = sorted((sx * 0.5, sx * 1.5))
        s.box(xa, xb, -hb, hb, 2, 38, "plate", "Plates")
        xa, xb = sorted((sx * 1.5, sx * 15))
        s.box(xa, xb, -tf / 2, tf / 2, 4, 36, "plate", "Plates")
        for z in (6.0, 12.0, 28.0, 34.0):
            dowel_y(s, sx * 8, z, -hb, hb)
    s.box(-0.5, 0.5, -5, 5, 4, 36, "plate", "Plates")
    for sy in (1, -1):
        y0, y1 = sorted((sy * hb, sy * (hb + 1)))
        s.box(-19, 19, y0, y1, 17, 23, "plate", "Straps")
    for x in (-13.0, 13.0):
        bolt_y(s, x, 20.0, -hb - 1, hb + 1)
    return view(s, (0, 0, 20), 0.7)


def arch_2():
    """Arch foot: shoe with slotted-in plate and dowels, welded steel hinge on a footing."""
    s = Scene("Support of arch (welded steel hinge)")
    sub = Scene("")
    tbox(sub, -20, 20, -7, 7, 12, 80, "Arch")
    sub.box(-20, 20, -7.5, 7.5, 10, 12, "plate", "Shoe")
    sub.box(-16, 16, -0.5, 0.5, 12, 30, "plate", "Shoe")
    for x in (-12.0, -4.0, 4.0, 12.0):
        dowel_y(sub, x, 21.0, -7, 7)
    sub.box(-4, 4, -1, 1, 1.5, 10, "plate", "Hinge")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 1, sy * 2.2))
        sub.box(-6, 6, y0, y1, 0, 7, "plate", "Hinge")
        sub.line_weld((-6, sy * 2.2, 0), (6, sy * 2.2, 0), (0, sy, 0), (0, 0, 1), A)
        sub.line_weld((-4, sy * 1, 10), (4, sy * 1, 10), (0, sy, 0), (0, 0, -1), A)
    bolt_y(sub, 0, 4.0, -2.2, 2.2, size="M20")
    sub.box(-25, 25, -15, 15, -2, 0, "plate", "Base plate")
    for x in (-20.0, 20.0):
        lock_bolt(sub, x, 0, 0, -24, layer="Anchors")
    merge(s, sub, -35.0)
    sloped_footing(s, -35.0)
    return view(s, (0, 0, 10), 0.75)


def arch_3():
    """Arch foot on a base plate with two welded side plates, three bolts."""
    s = Scene("Arch support")
    sub = Scene("")
    tbox(sub, -20, 20, -7, 7, 0, 80, "Arch")
    sub.box(-24, 24, -13, 13, -2, 0, "plate", "Base plate")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 7, sy * 8))
        sub.box(-16, 16, y0, y1, 0, 22, "plate", "Plates")
        sub.line_weld((-16, sy * 8, 0), (16, sy * 8, 0), (0, sy, 0), (0, 0, 1), A)
        lock_bolt(sub, 0, sy * 10.5, 0, -24, layer="Anchors")
    for x, z in ((-8.0, 8.0), (8.0, 8.0), (0.0, 16.0)):
        bolt_y(sub, x, z, -8, 8)
    merge(s, sub, -40.0)
    sloped_footing(s, -40.0)
    return view(s, (0, 0, 10), 0.75)


# ============================================================================= registry
# group (figure) -> intro; key -> (function, group, caption, drawing, points to check)
CHECK_GROUPS = {
    "12.7": "Straight beam (possibly with cantilever)",
    "12.10": "Saddle roof with inclined upper edge",
    "12.13": "Saddle roof with inclined or curved upper and lower edge",
    "12.16": "Continuous beams",
    "12.19": "Straight truss",
    "12.22": "Triangular or trapezoidal truss",
    "12.25": "Under stressed beam",
    "12.28": "Rigid frame",
    "12.31": "Three hinged frame (straight legs)",
    "12.34": "Three hinged frame (curved/kinked legs)",
    "12.37": "Arch (solid and truss beam)",
}

_D = "book/design/timber/Images/"

CHECK_DETAILS = {
    # ---- 12.7
    "timber_cantilever_1": (cantilever_1, "12.7", "Left: purlins on main beam with Z-profiles", _D + "straight_beam_cantilever_details.png", [
        "Purlins on both sides of the main beam, tops flush with the main beam; one Z-profile per purlin "
        "(top flange on the main beam, web against its side, bottom flange under the purlin). Is that the intended reading?",
        "One screw through each flange (down into the main beam, up into the purlin): enough, or nails / more screws?",
        "Sizes assumed: main beam 120 x 300, purlins 75 x 240, Z-profile 4 mm, 80 mm wide.",
    ]),
    "timber_cantilever_2": (cantilever_2, "12.7", "Middle: double beam on double column (bolted)", _D + "straight_beam_cantilever_details.png", [
        "Read as: two beam halves resting on two column halves, with one central filler (6 cm) running from the "
        "column up to the beam top, everything bolted through. Correct?",
        "The beam is drawn slightly sloping in the elevation; modelled horizontal.",
        "Bolts: 6 in the beam zone (2 x 3), 2 in the column; M16 assumed.",
    ]),
    "timber_cantilever_3": (cantilever_3, "12.7", "Right: beam on column with steel connector", _D + "straight_beam_cantilever_details.png", [
        "Connector modelled as a horizontal plate with a fin plate welded on top (slotted into the beam) and one "
        "below (slotted into the column), with dowels (3 in the beam, 2 in the column). Correct?",
        "The haunched beam end of the drawing (bottom rising to the right) is not modelled; the beam is straight.",
    ]),
    # ---- 12.10
    "timber_saddle_inclined_1": (saddle_inclined_1, "12.10", "Left: beam on wall, welded steel fork", _D + "saddle_roof_inclined_details.png", [
        "Steel fork: base plate with two anchors, a tapered bearing block, bottom plate and two welded side "
        "plates; two bolts through beam and side plates. Correct?",
        "Anchor positions (beside the fork, across the wall) and the bearing block shape are assumed.",
    ]),
    "timber_saddle_inclined_2": (saddle_inclined_2, "12.10", "Middle: beam and double column (bolted)", _D + "saddle_roof_inclined_details.png", [
        "Beam between the two column halves, 2 x 2 bolts; column halves 140 x 230, a little higher than the beam top.",
        "The beam end (sloped in the drawing) is cut square, and the beam is horizontal instead of following the roof slope.",
    ]),
    "timber_saddle_inclined_3": (saddle_inclined_3, "12.10", "Right: Gerber joint with steel side plates", _D + "saddle_roof_inclined_details.png", [
        "Oblique joint: the left beam carries the right one. One parallelogram plate on each face, one bolt in each "
        "beam part. The drawing was hard to read here (rectangle + parallelogram outline, one bolt in the plan view): "
        "please check the plate shape and the bolt positions.",
        "Is the direction of the oblique cut right (which part supports which)?",
    ]),
    # ---- 12.13
    "timber_saddle_curved_1": (saddle_curved_1, "12.13", "Left: beam-column connection with nailed plates", _D + "saddle_roof_curved_details.png", [
        "Beam on top of the column, beam end flush with the column face; one nailed steel plate (3 mm) on each face, "
        "5 x 12 nails per plate. Correct?",
    ]),
    "timber_saddle_curved_2": (saddle_curved_2, "12.13", "Middle: support on wall, hinge with slotted hole", _D + "saddle_roof_curved_details.png", [
        "Same fork as 12.10 left, but with screwed side plates (screws along the top and sides) and one bolt in a "
        "horizontal slotted hole. Unclear: the inner rectangle in the elevation (modelled only as the slot outline) "
        "and whether the slot should be horizontal.",
    ]),
    "timber_saddle_curved_3": (saddle_curved_3, "12.13", "Right: purlin-beam connection over the main beam", _D + "saddle_roof_curved_details.png", [
        "Connector read as: strap over the main beam top, down both main beam faces, triangular plates along the "
        "purlin sides (one screw each) and a plate under each purlin. Please check this interpretation, in "
        "particular the small plate with two screws in the left view (not modelled separately).",
        "Purlins with their tops flush with the main beam; sizes assumed (main beam 140 x 360, purlins 90 x 290).",
    ]),
    # ---- 12.16
    "timber_continuous_1": (continuous_1, "12.16", "Left: beam-beam connection with slotted-in plate", _D + "continuous_beam_details.png", [
        "Gerber joint with a vertical joint and one slotted-in plate: 6 dowels in the left beam, 1 in the right "
        "beam, and a seat plate under the right beam. Plate outline follows the dashed line in the drawing. Correct?",
        "Seat plate modelled full beam width, under the beam (in the drawing it may be let into the beam).",
    ]),
    "timber_continuous_2": (continuous_2, "12.16", "Middle: heavy support (welded)", _D + "continuous_beam_details.png", [
        "Welded saddle: top plate, bottom plate, two sloped web plates and two stiffeners, on an elastomeric "
        "bearing on a concrete pier; 4 screws up into the beam. Correct?",
        "Unclear: the bearing below the saddle (elastomer or steel bearing plate?) and the number of screws.",
    ]),
    "timber_continuous_3": (continuous_3, "12.16", "Right: truss connection with column", _D + "continuous_beam_details.png", [
        "One slotted-in plate through chord (split at the column), vertical, diagonals and column, with dowels "
        "(chord 2 x 12, vertical 12, diagonals 9 each, column 2). Correct?",
        "Members all 120 mm wide; diagonals at 45 degrees; the chord joint at the column axis.",
    ]),
    # ---- 12.19
    "timber_straight_truss_1": (straight_truss_1, "12.19", "Left: steel strips to bottom chord and strut", _D + "straight_truss_details.png", [
        "Slotted-in plate in chord and strut with two ears; each diagonal is a pair of steel strips (one each "
        "side of the ear) on one pin. Correct?",
        "Strips 60 x 8 mm, pin M16 assumed.",
    ]),
    "timber_straight_truss_2": (straight_truss_2, "12.19", "Middle: chord and diagonals, screwed plates and central axle", _D + "straight_truss_details.png", [
        "Screwed steel plates on chord and diagonals (both faces); the diagonal plates have a tongue down to "
        "one central axle through the chord. Uncertain interpretation of the small extra view in the drawing.",
        "The diagonals are modelled 1.6 cm wider than the chord, so their plates lie over the chord plates.",
    ]),
    "timber_straight_truss_3": (straight_truss_3, "12.19", "Right: double chord and diagonals, screwed plates and axle", _D + "straight_truss_details.png", [
        "Read as: the diagonals between the two halves of a double chord, one screwed steel node plate on each "
        "side of the diagonals, one axle through chord halves and plates. This was the hardest drawing to read: "
        "please check the whole concept.",
    ]),
    # ---- 12.22
    "timber_triangular_truss_1": (triangular_truss_1, "12.22", "Left: upper chords, diagonals and vertical with slotted-in plate", _D + "triangular_truss_details.png", [
        "One slotted-in plate (coupler plate) in all members at the ridge, with dowels. Correct?",
        "Roof slope 8 degrees and diagonals at 50 degrees assumed.",
    ]),
    "timber_triangular_truss_2": (triangular_truss_2, "12.22", "Middle: bottom chord, diagonals and vertical with toothed plates", _D + "triangular_truss_details.png", [
        "Punched metal (toothed) plate on both faces; the teeth are only suggested by short lines. Correct?",
        "Member thickness 45 mm, chord height 100 mm assumed.",
    ]),
    "timber_triangular_truss_3": (triangular_truss_3, "12.22", "Right: upper chords and vertical, carpentry joint", _D + "triangular_truss_details.png", [
        "Continuous post with a wider head; the upper chords are cut against the narrower post below the head; one "
        "long bolt along x through chords and post. Please check the joint geometry and the bolt direction "
        "(the side view suggests the bolt is seen end-on).",
    ]),
    # ---- 12.25
    "timber_under_stressed_1": (under_stressed_1, "12.25", "Left: tension rod at the support", _D + "under_stressed_beam_details.png", [
        "End plate screwed into the beam end and column; inclined side plates on both beam faces with one bolt; "
        "the tension rod (eye plate) on a pin at the lower end. Correct?",
        "Unclear: the dashed lines at the beam end (screws?) and the element below the beam in the side view.",
    ]),
    "timber_under_stressed_2": (under_stressed_2, "12.25", "Middle: tension rods and strut, welded plates", _D + "under_stressed_beam_details.png", [
        "Steel shoe under the strut (bottom plate + two side plates, 2 x 2 bolts) with a welded lug below; two "
        "tension rods with welded forks on pins. Correct?",
        "Rod angle (10 degrees) and pin positions assumed.",
    ]),
    "timber_under_stressed_3": (under_stressed_3, "12.25", "Right: tension rods and diagonals with dowels", _D + "under_stressed_beam_details.png", [
        "Both diagonals on one slotted-in steel node with dowels (2 x 3 each); rods on pins below. Correct?",
        "In the drawing the two lugs look like separate plates; modelled as one node plate.",
    ]),
    # ---- 12.28
    "timber_rigid_frame_1": (rigid_frame_1, "12.28", "Left: column-floor support with angles and base plate", _D + "rigid_frame_details.png", [
        "Base plate with two angles welded to it (one on each column face), 3 bolts through angles and column, "
        "2 anchors through the horizontal angle legs. Correct?",
        "The tapered column of the drawing is modelled with a constant width.",
    ]),
    "timber_rigid_frame_2": (rigid_frame_2, "12.28", "Middle: moment joint double column - beam (dowels)", _D + "rigid_frame_details.png", [
        "Beam between the two column halves; a circle of 16 dowels (radius 16 cm). Correct?",
        "Dowel diameter 16 mm; beam modelled straight (tapered in the drawing).",
    ]),
    "timber_rigid_frame_3": (rigid_frame_3, "12.28", "Right: column-floor support with cast-in plates", _D + "rigid_frame_details.png", [
        "Four cast-in flat bars (two on each column face), one bolt each above the floor; the parts in the concrete "
        "(bolts / anchorage) are inside the floor and not visible. Correct?",
    ]),
    # ---- 12.31
    "timber_three_hinged_frame_1": (three_hinged_frame_1, "12.31", "Left: column foot on elastomeric bearing", _D + "three_hinged_frame_details.png", [
        "Inclined column (20 degrees) standing in a slot in the footing on an elastomeric pad, with a pin through "
        "the footing walls and the column. The left view of the drawing was unclear to me (plan or elevation?). "
        "Please check the whole concept.",
    ]),
    "timber_three_hinged_frame_2": (three_hinged_frame_2, "12.31", "Middle: double tie bar to double column", _D + "three_hinged_frame_details.png", [
        "Rafter end between the column halves on a filler; one flat tie bar on each outer face, on a pin through "
        "bars, column halves and rafter. Please check, especially how the tie bars are connected (in the drawing "
        "there is a ring/pin left of the column).",
    ]),
    "timber_three_hinged_frame_3": (three_hinged_frame_3, "12.31", "Right: column support with cast-in plates (screwed)", _D + "three_hinged_frame_details.png", [
        "Two cast-in plates on the column faces, screwed, plus one central bolt. Correct?",
        "In the drawing the column is slightly inclined with a sloped footing; modelled vertical.",
    ]),
    # ---- 12.34
    "timber_kinked_1": (kinked_1, "12.34", "Left: ridge with tension plates and shaped I-profile", _D + "three_hinged_kinked_details.png", [
        "A shaped (moulded) steel I-section between the rafter ends (web between the ends, flanges over top and "
        "bottom), and a tension plate on each face with 4 bolts. Correct?",
    ]),
    "timber_kinked_2": (kinked_2, "12.34", "Middle: ridge connection (bolted)", _D + "three_hinged_kinked_details.png", [
        "Steel shoe on each rafter end (end plate + side plates, 4 bolts), triangular lugs joined by one pin. Correct?",
    ]),
    "timber_kinked_3": (kinked_3, "12.34", "Right: support on footing with welded steel plate", _D + "three_hinged_kinked_details.png", [
        "Base plate with welded studs in the concrete (hidden) and two short side bars, one bolt through the "
        "column. Correct?",
        "The tapered column and the sloped side of the footing are not modelled.",
    ]),
    # ---- 12.37
    "timber_arch_1": (arch_1, "12.37", "Left: arch crown with steel connectors (dowels)", _D + "arch_details.png", [
        "Each arch end: slotted-in plate (4 dowels) welded to an end plate; a central bar between the end plates "
        "and a strap on each face with 2 bolts. Correct?",
        "The right view of this detail (with a separate small plate) was unclear.",
    ]),
    "timber_arch_2": (arch_2, "12.37", "Middle: support of arch (welded steel hinge)", _D + "arch_details.png", [
        "Arch shoe (end plate + slotted-in plate, 4 dowels) with a lug, pinned in a fork welded to a base plate on "
        "the footing (2 anchors). The crossed lines in the drawing are read as the lug and fork plates. Correct?",
        "The footing is drawn tilted with the arch (top face perpendicular to the arch).",
    ]),
    "timber_arch_3": (arch_3, "12.37", "Right: arch support", _D + "arch_details.png", [
        "Arch end directly on a base plate with two welded side plates and 3 bolts, 2 anchors. Unclear: the side "
        "view shows two bars (legs?) between arch and footing. Please check.",
    ]),
}
