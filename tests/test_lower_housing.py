"""Tests for lower housing axle alignment."""

import pytest
import cadquery as cq

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
def default_params():
    """Default housing parameters."""
    return LowerHousingParams()


@pytest.fixture
def housing(default_params):
    """Generate housing with default parameters."""
    gen = LowerHousingGenerator(default_params)
    return gen.generate()


@pytest.fixture
def axles(default_params):
    """Create all three axles."""
    p = default_params
    # Axles extend from well before left plate to well after right plate
    x_start = p.left_plate_x - 30
    x_end = p.right_plate_x + 30
    diameter = p.axle_diameter

    return {
        'selector': create_axle(p.selector_axle_y, p.selector_axle_z, x_start, x_end, diameter),
        'input_a': create_axle(p.input_a_y, p.input_a_z, x_start, x_end, diameter),
        'input_b': create_axle(p.input_b_y, p.input_b_z, x_start, x_end, diameter),
    }


class TestLowerHousingIdleState:
    """Tests that housing doesn't intersect axles in idle (correct) position."""

    def test_selector_axle_no_intersection(self, housing, axles):
        """Selector axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, axles['selector']), (
            "Selector axle should not intersect housing in idle state"
        )

    def test_input_a_axle_no_intersection(self, housing, axles):
        """Input A axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, axles['input_a']), (
            "Input A axle should not intersect housing in idle state"
        )

    def test_input_b_axle_no_intersection(self, housing, axles):
        """Input B axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, axles['input_b']), (
            "Input B axle should not intersect housing in idle state"
        )


class TestLowerHousingOffsetIntersection:
    """Tests that housing intersects axles when offset by clearance + 0.1mm orthogonally."""

    # The axles run along X, so orthogonal directions are Y and Z
    # Offset must be greater than clearance (0.2mm) to ensure intersection
    OFFSET = 0.3  # mm (clearance + 0.1mm)

    def _offset_housing(self, housing, dy: float, dz: float) -> cq.Workplane:
        """Return housing offset by given amounts in Y and Z."""
        return housing.translate((0, dy, dz))

    # --- Selector axle tests ---

    def test_selector_axle_intersects_with_positive_y_offset(self, housing, axles, default_params):
        """Housing offset +Y should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['selector']), (
            f"Selector axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_selector_axle_intersects_with_negative_y_offset(self, housing, axles, default_params):
        """Housing offset -Y should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['selector']), (
            f"Selector axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_selector_axle_intersects_with_positive_z_offset(self, housing, axles, default_params):
        """Housing offset +Z should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, axles['selector']), (
            f"Selector axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_selector_axle_intersects_with_negative_z_offset(self, housing, axles, default_params):
        """Housing offset -Z should intersect selector axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, axles['selector']), (
            f"Selector axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )

    # --- Input A axle tests ---

    def test_input_a_axle_intersects_with_positive_y_offset(self, housing, axles, default_params):
        """Housing offset +Y should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['input_a']), (
            f"Input A axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_input_a_axle_intersects_with_negative_y_offset(self, housing, axles, default_params):
        """Housing offset -Y should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['input_a']), (
            f"Input A axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_input_a_axle_intersects_with_positive_z_offset(self, housing, axles, default_params):
        """Housing offset +Z should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, axles['input_a']), (
            f"Input A axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_input_a_axle_intersects_with_negative_z_offset(self, housing, axles, default_params):
        """Housing offset -Z should intersect input A axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, axles['input_a']), (
            f"Input A axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )

    # --- Input B axle tests ---

    def test_input_b_axle_intersects_with_positive_y_offset(self, housing, axles, default_params):
        """Housing offset +Y should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['input_b']), (
            f"Input B axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_input_b_axle_intersects_with_negative_y_offset(self, housing, axles, default_params):
        """Housing offset -Y should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['input_b']), (
            f"Input B axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_input_b_axle_intersects_with_positive_z_offset(self, housing, axles, default_params):
        """Housing offset +Z should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, axles['input_b']), (
            f"Input B axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_input_b_axle_intersects_with_negative_z_offset(self, housing, axles, default_params):
        """Housing offset -Z should intersect input B axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, axles['input_b']), (
            f"Input B axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )


class TestLowerHousingGeometry:
    """Tests for basic housing geometry."""

    def test_generates_valid_solid(self, housing):
        """Housing should be a valid solid with positive volume."""
        solid = housing.val()
        assert solid is not None
        assert solid.Volume() > 0

    def test_has_two_plates(self, default_params):
        """Housing should consist of two separate plate regions."""
        gen = LowerHousingGenerator(default_params)
        left = gen.generate_left_plate()
        right = gen.generate_right_plate()

        # Both should be valid
        assert left.val().Volume() > 0
        assert right.val().Volume() > 0

        # They should not intersect each other
        assert not shapes_intersect(left, right), (
            "Left and right plates should not intersect"
        )

    def test_plates_at_correct_x_positions(self, default_params):
        """Plates should be at the specified X positions."""
        gen = LowerHousingGenerator(default_params)
        p = default_params

        left = gen.generate_left_plate()
        right = gen.generate_right_plate()

        left_bbox = left.val().BoundingBox()
        right_bbox = right.val().BoundingBox()

        # Left plate should be around left_plate_x
        left_center_x = (left_bbox.xmin + left_bbox.xmax) / 2
        assert abs(left_center_x - p.left_plate_x) < 0.1, (
            f"Left plate center X ({left_center_x}) should be at {p.left_plate_x}"
        )

        # Right plate should be around right_plate_x
        right_center_x = (right_bbox.xmin + right_bbox.xmax) / 2
        assert abs(right_center_x - p.right_plate_x) < 0.1, (
            f"Right plate center X ({right_center_x}) should be at {p.right_plate_x}"
        )
