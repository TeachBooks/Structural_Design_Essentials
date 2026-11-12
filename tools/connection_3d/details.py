"""Connection details for the 3D gallery (book/design/steel/S05_3d_connections.ipynb).

Each detail is a function returning an iris3d.Scene. Register it in DETAILS with
the S04 drawing it is based on. Units: cm, Z up; beams run along +x, columns
have their flanges perpendicular to x.
"""

from iris3d import (PROFILES, Mesh, Scene, add, angle_section, chamfered_rect, hexagon, i_section, mul,
                    offset_polygon, rect)

COL, BEAM = "HEA240", "IPE300"
C, B = PROFILES[COL], PROFILES[BEAM]
XF = C["h"] / 2                 # outer face of the column flange the beam connects to
XFI = XF - C["tf"]              # inner face of that flange
COL_BOT = -95.0                 # column length shown below the top / connection
BEAM_END = 95.0                 # beam length shown


# ----------------------------------------------------------------------------- helpers
def cap_plate(s, z, t=1.5, overhang=1.0):
    """Cap plate on top of the column at level z (column top), welded all round."""
    s.box(-XF - overhang, XF + overhang, -C["b"] / 2 - overhang, C["b"] / 2 + overhang, z, z + t,
          "plate", "Plates")
    s.profile_weld(COL, (0, 0, z), (0, -1, 0), (1, 0, 0), (0, 0, -1))


def end_plate(s, x0, z_top, z_bot, t=1.5, width=16.0, beam_top=None):
    """Plate in the y-z plane from x0 to x0 + t, with the beam welded to its +x face."""
    s.box(x0, x0 + t, -width / 2, width / 2, z_bot, z_top, "plate", "Plates")
    bt = z_top if beam_top is None else beam_top
    s.profile_weld(BEAM, (x0 + t, 0, bt - B["h"] / 2), (0, 1, 0), (0, 0, 1), (1, 0, 0))


def inner_profile_welds(s, prof, origin, u, v, w, umax, a=0.4, layer="Welds"):
    """Fillet welds inside an I/H profile end that meets a plate.

    One continuous weld per side of the web, following the inner flange face, the root
    radius, the web, the other root radius and the other inner flange face, ending where
    the plate ends (|u| = umax). origin/u/v: section frame on the plate surface
    (u = flange width, v = depth); w points into the member."""
    p = PROFILES[prof]
    hb, hh, tf = p["b"] / 2, p["h"] / 2, p["tf"]
    pts, _ = i_section(p)
    off = offset_polygon(pts, a)            # outwards = into the space between the flanges

    def idx(q):
        return min(range(len(pts)), key=lambda i: (pts[i][0] - q[0]) ** 2 + (pts[i][1] - q[1]) ** 2)

    def P(q, t):
        return add(origin, mul(u, q[0]), mul(v, q[1]), mul(w, t))

    for sg, start, end in ((1, (hb, -hh + tf), (hb, hh - tf)), (-1, (-hb, hh - tf), (-hb, -hh + tf))):
        i0, i1 = idx(start), idx(end)
        root = list(pts[i0:i1 + 1])
        toe = list(off[i0:i1 + 1])
        # end the weld at the plate edge, on the inner flange faces
        root[0], root[-1] = (sg * umax, root[0][1]), (sg * umax, root[-1][1])
        toe[0], toe[-1] = (sg * umax, off[i0 + 1][1]), (sg * umax, off[i1 - 1][1])
        m = Mesh()
        m.quad_strip([P(q, 0.01) for q in toe], [P(q, a) for q in root], closed=False)
        s.add_mesh(m, "weld", layer)


def cap_plate_inset(s, z, t=0.8, inset=0.5, a=0.4):
    """Cap plate slightly smaller than the column outline (as in Fig. End_Column_Beam1).

    Welded above the plate (on the flange tops, along the plate edges) and below it
    (inside the profile, following flanges, root radii and web)."""
    xp, yp = XF - inset, C["b"] / 2 - inset
    s.box(-xp, xp, -yp, yp, z, z + t, "plate", "Plates")
    for sx in (1, -1):
        # above: on the flange top, against the plate edge
        s.line_weld((sx * xp, -yp, z), (sx * xp, yp, z), (sx, 0, 0), (0, 0, 1), a)
    # below: inside the profile (same section frame as profile_weld for the column)
    inner_profile_welds(s, COL, (0, 0, z), (0, -1, 0), (1, 0, 0), (0, 0, -1), yp, a)


def end_plate_inset(s, x0, beam_top, t=0.8, inset=0.5, a=0.4):
    """End plate slightly smaller than the beam outline, beam welded to its +x face.

    Welded on the exposed flange ends beyond the plate edges (outside) and inside the
    profile, following flanges, root radii and web."""
    xb = x0 + t                                  # beam end / plate face
    yp = B["b"] / 2 - inset
    zt, zb = beam_top - inset, beam_top - B["h"] + inset
    s.box(x0, xb, -yp, yp, zb, zt, "plate", "Plates")
    for sz, ze in ((1, zt), (-1, zb)):
        # outside: on the beam flange end, against the plate edge
        s.line_weld((xb, -yp, ze), (xb, yp, ze), (0, 0, sz), (-1, 0, 0), a)
    inner_profile_welds(s, BEAM, (xb, 0, beam_top - B["h"] / 2), (0, 1, 0), (0, 0, 1), (1, 0, 0), yp, a)


def col_stiffeners(s, z, t=1.0, welded=False, a=0.4):
    """Pair of column web stiffeners (between the flanges) centred at level z.

    welded=True adds fillet welds above and below each stiffener, to the web and to both
    inner flange faces."""
    c = C["r"]
    for sign in (1, -1):
        y0, y1 = C["tw"] / 2, C["b"] / 2 - 0.5
        poly = chamfered_rect(-XFI, XFI, y0, y1, c, c)
        if sign < 0:
            poly = [(u, -v) for u, v in poly]
        s.prism(poly, "z", z - t / 2, z + t / 2, "plate", "Stiffeners")
        if welded:
            for sz in (1, -1):
                zf = z + sz * t / 2
                # to the web, between the chamfers
                s.line_weld((-XFI + c, sign * y0, zf), (XFI - c, sign * y0, zf), (0, sign, 0), (0, 0, sz), a)
                # to the inner flange faces
                for sx in (1, -1):
                    s.line_weld((sx * XFI, sign * (y0 + c), zf), (sx * XFI, sign * y1, zf), (-sx, 0, 0),
                                (0, 0, sz), a)


def beam_stiffeners(s, x, z_top, t=1.0):
    """Pair of beam web stiffeners (between the beam flanges) centred at x."""
    c = B["r"]
    zt, zb = z_top - B["tf"], z_top - B["h"] + B["tf"]
    for sign in (1, -1):
        # 2D coordinates for axis 'x' are (y, z)
        poly = [(sign * B["tw"] / 2, zb + c), (sign * B["tw"] / 2, zt - c), (sign * (B["tw"] / 2 + c), zt),
                (sign * (B["b"] / 2 - 0.3), zt), (sign * (B["b"] / 2 - 0.3), zb), (sign * (B["tw"] / 2 + c), zb)]
        s.prism(poly, "x", x - t / 2, x + t / 2, "plate", "Stiffeners")


def bolts_x(s, x_head, grip, rows, ys=(-5.5, 5.5), size="M20"):
    """Horizontal bolts pointing in -x (head at x_head on the beam side)."""
    for z in rows:
        for y in ys:
            s.bolt((x_head, y, z), (-1, 0, 0), grip, size)


def bolts_z(s, z_head, grip, points, size="M20", down=True):
    for x, y in points:
        s.bolt((x, y, z_head), (0, 0, -1) if down else (0, 0, 1), grip, size)


# ----------------------------------------------------------------------------- End column-beam
def ecb1():
    """Welded endplate with two bolts: 8 mm cap plate and end plate slightly smaller than the
    profiles, welded above and below (Fig. End_Column_Beam1)."""
    s = Scene("End column-beam 1: welded endplate with two bolts")
    top, t = 0.0, 0.8
    s.column(COL, COL_BOT, top)
    cap_plate_inset(s, top, t)
    bt = top + t
    end_plate_inset(s, XF, bt, t)
    s.beam_x(BEAM, XF + t, BEAM_END, bt)
    bolts_x(s, XF + t, t + C["tf"], [bt - B["h"] / 2], ys=(-4.5, 4.5))  # close to the beam web, washers clear of the column root radii
    return s


def ecb2():
    """Connection with bolted angles: 8 mm cap plate slightly smaller than the column,
    welded above and below (Fig. End_Column_Beam2). No end plate on the beam."""
    s = Scene("End column-beam 2: bolted angles")
    top = 0.0
    s.column(COL, COL_BOT, top)
    t_cap = 0.8
    cap_plate_inset(s, top, t_cap)
    bt = top + t_cap
    gap = 1.0
    s.beam_x(BEAM, XF + gap, BEAM_END, bt)
    zc = bt - B["h"] / 2
    a, t, r, length = 9.0, 0.9, 1.1, 20.0
    pts, corners = angle_section(a, a, t, r)
    for sign in (1, -1):
        s.extrude(pts, (XF, sign * B["tw"] / 2, zc - length / 2), (1, 0, 0), (0, sign, 0), (0, 0, 1),
                  length, "plate", "Angles", corners=corners)
    rows = [zc - 7, zc, zc + 7]
    for z in rows:   # through angle - beam web - angle
        s.bolt((XF + 5.5, -(B["tw"] / 2 + t), z), (0, 1, 0), B["tw"] + 2 * t)
    bolts_x(s, XF + t, t + C["tf"], rows, ys=(-(B["tw"] / 2 + 5.5), B["tw"] / 2 + 5.5))
    s.view_dir = (0.75, -0.65, 0.45)
    return s


def ecb3():
    """Welded elongated endplate with top plate and stiffeners for extra stiffness: 8 mm cap
    plate slightly smaller than the column, welded stiffeners, top plate as thick as the
    beam flange (Fig. End_Column_Beam3)."""
    s = Scene("End column-beam 3: elongated endplate, top plate and stiffeners")
    top = 0.0
    t_cap = 0.8
    s.column(COL, COL_BOT, top - t_cap)
    cap_plate_inset(s, top - t_cap, t_cap)     # cap plate flush with the beam top
    bt = top
    z_bot = bt - B["h"] - 8.0
    end_plate(s, XF, bt, z_bot, beam_top=bt)
    s.beam_x(BEAM, XF + 1.5, BEAM_END, bt)
    bolts_x(s, XF + 1.5, 1.5 + C["tf"], [bt - 6, bt - 14, bt - B["h"] + 6, bt - B["h"] - 4])
    col_stiffeners(s, bt - B["h"] + B["tf"] / 2, welded=True)
    # tension (top) plate over column and beam, as thick as the beam flange
    tp = B["tf"]
    s.box(-XF, XF + 32, -B["b"] / 2, B["b"] / 2, bt, bt + tp, "plate", "Plates")
    pts = [(x, y) for x in (-6.0, 5.0, XF + 10, XF + 22) for y in (-4.5, 4.5)]
    bolts_z(s, bt + tp, tp + t_cap, pts[:4])        # into the column cap plate
    bolts_z(s, bt + tp, tp + B["tf"], pts[4:])      # into the beam top flange
    return s


def ecb3_original():
    """Previous version of ecb3, kept for comparison."""
    s = Scene("End column-beam 3 (previous version): elongated endplate, top plate and stiffeners")
    top = 0.0
    s.column(COL, COL_BOT, top - 1.5)
    cap_plate(s, top - 1.5)
    bt = top
    z_bot = bt - B["h"] - 8.0
    end_plate(s, XF, bt, z_bot, beam_top=bt)
    s.beam_x(BEAM, XF + 1.5, BEAM_END, bt)
    bolts_x(s, XF + 1.5, 1.5 + C["tf"], [bt - 6, bt - 14, bt - B["h"] + 6, bt - B["h"] - 4])
    col_stiffeners(s, bt - B["h"] + B["tf"] / 2)
    # tension (top) plate over column and beam
    tp = 1.5
    s.box(-XF, XF + 32, -B["b"] / 2, B["b"] / 2, bt, bt + tp, "plate", "Plates")
    pts = [(x, y) for x in (-6.0, 5.0, XF + 10, XF + 22) for y in (-4.5, 4.5)]
    bolts_z(s, bt + tp, tp + 1.5, pts[:4])          # into the column cap plate
    bolts_z(s, bt + tp, tp + B["tf"], pts[4:])      # into the beam top flange
    return s


def ecb4():
    """Beam on top of the column, welded endplate, two bolts."""
    s = Scene("End column-beam 4: beam on column, welded endplate with two bolts")
    top = 0.0
    s.column(COL, COL_BOT, top)
    cap_plate(s, top)
    bb = top + 1.5
    x0 = -XF - 1.0
    s.box(x0 - 1.5, x0, -8, 8, bb, bb + B["h"], "plate", "Plates")
    s.profile_weld(BEAM, (x0, 0, bb + B["h"] / 2), (0, 1, 0), (0, 0, 1), (1, 0, 0))
    s.beam_x(BEAM, x0, BEAM_END, bb + B["h"])
    bolts_z(s, bb + B["tf"], B["tf"] + 1.5, [(0, -4.5), (0, 4.5)])
    s.view_dir = (0.5, -0.85, 0.35)
    return s


def ecb5():
    """Welded endplate with six bolts."""
    s = Scene("End column-beam 5: welded endplate with six bolts")
    top = 0.0
    s.column(COL, COL_BOT, top)
    cap_plate(s, top)
    bt = top + 1.5
    end_plate(s, XF, bt, bt - B["h"])
    s.beam_x(BEAM, XF + 1.5, BEAM_END, bt)
    zc = bt - B["h"] / 2
    bolts_x(s, XF + 1.5, 1.5 + C["tf"], [zc - 9, zc, zc + 9])
    return s


def ecb6():
    """Beam on column, endplate extended down the column (tension zone) and stiffeners."""
    s = Scene("End column-beam 6: extended endplate in tension zone and stiffeners")
    top = 0.0
    s.column(COL, COL_BOT, top)
    cap_plate(s, top)
    bb = top + 1.5
    xo = -XF - 1.0
    z_low = top - 30.0
    s.box(xo - 2.0, xo, -C["b"] / 2, C["b"] / 2, z_low, bb + B["h"], "plate", "Plates")
    s.profile_weld(BEAM, (xo, 0, bb + B["h"] / 2), (0, 1, 0), (0, 0, 1), (1, 0, 0))
    s.beam_x(BEAM, xo, BEAM_END, bb + B["h"])
    # side plate bolted to the outer column flange (tension zone)
    for z in (top - 8, top - 16, top - 24):
        for y in (-6.5, 6.5):
            s.bolt((xo - 2.0, y, z), (1, 0, 0), 2.0 + 1.0 + C["tf"])
    bolts_z(s, bb + B["tf"], B["tf"] + 1.5, [(4.0, -4.5), (4.0, 4.5)])
    beam_stiffeners(s, XFI, bb + B["h"])
    beam_stiffeners(s, -XFI, bb + B["h"])
    col_stiffeners(s, top - 30.0 + 0.5)
    s.view_dir = (-0.45, -0.85, 0.4)
    return s


def ecb7():
    """Beam on column, welded endplate with four bolts."""
    s = Scene("End column-beam 7: beam on column, welded endplate with four bolts")
    top = 0.0
    s.column(COL, COL_BOT, top)
    cap_plate(s, top)
    bb = top + 1.5
    x0 = -XF - 1.0
    s.box(x0 - 1.5, x0, -8, 8, bb, bb + B["h"], "plate", "Plates")
    s.profile_weld(BEAM, (x0, 0, bb + B["h"] / 2), (0, 1, 0), (0, 0, 1), (1, 0, 0))
    s.beam_x(BEAM, x0, BEAM_END, bb + B["h"])
    bolts_z(s, bb + B["tf"], B["tf"] + 1.5, [(x, y) for x in (-6.0, 6.0) for y in (-4.5, 4.5)])
    s.view_dir = (0.5, -0.85, 0.35)
    return s


def ecb8():
    """Welded elongated endplate with four bolts and stiffeners."""
    s = Scene("End column-beam 8: elongated endplate with four bolts and stiffeners")
    top = 0.0
    s.column(COL, COL_BOT, top)
    cap_plate(s, top)
    bt = top + 1.5
    end_plate(s, XF, bt, bt - B["h"] - 4.0, beam_top=bt)
    s.beam_x(BEAM, XF + 1.5, BEAM_END, bt)
    bolts_x(s, XF + 1.5, 1.5 + C["tf"], [bt - 5.5, bt - B["h"] + 5.5])
    col_stiffeners(s, bt - B["h"] + B["tf"] / 2)
    return s


# ----------------------------------------------------------------------------- Column support
def column_base():
    """HEB 200 column on a base plate with two anchor bolts, grout and foundation."""
    s = Scene("Column base: welded base plate with two anchor bolts")
    prof = PROFILES["HEB200"]
    pl_t, grout_t = 2.5, 3.0
    pl_x, pl_y = 36.0, 30.0
    s.member("HEB200", (0, 0, pl_t), (0, -1, 0), (1, 0, 0), (0, 0, 1), 60.0, "Column")
    s.profile_weld("HEB200", (0, 0, pl_t), (0, -1, 0), (1, 0, 0), (0, 0, 1), a=0.7)
    s.box(-pl_x / 2, pl_x / 2, -pl_y / 2, pl_y / 2, 0, pl_t, "plate", "Base plate")
    bot = -grout_t - 30.0
    for y in (-5.5, 5.5):
        # anchor bolt: nut + washer on the plate, anchor plate + nut at the embedded end
        s.cylinder((0, y, bot), (0, 0, 1), 1.0, pl_t + 0.4 + 1.6 + 1.2 - bot, "bolt", "Anchor bolts")
        s.cylinder((0, y, pl_t), (0, 0, 1), 1.85, 0.4, "nut", "Anchor bolts")
        s.prism(hexagon(3.0, 0, y), "z", pl_t + 0.4, pl_t + 2.0, "nut", "Anchor bolts", outline=False)
        s.box(-3.5, 3.5, y - 3.5, y + 3.5, bot + 1.6, bot + 2.6, "nut", "Anchor bolts")
        s.prism(hexagon(3.0, 0, y), "z", bot + 0.2, bot + 1.6, "nut", "Anchor bolts", outline=False)
    # grout, tapered
    gt = rect(-pl_x / 2 - 0.5, pl_x / 2 + 0.5, -pl_y / 2 - 0.5, pl_y / 2 + 0.5)
    gb = rect(-pl_x / 2 - 4.5, pl_x / 2 + 4.5, -pl_y / 2 - 4.5, pl_y / 2 + 4.5)
    top3 = [(u, v, 0.0) for u, v in gt]
    bot3 = [(u, v, -grout_t) for u, v in gb]
    m = Mesh()
    m.polygon(top3, gt)
    m.polygon(bot3, gb)
    m.quad_strip(bot3, top3)
    s.add_mesh(m, "grout", "Grout")
    s.add_line(top3, "Grout", closed=True)
    s.add_line(bot3, "Grout", closed=True)
    for a, b in zip(bot3, top3):
        s.add_line([a, b], "Grout")
    s.box(-35, 35, -30, 30, -grout_t - 40, -grout_t, "concrete", "Foundation")
    s.view_dir = (0.55, -0.78, 0.47)
    s.pivot = (0.0, 0.0, 2.0)     # base plate, not the centre of the long anchor bolts
    return s


# ----------------------------------------------------------------------------- registry
# id: (function, group, caption, S04 drawing)
DETAILS = {
    "end_column_beam_1": (ecb1, "End column-beam", "Welded endplate with two bolts.", "End_Column_Beam1.jpg"),
    "end_column_beam_2": (ecb2, "End column-beam", "Connection with bolted angles.", "End_Column_Beam2.jpg"),
    "end_column_beam_3": (ecb3, "End column-beam",
                          "Welded elongated endplate with top plate and stiffeners for extra stiffness.",
                          "End_Column_Beam3.jpg"),
    "end_column_beam_3_original": (ecb3_original, "End column-beam",
                                   "Welded elongated endplate with top plate and stiffeners (previous version, for comparison).",
                                   "End_Column_Beam3.jpg"),
    "end_column_beam_4": (ecb4, "End column-beam", "Beam on column: welded endplate with two bolts.", "End_Column_Beam4.jpg"),
    "end_column_beam_5": (ecb5, "End column-beam", "Welded endplate with six bolts.", "End_Column_Beam5.jpg"),
    "end_column_beam_6": (ecb6, "End column-beam",
                          "Welded endplate with extra plate in tension zone and stiffeners.",
                          "End_Column_Beam6.jpg"),
    "end_column_beam_7": (ecb7, "End column-beam", "Beam on column: welded endplate with four bolts.", "End_Column_Beam7.jpg"),
    "end_column_beam_8": (ecb8, "End column-beam",
                          "Welded elongated endplate with four bolts and stiffeners.", "End_Column_Beam8.jpg"),
    "column_support_1": (column_base, "Column-support",
                         "Column support with welded endplate and a single row of bolts.",
                         "Column_Support1.jpg"),
}
