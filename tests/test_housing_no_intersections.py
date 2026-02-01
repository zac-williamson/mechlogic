"""Tests that housing components don't intersect with any other parts.

Validates that:
- Lower housing doesn't intersect with gears, clutch, lever, or bevel gears
- Upper housing doesn't intersect with gears, clutch, lever, or lower housing
- No housing-to-housing intersections
"""

import pytest
import cadquery as cq
import yaml

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType
from mechlogic.generators.gear_spur import SpurGearGenerator
from mechlogic.generators.dog_clutch import DogClutchGenerator
from mechlogic.generators.shift_lever import ShiftLeverGenerator
from mechlogic.generators.gear_bevel import BevelGearGenerator
from mechlogic.generators.lower_housing import LowerHousingGenerator, LowerHousingParams
from mechlogic.generators.upper_housing import UpperHousingGenerator, UpperHousingParams


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

    input_a_x, input_a_y, input_a_z = gear_a_center, 0, mesh_distance_spur
    input_b_x, input_b_y, input_b_z = gear_b_center, 0, -mesh_distance_spur

    gear_od = spur_pitch_diameter
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27

    bevel_gen = BevelGearGenerator(gear_id="driving")
    bevel_mesh_distance = bevel_gen.get_cone_distance(spec) * 0.79

    return {
        'module': module,
        'shaft_diameter': shaft_diameter,
        'spur_pitch_diameter': spur_pitch_diameter,
        'bevel_teeth': bevel_teeth,
        'gear_a_center': gear_a_center,
        'clutch_center': clutch_center,
        'gear_b_center': gear_b_center,
        'selector_axle_y': selector_axle_y,
        'selector_axle_z': selector_axle_z,
        'input_a_x': input_a_x,
        'input_a_y': input_a_y,
        'input_a_z': input_a_z,
        'input_b_x': input_b_x,
        'input_b_y': input_b_y,
        'input_b_z': input_b_z,
        'pivot_y': pivot_y,
        'bevel_mesh_distance': bevel_mesh_distance,
        'driving_bevel_x': clutch_center - bevel_mesh_distance,
        'driving_bevel_y': pivot_y,
        'driving_bevel_z': 0.0,
        'driven_bevel_x': clutch_center,
        'driven_bevel_y': pivot_y,
        'driven_bevel_z': -bevel_mesh_distance,
    }


@pytest.fixture
def lower_housing(mux_geometry):
    """Generate lower housing."""
    g = mux_geometry
    params = LowerHousingParams(
        selector_axle_y=g['selector_axle_y'],
        selector_axle_z=g['selector_axle_z'],
        input_a_y=g['input_a_y'],
        input_a_z=g['input_a_z'],
        input_b_y=g['input_b_y'],
        input_b_z=g['input_b_z'],
        axle_diameter=g['shaft_diameter'],
    )
    return LowerHousingGenerator(params).generate()


@pytest.fixture
def upper_housing(mux_geometry):
    """Generate upper housing."""
    g = mux_geometry
    params = UpperHousingParams(
        driving_bevel_x=g['driving_bevel_x'],
        driving_bevel_y=g['driving_bevel_y'],
        driving_bevel_z=g['driving_bevel_z'],
        driven_bevel_x=g['driven_bevel_x'],
        driven_bevel_y=g['driven_bevel_y'],
        driven_bevel_z=g['driven_bevel_z'],
        axle_diameter=g['shaft_diameter'],
    )
    return UpperHousingGenerator(params).generate()


@pytest.fixture
def components(spec, mux_geometry):
    """Generate all mechanism components in their final positions."""
    g = mux_geometry
    placement = PartPlacement(part_type=PartType.GEAR_A, part_id='test')
    bevel_tooth_angle = 360.0 / g['bevel_teeth']
    mesh_offset_angle = bevel_tooth_angle / 2

    # Generate base components
    gear_a = SpurGearGenerator(gear_id='a').generate(spec, placement)
    gear_b = SpurGearGenerator(gear_id='b').generate(spec, placement)
    dog_clutch = DogClutchGenerator().generate(spec, placement)
    shift_lever = ShiftLeverGenerator().generate(spec, placement)
    input_gear_a = SpurGearGenerator(gear_id='a').generate(spec, placement)
    input_gear_b = SpurGearGenerator(gear_id='b').generate(spec, placement)
    driving_bevel = BevelGearGenerator(gear_id='driving').generate(spec, placement)
    driven_bevel = BevelGearGenerator(gear_id='driven').generate(spec, placement)

    # Position components
    gear_a_positioned = (
        gear_a.rotate((0,0,0), (0,1,0), 90)
        .translate((g['gear_a_center'], g['selector_axle_y'], g['selector_axle_z']))
    )

    gear_b_positioned = (
        gear_b.rotate((0,0,0), (0,1,0), 90)
        .translate((g['gear_b_center'], g['selector_axle_y'], g['selector_axle_z']))
    )

    clutch_positioned = (
        dog_clutch.rotate((0,0,0), (0,1,0), 90)
        .translate((g['clutch_center'], g['selector_axle_y'], g['selector_axle_z']))
    )

    lever_positioned = shift_lever.translate(
        (g['clutch_center'], g['selector_axle_y'], g['selector_axle_z'])
    )

    input_a_positioned = (
        input_gear_a.rotate((0,0,0), (0,1,0), 90)
        .translate((g['input_a_x'], g['input_a_y'], g['input_a_z']))
    )

    input_b_positioned = (
        input_gear_b.rotate((0,0,0), (0,1,0), 90)
        .translate((g['input_b_x'], g['input_b_y'], g['input_b_z']))
    )

    driven_bevel_positioned = driven_bevel.translate(
        (g['clutch_center'], g['pivot_y'], -g['bevel_mesh_distance'])
    )

    driving_bevel_positioned = (
        driving_bevel
        .rotate((0,0,0), (1,0,0), 180)
        .rotate((0,0,0), (0,0,1), mesh_offset_angle)
        .rotate((0,0,0), (0,1,0), -90)
        .translate((g['clutch_center'] - g['bevel_mesh_distance'], g['pivot_y'], 0))
    )

    return {
        'gear_a': gear_a_positioned,
        'gear_b': gear_b_positioned,
        'clutch': clutch_positioned,
        'lever': lever_positioned,
        'input_a': input_a_positioned,
        'input_b': input_b_positioned,
        'driven_bevel': driven_bevel_positioned,
        'driving_bevel': driving_bevel_positioned,
    }


class TestLowerHousingNoIntersections:
    """Tests that lower housing doesn't intersect with mechanism components."""

    def test_lower_housing_no_intersection_with_gear_a(self, lower_housing, components):
        """Lower housing should not intersect with Gear A."""
        assert not shapes_intersect(lower_housing, components['gear_a']), (
            "Lower housing intersects with Gear A"
        )

    def test_lower_housing_no_intersection_with_gear_b(self, lower_housing, components):
        """Lower housing should not intersect with Gear B."""
        assert not shapes_intersect(lower_housing, components['gear_b']), (
            "Lower housing intersects with Gear B"
        )

    def test_lower_housing_no_intersection_with_clutch(self, lower_housing, components):
        """Lower housing should not intersect with dog clutch."""
        assert not shapes_intersect(lower_housing, components['clutch']), (
            "Lower housing intersects with dog clutch"
        )

    def test_lower_housing_no_intersection_with_lever(self, lower_housing, components):
        """Lower housing should not intersect with shift lever."""
        assert not shapes_intersect(lower_housing, components['lever']), (
            "Lower housing intersects with shift lever"
        )

    def test_lower_housing_no_intersection_with_input_a(self, lower_housing, components):
        """Lower housing should not intersect with Input A gear."""
        assert not shapes_intersect(lower_housing, components['input_a']), (
            "Lower housing intersects with Input A gear"
        )

    def test_lower_housing_no_intersection_with_input_b(self, lower_housing, components):
        """Lower housing should not intersect with Input B gear."""
        assert not shapes_intersect(lower_housing, components['input_b']), (
            "Lower housing intersects with Input B gear"
        )

    def test_lower_housing_no_intersection_with_driven_bevel(self, lower_housing, components):
        """Lower housing should not intersect with driven bevel gear."""
        assert not shapes_intersect(lower_housing, components['driven_bevel']), (
            "Lower housing intersects with driven bevel gear"
        )

    def test_lower_housing_no_intersection_with_driving_bevel(self, lower_housing, components):
        """Lower housing should not intersect with driving bevel gear."""
        assert not shapes_intersect(lower_housing, components['driving_bevel']), (
            "Lower housing intersects with driving bevel gear"
        )


class TestUpperHousingNoIntersections:
    """Tests that upper housing doesn't intersect with mechanism components."""

    def test_upper_housing_no_intersection_with_gear_a(self, upper_housing, components):
        """Upper housing should not intersect with Gear A."""
        assert not shapes_intersect(upper_housing, components['gear_a']), (
            "Upper housing intersects with Gear A"
        )

    def test_upper_housing_no_intersection_with_gear_b(self, upper_housing, components):
        """Upper housing should not intersect with Gear B."""
        assert not shapes_intersect(upper_housing, components['gear_b']), (
            "Upper housing intersects with Gear B"
        )

    def test_upper_housing_no_intersection_with_clutch(self, upper_housing, components):
        """Upper housing should not intersect with dog clutch."""
        assert not shapes_intersect(upper_housing, components['clutch']), (
            "Upper housing intersects with dog clutch"
        )

    def test_upper_housing_no_intersection_with_lever(self, upper_housing, components):
        """Upper housing should not intersect with shift lever."""
        assert not shapes_intersect(upper_housing, components['lever']), (
            "Upper housing intersects with shift lever"
        )

    def test_upper_housing_no_intersection_with_input_a(self, upper_housing, components):
        """Upper housing should not intersect with Input A gear."""
        assert not shapes_intersect(upper_housing, components['input_a']), (
            "Upper housing intersects with Input A gear"
        )

    def test_upper_housing_no_intersection_with_input_b(self, upper_housing, components):
        """Upper housing should not intersect with Input B gear."""
        assert not shapes_intersect(upper_housing, components['input_b']), (
            "Upper housing intersects with Input B gear"
        )

    def test_upper_housing_no_intersection_with_driven_bevel(self, upper_housing, components):
        """Upper housing should not intersect with driven bevel gear."""
        assert not shapes_intersect(upper_housing, components['driven_bevel']), (
            "Upper housing intersects with driven bevel gear"
        )

    def test_upper_housing_no_intersection_with_driving_bevel(self, upper_housing, components):
        """Upper housing should not intersect with driving bevel gear."""
        assert not shapes_intersect(upper_housing, components['driving_bevel']), (
            "Upper housing intersects with driving bevel gear"
        )


class TestHousingToHousingNoIntersections:
    """Tests that housing components don't intersect with each other."""

    def test_lower_upper_housing_no_intersection(self, lower_housing, upper_housing):
        """Lower and upper housing should not intersect."""
        assert not shapes_intersect(lower_housing, upper_housing), (
            "Lower housing intersects with upper housing"
        )
