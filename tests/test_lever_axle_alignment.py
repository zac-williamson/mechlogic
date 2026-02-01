"""Tests for lever pivot axle alignment.

The driven bevel axle passes through the shift lever's pivot hole.
This test validates that:
- In idle state, the axle doesn't intersect the lever (passes through the hole)
- When offset by 0.3mm perpendicular to the axle, it does intersect
"""

import pytest
import cadquery as cq
import yaml

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType
from mechlogic.generators.shift_lever import ShiftLeverGenerator
from mechlogic.generators.gear_bevel import BevelGearGenerator


def shapes_intersect(shape1, shape2, tolerance=0.001):
    """Check if two shapes intersect."""
    try:
        if hasattr(shape1, 'val'):
            shape1 = shape1.val()
        if hasattr(shape2, 'val'):
            shape2 = shape2.val()
        intersection = shape1.intersect(shape2)
        return intersection.Volume() > tolerance
    except Exception:
        return False


def create_z_axle(x: float, y: float, z_start: float, z_end: float, diameter: float) -> cq.Workplane:
    """Create a cylindrical axle along the Z-axis."""
    length = z_end - z_start
    return (
        cq.Workplane('XY')
        .center(x, y)
        .circle(diameter / 2)
        .extrude(length)
        .translate((0, 0, z_start))
    )


@pytest.fixture
def spec():
    """Load the mux spec."""
    with open("examples/mux_2to1.yaml") as f:
        spec_data = yaml.safe_load(f)
    return LogicElementSpec.model_validate(spec_data)


@pytest.fixture
def mux_geometry(spec):
    """Calculate mux geometry positions."""
    module = spec.gears.module
    coaxial_teeth = spec.gears.coaxial_teeth
    shaft_diameter = spec.primary_shaft_diameter

    spur_pitch_diameter = module * coaxial_teeth
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    clutch_half_span = clutch_width / 2 + dog_tooth_height
    gear_teeth_end = face_width + dog_tooth_height
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span

    gear_od = spur_pitch_diameter
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27  # Must match shift_lever.py

    return {
        'shaft_diameter': shaft_diameter,
        'clutch_center': clutch_center,
        'pivot_y': pivot_y,
    }


@pytest.fixture
def lever(spec, mux_geometry):
    """Generate the shift lever in its assembly position."""
    g = mux_geometry
    placement = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id='test')

    lever = ShiftLeverGenerator().generate(spec, placement)

    # Position lever at clutch center (same as in assembly)
    # The lever is built with pivot at (0, pivot_y, 0), so translate X to clutch_center
    lever_positioned = lever.translate((g['clutch_center'], 0, 0))

    return lever_positioned


@pytest.fixture
def lever_pivot_axle(mux_geometry):
    """Create the axle that passes through the lever pivot hole.

    This is the driven bevel axle - it runs along Z at (clutch_center, pivot_y).
    """
    g = mux_geometry

    # Axle runs along Z, passing through the lever pivot
    # Extend from -50 to +50 to cover the full range
    return create_z_axle(
        x=g['clutch_center'],
        y=g['pivot_y'],
        z_start=-50,
        z_end=50,
        diameter=g['shaft_diameter']
    )


class TestLeverAxleIdleState:
    """Tests that axle passes through lever hole in idle state."""

    def test_lever_axle_no_intersection(self, lever, lever_pivot_axle):
        """Lever pivot axle should pass through lever hole without intersection."""
        assert not shapes_intersect(lever, lever_pivot_axle), (
            "Lever pivot axle should pass through lever hole without intersection"
        )


class TestLeverAxleOffsetIntersection:
    """Tests that axle intersects lever when offset perpendicular to axle.

    The axle runs along Z, so perpendicular directions are X and Y.
    """

    OFFSET = 0.3  # mm (clearance + 0.1mm)

    def test_lever_intersects_with_positive_x_offset(self, lever, lever_pivot_axle):
        """Axle offset +X should intersect lever."""
        offset_axle = lever_pivot_axle.translate((self.OFFSET, 0, 0))
        assert shapes_intersect(lever, offset_axle), (
            f"Lever should intersect axle when offset by +{self.OFFSET}mm in X"
        )

    def test_lever_intersects_with_negative_x_offset(self, lever, lever_pivot_axle):
        """Axle offset -X should intersect lever."""
        offset_axle = lever_pivot_axle.translate((-self.OFFSET, 0, 0))
        assert shapes_intersect(lever, offset_axle), (
            f"Lever should intersect axle when offset by -{self.OFFSET}mm in X"
        )

    def test_lever_intersects_with_positive_y_offset(self, lever, lever_pivot_axle):
        """Axle offset +Y should intersect lever."""
        offset_axle = lever_pivot_axle.translate((0, self.OFFSET, 0))
        assert shapes_intersect(lever, offset_axle), (
            f"Lever should intersect axle when offset by +{self.OFFSET}mm in Y"
        )

    def test_lever_intersects_with_negative_y_offset(self, lever, lever_pivot_axle):
        """Axle offset -Y should intersect lever."""
        offset_axle = lever_pivot_axle.translate((0, -self.OFFSET, 0))
        assert shapes_intersect(lever, offset_axle), (
            f"Lever should intersect axle when offset by -{self.OFFSET}mm in Y"
        )
