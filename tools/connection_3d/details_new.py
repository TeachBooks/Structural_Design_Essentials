"""Connection details that only appear on the compact page (S05a_3d_connections_new.ipynb).

Same conventions as details.py (units cm, Z up, beams along +x, column flanges
perpendicular to x) and the same design rules:
- cap / base plates on columns 8 mm, 0.5 cm smaller than the profile, welded on the
  exposed flange ends and inside the profile along flanges, root radii and web;
- flush end plates 8 mm, 0.5 cm smaller than the beam; elongated plates 1.5 cm;
- stiffeners always welded; bolts close to the web with washers clear of root radii.
"""

import math

from details import (B, BEAM, BEAM_END, C, COL, COL_BOT, XF, XFI, bolts_x, bolts_z, cap_plate,
                     cap_plate_inset, col_stiffeners, end_plate, end_plate_inset, inner_profile_welds)
from iris3d import PROFILES, Mesh, Scene, angle_section, hexagon, i_section, rect

SEC = "IPE240"                  # secondary beam
S = PROFILES[SEC]
COL_TOP = 45.0                  # length of a continuous column shown above the beam top
UPPER = "HEB200"                # smaller column above a continuous beam
A = 0.4                         # fillet weld leg


# ----------------------------------------------------------------------------- helpers
def column_plate(s, prof, z, t=0.8, inset=0.5, a=A, column_below=True):
    """Plate on top of (column_below) or under a column, 0.5 cm smaller than the profile.

    z is the column end. Welds on the exposed flange ends along the plate edges and
    inside the profile (flanges, root radii, web)."""
    p = PROFILES[prof]
    xp, yp = p["h"] / 2 - inset, p["b"] / 2 - inset
    sd = 1 if column_below else -1                 # from the column into the plate
    z0, z1 = (z, z + t) if column_below else (z - t, z)
    s.box(-xp, xp, -yp, yp, z0, z1, "plate", "Plates")
    for sx in (1, -1):
        s.line_weld((sx * xp, -yp, z), (sx * xp, yp, z), (sx, 0, 0), (0, 0, sd), a)
    inner_profile_welds(s, prof, (0, 0, z), (0, -1, 0), (1, 0, 0), (0, 0, -sd), yp, a)


def web_stiffeners(s, x_bot, x_top, z_top, prof=BEAM, t=1.0, a=A, layer="Stiffeners"):
    """Pair of welded web stiffeners between the flanges of a beam along x (top flange at z_top).

    The stiffener runs from x_bot at the bottom flange to x_top at the top flange, so it
    can be slanted. Welded to the web and to both flanges."""
    p = PROFILES[prof]
    c = p["r"]
    zt, zb = z_top - p["tf"], z_top - p["h"] + p["tf"]
    k = (x_top - x_bot) / (zt - zb)               # shear: x shift per unit z
    origin = (x_bot - k * zb - t / 2, 0, 0)
    for sy in (1, -1):
        yw, ye = sy * p["tw"] / 2, sy * (p["b"] / 2 - 0.3)
        poly = [(yw, zb + c), (yw, zt - c), (sy * (p["tw"] / 2 + c), zt), (ye, zt), (ye, zb),
                (sy * (p["tw"] / 2 + c), zb)]
        s.extrude(poly, origin, (0, 1, 0), (k, 0, 1), (1, 0, 0), t, "plate", layer)
        for f in (1, -1):
            xb, xt = x_bot + f * t / 2, x_top + f * t / 2
            # to the web
            s.line_weld((xb + k * c, yw, zb + c), (xt - k * c, yw, zt - c), (f, 0, 0), (0, sy, 0), a)
            # to the flanges
            for x, z, dz in ((xt, zt, -1), (xb, zb, 1)):
                s.line_weld((x, sy * (p["tw"] / 2 + c), z), (x, ye, z), (f, 0, 0), (0, 0, dz), a)


def angle_cleats(s, x_face, x_bolt, zc, rows, web_t, grip_face, y_face_bolts, length, layer="Angles"):
    """Two angles either side of a beam web (web along x at y = 0), legs against a face at x_face.

    Bolts through angle-web-angle at x_bolt and through each angle leg into the face."""
    a, t, r = 9.0, 0.9, 1.1
    pts, corners = angle_section(a, a, t, r)
    for sign in (1, -1):
        s.extrude(pts, (x_face, sign * web_t / 2, zc - length / 2), (1, 0, 0), (0, sign, 0), (0, 0, 1),
                  length, "plate", layer, corners=corners)
    for z in rows:
        s.bolt((x_bolt, -(web_t / 2 + t), z), (0, 1, 0), web_t + 2 * t)
    bolts_x(s, x_face + t, t + grip_face, rows, ys=(-y_face_bolts, y_face_bolts))


def coped_beam(s, prof, x0, xc, x1, z_top, z_cope, layer="Secondary beam"):
    """Beam along x from x0 to x1 with its top flange and upper web cut back to xc."""
    p = PROFILES[prof]
    s.beam_x(prof, xc, x1, z_top, layer=layer)
    zb = z_top - p["h"]
    s.box(x0, xc, -p["b"] / 2, p["b"] / 2, zb, zb + p["tf"], "steel", layer)
    s.box(x0, xc, -p["tw"] / 2, p["tw"] / 2, zb + p["tf"], z_cope, "steel", layer)


def lock_bolt(s, x, y, z_top_flange, z_bot=-22.0, layer="Lock bolts"):
    """Anchor (lock) bolt M20 cast in concrete, washer + nut on the bottom flange."""
    s.cylinder((x, y, z_bot), (0, 0, 1), 1.0, z_top_flange + 0.4 + 1.6 + 0.6 - z_bot, "bolt", layer)
    s.cylinder((x, y, z_top_flange), (0, 0, 1), 1.85, 0.4, "nut", layer)
    s.prism(hexagon(3.0, x, y), "z", z_top_flange + 0.4, z_top_flange + 2.0, "nut", layer, outline=False)


def frustum(s, x0, x1, y0, y1, z0, z1, taper, mat, layer):
    """Block whose bottom (z0) is `taper` larger all round than its top (z1)."""
    top2 = rect(x0, x1, y0, y1)
    bot2 = rect(x0 - taper, x1 + taper, y0 - taper, y1 + taper)
    top3 = [(u, v, z1) for u, v in top2]
    bot3 = [(u, v, z0) for u, v in bot2]
    m = Mesh()
    m.polygon(top3, top2)
    m.polygon(bot3, bot2)
    m.quad_strip(bot3, top3)
    s.add_mesh(m, mat, layer)
    s.add_line(top3, layer, closed=True)
    s.add_line(bot3, layer, closed=True)
    for a, b in zip(bot3, top3):
        s.add_line([a, b], layer)


def anchor_bolt(s, x, y, pl_t, bot, layer="Anchor bolts"):
    """Anchor bolt as in details.column_base: nut + washer on the plate, anchor plate below."""
    s.cylinder((x, y, bot), (0, 0, 1), 1.0, pl_t + 0.4 + 1.6 + 1.2 - bot, "bolt", layer)
    s.cylinder((x, y, pl_t), (0, 0, 1), 1.85, 0.4, "nut", layer)
    s.prism(hexagon(3.0, x, y), "z", pl_t + 0.4, pl_t + 2.0, "nut", layer, outline=False)
    s.box(x - 3.5, x + 3.5, y - 3.5, y + 3.5, bot + 1.6, bot + 2.6, "nut", layer)
    s.prism(hexagon(3.0, x, y), "z", bot + 0.2, bot + 1.6, "nut", layer, outline=False)


def base_and_foundation(s, pl_x, pl_y, anchors, pl_t=2.5, grout_t=3.0):
    s.box(-pl_x / 2, pl_x / 2, -pl_y / 2, pl_y / 2, 0, pl_t, "plate", "Base plate")
    bot = -grout_t - 30.0
    for x, y in anchors:
        anchor_bolt(s, x, y, pl_t, bot)
    frustum(s, -pl_x / 2 - 0.5, pl_x / 2 + 0.5, -pl_y / 2 - 0.5, pl_y / 2 + 0.5, -grout_t, 0.0, 4.0,
            "grout", "Grout")
    hx, hy = pl_x / 2 + 18, pl_y / 2 + 18
    s.box(-hx, hx, -hy, hy, -grout_t - 40, -grout_t, "concrete", "Foundation")
    s.view_dir = (0.55, -0.78, 0.47)
    s.pivot = (0.0, 0.0, 2.0)


# ----------------------------------------------------------------------------- Cont. column-beam
def cb1():
    """Continuous column, beam connected to the flange with two bolted angles."""
    s = Scene("Cont. column-beam 1: bolted angles")
    bt = 0.0
    s.column(COL, COL_BOT, COL_TOP)
    s.beam_x(BEAM, XF + 1.0, BEAM_END, bt)
    zc = bt - B["h"] / 2
    angle_cleats(s, XF, XF + 5.5, zc, [zc - 7, zc, zc + 7], B["tw"], C["tf"], B["tw"] / 2 + 5.5, 20.0)
    s.view_dir = (0.75, -0.65, 0.45)
    return s


def cb2():
    """Continuous column, beam with welded 8 mm end plate bolted to the flange (four rows)."""
    s = Scene("Cont. column-beam 2: welded endplate, bolted to column")
    bt, t = 0.0, 0.8
    s.column(COL, COL_BOT, COL_TOP)
    end_plate_inset(s, XF, bt, t)
    s.beam_x(BEAM, XF + t, BEAM_END, bt)
    bolts_x(s, XF + t, t + C["tf"], [bt - 6, bt - 12, bt - 18, bt - 24], ys=(-4.5, 4.5))
    return s


def cb3():
    """Elongated end plate (extending above the beam), bolted to a column with welded stiffeners."""
    s = Scene("Cont. column-beam 3: elongated endplate, stiffened column")
    bt = 0.0
    s.column(COL, COL_BOT, COL_TOP)
    end_plate(s, XF, bt + 10.0, bt - B["h"] - 2.0, beam_top=bt)
    s.beam_x(BEAM, XF + 1.5, BEAM_END, bt)
    bolts_x(s, XF + 1.5, 1.5 + C["tf"], [bt + 5, bt - 5.5, bt - 15, bt - 24.5])
    col_stiffeners(s, bt - B["tf"] / 2, welded=True)
    col_stiffeners(s, bt - B["h"] + B["tf"] / 2, welded=True)
    return s


# ----------------------------------------------------------------------------- Beam-beam
P_TW = B["tw"]                                  # primary beam (IPE300 along y) web
X_COPE = B["b"] / 2 + 1.0                       # secondary flanges cut back to clear the primary
Z_COPE = -(B["tf"] + B["r"] + 0.5)              # top of the coped secondary web


def primary(s):
    s.beam_y(BEAM, -45.0, 45.0, 0.0, layer="Primary beam")


def bb1():
    """Secondary beam (coped) to the primary web with two bolted angles."""
    s = Scene("Beam-beam 1: bolted angles")
    primary(s)
    coped_beam(s, SEC, P_TW / 2 + 1.0, X_COPE, 90.0, 0.0, Z_COPE)
    zc = -S["h"] / 2
    angle_cleats(s, P_TW / 2, P_TW / 2 + 5.5, zc, [zc - 3.5, zc + 3.5], S["tw"], P_TW, S["tw"] / 2 + 5.5, 14.0)
    s.view_dir = (0.7, -0.6, 0.5)
    return s


def bb2():
    """Secondary beam (coped) with a welded 8 mm end plate, bolted to the primary web."""
    s = Scene("Beam-beam 2: welded endplate, bolted to other element")
    primary(s)
    t, yp = 0.8, S["b"] / 2 - 0.5
    x0 = P_TW / 2
    xb = x0 + t
    zb = -S["h"]
    zp_bot = zb + 0.5
    s.box(x0, xb, -yp, yp, zp_bot, Z_COPE, "plate", "Plates")
    coped_beam(s, SEC, xb, X_COPE, 90.0, 0.0, Z_COPE)
    zf = zb + S["tf"]
    for sy in (1, -1):
        # web to plate, both sides; top of the bottom flange to plate
        s.line_weld((xb, sy * S["tw"] / 2, zf + S["r"]), (xb, sy * S["tw"] / 2, Z_COPE), (1, 0, 0), (0, sy, 0), A)
        s.line_weld((xb, sy * (S["tw"] / 2 + S["r"]), zf), (xb, sy * yp, zf), (1, 0, 0), (0, 0, 1), A)
    bolts_x(s, xb, t + P_TW, [-8.0, -18.0], ys=(-4.0, 4.0))
    s.view_dir = (0.7, -0.6, 0.5)
    return s


SLOPE = math.radians(12.0)


def ridge(haunch):
    """Two sloping beams with elongated end plates bolted together at the ridge.

    The beams are cut plumb; with haunch=True a welded haunch is added under each beam."""
    s = Scene("Beam-beam 3: elongated endplates at the ridge" + (" with haunch" if haunch else ""))
    ca, sa = math.cos(SLOPE), math.sin(SLOPE)
    h_v = B["h"] / ca                                # vertical depth of the sloping beam
    tp = 1.5
    pts, corners = i_section(B)
    dh, lh = 20.0, 70.0                              # haunch depth at the plate, horizontal length

    def z_top(x):
        return -abs(x) * sa / ca

    def z_bot(x):
        return z_top(x) - h_v

    zb_plate = (z_bot(tp) - dh - 3.0) if haunch else (z_bot(tp) - 6.0)
    for side in (1, -1):
        s.box(min(0, side * tp), max(0, side * tp), -8.0, 8.0, zb_plate, 6.0, "plate", "Plates")
        x0 = side * tp
        origin = (x0, 0, z_top(tp) - h_v / 2)
        u, v, w = (0, 1, 0), (0, 0, 1 / ca), (side * ca, 0, -sa)
        s.extrude(pts, origin, u, v, w, 90.0, "steel", "Beams", corners=corners)
        s.contour_weld(pts, origin, u, v, w, 0.5)
        if haunch:
            xa, x1 = tp, tp + lh
            pa, pb = (side * xa, 0, z_bot(xa)), (side * x1, 0, z_bot(x1))
            pc = (side * xa, 0, z_bot(xa) - dh)
            # web: triangle in the plane y = 0
            web2 = [(pa[2], pa[0]), (pb[2], pb[0]), (pc[2], pc[0])]
            s.prism(web2, "y", -B["tw"] / 2, B["tw"] / 2, "plate", "Haunch")
            # flange along pc-pb, on the outside (below)
            dx, dz = pb[0] - pc[0], pb[2] - pc[2]
            ln = math.hypot(dx, dz)
            d = (dx / ln, 0, dz / ln)
            n = (d[2], 0, -d[0])
            if n[2] > 0:
                n = (-n[0], 0, -n[2])
            s.extrude(rect(-B["b"] / 2, B["b"] / 2, 0, B["tf"]), pc, (0, 1, 0), n, d, ln, "plate", "Haunch")
            inward = (-n[0], 0, -n[2])
            for sy in (1, -1):
                yw = sy * B["tw"] / 2
                s.line_weld((pa[0], yw, pa[2]), (pb[0], yw, pb[2]), (0, sy, 0), (0, 0, -1), A)
                s.line_weld((pc[0], yw, pc[2]), (pb[0], yw, pb[2]), (0, sy, 0), inward, A)
                s.line_weld((pc[0], yw, pc[2]), (pa[0], yw, pa[2]), (0, sy, 0), (side, 0, 0), A)
    rows = [3.0, -6.0, -15.0, -24.0] + ([-35.0, -43.0] if haunch else [z_bot(tp) - 3.0])
    bolts_x(s, tp, 2 * tp, rows, ys=(-4.5, 4.5))
    s.view_dir = (0.45, -0.85, 0.3)
    s.pivot = (0.0, 0.0, -16.0)
    return s


def bb3a():
    return ridge(False)


def bb3b():
    return ridge(True)


# ----------------------------------------------------------------------------- Beam-wall
def wall(s, x0=-16.0, x1=24.0):
    s.box(x0, x1, -30.0, 30.0, -45.0, 0.0, "concrete", "Wall")


def bw1():
    """Beam end on an elastomer bearing pad on a concrete wall, two lock bolts."""
    s = Scene("Beam-wall 1: support on elastomer with lock bolts")
    wall(s)
    pad = 1.5
    s.box(-13.0, 0.0, -7.0, 7.0, 0.0, pad, "elastomer", "Elastomer")
    s.beam_x(BEAM, -110.0, 0.0, pad + B["h"])
    for y in (-4.5, 4.5):
        lock_bolt(s, -6.5, y, pad + B["tf"])
    s.view_dir = (0.55, -0.75, 0.45)
    s.pivot = (-6.5, 0.0, 6.0)
    return s


def bw2():
    """Beam end on a tapered elastomer bearing, lock bolts near the beam end."""
    s = Scene("Beam-wall 2: support on tapered elastomer with lock bolts")
    wall(s, -12.0, 24.0)
    pad = 2.0
    frustum(s, -10.0, 1.5, -6.5, 6.5, 0.0, pad, 2.0, "elastomer", "Elastomer")
    s.beam_x(BEAM, -110.0, 0.0, pad + B["h"])
    for y in (-4.5, 4.5):
        lock_bolt(s, -4.0, y, pad + B["tf"])
    s.view_dir = (0.55, -0.75, 0.45)
    s.pivot = (-4.0, 0.0, 6.0)
    return s


def bw3():
    """Beam on a steel axle (rocker) between a sole plate and an anchored base plate."""
    s = Scene("Beam-wall 3: support with steel axle")
    xs = -10.0                                   # support line
    grout_t, pl_t, r_ax = 3.0, 2.0, 2.0
    s.box(xs - 30, xs + 30, -30.0, 30.0, -grout_t - 40.0, -grout_t, "concrete", "Wall")
    frustum(s, xs - 15.5, xs + 15.5, -15.5, 15.5, -grout_t, 0.0, 3.0, "grout", "Grout")
    s.box(xs - 15, xs + 15, -15.0, 15.0, 0.0, pl_t, "plate", "Base plate")
    for x in (xs - 11, xs + 11):
        for y in (-11.0, 11.0):
            anchor_bolt(s, x, y, pl_t, -grout_t - 25.0)
    # axle along y, held by two keeper bars on the base plate
    s.cylinder((xs, -9.0, pl_t + r_ax), (0, 1, 0), r_ax, 18.0, "bolt", "Axle")
    for x in (xs - r_ax - 1.2, xs + r_ax + 0.2):
        s.box(x, x + 1.0, -9.0, 9.0, pl_t, pl_t + 1.6, "plate", "Axle")
    # sole plate welded under the beam
    z_sole = pl_t + 2 * r_ax
    sole_t = 2.0
    s.box(xs - 10, xs + 10, -8.5, 8.5, z_sole, z_sole + sole_t, "plate", "Sole plate")
    bb = z_sole + sole_t
    for sy in (1, -1):
        s.line_weld((xs - 10, sy * B["b"] / 2, bb), (xs + 10, sy * B["b"] / 2, bb), (0, sy, 0), (0, 0, 1), A)
    s.beam_x(BEAM, -110.0, xs + 14.0, bb + B["h"])
    # bearing stiffeners above the support
    web_stiffeners(s, xs, xs, bb + B["h"])
    s.view_dir = (0.55, -0.75, 0.4)
    s.pivot = (xs, 0.0, 8.0)
    return s


# ----------------------------------------------------------------------------- Center-column-beam
def beam_on_column(s, plate_t=0.8):
    """Continuous beam along x on top of the column plate; returns the beam bottom level."""
    bb = plate_t
    s.beam_x(BEAM, -BEAM_END, BEAM_END, bb + B["h"])
    return bb


FOUR = [(x, y) for x in (-4.5, 4.5) for y in (-4.5, 4.5)]


def ccb1():
    """Column under a continuous beam: 8 mm cap plate (inset), four bolts."""
    s = Scene("Center-column-beam 1: welded endplate with four bolts")
    s.column(COL, COL_BOT, 0.0)
    cap_plate_inset(s, 0.0, 0.8)
    bb = beam_on_column(s)
    bolts_z(s, bb + B["tf"], B["tf"] + 0.8, FOUR)
    s.view_dir = (0.55, -0.75, 0.4)
    s.pivot = (0.0, 0.0, 0.0)
    return s


def ccb2():
    """As ccb1, with welded web stiffeners in the beam above the column flanges."""
    s = Scene("Center-column-beam 2: welded endplate with four bolts and web stiffeners")
    s.column(COL, COL_BOT, 0.0)
    cap_plate_inset(s, 0.0, 0.8)
    bb = beam_on_column(s)
    bolts_z(s, bb + B["tf"], B["tf"] + 0.8, FOUR)
    for x in (-(XF - C["tf"] / 2), XF - C["tf"] / 2):
        web_stiffeners(s, x, x, bb + B["h"])
    s.view_dir = (0.55, -0.75, 0.4)
    s.pivot = (0.0, 0.0, 0.0)
    return s


def ccb3():
    """Elongated end plate (beyond the column flanges), eight bolts, welded beam web stiffeners."""
    s = Scene("Center-column-beam 3: elongated endplate with eight bolts and web stiffeners")
    s.column(COL, COL_BOT, 0.0)
    t = 1.5
    s.box(-XF - 9.0, XF + 9.0, -C["b"] / 2 + 0.5, C["b"] / 2 - 0.5, 0.0, t, "plate", "Plates")
    s.profile_weld(COL, (0, 0, 0.0), (0, -1, 0), (1, 0, 0), (0, 0, -1))
    bb = beam_on_column(s, t)
    pts = [(x, y) for x in (-6.5, 6.5, -(XF + 4.5), XF + 4.5) for y in (-4.5, 4.5)]
    bolts_z(s, bb + B["tf"], B["tf"] + t, pts)
    for x in (-(XF - C["tf"] / 2), XF - C["tf"] / 2):
        web_stiffeners(s, x, x, bb + B["h"])
    s.view_dir = (0.55, -0.75, 0.4)
    s.pivot = (0.0, 0.0, 0.0)
    return s


def ccb4():
    """Column under a continuous beam: 8 mm end plate slightly larger than the column, four bolts."""
    s = Scene("Center-column-beam 4: welded endplate with four bolts")
    s.column(COL, COL_BOT, 0.0)
    cap_plate(s, 0.0, t=0.8, overhang=1.0)
    bb = beam_on_column(s)
    bolts_z(s, bb + B["tf"], B["tf"] + 0.8, FOUR)
    s.view_dir = (0.55, -0.75, 0.4)
    s.pivot = (0.0, 0.0, 0.0)
    return s


def column_through(s, upper, slanted):
    """Continuous beam between a lower HEA240 column and an upper column, with plates,
    bolts and welded beam web stiffeners linking the column flanges."""
    t = 0.8
    s.column(COL, COL_BOT, 0.0)
    cap_plate_inset(s, 0.0, t)
    bb = beam_on_column(s, t)
    bt = bb + B["h"]
    bolts_z(s, bb + B["tf"], B["tf"] + t, FOUR)
    up = PROFILES[upper]
    z_up = bt + t
    s.column(upper, z_up, z_up + 45.0)
    column_plate(s, upper, z_up, t, column_below=False)
    bolts_z(s, z_up, t + B["tf"], FOUR)
    x_low = XF - C["tf"] / 2
    x_up = up["h"] / 2 - up["tf"] / 2
    for sx in (1, -1):
        web_stiffeners(s, sx * x_low, sx * (x_up if slanted else x_low), bt)
    s.view_dir = (0.55, -0.75, 0.35)
    s.pivot = (0.0, 0.0, bb + B["h"] / 2)
    return s


def ccb5():
    s = Scene("Center-column-beam 5: endplates with slanted web stiffeners")
    return column_through(s, UPPER, slanted=True)


def ccb6():
    s = Scene("Center-column-beam 6: endplates with web stiffeners")
    return column_through(s, COL, slanted=False)


# ----------------------------------------------------------------------------- Column support
def cs2():
    """HEB 200 on a base plate with four anchor bolts inside the column section."""
    s = Scene("Column support 2: welded base plate with four anchor bolts")
    pl_t = 2.5
    s.member("HEB200", (0, 0, pl_t), (0, -1, 0), (1, 0, 0), (0, 0, 1), 60.0, "Column")
    s.profile_weld("HEB200", (0, 0, pl_t), (0, -1, 0), (1, 0, 0), (0, 0, 1), a=0.7)
    base_and_foundation(s, 30.0, 26.0, [(x, y) for x in (-4.5, 4.5) for y in (-5.5, 5.5)], pl_t)
    return s


def cs3():
    """HEB 200 on a larger base plate with four anchor bolts outside the column section."""
    s = Scene("Column support 3: anchor bolts outside the column section")
    pl_t = 2.5
    s.member("HEB200", (0, 0, pl_t), (0, -1, 0), (1, 0, 0), (0, 0, 1), 60.0, "Column")
    s.profile_weld("HEB200", (0, 0, pl_t), (0, -1, 0), (1, 0, 0), (0, 0, 1), a=0.7)
    base_and_foundation(s, 44.0, 40.0, [(x, y) for x in (-17.0, 17.0) for y in (-15.0, 15.0)], pl_t)
    return s


def cs3_shs():
    """Square hollow section 200x200x10 on a base plate with four anchor bolts outside it."""
    s = Scene("Column support 3: hollow section, anchor bolts outside")
    pl_t, a, t = 2.5, 10.0, 1.0
    for x0, x1, y0, y1 in ((-a, a, -a, -a + t), (-a, a, a - t, a), (-a, -a + t, -a + t, a - t),
                           (a - t, a, -a + t, a - t)):
        s.box(x0, x1, y0, y1, pl_t, pl_t + 60.0, "steel", "Column")
    s.contour_weld(rect(-a, a, -a, a), (0, 0, pl_t), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.7)
    base_and_foundation(s, 40.0, 40.0, [(x, y) for x in (-15.0, 15.0) for y in (-15.0, 15.0)], pl_t)
    return s


# ----------------------------------------------------------------------------- registry
# id: (function, group, caption, S04 drawing) -- shown on the compact page only
NEW_DETAILS = {
    "cont_column_beam_1": (cb1, "Cont. column-beam", "Connection with bolted angles.", "Column_Beam1.jpg"),
    "cont_column_beam_2": (cb2, "Cont. column-beam", "Connection with welded endplate, bolted to column.",
                           "Column_Beam2.jpg"),
    "cont_column_beam_3": (cb3, "Cont. column-beam",
                           "Connection with elongated endplate, bolted to stiffened column.", "Column_Beam3.jpg"),
    "beam_beam_1": (bb1, "Beam-beam", "Connection with bolted angles.", "Beam_Beam1.jpg"),
    "beam_beam_2": (bb2, "Beam-beam", "Connection with welded endplate, bolted to other element.",
                    "Beam_Beam2.jpg"),
    "beam_beam_3": (bb3a, "Beam-beam", "Connection with elongated endplate, bolted to other element.",
                    "Beam_Beam3.jpg"),
    "beam_beam_3_haunch": (bb3b, "Beam-beam",
                           "Connection with elongated endplate, bolted to other element, with haunch.",
                           "Beam_Beam3.jpg"),
    "beam_wall_1": (bw1, "Beam-wall", "Support on elastomer, with lock bolt.", "Beam_Wall1.jpg"),
    "beam_wall_2": (bw2, "Beam-wall", "Support on (tapered) elastomer, with lock bolt.", "Beam_Wall2.jpg"),
    "beam_wall_3": (bw3, "Beam-wall", "Support with steel axle.", "Beam_Wall3.jpg"),
    "center_column_beam_1": (ccb1, "Center-column-beam", "Welded endplate with four bolts.",
                             "Center_Column_Beam1.jpg"),
    "center_column_beam_2": (ccb2, "Center-column-beam",
                             "Welded endplate with four bolts with welded stiffeners on beam web.",
                             "Center_Column_Beam2.jpg"),
    "center_column_beam_3": (ccb3, "Center-column-beam",
                             "Elongated welded endplate with eight bolts, welded stiffeners on beam web.",
                             "Center_Column_Beam3.jpg"),
    "center_column_beam_4": (ccb4, "Center-column-beam", "Welded endplate with four bolts (plate larger than column).",
                             "Center_Column_Beam4.jpg"),
    "center_column_beam_5": (ccb5, "Center-column-beam", "Welded endplate with welded (slanted) stiffeners on beam web.",
                             "Center_Column_Beam5.jpg"),
    "center_column_beam_6": (ccb6, "Center-column-beam", "Welded endplate with welded stiffeners on beam web.",
                             "Center_Column_Beam6.jpg"),
    "column_support_2": (cs2, "Column-support", "Column support with welded endplate and four bolts.",
                         "Column_Support2.jpg"),
    "column_support_3": (cs3, "Column-support",
                         "Column support with bolts outside column section for extra stiffness.",
                         "Column_Support3.jpg"),
    "column_support_3_shs": (cs3_shs, "Column-support",
                             "Column support with bolts outside column section, hollow section column.",
                             "Column_Support3.jpg"),
}
