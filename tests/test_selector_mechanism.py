"""Tests for selector mechanism clutch engagement."""

import pytest
import cadquery as cq

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType
from mechlogic.generators.gear_spur import SpurGearGenerator
from mechlogic.generators.dog_clutch import DogClutchGenerator


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
            "gear_spacing": 3.0,
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


def create_selector_components(spec):
    """Create the selector mechanism components.

    Returns dict with gear_a, gear_b, clutch workplanes and position info.
    """
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    # Generate components
    gear_a_gen = SpurGearGenerator(gear_id="a")
    gear_b_gen = SpurGearGenerator(gear_id="b")
    clutch_gen = DogClutchGenerator()

    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="test")

    gear_a = gear_a_gen.generate(spec, placement)
    gear_b = gear_b_gen.generate(spec, placement)
    clutch = clutch_gen.generate(spec, placement)

    # Rotate to align with X-axis (as in generate_selector_mechanism.py)
    gear_a = gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
    gear_b = gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
    clutch = clutch.rotate((0, 0, 0), (0, 1, 0), 90)

    # Calculate positions (same as generate_selector_mechanism.py)
    clutch_half_span = clutch_width / 2 + dog_tooth_height
    gear_teeth_end = face_width + dog_tooth_height

    gear_a_center = 0
    clutch_center_neutral = gear_teeth_end + gear_spacing + clutch_half_span

    engagement_travel = gear_spacing + dog_tooth_height

    # Gear B: positioned so teeth align with clutch when engaged
    gear_b_center = clutch_center_neutral + engagement_travel + clutch_half_span

    return {
        "gear_a": gear_a,
        "gear_b": gear_b,
        "clutch": clutch,
        "gear_a_center": gear_a_center,
        "gear_b_center": gear_b_center,
        "clutch_center_neutral": clutch_center_neutral,
        "engagement_travel": engagement_travel,
    }


def position_components(components, clutch_offset=0.0, clutch_rotation=0.0):
    """Position components and return solids for intersection testing.

    Args:
        components: Dict from create_selector_components
        clutch_offset: X offset from neutral position (negative = toward A, positive = toward B)
        clutch_rotation: Rotation of clutch around X-axis in degrees

    Returns:
        Tuple of (gear_a_solid, gear_b_solid, clutch_solid)
    """
    gear_a = components["gear_a"].translate((components["gear_a_center"], 0, 0))
    gear_b = components["gear_b"].translate((components["gear_b_center"], 0, 0))

    clutch_x = components["clutch_center_neutral"] + clutch_offset
    clutch = components["clutch"]
    if clutch_rotation != 0:
        clutch = clutch.rotate((0, 0, 0), (1, 0, 0), clutch_rotation)
    clutch = clutch.translate((clutch_x, 0, 0))

    return gear_a.val(), gear_b.val(), clutch.val()


class TestSelectorMechanismClutch:
    """Tests for clutch engagement in the selector mechanism."""

    def test_neutral_no_intersection_with_gear_a(self, spec):
        """In neutral position, clutch does not intersect with gear A (blue)."""
        components = create_selector_components(spec)
        gear_a, gear_b, clutch = position_components(components, clutch_offset=0.0)

        assert not shapes_intersect(gear_a, clutch), (
            "Clutch should not intersect gear A in neutral position"
        )

    def test_neutral_no_intersection_with_gear_b(self, spec):
        """In neutral position, clutch does not intersect with gear B (orange)."""
        components = create_selector_components(spec)
        gear_a, gear_b, clutch = position_components(components, clutch_offset=0.0)

        assert not shapes_intersect(gear_b, clutch), (
            "Clutch should not intersect gear B in neutral position"
        )

    def test_engaged_with_gear_a_no_intersection(self, spec):
        """When engaged with gear A, clutch does not intersect (teeth interleave)."""
        components = create_selector_components(spec)
        engagement = components["engagement_travel"]

        gear_a, gear_b, clutch = position_components(
            components, clutch_offset=-engagement  # Move toward gear A
        )

        assert not shapes_intersect(gear_a, clutch), (
            "Clutch should not intersect gear A when properly engaged "
            "(teeth should interleave in the gaps)"
        )

    def test_engaged_with_gear_a_misaligned_rotation_intersects(self, spec):
        """When engaged with gear A but rotated to misalign teeth, clutch intersects."""
        components = create_selector_components(spec)
        engagement = components["engagement_travel"]

        # Rotation of 30° puts clutch teeth directly against gear teeth
        # (teeth occupy ~45% of the arc, gaps ~55%, so 30° rotation
        # moves teeth from the gap into collision with gear teeth)
        misalign_angle = 30.0

        gear_a, gear_b, clutch = position_components(
            components,
            clutch_offset=-engagement,  # Move toward gear A
            clutch_rotation=misalign_angle
        )

        assert shapes_intersect(gear_a, clutch), (
            "Clutch should intersect gear A when rotated to misalign teeth "
            "(teeth collide instead of interleaving)"
        )

    def test_engaged_with_gear_b_no_intersection(self, spec):
        """When engaged with gear B, clutch does not intersect (teeth interleave)."""
        components = create_selector_components(spec)
        engagement = components["engagement_travel"]

        gear_a, gear_b, clutch = position_components(
            components, clutch_offset=engagement  # Move toward gear B
        )

        assert not shapes_intersect(gear_b, clutch), (
            "Clutch should not intersect gear B when properly engaged "
            "(teeth should interleave in the gaps)"
        )

    def test_engaged_with_gear_b_misaligned_rotation_intersects(self, spec):
        """When engaged with gear B but rotated to misalign teeth, clutch intersects."""
        components = create_selector_components(spec)
        engagement = components["engagement_travel"]

        # Rotation of 30° puts clutch teeth directly against gear teeth
        misalign_angle = 30.0

        gear_a, gear_b, clutch = position_components(
            components,
            clutch_offset=engagement,  # Move toward gear B
            clutch_rotation=misalign_angle
        )

        assert shapes_intersect(gear_b, clutch), (
            "Clutch should intersect gear B when rotated to misalign teeth "
            "(teeth collide instead of interleaving)"
        )
