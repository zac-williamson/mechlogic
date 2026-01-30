"""Tests for combined selector mechanism bevel gear meshing."""

import pytest
import cadquery as cq

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType
from mechlogic.generators.gear_bevel import BevelGearGenerator
from mechlogic.generators.gear_spur import SpurGearGenerator
from mechlogic.generators.dog_clutch import DogClutchGenerator
from mechlogic.generators.shift_lever import ShiftLeverGenerator


@pytest.fixture
def spec():
    """Return a valid specification for testing."""
    spec_data = {
        "element": {"name": "test_mux", "type": "mux"},
        "inputs": {
            "a": {"shaft_diameter": 6.0},
            "b": {"shaft_diameter": 6.0},
            "s": {"shaft_diameter": 6.0},
        },
        "output": {"o": {"shaft_diameter": 6.0}},
        "gears": {
            "module": 1.5,
            "pressure_angle": 20,
            "coaxial_teeth": 24,
            "bevel_teeth": 16,
            "dog_clutch": {
                "teeth": 3,
                "tooth_height": 2.0,
                "engagement_depth": 1.5,
            },
        },
        "geometry": {
            "axle_length": 60.0,
            "housing_thickness": 4.0,
            "lever_throw": 8.0,
            "clutch_width": 10.0,
            "gear_face_width": 8.0,
            "gear_spacing": 1.0,
        },
        "flexure": {
            "thickness": 1.2,
            "length": 15.0,
            "max_deflection": 2.0,
        },
    }
    return LogicElementSpec.model_validate(spec_data)


def shapes_intersect(shape1, shape2, tolerance=0.01):
    """Check if two CadQuery shapes intersect."""
    try:
        intersection = shape1.intersect(shape2)
        vol = intersection.Volume()
        return vol > tolerance
    except Exception:
        return False


def create_meshed_bevel_gears(spec, driving_rotation_deg=0.0):
    """Create driving and driven bevel gears positioned for meshing.

    Based on the working generate_bevel_submodel.py layout:
    - Driving gear on Z-axis at Z = -mesh_distance, teeth pointing +Z
    - Driven gear on X-axis at X = -mesh_distance, rotated 90° around Y

    Args:
        spec: LogicElementSpec
        driving_rotation_deg: Additional rotation of driving gear around its axis

    Returns:
        Tuple of (driving_solid, driven_solid)
    """
    # Generate gears
    driving_gen = BevelGearGenerator(gear_id="driving")
    driven_gen = BevelGearGenerator(gear_id="driven")

    driving_placement = PartPlacement(part_type=PartType.BEVEL_DRIVE, part_id="driving")
    driven_placement = PartPlacement(part_type=PartType.BEVEL_DRIVEN, part_id="driven")

    driving_gear = driving_gen.generate(spec, driving_placement)
    driven_gear = driven_gen.generate(spec, driven_placement)

    # Get geometry for positioning
    cone_distance = driving_gen.get_cone_distance(spec)
    mesh_distance = cone_distance * 0.79
    teeth = spec.gears.bevel_teeth
    tooth_angle = 360.0 / teeth
    mesh_offset_angle = tooth_angle / 2

    # Driving gear: on Z-axis, teeth pointing +Z
    # Apply additional rotation around Z-axis before positioning
    driving_rotated = driving_gear
    if driving_rotation_deg != 0:
        driving_rotated = driving_rotated.rotate((0, 0, 0), (0, 0, 1), driving_rotation_deg)
    # Position at Z = -mesh_distance
    driving_positioned = driving_rotated.translate((0, 0, -mesh_distance))

    # Driven gear: flip so teeth point toward driving gear, add mesh alignment
    driven_rotated = (
        driven_gear
        .rotate((0, 0, 0), (1, 0, 0), 180)  # Flip so teeth point other way
        .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)  # Mesh alignment
        .rotate((0, 0, 0), (0, 1, 0), -90)  # Rotate to X-axis orientation
    )
    # Position at X = -mesh_distance
    driven_positioned = driven_rotated.translate((-mesh_distance, 0, 0))

    return driving_positioned.val(), driven_positioned.val()


class TestBevelGearMeshing:
    """Tests for bevel gear meshing in combined selector."""

    def test_default_no_intersection(self, spec):
        """In default position, bevel gears should not intersect (teeth interleave)."""
        driving, driven = create_meshed_bevel_gears(spec, driving_rotation_deg=0.0)

        assert not shapes_intersect(driving, driven), (
            "Bevel gears should not intersect in default meshed position "
            "(teeth should interleave in the gaps)"
        )

    def test_half_tooth_rotation_intersects(self, spec):
        """When driving gear is rotated by half a tooth, gears should intersect."""
        teeth = spec.gears.bevel_teeth
        half_tooth_angle = (360.0 / teeth) / 2  # Half of one tooth pitch

        driving, driven = create_meshed_bevel_gears(spec, driving_rotation_deg=half_tooth_angle)

        assert shapes_intersect(driving, driven), (
            f"Bevel gears should intersect when driving gear is rotated by "
            f"half a tooth ({half_tooth_angle:.1f}°) - teeth should collide"
        )

    def test_quarter_tooth_rotation_intersects(self, spec):
        """When driving gear is rotated by quarter tooth, gears should intersect."""
        teeth = spec.gears.bevel_teeth
        quarter_tooth_angle = (360.0 / teeth) / 4

        driving, driven = create_meshed_bevel_gears(spec, driving_rotation_deg=quarter_tooth_angle)

        assert shapes_intersect(driving, driven), (
            f"Bevel gears should intersect when driving gear is rotated by "
            f"quarter tooth ({quarter_tooth_angle:.1f}°)"
        )

    def test_full_tooth_rotation_no_intersection(self, spec):
        """When driving gear is rotated by full tooth, should not intersect again."""
        teeth = spec.gears.bevel_teeth
        full_tooth_angle = 360.0 / teeth  # One full tooth pitch

        driving, driven = create_meshed_bevel_gears(spec, driving_rotation_deg=full_tooth_angle)

        assert not shapes_intersect(driving, driven), (
            f"Bevel gears should not intersect when driving gear is rotated by "
            f"full tooth ({full_tooth_angle:.1f}°) - back to aligned position"
        )


def create_combined_selector_components(spec):
    """Create all components of the combined selector in idle position.

    Returns dict with all component solids positioned as in the assembly.
    """
    # Dimensions from generate_combined_selector.py
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    clutch_half_span = clutch_width / 2 + dog_tooth_height
    gear_teeth_end = face_width + dog_tooth_height

    gear_a_center = 0
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span
    engagement_travel = gear_spacing + dog_tooth_height
    gear_b_center = clutch_center + engagement_travel + clutch_half_span

    # Pivot location
    gear_od = spec.gears.module * spec.gears.coaxial_teeth
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27  # Must match shift_lever.py

    # Bevel gear positioning
    bevel_gen = BevelGearGenerator(gear_id="driving")
    cone_distance = bevel_gen.get_cone_distance(spec)
    mesh_distance = cone_distance * 0.79
    teeth = spec.gears.bevel_teeth
    tooth_angle = 360.0 / teeth
    mesh_offset_angle = tooth_angle / 2

    # Generate components
    gear_a_gen = SpurGearGenerator(gear_id="a")
    gear_b_gen = SpurGearGenerator(gear_id="b")
    clutch_gen = DogClutchGenerator()
    lever_gen = ShiftLeverGenerator()
    driving_bevel_gen = BevelGearGenerator(gear_id="driving")
    driven_bevel_gen = BevelGearGenerator(gear_id="driven")

    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="test")

    gear_a = gear_a_gen.generate(spec, placement)
    gear_b = gear_b_gen.generate(spec, placement)
    dog_clutch = clutch_gen.generate(spec, placement)
    shift_lever = lever_gen.generate(spec, placement)
    driving_bevel = driving_bevel_gen.generate(spec, placement)
    driven_bevel = driven_bevel_gen.generate(spec, placement)

    # Position spur gears (rotated to X-axis)
    gear_a_positioned = gear_a.rotate((0, 0, 0), (0, 1, 0), 90).translate((gear_a_center, 0, 0))
    gear_b_positioned = gear_b.rotate((0, 0, 0), (0, 1, 0), 90).translate((gear_b_center, 0, 0))

    # Position dog clutch
    clutch_positioned = dog_clutch.rotate((0, 0, 0), (0, 1, 0), 90).translate((clutch_center, 0, 0))

    # Position shift lever
    lever_positioned = shift_lever.translate((clutch_center, 0, 0))

    # Position driven bevel (on Z-axis)
    driven_bevel_positioned = driven_bevel.translate((clutch_center, pivot_y, -mesh_distance))

    # Position driving bevel (on X-axis, flipped and rotated)
    driving_bevel_positioned = (
        driving_bevel
        .rotate((0, 0, 0), (1, 0, 0), 180)
        .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)
        .rotate((0, 0, 0), (0, 1, 0), -90)
        .translate((clutch_center - mesh_distance, pivot_y, 0))
    )

    return {
        "gear_a": gear_a_positioned.val(),
        "gear_b": gear_b_positioned.val(),
        "dog_clutch": clutch_positioned.val(),
        "shift_lever": lever_positioned.val(),
        "driving_bevel": driving_bevel_positioned.val(),
        "driven_bevel": driven_bevel_positioned.val(),
    }


class TestCombinedSelectorIdlePosition:
    """Tests for combined selector in idle position - no components should intersect."""

    def test_driving_bevel_no_intersection_with_gear_a(self, spec):
        """Driving bevel gear should not intersect spur gear A."""
        components = create_combined_selector_components(spec)

        assert not shapes_intersect(components["driving_bevel"], components["gear_a"]), (
            "Driving bevel gear should not intersect gear A in idle position"
        )

    def test_driven_bevel_no_intersection_with_shift_lever(self, spec):
        """Driven bevel gear should not intersect shift lever."""
        components = create_combined_selector_components(spec)

        assert not shapes_intersect(components["driven_bevel"], components["shift_lever"]), (
            "Driven bevel gear should not intersect shift lever in idle position"
        )

    def test_driving_bevel_no_intersection_with_driven_bevel(self, spec):
        """Bevel gears should mesh without intersection."""
        components = create_combined_selector_components(spec)

        assert not shapes_intersect(components["driving_bevel"], components["driven_bevel"]), (
            "Bevel gears should not intersect in idle position (teeth should interleave)"
        )

    def test_shift_lever_no_intersection_with_dog_clutch(self, spec):
        """Shift lever should not intersect dog clutch in idle position."""
        components = create_combined_selector_components(spec)

        assert not shapes_intersect(components["shift_lever"], components["dog_clutch"]), (
            "Shift lever should not intersect dog clutch in idle position"
        )

    def test_dog_clutch_no_intersection_with_gear_a(self, spec):
        """Dog clutch should not intersect gear A in neutral position."""
        components = create_combined_selector_components(spec)

        assert not shapes_intersect(components["dog_clutch"], components["gear_a"]), (
            "Dog clutch should not intersect gear A in neutral position"
        )

    def test_dog_clutch_no_intersection_with_gear_b(self, spec):
        """Dog clutch should not intersect gear B in neutral position."""
        components = create_combined_selector_components(spec)

        assert not shapes_intersect(components["dog_clutch"], components["gear_b"]), (
            "Dog clutch should not intersect gear B in neutral position"
        )
