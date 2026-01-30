"""Tests for shift lever geometry and clutch engagement."""

import pytest
import cadquery as cq

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType
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


def create_lever_and_clutch(spec, lever_rotation_deg=0.0):
    """Create shift lever and dog clutch positioned for testing.

    Args:
        spec: LogicElementSpec
        lever_rotation_deg: Rotation of lever around its pivot axis (degrees)

    Returns:
        Tuple of (lever_solid, clutch_solid)
    """
    # Generate components
    clutch_gen = DogClutchGenerator()
    lever_gen = ShiftLeverGenerator()

    placement = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="test")

    clutch = clutch_gen.generate(spec, placement)
    lever = lever_gen.generate(spec, placement)

    # Rotate clutch to align with X-axis (as in selector mechanism)
    clutch = clutch.rotate((0, 0, 0), (0, 1, 0), 90)

    # Get pivot location from lever generator for rotation
    # The lever is in XY plane, rotates around Z axis through pivot point
    gear_od = spec.gears.module * spec.gears.coaxial_teeth
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 25  # Must match shift_lever.py

    # Rotate lever around Z-axis through pivot point
    # This moves the fork along the X direction (clutch axis)
    if lever_rotation_deg != 0:
        lever = lever.rotate((0, pivot_y, 0), (0, 0, 1), lever_rotation_deg)

    return lever.val(), clutch.val()


class TestShiftLeverGeometry:
    """Tests for shift lever geometry relative to dog clutch."""

    def test_idle_no_intersection(self, spec):
        """In idle position (0° rotation), lever does not intersect clutch."""
        lever, clutch = create_lever_and_clutch(spec, lever_rotation_deg=0.0)

        assert not shapes_intersect(lever, clutch), (
            "Lever should not intersect clutch in idle position (0° rotation)"
        )

    @pytest.mark.parametrize("angle", [-20, -16, 16, 20])
    def test_rotated_intersects(self, spec, angle):
        """When lever is rotated beyond clearance range, it intersects the clutch."""
        lever, clutch = create_lever_and_clutch(spec, lever_rotation_deg=angle)

        assert shapes_intersect(lever, clutch), (
            f"Lever should intersect clutch when rotated by {angle}° "
            "(fork should enter groove)"
        )

    @pytest.mark.parametrize("y_offset", [1, 5, 20])
    def test_assembly_clearance(self, spec, y_offset):
        """Lever can be assembled by sliding down onto clutch (no interference)."""
        lever, clutch = create_lever_and_clutch(spec, lever_rotation_deg=0.0)

        # Move lever up by y_offset - should not intersect
        # This simulates assembling the lever by lowering it onto the clutch
        lever_shifted = cq.Workplane().add(lever).translate((0, y_offset, 0)).val()

        assert not shapes_intersect(lever_shifted, clutch), (
            f"Lever should not intersect clutch when moved up by {y_offset}mm "
            "(must be possible to assemble by sliding down)"
        )


class TestLeverClutchEngagement:
    """Tests for lever fitting in clutch groove during engagement."""

    def test_lever_fits_in_groove_when_clutch_engaged_with_gear_b(self, spec):
        """Find a valid rotation angle where lever fits in clutch groove.

        When the dog clutch is engaged with gear B (orange), the lever must
        be rotated to follow. There should be an angle between 0-20 degrees
        where the lever fork fits snugly in the groove without intersection.
        """
        # Calculate engagement travel (same as generate_selector_mechanism.py)
        gear_spacing = spec.geometry.gear_spacing
        dog_tooth_height = spec.gears.dog_clutch.tooth_height
        engagement_travel = gear_spacing + dog_tooth_height

        # Get pivot location for rotation
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        clutch_od = gear_od * 0.4
        pivot_y = clutch_od / 2 + 25

        # Generate components
        clutch_gen = DogClutchGenerator()
        lever_gen = ShiftLeverGenerator()
        placement = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="test")

        clutch = clutch_gen.generate(spec, placement)
        lever = lever_gen.generate(spec, placement)

        # Rotate clutch to align with X-axis and move to engaged position
        clutch = clutch.rotate((0, 0, 0), (0, 1, 0), 90)
        clutch = clutch.translate((engagement_travel, 0, 0))
        clutch_solid = clutch.val()

        # Try angles from 0 to 20 degrees to find one that fits
        valid_angles = []
        for angle_tenth in range(0, 201):  # 0.0 to 20.0 in 0.1 degree steps
            angle = angle_tenth / 10.0

            # Rotate lever around Z-axis through pivot point
            rotated_lever = lever.rotate((0, pivot_y, 0), (0, pivot_y, 1), angle)
            lever_solid = rotated_lever.val()

            if not shapes_intersect(lever_solid, clutch_solid):
                valid_angles.append(angle)

        assert len(valid_angles) > 0, (
            f"No valid rotation angle found between 0-20 degrees where lever "
            f"fits in clutch groove when clutch is engaged with gear B "
            f"(engagement_travel={engagement_travel}mm). "
            f"The lever may be too thick or the groove too narrow."
        )

        # Report the valid range
        print(f"\nValid lever angles when clutch engaged with gear B: "
              f"{min(valid_angles):.1f}° to {max(valid_angles):.1f}°")
