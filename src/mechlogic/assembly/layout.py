"""Layout solver for computing part placements."""

from ..models.spec import LogicElementSpec
from ..models.geometry import AssemblyModel, PartType


class LayoutSolver:
    """Computes part placements ensuring proper alignment and spacing.

    The layout is organized around the main axis (Z-axis):
    - Housing plates at front and back (XY planes)
    - Gears, clutch, and main axle along Z
    - S-axis perpendicular (along Y, offset from center)
    - Lever pivots on S-axis motion to clutch linear motion
    """

    def __init__(self, spec: LogicElementSpec):
        self.spec = spec

    def solve(self) -> AssemblyModel:
        """Compute all part placements."""
        model = AssemblyModel()
        spec = self.spec

        # Key dimensions
        housing_t = spec.geometry.housing_thickness
        face_width = spec.geometry.gear_face_width
        gear_spacing = spec.geometry.gear_spacing
        clutch_width = spec.geometry.clutch_width
        axle_length = spec.geometry.axle_length
        dog_tooth_height = spec.gears.dog_clutch.tooth_height

        # Bevel gear dimensions (needed for layout calculation)
        bevel_face_width = 2.5 * spec.gears.module
        bevel_pitch_radius = (spec.gears.module * spec.gears.bevel_teeth) / 2

        # Clearance between bevel gear and housing (mm)
        BEVEL_CLEARANCE_MM = 5.0

        # Extra length needed for bevel gear zone
        # Space for: driving bevel offset + driven bevel + clearance
        bevel_zone_length = bevel_pitch_radius + bevel_face_width + BEVEL_CLEARANCE_MM

        # Calculate total assembly length along Z
        # Layout: [housing_front] [gear_a] [gap] [clutch] [gap] [gear_b] [housing_back]
        gear_a_length = face_width + dog_tooth_height
        gear_b_length = face_width + dog_tooth_height
        base_inner_length = gear_a_length + gear_spacing + clutch_width + gear_spacing + gear_b_length + bevel_zone_length
        inner_length = base_inner_length * 2  # Double spacing for bevel gear clearance
        total_length = 2 * housing_t + inner_length

        # Double the gear spacing for position calculations to spread gears across doubled space
        doubled_gear_spacing = gear_spacing * 2

        # Z positions (centered at origin, with doubled spacing)
        z_front_housing = -total_length / 2 + housing_t / 2
        z_back_housing = total_length / 2 - housing_t / 2  # Symmetric with front
        z_gear_a = z_front_housing + housing_t / 2 + gear_a_length / 2
        z_clutch = z_gear_a + gear_a_length / 2 + doubled_gear_spacing + clutch_width / 2
        z_gear_b = z_clutch + clutch_width / 2 + doubled_gear_spacing + gear_b_length / 2

        # S-axis Y offset
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        s_offset_y = gear_od / 2 + 15  # Above the main gear

        # Housing plates
        model.add_part(
            PartType.HOUSING_FRONT,
            "housing_front",
            origin=(0, 0, z_front_housing),
        )
        model.add_part(
            PartType.HOUSING_BACK,
            "housing_back",
            origin=(0, 0, z_back_housing),
        )

        # Coaxial gears
        model.add_part(
            PartType.GEAR_A,
            "gear_a",
            origin=(0, 0, z_gear_a),
        )
        model.add_part(
            PartType.GEAR_B,
            "gear_b",
            origin=(0, 0, z_gear_b),
        )

        # Dog clutch (centered between gears)
        model.add_part(
            PartType.DOG_CLUTCH,
            "dog_clutch",
            origin=(0, 0, z_clutch),
        )

        # Main axle
        model.add_part(
            PartType.AXLE_MAIN,
            "axle_main",
            origin=(0, 0, 0),
            metadata={"length": total_length + 10}  # Extra for protrusion
        )

        # Bevel gear pair - positioned so pitch cone apexes meet at one point
        # (bevel_face_width and bevel_pitch_radius calculated earlier)
        #
        # For 45-degree bevel gears meeting at 90 degrees:
        # - Driven bevel: axis along Z, apex at Z = origin_z + pitch_radius
        # - Driving bevel: axis along Y (after 90° X rotation), apex at Y = origin_y - pitch_radius
        # - Both apexes must meet at the SAME point in 3D space
        #
        # If driven is at (0, Yd, Zd), its apex is at (0, Yd, Zd + pitch_radius)
        # If driving is at (0, Yg, Zg), its apex is at (0, Yg - pitch_radius, Zg)
        # For apexes to meet: Yd = Yg - pitch_radius, and Zd + pitch_radius = Zg
        # Therefore: Yg = Yd + pitch_radius, Zg = Zd + pitch_radius

        # Driven bevel position (on lever pivot axis)
        # Adjusted Y to properly position lever pivot through driven bevel bore
        lever_pivot_y = s_offset_y - 1.5 * bevel_pitch_radius
        z_bevel_driven = z_clutch + clutch_width + 5.0

        # Driving bevel position - derived from apex meeting condition
        # Add clearance for 3D printing tolerance (teeth don't intersect)
        printing_clearance = 1.0  # 1mm clearance for FDM printing
        driving_y = lever_pivot_y + bevel_pitch_radius + printing_clearance
        z_bevel_driving = z_bevel_driven + bevel_pitch_radius + printing_clearance

        # Rotation offset for driving bevel to mesh teeth (half tooth pitch)
        teeth = spec.gears.bevel_teeth
        tooth_pitch_angle = 360.0 / teeth
        driving_rotation_offset = tooth_pitch_angle / 2  # Rotate by half a tooth to interleave

        # Lever (attached to lever pivot, fork reaches clutch)
        lever_z = z_clutch
        model.add_part(
            PartType.LEVER,
            "lever",
            origin=(0, lever_pivot_y, lever_z),
            rotation=(0, 0, 90),  # Rotate so fork faces clutch
        )

        # Hub height offset - the gear origin is at back face of frustum,
        # but hub extends behind it. Account for this in positioning.
        hub_height = bevel_face_width * 0.6

        # Driving bevel on S-axis
        # After 90° rotation around X: Z axis becomes -Y, so hub is at +Y side
        # Add Z rotation to offset teeth for proper mesh with driven bevel
        model.add_part(
            PartType.BEVEL_DRIVE,
            "bevel_driving",
            origin=(0, driving_y, z_bevel_driving),
            rotation=(90, 0, driving_rotation_offset),  # X rotation for axis, Z for tooth mesh
        )

        # S-axis - must pass through driving bevel bore
        # Driving bevel is rotated 90° so bore runs along Y axis at z_bevel_driving
        s_axis_length = s_offset_y + 20
        model.add_part(
            PartType.AXLE_S,
            "axle_s",
            origin=(0, s_offset_y, z_bevel_driving),  # Same Z as driving bevel
            rotation=(90, 0, 0),  # Rotate to align with Y axis
            metadata={"length": s_axis_length}
        )

        # Driven bevel on lever pivot axis
        # Teeth point up (+Z direction) toward driving bevel
        model.add_part(
            PartType.BEVEL_DRIVEN,
            "bevel_driven",
            origin=(0, lever_pivot_y, z_bevel_driven),
            rotation=(0, 0, 0),  # Axis along Z, teeth face up
        )

        # Lever pivot axle - must pass through driven bevel bore
        # Both driven bevel and lever pivot should be at the same Y
        lever_pivot_length = total_length * 0.4
        model.add_part(
            PartType.LEVER_PIVOT,
            "lever_pivot",
            origin=(0, lever_pivot_y, z_bevel_driven),
            rotation=(0, 0, 0),
            metadata={"length": lever_pivot_length}
        )

        # Flexure block (bolted to front housing outer face, supports S-shaft)
        # Mounting plate against housing, beam extends inward (-Y direction toward bevels)
        flexure_z = z_front_housing - housing_t / 2  # Outer face of housing
        model.add_part(
            PartType.FLEXURE_BLOCK,
            "flexure_block",
            origin=(0, s_offset_y, flexure_z),
            rotation=(0, 180, 0),  # Flip so beam points toward assembly center
        )

        # Define shaft axes
        model.add_shaft_axis(
            "main_axis",
            direction=(0, 0, 1),
            origin=(0, 0, 0),
            parts=["gear_a", "gear_b", "dog_clutch", "axle_main"],
        )
        model.add_shaft_axis(
            "s_axis",
            direction=(0, 1, 0),
            origin=(0, s_offset_y, z_clutch),
            parts=["axle_s"],
        )

        # Define mating constraints
        model.add_mate("axle_main", "gear_a", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("axle_main", "gear_b", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("axle_main", "dog_clutch", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("axle_main", "housing_front", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("axle_main", "housing_back", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("dog_clutch", "lever", "fork_groove", 0.5)
        model.add_mate("dog_clutch", "gear_a", "dog_clutch", 0)
        model.add_mate("dog_clutch", "gear_b", "dog_clutch", 0)
        model.add_mate("axle_s", "bevel_driving", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("bevel_driving", "bevel_driven", "gear_mesh", spec.tolerances.gear_backlash)
        model.add_mate("lever_pivot", "bevel_driven", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("lever_pivot", "lever", "pivot", 0)

        return model
