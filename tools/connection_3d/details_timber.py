"""Timber connection details (book/design/timber/T02_timber_structures_and_details.ipynb).

Same conventions as details.py: units cm, Z up, the beam runs along +x and the
column face it connects to lies in the plane x = 0. Beam bottom at z = 0.
"""

from iris3d import Mesh, Scene, add, circle, frame_from_axis, hexagon, mul, rect

A = 0.4                     # weld leg


def timber_column(s, x0, x1, y0, y1, z0, z1, layer="Column"):
    s.box(x0, x1, y0, y1, z0, z1, "timber", layer)


def slotted_beam(s, x0, x1, b, h, slot_t, slot_x1, slot_h, chamfer=0.5, layer="Beam"):
    """Timber beam from x0 to x1 (width b, height h, bottom at z = 0) with a slot for a
    fin plate, open at the end and at the bottom (width slot_t, from x0 to slot_x1, up to
    z = slot_h). The slot edges at the bottom are chamfered to clear the fin plate welds."""
    hb, ht = b / 2, slot_t / 2
    notched = [(-hb, 0), (-ht - chamfer, 0), (-ht, chamfer), (-ht, slot_h), (ht, slot_h), (ht, chamfer),
               (ht + chamfer, 0), (hb, 0), (hb, h), (-hb, h)]
    full = rect(-hb, hb, 0, h)
    u, v, w = (0, 1, 0), (0, 0, 1), (1, 0, 0)
    s.extrude(notched, (x0, 0, 0), u, v, w, slot_x1 - x0, "timber", layer, outline=False)
    s.extrude(full, (slot_x1, 0, 0), u, v, w, x1 - slot_x1, "timber", layer, outline=False)

    def P(x, q):
        return (x, q[0], q[1])

    s.add_line([P(x0, q) for q in notched], layer, closed=True)          # beam end
    s.add_line([P(x1, q) for q in full], layer, closed=True)             # cut end
    for q in full:                                                        # long edges
        s.add_line([P(x0, q), P(x1, q)], layer)
    for q in notched[1:7]:                                                # slot edges
        s.add_line([P(x0, q), P(slot_x1, q)], layer)
    s.add_line([P(slot_x1, q) for q in notched[1:7]], layer)             # slot end


def dowel(s, x, z, length, d=1.2, layer="Dowels"):
    """Steel dowel across the beam (along y), flush with both faces."""
    s.cylinder((x, -length / 2, z), (0, 1, 0), d / 2, length, "bolt", layer, n=20, outline=True)


def coach_screw(s, head_at, axis, length, d=1.2, s_af=1.8, k=0.8, dw=2.4, tw=0.25, layer="Screws"):
    """Hexagon-head coach screw: washer + head before `head_at`, shank `length` along axis."""
    u, v, w = frame_from_axis(axis)
    s.extrude(circle(dw / 2), add(head_at, mul(w, -tw)), u, v, w, tw, "nut", layer, outline=False)
    s.extrude(hexagon(s_af), add(head_at, mul(w, -tw - k)), u, v, w, k, "bolt", layer, outline=False)
    s.cylinder(add(head_at, mul(w, -tw - k)), w, d / 2, length + tw + k, "bolt", layer, n=16)


# ----------------------------------------------------------------------------- details
def beam_continuous_column():
    """Fig. 12.4 left: beam on a continuous column, steel hanger with slotted-in fin plate.

    Back plate screwed to the column face (2 x 3 coach screws), seat plate under the beam,
    fin plate in a slot in the beam end, fixed with three dowels."""
    s = Scene("Timber beam on continuous column")
    bc = 24.0                   # glulam column 240 x 240
    b, h = 16.0, 40.0           # glulam beam 160 x 400
    t = 0.8                     # back and seat plate
    tf = 1.0                    # fin plate
    gap = 1.2                   # back plate to beam end (screw heads)
    xb = t + gap                # beam end
    fin_x1, fin_h = 17.0, 26.0
    seat_x1 = 21.0
    back_h = 33.0

    timber_column(s, -bc, 0, -bc / 2, bc / 2, -45.0, h + 45.0)
    slotted_beam(s, xb, 95.0, b, h, tf + 0.2, fin_x1 + 0.5, fin_h + 0.5)

    # steel hanger
    s.box(0, seat_x1, -b / 2, b / 2, -t, 0, "plate", "Plates")              # seat
    s.box(0, t, -b / 2, b / 2, 0, back_h, "plate", "Plates")                # back plate
    s.box(t, fin_x1, -tf / 2, tf / 2, 0, fin_h, "plate", "Plates")          # fin plate
    for sy in (1, -1):
        y = sy * tf / 2
        s.line_weld((t, y, 0), (t, y, fin_h), (0, sy, 0), (1, 0, 0), A)     # fin - back plate
        s.line_weld((t, y, 0), (fin_x1, y, 0), (0, sy, 0), (0, 0, 1), A)    # fin - seat
    for y0, y1 in ((-b / 2, -tf / 2), (tf / 2, b / 2)):
        s.line_weld((t, y0, 0), (t, y1, 0), (1, 0, 0), (0, 0, 1), A)        # back plate - seat

    # coach screws into the column, dowels through beam and fin plate
    for z in (5.0, 17.0, 29.0):
        for y in (-4.4, 4.4):
            coach_screw(s, (t, y, z), (-1, 0, 0), 10.0)
    for z in (5.5, 13.0, 20.5):
        dowel(s, 11.0, z, b)

    s.pivot = (6.0, 0.0, 16.0)
    s.view_dir = (0.75, -0.85, 0.35)
    s.zoom = 0.6
    return s


# key -> (function, group, caption, drawing)
TIMBER_DETAILS = {
    "timber_beam_column_1": (beam_continuous_column, "Straight beam",
                             "Beam on continuous column (steel hanger with slotted-in plate and dowels).",
                             "book/design/timber/Images/straight_beam_precamber_details.png (left)"),
}
