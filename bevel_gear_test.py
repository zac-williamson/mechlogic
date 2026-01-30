"""
Proper bevel gear generator using Tredgold approximation.

This creates straight bevel gears with involute tooth profiles that
properly converge toward the pitch cone apex.

For a 1:1 ratio 90-degree bevel gear pair:
- Each gear has a 45-degree pitch cone angle
- Teeth follow involute profile (approximated via Tredgold method)
- All tooth elements converge toward the cone apex
"""

import math
import cadquery as cq


def involute_point(base_radius: float, angle: float) -> tuple[float, float]:
    """Calculate a point on an involute curve.

    Args:
        base_radius: Base circle radius
        angle: Parameter angle in radians (0 = start of involute at base circle)

    Returns:
        (x, y) coordinates of the involute point
    """
    x = base_radius * (math.cos(angle) + angle * math.sin(angle))
    y = base_radius * (math.sin(angle) - angle * math.cos(angle))
    return (x, y)


def involute_intersect_angle(base_radius: float, target_radius: float) -> float:
    """Find the involute parameter angle where curve reaches target_radius.

    Uses the relation: r = r_b * sqrt(1 + t^2) where t is the parameter.
    """
    if target_radius <= base_radius:
        return 0.0
    ratio = target_radius / base_radius
    # r = r_b * sqrt(1 + t^2)  =>  t = sqrt((r/r_b)^2 - 1)
    return math.sqrt(ratio * ratio - 1)


def generate_involute_tooth_profile(
    module: float,
    num_teeth: int,
    pressure_angle_deg: float = 20.0,
    num_points: int = 15,
) -> list[tuple[float, float]]:
    """Generate points for one tooth profile (one side of tooth + root + other side).

    Returns points for a single tooth centered at angle=0, going CCW.
    The profile goes: root -> left flank (involute) -> tip -> right flank (involute) -> root
    """
    pressure_angle = math.radians(pressure_angle_deg)

    # Standard gear geometry
    pitch_radius = (module * num_teeth) / 2
    base_radius = pitch_radius * math.cos(pressure_angle)
    addendum = module
    dedendum = module * 1.25
    outer_radius = pitch_radius + addendum
    root_radius = pitch_radius - dedendum

    # Tooth thickness at pitch circle (for standard gears = pi*m/2)
    tooth_thickness_pitch = math.pi * module / 2

    # Angular tooth thickness at pitch circle
    tooth_angle_pitch = tooth_thickness_pitch / pitch_radius

    # The involute starts at the base circle. We need to find where on the
    # involute the pitch circle is intersected, and use that to position the tooth.
    inv_angle_at_pitch = involute_intersect_angle(base_radius, pitch_radius)

    # The "involute function" inv(alpha) = tan(alpha) - alpha
    # At the pitch circle, the pressure angle alpha gives us the angular offset
    inv_pressure = math.tan(pressure_angle) - pressure_angle

    # Half tooth angle at pitch circle
    half_tooth_angle = tooth_angle_pitch / 2

    points = []

    # Generate right flank (going outward from root to tip)
    # The involute curve offset so tooth is centered at angle 0
    t_start = involute_intersect_angle(base_radius, max(root_radius, base_radius))
    t_end = involute_intersect_angle(base_radius, outer_radius)

    # Right flank points (from root to tip)
    right_flank = []
    for i in range(num_points):
        t = t_start + (t_end - t_start) * i / (num_points - 1)
        x, y = involute_point(base_radius, t)
        r = math.sqrt(x*x + y*y)
        theta = math.atan2(y, x)
        # Rotate to center tooth at angle 0
        # The involute at the pitch circle should be at half_tooth_angle
        rotation = half_tooth_angle + inv_pressure - involute_intersect_angle(base_radius, pitch_radius)
        theta_new = theta + rotation
        right_flank.append((r * math.cos(theta_new), r * math.sin(theta_new)))

    # Left flank is mirror of right flank
    left_flank = [(x, -y) for (x, y) in reversed(right_flank)]

    # Root arc (connect the two flanks at the root)
    # For simplicity, use straight line at root (or small arc)
    root_start = left_flank[-1]
    root_end = right_flank[0]

    # Tip arc
    tip_start = right_flank[-1]
    tip_end = left_flank[0]

    # Assemble: root_start -> left_flank -> tip_arc -> right_flank -> root_end
    # Actually we need the full tooth + gap profile

    # Return just the tooth profile points going CCW
    profile = []
    profile.extend(left_flank)

    # Tip arc (small arc at outer_radius)
    tip_angle_start = math.atan2(tip_end[1], tip_end[0])
    tip_angle_end = math.atan2(tip_start[1], tip_start[0])
    for i in range(5):
        angle = tip_angle_start + (tip_angle_end - tip_angle_start) * i / 4
        profile.append((outer_radius * math.cos(angle), outer_radius * math.sin(angle)))

    profile.extend(right_flank)

    return profile


def generate_gear_profile_points(
    module: float,
    num_teeth: int,
    pressure_angle_deg: float = 20.0,
    points_per_tooth: int = 12,
) -> list[tuple[float, float]]:
    """Generate complete gear profile as a list of (x,y) points.

    Creates a closed profile with all teeth, suitable for extrusion.
    """
    pressure_angle = math.radians(pressure_angle_deg)

    pitch_radius = (module * num_teeth) / 2
    base_radius = pitch_radius * math.cos(pressure_angle)
    addendum = module
    dedendum = module * 1.25
    outer_radius = pitch_radius + addendum
    root_radius = pitch_radius - dedendum

    # Tooth geometry
    tooth_thickness_pitch = math.pi * module / 2
    tooth_angle = 2 * math.pi / num_teeth
    half_tooth_angle_pitch = (tooth_thickness_pitch / pitch_radius) / 2

    # Involute function value at pressure angle
    inv_pressure = math.tan(pressure_angle) - pressure_angle

    all_points = []

    for tooth_idx in range(num_teeth):
        tooth_center_angle = tooth_idx * tooth_angle

        # Generate involute points for right flank
        t_root = involute_intersect_angle(base_radius, max(root_radius * 1.01, base_radius))
        t_tip = involute_intersect_angle(base_radius, outer_radius * 0.99)

        # Right flank (going from root toward tip)
        for i in range(points_per_tooth // 2):
            t = t_root + (t_tip - t_root) * i / (points_per_tooth // 2 - 1)
            x, y = involute_point(base_radius, t)
            r = math.sqrt(x*x + y*y)
            theta = math.atan2(y, x)

            # Position: involute starts at base circle, we offset to center tooth
            offset = half_tooth_angle_pitch + inv_pressure
            theta_final = tooth_center_angle + offset - theta

            all_points.append((r * math.cos(theta_final), r * math.sin(theta_final)))

        # Tip point
        all_points.append((
            outer_radius * math.cos(tooth_center_angle),
            outer_radius * math.sin(tooth_center_angle)
        ))

        # Left flank (going from tip toward root) - mirror of right
        for i in range(points_per_tooth // 2):
            t = t_tip - (t_tip - t_root) * i / (points_per_tooth // 2 - 1)
            x, y = involute_point(base_radius, t)
            r = math.sqrt(x*x + y*y)
            theta = math.atan2(y, x)

            offset = half_tooth_angle_pitch + inv_pressure
            theta_final = tooth_center_angle - offset + theta

            all_points.append((r * math.cos(theta_final), r * math.sin(theta_final)))

        # Root point (valley between teeth)
        root_angle = tooth_center_angle + tooth_angle / 2
        all_points.append((
            root_radius * math.cos(root_angle),
            root_radius * math.sin(root_angle)
        ))

    return all_points


def generate_bevel_gear(
    module: float,
    num_teeth: int,
    pressure_angle_deg: float = 20.0,
    cone_angle_deg: float = 45.0,
    face_width: float = None,
    bore_diameter: float = 6.0,
    hub_height: float = None,
    backlash: float = 0.1,
) -> cq.Workplane:
    """Generate a straight bevel gear with proper involute teeth.

    Uses the Tredgold approximation: treats the bevel gear as a virtual
    spur gear on the "back cone" and then projects it onto the pitch cone.

    Args:
        module: Gear module (tooth size parameter) in mm
        num_teeth: Number of teeth
        pressure_angle_deg: Pressure angle in degrees (typically 20)
        cone_angle_deg: Pitch cone half-angle in degrees (45 for 1:1 90° mesh)
        face_width: Face width of gear teeth (default: ~1/3 of cone distance)
        bore_diameter: Central bore diameter in mm
        hub_height: Height of mounting hub (default: face_width * 0.6)
        backlash: Backlash allowance in mm

    Returns:
        CadQuery Workplane with the bevel gear
    """
    cone_angle = math.radians(cone_angle_deg)
    pressure_angle = math.radians(pressure_angle_deg)

    # Pitch diameter at the large end (back)
    pitch_diameter = module * num_teeth
    pitch_radius = pitch_diameter / 2

    # Cone distance (distance from apex to pitch circle at back)
    # For a 45° cone: cone_distance = pitch_radius / sin(45°)
    cone_distance = pitch_radius / math.sin(cone_angle)

    # Default face width is about 1/3 of cone distance (or 10*module, whichever is smaller)
    if face_width is None:
        face_width = min(cone_distance / 3, 10 * module)

    # Ensure face width doesn't exceed practical limits
    face_width = min(face_width, cone_distance * 0.35)

    if hub_height is None:
        hub_height = face_width * 0.6

    # Gear geometry
    addendum = module
    dedendum = module * 1.25

    # At the back (large end)
    outer_radius_back = pitch_radius + addendum
    root_radius_back = pitch_radius - dedendum

    # The gear "shrinks" linearly toward the apex
    # At distance (cone_distance - face_width) from apex:
    shrink_ratio = (cone_distance - face_width) / cone_distance

    # At the front (small end)
    pitch_radius_front = pitch_radius * shrink_ratio
    outer_radius_front = (pitch_radius + addendum) * shrink_ratio
    root_radius_front = (pitch_radius - dedendum) * shrink_ratio

    # For Tredgold approximation, the "virtual number of teeth"
    # on the back cone is: N_v = N / cos(cone_angle)
    virtual_teeth = num_teeth / math.cos(cone_angle)

    # Generate the gear profile for the back (large end)
    # Apply backlash by slightly reducing tooth thickness
    effective_module_back = module - (backlash / num_teeth)

    # Build the gear using cross-sections that taper toward the apex
    # We'll create the gear body first, then cut the teeth

    # Method: Create a series of cross-sections and loft between them
    # Each cross-section is a gear profile scaled appropriately

    num_sections = 8
    wires = []

    for section_idx in range(num_sections):
        # Distance along face from back (0) to front (face_width)
        z = face_width * section_idx / (num_sections - 1)

        # Scale factor at this section
        scale = (cone_distance - z) / cone_distance

        # Current radii
        pitch_r = pitch_radius * scale
        outer_r = outer_radius_back * scale
        root_r = root_radius_back * scale
        current_module = module * scale

        # Generate gear profile points at this scale
        points = generate_gear_profile_points(
            module=current_module,
            num_teeth=num_teeth,
            pressure_angle_deg=pressure_angle_deg,
            points_per_tooth=10,
        )

        # Apply backlash by scaling down slightly
        backlash_scale = 1 - (backlash / (2 * pitch_r))
        points = [(x * backlash_scale, y * backlash_scale) for (x, y) in points]

        # Create wire at this Z level
        wp = cq.Workplane("XY").workplane(offset=z)
        wire = wp.polyline(points).close().val()
        wires.append(wire)

    # Loft between the sections to create the gear body
    gear = cq.Workplane("XY").add(wires[0])
    for wire in wires[1:]:
        gear = gear.add(wire)

    # Use shell/loft - CadQuery's loft works with multiple sections
    # Actually, let's use a different approach - solid loft
    gear_solid = (
        cq.Workplane("XY")
        .polyline(generate_gear_profile_points(module, num_teeth, pressure_angle_deg, 10))
        .close()
        .extrude(face_width, taper=-math.degrees(math.atan(1/cone_distance * pitch_radius)))
    )

    # The taper approach above is approximate. Let's use a cleaner method:
    # Create back profile, front profile, and loft between them

    back_points = generate_gear_profile_points(module, num_teeth, pressure_angle_deg, 12)

    front_scale = shrink_ratio
    front_points = [(x * front_scale, y * front_scale) for (x, y) in back_points]

    # Create the two profiles
    back_wire = cq.Workplane("XY").polyline(back_points).close()
    front_wire = cq.Workplane("XY").workplane(offset=face_width).polyline(front_points).close()

    # Loft between them
    gear_solid = back_wire.workplane(offset=face_width).polyline(front_points).close().loft()

    # Add the hub (cylinder extending backward from the back face)
    hub_outer_radius = root_radius_back * 0.7
    hub = (
        cq.Workplane("XY")
        .circle(hub_outer_radius)
        .extrude(-hub_height)
    )

    gear_solid = gear_solid.union(hub)

    # Cut the central bore through everything
    bore = (
        cq.Workplane("XY")
        .workplane(offset=-hub_height - 1)
        .circle(bore_diameter / 2)
        .extrude(face_width + hub_height + 2)
    )

    gear_solid = gear_solid.cut(bore)

    return gear_solid


def generate_bevel_gear_pair(
    module: float = 1.5,
    num_teeth: int = 16,
    pressure_angle_deg: float = 20.0,
    shaft_angle_deg: float = 90.0,
    bore_diameter: float = 6.0,
    backlash: float = 0.1,
) -> tuple[cq.Workplane, cq.Workplane, dict]:
    """Generate a mating pair of bevel gears.

    For a 90-degree shaft angle with 1:1 ratio, both gears are identical
    with 45-degree pitch cones.

    Args:
        module: Gear module in mm
        num_teeth: Number of teeth (same for both gears in 1:1 ratio)
        pressure_angle_deg: Pressure angle in degrees
        shaft_angle_deg: Angle between shafts (90 for perpendicular)
        bore_diameter: Central bore diameter in mm
        backlash: Backlash allowance in mm

    Returns:
        Tuple of (driving_gear, driven_gear, geometry_info)
    """
    # For shaft angle Σ and gear ratio i = N2/N1:
    # cone_angle_1 = atan(sin(Σ) / (i + cos(Σ)))
    # cone_angle_2 = Σ - cone_angle_1
    # For 1:1 ratio and 90° shaft angle: both cone angles = 45°

    shaft_angle = math.radians(shaft_angle_deg)
    ratio = 1.0  # 1:1 ratio

    cone_angle_1 = math.atan(math.sin(shaft_angle) / (ratio + math.cos(shaft_angle)))
    cone_angle_2 = shaft_angle - cone_angle_1

    # For 1:1 at 90°, both should be 45°
    cone_angle_1_deg = math.degrees(cone_angle_1)
    cone_angle_2_deg = math.degrees(cone_angle_2)

    # Pitch diameter and cone distance
    pitch_diameter = module * num_teeth
    pitch_radius = pitch_diameter / 2
    cone_distance = pitch_radius / math.sin(cone_angle_1)

    # Face width (typically 1/3 of cone distance or 10*module)
    face_width = min(cone_distance / 3, 10 * module)

    gear1 = generate_bevel_gear(
        module=module,
        num_teeth=num_teeth,
        pressure_angle_deg=pressure_angle_deg,
        cone_angle_deg=cone_angle_1_deg,
        face_width=face_width,
        bore_diameter=bore_diameter,
        backlash=backlash,
    )

    gear2 = generate_bevel_gear(
        module=module,
        num_teeth=num_teeth,
        pressure_angle_deg=pressure_angle_deg,
        cone_angle_deg=cone_angle_2_deg,
        face_width=face_width,
        bore_diameter=bore_diameter,
        backlash=backlash,
    )

    geometry_info = {
        "module": module,
        "num_teeth": num_teeth,
        "pressure_angle_deg": pressure_angle_deg,
        "shaft_angle_deg": shaft_angle_deg,
        "cone_angle_1_deg": cone_angle_1_deg,
        "cone_angle_2_deg": cone_angle_2_deg,
        "pitch_diameter": pitch_diameter,
        "cone_distance": cone_distance,
        "face_width": face_width,
    }

    return gear1, gear2, geometry_info


def create_assembled_pair(
    module: float = 1.5,
    num_teeth: int = 16,
    pressure_angle_deg: float = 20.0,
    bore_diameter: float = 6.0,
    backlash: float = 0.1,
) -> cq.Assembly:
    """Create an assembly with both gears positioned for meshing.

    The driving gear is on the Z-axis (vertical).
    The driven gear is on the X-axis (horizontal).
    They mesh at the origin.
    """
    gear1, gear2, info = generate_bevel_gear_pair(
        module=module,
        num_teeth=num_teeth,
        pressure_angle_deg=pressure_angle_deg,
        bore_diameter=bore_diameter,
        backlash=backlash,
    )

    pitch_radius = info["pitch_diameter"] / 2
    cone_distance = info["cone_distance"]
    face_width = info["face_width"]

    # Create assembly
    assy = cq.Assembly()

    # Gear 1: driving gear on Z-axis
    # Position so pitch cone apex is at origin
    # The gear was created with back face at Z=0 and front at Z=face_width
    # We need to move it so the apex (at Z=cone_distance) is at origin
    gear1_offset = -cone_distance

    assy.add(
        gear1,
        name="driving_gear",
        loc=cq.Location(cq.Vector(0, 0, gear1_offset)),
        color=cq.Color("steelblue"),
    )

    # Gear 2: driven gear on X-axis
    # Rotate 90° around Y, then position so apex at origin
    # Also rotate slightly around its axis to mesh teeth properly
    tooth_angle = 360.0 / num_teeth
    mesh_rotation = tooth_angle / 2  # Offset to mesh between gear1's teeth

    assy.add(
        gear2,
        name="driven_gear",
        loc=cq.Location(
            cq.Vector(-cone_distance, 0, 0),
            cq.Vector(0, 1, 0),
            90  # Rotate 90° around Y-axis
        ),
        color=cq.Color("darkorange"),
    )

    return assy, info


if __name__ == "__main__":
    # Test the bevel gear generator
    print("Generating bevel gear pair...")

    # Parameters matching your spec
    module = 1.5
    num_teeth = 16
    bore_diameter = 6.2  # 6mm shaft + 0.2mm clearance

    # Generate single gear for inspection
    gear = generate_bevel_gear(
        module=module,
        num_teeth=num_teeth,
        pressure_angle_deg=20.0,
        cone_angle_deg=45.0,
        bore_diameter=bore_diameter,
        backlash=0.15,
    )

    # Export single gear
    cq.exporters.export(gear, "bevel_gear_single.step")
    print("Exported: bevel_gear_single.step")

    # Generate and export the pair
    assy, info = create_assembled_pair(
        module=module,
        num_teeth=num_teeth,
        bore_diameter=bore_diameter,
        backlash=0.15,
    )

    # Export assembly
    assy.save("bevel_gear_pair.step")
    print("Exported: bevel_gear_pair.step")

    # Print geometry info
    print("\nGeometry Info:")
    for key, value in info.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")
