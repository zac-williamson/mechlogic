"""Tests for mux assembly with upper housing integration.

Validates that the bevel gear axles (driving, driven) are properly
aligned with the upper housing holes.
"""

import pytest
import cadquery as cq
import yaml

from mechlogic.models.spec import LogicElementSpec
from mechlogic.generators.upper_housing import UpperHousingGenerator, UpperHousingParams
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
    """Calculate mux geometry positions for bevel gears."""
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
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span

    # Lever pivot position
    gear_od = spur_pitch_diameter
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27

    # Bevel mesh distance
    bevel_gen = BevelGearGenerator(gear_id="driving")
    bevel_mesh_distance = bevel_gen.get_cone_distance(spec) * 0.79

    # Driving bevel: at (clutch_center - bevel_mesh_distance, pivot_y, 0), axle along X
    driving_bevel_x = clutch_center - bevel_mesh_distance
    driving_bevel_y = pivot_y
    driving_bevel_z = 0.0

    # Driven bevel: at (clutch_center, pivot_y, -bevel_mesh_distance), axle along Z
    driven_bevel_x = clutch_center
    driven_bevel_y = pivot_y
    driven_bevel_z = -bevel_mesh_distance

    return {
        'shaft_diameter': shaft_diameter,
        'clutch_center': clutch_center,
        'pivot_y': pivot_y,
        'bevel_mesh_distance': bevel_mesh_distance,
        'driving_bevel_x': driving_bevel_x,
        'driving_bevel_y': driving_bevel_y,
        'driving_bevel_z': driving_bevel_z,
        'driven_bevel_x': driven_bevel_x,
        'driven_bevel_y': driven_bevel_y,
        'driven_bevel_z': driven_bevel_z,
    }


@pytest.fixture
def housing_params(mux_geometry):
    """Create housing params matching the mux geometry."""
    g = mux_geometry
    return UpperHousingParams(
        driving_bevel_y=g['driving_bevel_y'],
        driving_bevel_z=g['driving_bevel_z'],
        driven_bevel_x=g['driven_bevel_x'],
        driven_bevel_y=g['driven_bevel_y'],
        axle_diameter=g['shaft_diameter'],
    )


@pytest.fixture
def housing(housing_params):
    """Generate the upper housing."""
    gen = UpperHousingGenerator(housing_params)
    return gen.generate()


@pytest.fixture
def mux_axles(mux_geometry, housing_params):
    """Create bevel axles that extend through all housing plates."""
    g = mux_geometry
    p = housing_params

    # Driving bevel axle extends along X through both YZ plates
    driving_x_start = p.driving_left_plate_x - 20
    driving_x_end = p.driving_right_plate_x + 20

    # Driven bevel axle extends along Z through both XY plates
    driven_z_start = p.driven_front_plate_z - 20
    driven_z_end = p.driven_back_plate_z + 20

    return {
        'driving': create_x_axle(
            g['driving_bevel_y'], g['driving_bevel_z'],
            driving_x_start, driving_x_end, g['shaft_diameter']
        ),
        'driven': create_z_axle(
            g['driven_bevel_x'], g['driven_bevel_y'],
            driven_z_start, driven_z_end, g['shaft_diameter']
        ),
    }


class TestMuxUpperHousingIdleState:
    """Tests that housing doesn't intersect axles in idle (aligned) position."""

    def test_driving_axle_no_intersection(self, housing, mux_axles):
        """Driving bevel axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, mux_axles['driving']), (
            "Driving bevel axle should not intersect housing in idle state"
        )

    def test_driven_axle_no_intersection(self, housing, mux_axles):
        """Driven bevel axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, mux_axles['driven']), (
            "Driven bevel axle should not intersect housing in idle state"
        )


class TestMuxUpperHousingDrivingAxleOffset:
    """Tests that housing intersects driving axle when offset 0.3mm orthogonally."""

    OFFSET = 0.3  # mm (clearance + 0.1mm)

    def _offset_housing(self, housing, dy: float, dz: float) -> cq.Workplane:
        return housing.translate((0, dy, dz))

    def test_driving_axle_intersects_with_positive_y_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['driving']), (
            f"Driving axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_driving_axle_intersects_with_negative_y_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['driving']), (
            f"Driving axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_driving_axle_intersects_with_positive_z_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['driving']), (
            f"Driving axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_driving_axle_intersects_with_negative_z_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['driving']), (
            f"Driving axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )


class TestMuxUpperHousingDrivenAxleOffset:
    """Tests that housing intersects driven axle when offset 0.3mm orthogonally."""

    OFFSET = 0.3  # mm (clearance + 0.1mm)

    def _offset_housing(self, housing, dx: float, dy: float) -> cq.Workplane:
        return housing.translate((dx, dy, 0))

    def test_driven_axle_intersects_with_positive_x_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dx=self.OFFSET, dy=0)
        assert shapes_intersect(offset_housing, mux_axles['driven']), (
            f"Driven axle should intersect housing when offset by +{self.OFFSET}mm in X"
        )

    def test_driven_axle_intersects_with_negative_x_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dx=-self.OFFSET, dy=0)
        assert shapes_intersect(offset_housing, mux_axles['driven']), (
            f"Driven axle should intersect housing when offset by -{self.OFFSET}mm in X"
        )

    def test_driven_axle_intersects_with_positive_y_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dx=0, dy=self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['driven']), (
            f"Driven axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_driven_axle_intersects_with_negative_y_offset(self, housing, mux_axles):
        offset_housing = self._offset_housing(housing, dx=0, dy=-self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['driven']), (
            f"Driven axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )


class TestMuxUpperAxleExtent:
    """Tests that axles extend through all their respective plates."""

    def test_driving_axle_extends_past_left_plate(self, mux_axles, housing_params):
        axle = mux_axles['driving']
        bbox = axle.val().BoundingBox()
        assert bbox.xmin < housing_params.driving_left_plate_x, (
            f"Driving axle xmin ({bbox.xmin}) should be < left plate ({housing_params.driving_left_plate_x})"
        )

    def test_driving_axle_extends_past_right_plate(self, mux_axles, housing_params):
        axle = mux_axles['driving']
        bbox = axle.val().BoundingBox()
        assert bbox.xmax > housing_params.driving_right_plate_x, (
            f"Driving axle xmax ({bbox.xmax}) should be > right plate ({housing_params.driving_right_plate_x})"
        )

    def test_driven_axle_extends_past_front_plate(self, mux_axles, housing_params):
        axle = mux_axles['driven']
        bbox = axle.val().BoundingBox()
        assert bbox.zmin < housing_params.driven_front_plate_z, (
            f"Driven axle zmin ({bbox.zmin}) should be < front plate ({housing_params.driven_front_plate_z})"
        )

    def test_driven_axle_extends_past_back_plate(self, mux_axles, housing_params):
        axle = mux_axles['driven']
        bbox = axle.val().BoundingBox()
        assert bbox.zmax > housing_params.driven_back_plate_z, (
            f"Driven axle zmax ({bbox.zmax}) should be > back plate ({housing_params.driven_back_plate_z})"
        )
