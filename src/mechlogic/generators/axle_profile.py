"""D-flat axle and bore helpers.

A D-flat is a single flat chord cut along one side of a cylinder, providing
positive rotation lock while allowing axial sliding. The flat face is at
y = radius - d_flat_depth (+Y side convention).

Full D-flat axles are simple:
- Fixed components (D-flat bore): rotation-locked, can still slide on for assembly
- Free-spinning components (circular bore): spin freely because the circular bore
  clears the D-flat everywhere
"""

import cadquery as cq


def make_d_flat_profile(diameter: float, d_flat_depth: float) -> cq.Workplane:
    """Create a 2D D-flat profile (circle with a flat chord on +Y side).

    Args:
        diameter: Cylinder diameter in mm.
        d_flat_depth: Depth of the flat cut from the +Y edge in mm.

    Returns:
        CQ Workplane with a 2D wire (circle minus the +Y chord).
    """
    radius = diameter / 2
    flat_y = radius - d_flat_depth  # Y of the flat face

    # Build as circle minus a box on the +Y side
    circle = cq.Workplane("XY").circle(radius)
    cut_box = (
        cq.Workplane("XY")
        .rect(diameter + 2, d_flat_depth + 1)
        .translate((0, radius - d_flat_depth / 2 + 0.5, 0))
    )
    return circle.cut(cut_box)


def make_d_flat_cylinder(
    diameter: float, length: float, d_flat_depth: float,
) -> cq.Workplane:
    """Create a D-flat cylinder (extruded in Z, centered at origin).

    Args:
        diameter: Cylinder diameter in mm.
        length: Length along Z axis in mm.
        d_flat_depth: Depth of flat cut from +Y edge in mm.

    Returns:
        CQ Workplane solid centered at origin.
    """
    radius = diameter / 2
    flat_y = radius - d_flat_depth

    circle = (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(length / 2, both=True)
    )
    cut_box = (
        cq.Workplane("XY")
        .box(diameter + 2, d_flat_depth + 1, length + 2, centered=True)
        .translate((0, radius - d_flat_depth / 2 + 0.5, 0))
    )
    return circle.cut(cut_box)


def make_d_flat_axle(
    diameter: float,
    length: float,
    d_flat_depth: float,
) -> cq.Workplane:
    """Create a D-flat axle along X axis.

    The axle starts at X=0 and extends in +X for `length`.
    D-flat is on the +Y side.

    Args:
        diameter: Axle diameter in mm.
        length: Total axle length in mm.
        d_flat_depth: Depth of flat cut in mm.

    Returns:
        CQ Workplane solid.
    """
    radius = diameter / 2
    flat_y = radius - d_flat_depth

    # Build circular cross-section in YZ, extrude along X
    axle = (
        cq.Workplane("YZ")
        .circle(radius)
        .extrude(length)
    )

    # Cut the flat along +Y for the full length
    cut_box = (
        cq.Workplane("XY")
        .box(length + 2, d_flat_depth + 1, diameter + 2, centered=True)
        .translate((length / 2, radius - d_flat_depth / 2 + 0.5, 0))
    )
    return axle.cut(cut_box)


def add_groove_to_axle(
    axle: cq.Workplane,
    x_position: float,
    shaft_dia: float,
    groove_depth: float = 0.75,
    groove_width: float = 1.5,
) -> cq.Workplane:
    """Cut a circumferential retention groove into an X-axis axle.

    The groove is a reduced-diameter ring centered at x_position.

    Args:
        axle: Existing axle workplane.
        x_position: X center of the groove.
        shaft_dia: Shaft diameter in mm.
        groove_depth: Depth of cut per side in mm.
        groove_width: Width of the groove in X in mm.

    Returns:
        Axle with groove cut.
    """
    groove_dia = shaft_dia - 2 * groove_depth
    # Cut only the annular ring (keeps the inner core intact, never splits the axle)
    groove_ring = (
        cq.Workplane("YZ")
        .circle(shaft_dia / 2 + 0.1)  # Slightly oversize to ensure clean cut
        .circle(groove_dia / 2)        # Inner hole preserves core
        .extrude(groove_width)
        .translate((x_position - groove_width / 2, 0, 0))
    )
    return axle.cut(groove_ring)


def add_groove_to_axle_z(
    axle: cq.Workplane,
    z_position: float,
    shaft_dia: float,
    groove_depth: float = 0.75,
    groove_width: float = 1.5,
) -> cq.Workplane:
    """Cut a circumferential retention groove into a Z-axis axle.

    The groove is a reduced-diameter ring centered at z_position.

    Args:
        axle: Existing axle workplane.
        z_position: Z center of the groove.
        shaft_dia: Shaft diameter in mm.
        groove_depth: Depth of cut per side in mm.
        groove_width: Width of the groove in Z in mm.

    Returns:
        Axle with groove cut.
    """
    groove_dia = shaft_dia - 2 * groove_depth
    groove_ring = (
        cq.Workplane("XY")
        .circle(shaft_dia / 2 + 0.1)
        .circle(groove_dia / 2)
        .extrude(groove_width)
        .translate((0, 0, z_position - groove_width / 2))
    )
    return axle.cut(groove_ring)


def make_c_clip(
    groove_diameter: float = 4.5,
    clip_od: float = 10.0,
    thickness: float = 1.5,
    gap_angle: float = 120.0,
) -> cq.Workplane:
    """Generate a printable C-clip for axle retention.

    The clip is an annular ring with a gap on the +Y side. The gap allows
    the clip to slide onto a D-flat axle from the flat side, then seat
    into a circumferential groove.

    Args:
        groove_diameter: Inner diameter matching groove bottom.
        clip_od: Outer diameter (must exceed gear bore to act as stop).
        thickness: Thickness matching groove width.
        gap_angle: Angular gap in degrees, centered on +Y.

    Returns:
        CQ Workplane solid (flat on XY, extruded in Z).
    """
    import math

    inner_r = groove_diameter / 2
    outer_r = clip_od / 2
    half_gap = gap_angle / 2

    # Build as an arc from (90 + half_gap) to (450 - half_gap) degrees
    # i.e., starting just past the +Y gap and sweeping around
    start_angle = 90 + half_gap
    end_angle = 360 + 90 - half_gap
    sweep = end_angle - start_angle

    # Create the arc ring using CadQuery wire operations
    # Outer arc
    sa_rad = math.radians(start_angle)
    ea_rad = math.radians(end_angle)

    # Build the C-shape as a 2D sketch then extrude
    # Use points to define the shape: outer arc, then inner arc reversed
    # CadQuery approach: make full annulus then cut the gap
    annulus = (
        cq.Workplane("XY")
        .circle(outer_r)
        .circle(inner_r)
        .extrude(thickness)
        .translate((0, 0, -thickness / 2))
    )

    # Cut the gap: intersect two half-planes to form a wedge that removes
    # everything (inner and outer ring) within the gap angle.
    # Each half-plane is a large box rotated to the gap boundary edge.
    gap_len = outer_r + 2
    h = 2 * gap_len  # Large enough to cover the full annulus

    # Right boundary of gap: line at angle (90 - half_gap) from +X axis
    # Keep everything to the left of this line (i.e., cut everything to the right)
    right_angle = 90 - half_gap
    # Left boundary of gap: line at angle (90 + half_gap)
    left_angle = 90 + half_gap

    # Build the gap as a sector: triangle from origin plus a box covering
    # the +Y area between the two boundary lines
    # Use a fan of points to trace the sector reliably
    pts = [(0, 0)]
    # Walk from right_angle to left_angle in small steps
    n_steps = 16
    for i in range(n_steps + 1):
        a = math.radians(right_angle + (left_angle - right_angle) * i / n_steps)
        pts.append((gap_len * math.cos(a), gap_len * math.sin(a)))

    gap_cut = (
        cq.Workplane("XY")
        .moveTo(pts[0][0], pts[0][1])
    )
    for px, py in pts[1:]:
        gap_cut = gap_cut.lineTo(px, py)
    gap_cut = (
        gap_cut
        .close()
        .extrude(thickness + 2)
        .translate((0, 0, -thickness / 2 - 1))
    )

    return annulus.cut(gap_cut)


def add_d_flat_to_bore(
    part: cq.Workplane,
    bore_dia: float,
    d_flat_depth: float,
    bore_length: float,
    z_offset: float = 0.0,
) -> cq.Workplane:
    """Add a D-flat fill (lune) inside an existing circular bore.

    This unions a crescent-shaped solid into the bore to create the flat face,
    effectively converting a circular bore into a D-flat bore.

    The lune is the area between the bore circle and the flat chord,
    positioned on the +Y side of the bore.

    The bore runs along Z axis. Use z_offset to shift the fill.

    Args:
        part: The part with an existing circular bore.
        bore_dia: Diameter of the existing bore.
        d_flat_depth: Depth of the D-flat cut.
        bore_length: Length of the bore along Z.
        z_offset: Z offset for the fill solid.

    Returns:
        Part with D-flat fill added.
    """
    bore_radius = bore_dia / 2
    flat_y = bore_radius - d_flat_depth

    # The lune is the intersection of the bore circle with the half-plane y > flat_y
    # Build it as a box clipped to the bore circle
    lune = (
        cq.Workplane("XY")
        .workplane(offset=z_offset)
        .rect(bore_dia, d_flat_depth)
        .extrude(bore_length / 2, both=True)
        .translate((0, flat_y + d_flat_depth / 2, 0))
    )

    # Clip to bore circle
    bore_cylinder = (
        cq.Workplane("XY")
        .workplane(offset=z_offset)
        .circle(bore_radius)
        .extrude(bore_length / 2, both=True)
    )
    lune = lune.intersect(bore_cylinder)

    return part.union(lune)


def make_d_flat_axle_along_z(
    diameter: float,
    length: float,
    d_flat_depth: float,
    z_start: float = 0.0,
) -> cq.Workplane:
    """Create a D-flat axle along Z axis.

    The axle starts at z_start and extends in +Z for `length`.
    D-flat is on the +Y side.

    Args:
        diameter: Axle diameter in mm.
        length: Total axle length in mm.
        d_flat_depth: Depth of flat cut in mm.
        z_start: Starting Z position.

    Returns:
        CQ Workplane solid.
    """
    radius = diameter / 2

    axle = (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(length)
        .translate((0, 0, z_start))
    )

    # Cut the flat along +Y for the full length
    cut_box = (
        cq.Workplane("XY")
        .box(diameter + 2, d_flat_depth + 1, length + 2, centered=True)
        .translate((0, radius - d_flat_depth / 2 + 0.5, z_start + length / 2))
    )
    return axle.cut(cut_box)
