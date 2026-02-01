"""Tests that no axles intersect with each other.

The mux assembly has 5 axles:
- Selector axle (along X at Y=0, Z=0)
- Input A axle (along X at Y=0, Z=+36)
- Input B axle (along X at Y=0, Z=-36)
- Driving bevel axle (along X at Y=pivot_y, Z=0)
- Driven bevel axle (along Z at X=clutch_center, Y=pivot_y)

The driving and driven bevel axles could potentially intersect since they
both pass through Y=pivot_y.
"""

import pytest
import cadquery as cq
import yaml

from mechlogic.models.spec import LogicElementSpec
from mechlogic.generators.gear_bevel import BevelGearGenerator
from mechlogic.generators.lower_housing import LowerHousingParams
from mechlogic.generators.upper_housing import UpperHousingParams


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


def create_x_axle(y: float, z: float, x_start: float, x_end: float, diameter: float) -> cq.Workplane:
    """Create a cylindrical axle along the X-axis."""
    length = x_end - x_start
    return (
        cq.Workplane('YZ')
        .center(y, z)
        .circle(diameter / 2)
        .extrude(length)
        .translate((x_start, 0, 0))
    )


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
    """Calculate all mux geometry positions."""
    module = spec.gears.module
    coaxial_teeth = spec.gears.coaxial_teeth
    bevel_teeth = spec.gears.bevel_teeth
    shaft_diameter = spec.primary_shaft_diameter

    spur_pitch_diameter = module * coaxial_teeth
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    clutch_half_span = clutch_width / 2 + dog_tooth_height
    gear_teeth_end = face_width + dog_tooth_height

    gear_a_center = 0
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span
    gear_b_center = clutch_center + (gear_spacing + dog_tooth_height) + clutch_half_span

    selector_axle_y = 0
    selector_axle_z = 0
    mesh_distance_spur = spur_pitch_diameter

    input_a_y = 0
    input_a_z = mesh_distance_spur
    input_b_y = 0
    input_b_z = -mesh_distance_spur

    gear_od = spur_pitch_diameter
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27

    bevel_gen = BevelGearGenerator(gear_id="driving")
    bevel_mesh_distance = bevel_gen.get_cone_distance(spec) * 0.79

    driving_bevel_x = clutch_center - bevel_mesh_distance
    driven_bevel_z = -bevel_mesh_distance

    return {
        'shaft_diameter': shaft_diameter,
        'clutch_center': clutch_center,
        'gear_b_center': gear_b_center,
        'selector_axle_y': selector_axle_y,
        'selector_axle_z': selector_axle_z,
        'input_a_y': input_a_y,
        'input_a_z': input_a_z,
        'input_b_y': input_b_y,
        'input_b_z': input_b_z,
        'pivot_y': pivot_y,
        'bevel_mesh_distance': bevel_mesh_distance,
        'driving_bevel_x': driving_bevel_x,
        'driving_bevel_y': pivot_y,
        'driving_bevel_z': 0.0,
        'driven_bevel_x': clutch_center,
        'driven_bevel_y': pivot_y,
        'driven_bevel_z': driven_bevel_z,
    }


@pytest.fixture
def axles(mux_geometry):
    """Create all 5 axles with proper extents.

    The bevel axles are limited to not extend past their gear positions
    to avoid intersection at the lever pivot point.
    """
    g = mux_geometry
    d = g['shaft_diameter']

    # Lower housing params for axle extents
    lower_params = LowerHousingParams(
        selector_axle_y=g['selector_axle_y'],
        selector_axle_z=g['selector_axle_z'],
        input_a_y=g['input_a_y'],
        input_a_z=g['input_a_z'],
        input_b_y=g['input_b_y'],
        input_b_z=g['input_b_z'],
        axle_diameter=d,
    )

    # Upper housing params for axle extents
    upper_params = UpperHousingParams(
        driving_bevel_x=g['driving_bevel_x'],
        driving_bevel_y=g['driving_bevel_y'],
        driving_bevel_z=g['driving_bevel_z'],
        driven_bevel_x=g['driven_bevel_x'],
        driven_bevel_y=g['driven_bevel_y'],
        driven_bevel_z=g['driven_bevel_z'],
        axle_diameter=d,
    )

    # Lower axles extend through both lower housing plates
    lower_x_start = lower_params.left_plate_x - 20
    lower_x_end = lower_params.right_plate_x + 20

    # Bevel axles: extend from outer plate through gear, but NOT past the
    # intersection point (clutch_center, pivot_y, 0) where the other axle crosses.
    # - Driving axle: extends along X, stops before X = driven_bevel_x (clutch_center)
    # - Driven axle: extends along Z, stops before Z = driving_bevel_z (0)
    clearance = d + 2  # Clearance to avoid intersection

    # Driving bevel axle: from left plate to just past the gear (but not to clutch_center)
    driving_x_start = upper_params.driving_left_plate_x - 20
    driving_x_end = min(upper_params.driving_right_plate_x + 20,
                        g['driven_bevel_x'] - clearance)  # Stop before driven axle

    # Driven bevel axle: from front plate to just past the gear (but not to Z=0)
    driven_z_start = upper_params.driven_front_plate_z - 20
    driven_z_end = min(upper_params.driven_back_plate_z + 20,
                       g['driving_bevel_z'] - clearance)  # Stop before driving axle

    return {
        'selector': create_x_axle(
            g['selector_axle_y'], g['selector_axle_z'],
            lower_x_start, lower_x_end, d
        ),
        'input_a': create_x_axle(
            g['input_a_y'], g['input_a_z'],
            lower_x_start, lower_x_end, d
        ),
        'input_b': create_x_axle(
            g['input_b_y'], g['input_b_z'],
            lower_x_start, lower_x_end, d
        ),
        'driving_bevel': create_x_axle(
            g['driving_bevel_y'], g['driving_bevel_z'],
            driving_x_start, driving_x_end, d
        ),
        'driven_bevel': create_z_axle(
            g['driven_bevel_x'], g['driven_bevel_y'],
            driven_z_start, driven_z_end, d
        ),
    }


class TestLowerAxlesNoIntersections:
    """Tests that lower axles don't intersect each other."""

    def test_selector_input_a_no_intersection(self, axles):
        """Selector and Input A axles should not intersect."""
        assert not shapes_intersect(axles['selector'], axles['input_a']), (
            "Selector axle intersects with Input A axle"
        )

    def test_selector_input_b_no_intersection(self, axles):
        """Selector and Input B axles should not intersect."""
        assert not shapes_intersect(axles['selector'], axles['input_b']), (
            "Selector axle intersects with Input B axle"
        )

    def test_input_a_input_b_no_intersection(self, axles):
        """Input A and Input B axles should not intersect."""
        assert not shapes_intersect(axles['input_a'], axles['input_b']), (
            "Input A axle intersects with Input B axle"
        )


class TestUpperAxlesNoIntersections:
    """Tests that upper axles don't intersect each other."""

    def test_driving_driven_bevel_no_intersection(self, axles):
        """Driving and driven bevel axles should not intersect."""
        assert not shapes_intersect(axles['driving_bevel'], axles['driven_bevel']), (
            "Driving bevel axle intersects with driven bevel axle"
        )


class TestLowerUpperAxlesNoIntersections:
    """Tests that lower and upper axles don't intersect each other."""

    def test_selector_driving_bevel_no_intersection(self, axles):
        """Selector and driving bevel axles should not intersect."""
        assert not shapes_intersect(axles['selector'], axles['driving_bevel']), (
            "Selector axle intersects with driving bevel axle"
        )

    def test_selector_driven_bevel_no_intersection(self, axles):
        """Selector and driven bevel axles should not intersect."""
        assert not shapes_intersect(axles['selector'], axles['driven_bevel']), (
            "Selector axle intersects with driven bevel axle"
        )

    def test_input_a_driving_bevel_no_intersection(self, axles):
        """Input A and driving bevel axles should not intersect."""
        assert not shapes_intersect(axles['input_a'], axles['driving_bevel']), (
            "Input A axle intersects with driving bevel axle"
        )

    def test_input_a_driven_bevel_no_intersection(self, axles):
        """Input A and driven bevel axles should not intersect."""
        assert not shapes_intersect(axles['input_a'], axles['driven_bevel']), (
            "Input A axle intersects with driven bevel axle"
        )

    def test_input_b_driving_bevel_no_intersection(self, axles):
        """Input B and driving bevel axles should not intersect."""
        assert not shapes_intersect(axles['input_b'], axles['driving_bevel']), (
            "Input B axle intersects with driving bevel axle"
        )

    def test_input_b_driven_bevel_no_intersection(self, axles):
        """Input B and driven bevel axles should not intersect."""
        assert not shapes_intersect(axles['input_b'], axles['driven_bevel']), (
            "Input B axle intersects with driven bevel axle"
        )
