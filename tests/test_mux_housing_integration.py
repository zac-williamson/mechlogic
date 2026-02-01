"""Tests for mux assembly with lower housing integration.

Validates that the three lower axles (selector, input_a, input_b) are properly
aligned with the housing holes and will intersect if the housing is misaligned.
"""

import pytest
import cadquery as cq
import yaml

from mechlogic.models.spec import LogicElementSpec
from mechlogic.generators.lower_housing import LowerHousingGenerator, LowerHousingParams


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


def create_axle(y: float, z: float, x_start: float, x_end: float, diameter: float) -> cq.Workplane:
    """Create a cylindrical axle along the X-axis."""
    length = x_end - x_start
    axle = (
        cq.Workplane('YZ')
        .center(y, z)
        .circle(diameter / 2)
        .extrude(length)
        .translate((x_start, 0, 0))
    )
    return axle


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

    gear_a_center = 0
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span
    gear_b_center = clutch_center + (gear_spacing + dog_tooth_height) + clutch_half_span

    # Axle positions
    selector_axle_y = 0
    selector_axle_z = 0
    mesh_distance_spur = spur_pitch_diameter

    input_a_x = gear_a_center
    input_a_y = 0
    input_a_z = mesh_distance_spur  # +36 with default spec

    input_b_x = gear_b_center
    input_b_y = 0
    input_b_z = -mesh_distance_spur  # -36 with default spec

    return {
        'shaft_diameter': shaft_diameter,
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
    }


@pytest.fixture
def housing_params(mux_geometry):
    """Create housing params matching the mux geometry."""
    return LowerHousingParams(
        selector_axle_y=mux_geometry['selector_axle_y'],
        selector_axle_z=mux_geometry['selector_axle_z'],
        input_a_y=mux_geometry['input_a_y'],
        input_a_z=mux_geometry['input_a_z'],
        input_b_y=mux_geometry['input_b_y'],
        input_b_z=mux_geometry['input_b_z'],
        axle_diameter=mux_geometry['shaft_diameter'],
    )


@pytest.fixture
def housing(housing_params):
    """Generate the lower housing."""
    gen = LowerHousingGenerator(housing_params)
    return gen.generate()


@pytest.fixture
def mux_axles(mux_geometry, housing_params):
    """Create axles that extend through both housing plates.

    Axles must pass through both the left plate (X=-20) and right plate (X=40)
    to properly test housing alignment.
    """
    p = housing_params
    g = mux_geometry

    # Axles extend from well before left plate to well after right plate
    x_start = p.left_plate_x - 20  # -40
    x_end = p.right_plate_x + 20   # +60
    diameter = g['shaft_diameter']

    return {
        'selector': create_axle(
            g['selector_axle_y'],
            g['selector_axle_z'],
            x_start, x_end, diameter
        ),
        'input_a': create_axle(
            g['input_a_y'],
            g['input_a_z'],
            x_start, x_end, diameter
        ),
        'input_b': create_axle(
            g['input_b_y'],
            g['input_b_z'],
            x_start, x_end, diameter
        ),
    }


class TestMuxHousingIdleState:
    """Tests that housing doesn't intersect axles in idle (aligned) position."""

    def test_selector_axle_no_intersection(self, housing, mux_axles):
        """Selector axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, mux_axles['selector']), (
            "Selector axle should not intersect housing in idle state"
        )

    def test_input_a_axle_no_intersection(self, housing, mux_axles):
        """Input A axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, mux_axles['input_a']), (
            "Input A axle should not intersect housing in idle state"
        )

    def test_input_b_axle_no_intersection(self, housing, mux_axles):
        """Input B axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, mux_axles['input_b']), (
            "Input B axle should not intersect housing in idle state"
        )


class TestMuxHousingOffsetIntersection:
    """Tests that housing intersects axles when offset by 0.3mm orthogonally.

    The housing has 0.2mm clearance per side, so a 0.3mm offset should cause
    a 0.1mm overlap/intersection.
    """

    OFFSET = 0.3  # mm (clearance + 0.1mm)

    def _offset_housing(self, housing, dy: float, dz: float) -> cq.Workplane:
        """Return housing offset by given amounts in Y and Z."""
        return housing.translate((0, dy, dz))

    # --- Selector axle tests ---

    def test_selector_axle_intersects_with_positive_y_offset(self, housing, mux_axles):
        """Housing offset +Y should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['selector']), (
            f"Selector axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_selector_axle_intersects_with_negative_y_offset(self, housing, mux_axles):
        """Housing offset -Y should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['selector']), (
            f"Selector axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_selector_axle_intersects_with_positive_z_offset(self, housing, mux_axles):
        """Housing offset +Z should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['selector']), (
            f"Selector axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_selector_axle_intersects_with_negative_z_offset(self, housing, mux_axles):
        """Housing offset -Z should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['selector']), (
            f"Selector axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )

    # --- Input A axle tests ---

    def test_input_a_axle_intersects_with_positive_y_offset(self, housing, mux_axles):
        """Housing offset +Y should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['input_a']), (
            f"Input A axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_input_a_axle_intersects_with_negative_y_offset(self, housing, mux_axles):
        """Housing offset -Y should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['input_a']), (
            f"Input A axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_input_a_axle_intersects_with_positive_z_offset(self, housing, mux_axles):
        """Housing offset +Z should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['input_a']), (
            f"Input A axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_input_a_axle_intersects_with_negative_z_offset(self, housing, mux_axles):
        """Housing offset -Z should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['input_a']), (
            f"Input A axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )

    # --- Input B axle tests ---

    def test_input_b_axle_intersects_with_positive_y_offset(self, housing, mux_axles):
        """Housing offset +Y should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['input_b']), (
            f"Input B axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_input_b_axle_intersects_with_negative_y_offset(self, housing, mux_axles):
        """Housing offset -Y should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, mux_axles['input_b']), (
            f"Input B axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_input_b_axle_intersects_with_positive_z_offset(self, housing, mux_axles):
        """Housing offset +Z should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['input_b']), (
            f"Input B axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_input_b_axle_intersects_with_negative_z_offset(self, housing, mux_axles):
        """Housing offset -Z should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, mux_axles['input_b']), (
            f"Input B axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )


class TestMuxAxleExtent:
    """Tests that axles extend through both housing plates."""

    def test_selector_axle_extends_past_left_plate(self, mux_axles, housing_params):
        """Selector axle should extend past the left plate."""
        axle = mux_axles['selector']
        bbox = axle.val().BoundingBox()
        assert bbox.xmin < housing_params.left_plate_x, (
            f"Selector axle xmin ({bbox.xmin}) should be < left plate ({housing_params.left_plate_x})"
        )

    def test_selector_axle_extends_past_right_plate(self, mux_axles, housing_params):
        """Selector axle should extend past the right plate."""
        axle = mux_axles['selector']
        bbox = axle.val().BoundingBox()
        assert bbox.xmax > housing_params.right_plate_x, (
            f"Selector axle xmax ({bbox.xmax}) should be > right plate ({housing_params.right_plate_x})"
        )

    def test_input_a_axle_extends_past_left_plate(self, mux_axles, housing_params):
        """Input A axle should extend past the left plate."""
        axle = mux_axles['input_a']
        bbox = axle.val().BoundingBox()
        assert bbox.xmin < housing_params.left_plate_x, (
            f"Input A axle xmin ({bbox.xmin}) should be < left plate ({housing_params.left_plate_x})"
        )

    def test_input_a_axle_extends_past_right_plate(self, mux_axles, housing_params):
        """Input A axle should extend past the right plate."""
        axle = mux_axles['input_a']
        bbox = axle.val().BoundingBox()
        assert bbox.xmax > housing_params.right_plate_x, (
            f"Input A axle xmax ({bbox.xmax}) should be > right plate ({housing_params.right_plate_x})"
        )

    def test_input_b_axle_extends_past_left_plate(self, mux_axles, housing_params):
        """Input B axle should extend past the left plate."""
        axle = mux_axles['input_b']
        bbox = axle.val().BoundingBox()
        assert bbox.xmin < housing_params.left_plate_x, (
            f"Input B axle xmin ({bbox.xmin}) should be < left plate ({housing_params.left_plate_x})"
        )

    def test_input_b_axle_extends_past_right_plate(self, mux_axles, housing_params):
        """Input B axle should extend past the right plate."""
        axle = mux_axles['input_b']
        bbox = axle.val().BoundingBox()
        assert bbox.xmax > housing_params.right_plate_x, (
            f"Input B axle xmax ({bbox.xmax}) should be > right plate ({housing_params.right_plate_x})"
        )
