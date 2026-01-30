"""
Improved bevel gear generator - builds teeth individually for better control.

This version constructs each tooth as a tapered solid that converges toward
the pitch cone apex, ensuring proper mesh geometry.
"""

import math
import cadquery as cq


def involute_point(base_radius: float, t: float) -> tuple[float, float]:
    """Calculate a point on an involute curve.

    Args:
        base_radius: Base circle radius
        t: Parameter (roll angle from base circle)

    Returns:
        (x, y) coordinates
    """
    x = base_radius * (math.cos(t) + t * math.sin(t))
    y = base_radius * (math.sin(t) - t * math.cos(t))
    return (x, y)


def involute_param_at_radius(base_radius: float, target_radius: float) -> float:
    """Find involute parameter t where curve reaches target_radius."""
    if target_radius <= base_radius:
        return 0.0
    # r = base_radius * sqrt(1 + t^2)
    ratio = target_radius / base_radius
    return math.sqrt(ratio * ratio - 1)


def generate_tooth_profile_2d(
    pitch_radius: float,
    module: float,
    pressure_angle_deg: float = 20.0,
    num_points: int = 8,
    backlash: float = 0.0,
) -> list[tuple[float, float]]:
    """Generate 2D profile points for one gear tooth.

    Returns points for the left flank, tip arc, and right flank of a single tooth,
    centered at angle=0.
    """
    pressure_angle = math.radians(pressure_angle_deg)

    base_radius = pitch_radius * math.cos(pressure_angle)
    addendum = module
    dedendum = module * 1.25

    outer_radius = pitch_radius + addendum
    root_radius = max(pitch_radius - dedendum, base_radius * 1.01)

    # Tooth thickness at pitch circle (standard = pi*m/2, reduced by backlash)
    tooth_thickness = (math.pi * module / 2) - backlash
    half_tooth_angle = tooth_thickness / (2 * pitch_radius)

    # Involute function: inv(α) = tan(α) - α
    inv_alpha = math.tan(pressure_angle) - pressure_angle

    # Parameter range for involute
    t_root = involute_param_at_radius(base_radius, root_radius)
    t_tip = involute_param_at_radius(base_radius, outer_radius)

    points = []

    # Right flank (from root to tip)
    right_flank = []
    for i in range(num_points):
        t = t_root + (t_tip - t_root) * i / (num_points - 1)
        x, y = involute_point(base_radius, t)
        r = math.sqrt(x * x + y * y)
        theta = math.atan2(y, x)
        # Offset to position tooth centered at angle 0
        theta_offset = half_tooth_angle + inv_alpha
        new_theta = theta_offset - theta
        right_flank.append((r * math.cos(new_theta), r * math.sin(new_theta)))

    # Left flank (mirror of right)
    left_flank = [(x, -y) for x, y in right_flank]
    left_flank.reverse()

    # Assemble: left flank -> tip -> right flank
    points.extend(left_flank)

    # Small tip arc (3 points)
    tip_left = left_flank[-1]
    tip_right = right_flank[0]
    tip_angle_left = math.atan2(tip_left[1], tip_left[0])
    tip_angle_right = math.atan2(tip_right[1], tip_right[0])
    for i in range(3):
        angle = tip_angle_left + (tip_angle_right - tip_angle_left) * (i + 1) / 4
        points.append((outer_radius * math.cos(angle), outer_radius * math.sin(angle)))

    points.extend(right_flank)

    return points


def make_bevel_gear(
    module: float,
    num_teeth: int,
    pressure_angle_deg: float = 20.0,
    cone_angle_deg: float = 45.0,
    face_width: float = None,
    bore_diameter: float = 6.0,
    hub_diameter: float = None,
    hub_height: float = None,
    backlash: float = 0.1,
) -> cq.Workplane:
    """Create a bevel gear with properly converging teeth.

    Args:
        module: Gear module in mm
        num_teeth: Number of teeth
        pressure_angle_deg: Pressure angle (typically 20°)
        cone_angle_deg: Pitch cone half-angle (45° for 1:1 ratio at 90°)
        face_width: Tooth face width (default: ~30% of cone distance)
        bore_diameter: Central shaft bore diameter
        hub_diameter: Hub outer diameter (default: auto-calculated)
        hub_height: Hub height extending behind gear (default: face_width * 0.6)
        backlash: Backlash allowance in mm

    Returns:
        CadQuery Workplane with the gear solid
    """
    cone_angle = math.radians(cone_angle_deg)

    # Basic geometry
    pitch_diameter = module * num_teeth
    pitch_radius = pitch_diameter / 2

    # Cone distance (apex to pitch circle at back)
    cone_distance = pitch_radius / math.sin(cone_angle)

    # Default face width: 30% of cone distance or 10*module, whichever is smaller
    if face_width is None:
        face_width = min(cone_distance * 0.3, 10 * module)
    face_width = min(face_width, cone_distance * 0.4)  # Cap at 40%

    if hub_height is None:
        hub_height = face_width * 0.6

    # Tooth dimensions
    addendum = module
    dedendum = module * 1.25

    outer_radius_back = pitch_radius + addendum
    root_radius_back = pitch_radius - dedendum

    # Scale factor for front (small end)
    front_scale = (cone_distance - face_width) / cone_distance

    outer_radius_front = outer_radius_back * front_scale
    root_radius_front = root_radius_back * front_scale
    pitch_radius_front = pitch_radius * front_scale

    # Hub dimensions
    if hub_diameter is None:
        hub_diameter = root_radius_back * 1.2
    hub_radius = hub_diameter / 2

    # Build the gear blank (cone frustum from root)
    # Use revolution of a trapezoid profile
    blank_profile = [
        (root_radius_back, 0),
        (root_radius_front, face_width),
        (bore_diameter / 2, face_width),
        (bore_diameter / 2, 0),
    ]

    blank = (
        cq.Workplane("XZ")
        .polyline(blank_profile)
        .close()
        .revolve(360, (0, 0, 0), (0, 0, 1))
    )

    # Add hub
    hub = (
        cq.Workplane("XY")
        .circle(hub_radius)
        .circle(bore_diameter / 2)
        .extrude(-hub_height)
    )
    blank = blank.union(hub)

    # Now add each tooth
    tooth_angle = 2 * math.pi / num_teeth

    for i in range(num_teeth):
        rotation = math.degrees(i * tooth_angle)

        # Create tooth profile at back (large end)
        back_profile = generate_tooth_profile_2d(
            pitch_radius=pitch_radius,
            module=module,
            pressure_angle_deg=pressure_angle_deg,
            num_points=6,
            backlash=backlash,
        )

        # Create tooth profile at front (small end) - scaled down
        front_profile = [
            (x * front_scale, y * front_scale) for x, y in back_profile
        ]

        # Close the profiles by adding root arc points
        # Back root points
        root_angle_half = tooth_angle / 2
        back_root_start = back_profile[-1]
        back_root_end = back_profile[0]

        # Add root arc (going from right side to left side through the root)
        back_start_angle = math.atan2(back_root_start[1], back_root_start[0])
        back_end_angle = math.atan2(back_root_end[1], back_root_end[0])

        # The root arc goes through the valley
        back_closed = list(back_profile)
        for j in range(3):
            angle = back_start_angle - (back_start_angle - back_end_angle + tooth_angle) * (j + 1) / 4
            back_closed.append((root_radius_back * math.cos(angle), root_radius_back * math.sin(angle)))

        front_closed = [(x * front_scale, y * front_scale) for x, y in back_closed]

        # Create the tooth as a lofted solid between back and front profiles
        try:
            back_wire = (
                cq.Workplane("XY")
                .polyline(back_closed)
                .close()
            )

            front_wire = (
                cq.Workplane("XY")
                .workplane(offset=face_width)
                .polyline(front_closed)
                .close()
            )

            tooth = back_wire.workplane(offset=face_width).polyline(front_closed).close().loft()

            # Rotate tooth to correct position
            tooth = tooth.rotate((0, 0, 0), (0, 0, 1), rotation)

            blank = blank.union(tooth)
        except Exception as e:
            print(f"Warning: Could not create tooth {i}: {e}")
            continue

    return blank


def make_bevel_gear_simple(
    module: float,
    num_teeth: int,
    pressure_angle_deg: float = 20.0,
    cone_angle_deg: float = 45.0,
    face_width: float = None,
    bore_diameter: float = 6.0,
    hub_height: float = None,
    backlash: float = 0.1,
) -> cq.Workplane:
    """Create a bevel gear using whole-profile loft (simpler but effective).

    This method creates the entire gear profile at back and front,
    then lofts between them for a single clean operation.
    """
    cone_angle = math.radians(cone_angle_deg)
    pressure_angle = math.radians(pressure_angle_deg)

    pitch_diameter = module * num_teeth
    pitch_radius = pitch_diameter / 2
    cone_distance = pitch_radius / math.sin(cone_angle)

    if face_width is None:
        face_width = min(cone_distance * 0.3, 10 * module)
    face_width = min(face_width, cone_distance * 0.4)

    if hub_height is None:
        hub_height = face_width * 0.6

    addendum = module
    dedendum = module * 1.25

    base_radius = pitch_radius * math.cos(pressure_angle)
    outer_radius = pitch_radius + addendum
    root_radius = max(pitch_radius - dedendum, base_radius * 1.02)

    front_scale = (cone_distance - face_width) / cone_distance
    hub_radius = root_radius * 0.7

    # Tooth geometry
    tooth_thickness = (math.pi * module / 2) - backlash
    half_tooth_angle = tooth_thickness / (2 * pitch_radius)
    tooth_angle = 2 * math.pi / num_teeth

    inv_alpha = math.tan(pressure_angle) - pressure_angle

    # Generate complete gear profile
    def make_gear_profile(scale: float) -> list[tuple[float, float]]:
        pr = pitch_radius * scale
        br = base_radius * scale
        outr = outer_radius * scale
        rootr = root_radius * scale
        m = module * scale

        points = []

        for tooth_i in range(num_teeth):
            center_angle = tooth_i * tooth_angle

            # Tooth half-angle at this scale
            tt = (math.pi * m / 2) - backlash * scale
            hta = tt / (2 * pr)

            # Involute parameters
            t_root = involute_param_at_radius(br, max(rootr, br * 1.01))
            t_tip = involute_param_at_radius(br, outr * 0.99)

            # Right flank (root to tip)
            for j in range(5):
                t = t_root + (t_tip - t_root) * j / 4
                x, y = involute_point(br, t)
                r = math.sqrt(x*x + y*y)
                theta = math.atan2(y, x)
                theta_new = center_angle + hta + inv_alpha - theta
                points.append((r * math.cos(theta_new), r * math.sin(theta_new)))

            # Tip point
            points.append((outr * math.cos(center_angle), outr * math.sin(center_angle)))

            # Left flank (tip to root)
            for j in range(5):
                t = t_tip - (t_tip - t_root) * j / 4
                x, y = involute_point(br, t)
                r = math.sqrt(x*x + y*y)
                theta = math.atan2(y, x)
                theta_new = center_angle - hta - inv_alpha + theta
                points.append((r * math.cos(theta_new), r * math.sin(theta_new)))

            # Root point (between this tooth and next)
            root_angle = center_angle + tooth_angle / 2
            points.append((rootr * math.cos(root_angle), rootr * math.sin(root_angle)))

        return points

    back_profile = make_gear_profile(1.0)
    front_profile = make_gear_profile(front_scale)

    # Create gear body via loft
    gear = (
        cq.Workplane("XY")
        .polyline(back_profile)
        .close()
        .workplane(offset=face_width)
        .polyline(front_profile)
        .close()
        .loft()
    )

    # Add hub
    hub = (
        cq.Workplane("XY")
        .circle(hub_radius)
        .extrude(-hub_height)
    )
    gear = gear.union(hub)

    # Cut bore
    bore = (
        cq.Workplane("XY")
        .workplane(offset=-hub_height - 1)
        .circle(bore_diameter / 2)
        .extrude(face_width + hub_height + 2)
    )
    gear = gear.cut(bore)

    return gear


def assemble_gear_pair(
    module: float = 1.5,
    num_teeth: int = 16,
    pressure_angle_deg: float = 20.0,
    bore_diameter: float = 6.0,
    backlash: float = 0.1,
) -> cq.Assembly:
    """Create an assembly with two meshing bevel gears at 90 degrees."""
    pitch_radius = (module * num_teeth) / 2
    cone_distance = pitch_radius / math.sin(math.radians(45))
    face_width = min(cone_distance * 0.3, 10 * module)

    # Generate both gears (identical for 1:1 ratio)
    gear1 = make_bevel_gear_simple(
        module=module,
        num_teeth=num_teeth,
        pressure_angle_deg=pressure_angle_deg,
        cone_angle_deg=45.0,
        bore_diameter=bore_diameter,
        backlash=backlash,
    )

    gear2 = make_bevel_gear_simple(
        module=module,
        num_teeth=num_teeth,
        pressure_angle_deg=pressure_angle_deg,
        cone_angle_deg=45.0,
        bore_diameter=bore_diameter,
        backlash=backlash,
    )

    assy = cq.Assembly()

    # Gear 1 on Z-axis, apex at origin
    # The gear back face is at Z=0, front at Z=face_width
    # Apex would be at Z=cone_distance
    # So translate by -cone_distance to put apex at origin
    assy.add(
        gear1,
        name="gear1_z_axis",
        loc=cq.Location(cq.Vector(0, 0, -cone_distance)),
        color=cq.Color("steelblue"),
    )

    # Gear 2 on X-axis (rotate around Y by -90°)
    # Then translate along -X by cone_distance
    # Also rotate around the gear's own axis (Z before transformation) to mesh teeth
    tooth_angle = 360.0 / num_teeth
    mesh_offset = tooth_angle / 2  # Half tooth for meshing

    # Create rotation: first rotate around Z for mesh alignment, then around Y for 90° turn
    assy.add(
        gear2.rotate((0, 0, 0), (0, 0, 1), mesh_offset),
        name="gear2_x_axis",
        loc=cq.Location(
            cq.Vector(-cone_distance, 0, 0),
            cq.Vector(0, 1, 0),
            -90
        ),
        color=cq.Color("darkorange"),
    )

    return assy


if __name__ == "__main__":
    print("Generating improved bevel gears...")

    module = 1.5
    num_teeth = 16
    bore = 6.2

    # Single gear
    gear = make_bevel_gear_simple(
        module=module,
        num_teeth=num_teeth,
        bore_diameter=bore,
        backlash=0.15,
    )
    cq.exporters.export(gear, "bevel_v2_single.step")
    print("Exported: bevel_v2_single.step")

    # Assembly
    assy = assemble_gear_pair(
        module=module,
        num_teeth=num_teeth,
        bore_diameter=bore,
        backlash=0.15,
    )
    assy.save("bevel_v2_pair.step")
    print("Exported: bevel_v2_pair.step")

    # Print info
    pitch_radius = (module * num_teeth) / 2
    cone_distance = pitch_radius / math.sin(math.radians(45))
    face_width = min(cone_distance * 0.3, 10 * module)

    print(f"\nGeometry:")
    print(f"  Module: {module} mm")
    print(f"  Teeth: {num_teeth}")
    print(f"  Pitch diameter: {module * num_teeth} mm")
    print(f"  Cone distance: {cone_distance:.2f} mm")
    print(f"  Face width: {face_width:.2f} mm")
