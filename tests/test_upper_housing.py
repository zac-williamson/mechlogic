"""Tests for upper housing axle alignment.

The upper housing supports two bevel gear axles:
- Driving bevel axle: runs along X-axis
- Driven bevel axle: runs along Z-axis
"""

import pytest
import cadquery as cq

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
def default_params():
    """Default housing parameters."""
    return UpperHousingParams()


@pytest.fixture
def housing(default_params):
    """Generate housing with default parameters."""
    gen = UpperHousingGenerator(default_params)
    return gen.generate()


@pytest.fixture
def axles(default_params):
    """Create both bevel axles extending through all plates."""
    p = default_params

    # Driving bevel axle extends along X through both YZ plates
    driving_x_start = p.driving_left_plate_x - 20
    driving_x_end = p.driving_right_plate_x + 20

    # Driven bevel axle extends along Z through both XY plates
    driven_z_start = p.driven_front_plate_z - 20
    driven_z_end = p.driven_back_plate_z + 20

    return {
        'driving': create_x_axle(
            p.driving_bevel_y, p.driving_bevel_z,
            driving_x_start, driving_x_end, p.axle_diameter
        ),
        'driven': create_z_axle(
            p.driven_bevel_x, p.driven_bevel_y,
            driven_z_start, driven_z_end, p.axle_diameter
        ),
    }


class TestUpperHousingIdleState:
    """Tests that housing doesn't intersect axles in idle (correct) position."""

    def test_driving_axle_no_intersection(self, housing, axles):
        """Driving bevel axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, axles['driving']), (
            "Driving bevel axle should not intersect housing in idle state"
        )

    def test_driven_axle_no_intersection(self, housing, axles):
        """Driven bevel axle should pass through housing holes without intersection."""
        assert not shapes_intersect(housing, axles['driven']), (
            "Driven bevel axle should not intersect housing in idle state"
        )


class TestUpperHousingDrivingAxleOffset:
    """Tests that housing intersects driving axle when offset orthogonally.

    The driving axle runs along X, so orthogonal directions are Y and Z.
    """

    OFFSET = 0.3  # mm (clearance + 0.1mm)

    def _offset_housing(self, housing, dy: float, dz: float) -> cq.Workplane:
        """Return housing offset by given amounts in Y and Z."""
        return housing.translate((0, dy, dz))

    def test_driving_axle_intersects_with_positive_y_offset(self, housing, axles):
        """Housing offset +Y should intersect driving axle."""
        offset_housing = self._offset_housing(housing, dy=self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['driving']), (
            f"Driving axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_driving_axle_intersects_with_negative_y_offset(self, housing, axles):
        """Housing offset -Y should intersect driving axle."""
        offset_housing = self._offset_housing(housing, dy=-self.OFFSET, dz=0)
        assert shapes_intersect(offset_housing, axles['driving']), (
            f"Driving axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )

    def test_driving_axle_intersects_with_positive_z_offset(self, housing, axles):
        """Housing offset +Z should intersect driving axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=self.OFFSET)
        assert shapes_intersect(offset_housing, axles['driving']), (
            f"Driving axle should intersect housing when offset by +{self.OFFSET}mm in Z"
        )

    def test_driving_axle_intersects_with_negative_z_offset(self, housing, axles):
        """Housing offset -Z should intersect driving axle."""
        offset_housing = self._offset_housing(housing, dy=0, dz=-self.OFFSET)
        assert shapes_intersect(offset_housing, axles['driving']), (
            f"Driving axle should intersect housing when offset by -{self.OFFSET}mm in Z"
        )


class TestUpperHousingDrivenAxleOffset:
    """Tests that housing intersects driven axle when offset orthogonally.

    The driven axle runs along Z, so orthogonal directions are X and Y.
    """

    OFFSET = 0.3  # mm (clearance + 0.1mm)

    def _offset_housing(self, housing, dx: float, dy: float) -> cq.Workplane:
        """Return housing offset by given amounts in X and Y."""
        return housing.translate((dx, dy, 0))

    def test_driven_axle_intersects_with_positive_x_offset(self, housing, axles):
        """Housing offset +X should intersect driven axle."""
        offset_housing = self._offset_housing(housing, dx=self.OFFSET, dy=0)
        assert shapes_intersect(offset_housing, axles['driven']), (
            f"Driven axle should intersect housing when offset by +{self.OFFSET}mm in X"
        )

    def test_driven_axle_intersects_with_negative_x_offset(self, housing, axles):
        """Housing offset -X should intersect driven axle."""
        offset_housing = self._offset_housing(housing, dx=-self.OFFSET, dy=0)
        assert shapes_intersect(offset_housing, axles['driven']), (
            f"Driven axle should intersect housing when offset by -{self.OFFSET}mm in X"
        )

    def test_driven_axle_intersects_with_positive_y_offset(self, housing, axles):
        """Housing offset +Y should intersect driven axle."""
        offset_housing = self._offset_housing(housing, dx=0, dy=self.OFFSET)
        assert shapes_intersect(offset_housing, axles['driven']), (
            f"Driven axle should intersect housing when offset by +{self.OFFSET}mm in Y"
        )

    def test_driven_axle_intersects_with_negative_y_offset(self, housing, axles):
        """Housing offset -Y should intersect driven axle."""
        offset_housing = self._offset_housing(housing, dx=0, dy=-self.OFFSET)
        assert shapes_intersect(offset_housing, axles['driven']), (
            f"Driven axle should intersect housing when offset by -{self.OFFSET}mm in Y"
        )


class TestUpperHousingAxleExtent:
    """Tests that axles extend through their outer plates (cantilevered design)."""

    def test_driving_axle_extends_past_left_plate(self, axles, default_params):
        """Driving axle should extend past the left (outer) plate."""
        axle = axles['driving']
        bbox = axle.val().BoundingBox()
        assert bbox.xmin < default_params.driving_left_plate_x, (
            f"Driving axle xmin ({bbox.xmin}) should be < left plate ({default_params.driving_left_plate_x})"
        )

    def test_driving_axle_reaches_gear_position(self, axles, default_params):
        """Driving axle should reach past the gear position."""
        axle = axles['driving']
        bbox = axle.val().BoundingBox()
        # Axle should extend past the gear (at driving_bevel_x)
        assert bbox.xmax > default_params.driving_bevel_x, (
            f"Driving axle xmax ({bbox.xmax}) should be > gear position ({default_params.driving_bevel_x})"
        )

    def test_driven_axle_extends_past_front_plate(self, axles, default_params):
        """Driven axle should extend past the front (outer) plate."""
        axle = axles['driven']
        bbox = axle.val().BoundingBox()
        assert bbox.zmin < default_params.driven_front_plate_z, (
            f"Driven axle zmin ({bbox.zmin}) should be < front plate ({default_params.driven_front_plate_z})"
        )

    def test_driven_axle_reaches_gear_position(self, axles, default_params):
        """Driven axle should reach past the gear position."""
        axle = axles['driven']
        bbox = axle.val().BoundingBox()
        # Axle should extend past the gear (at driven_bevel_z)
        assert bbox.zmax > default_params.driven_bevel_z, (
            f"Driven axle zmax ({bbox.zmax}) should be > gear position ({default_params.driven_bevel_z})"
        )


class TestUpperHousingGeometry:
    """Tests for basic housing geometry."""

    def test_generates_valid_solid(self, housing):
        """Housing should be a valid solid with positive volume."""
        solid = housing.val()
        assert solid is not None
        assert solid.Volume() > 0

    def test_has_two_plates_cantilevered(self, default_params):
        """Cantilevered housing should have two plates (outer only)."""
        gen = UpperHousingGenerator(default_params)

        # Default is cantilevered mode with only outer plates
        housing = gen.generate(cantilevered=True)
        driving_left = gen.generate_driving_left_plate()
        driven_front = gen.generate_driven_front_plate()

        # Both should be valid
        assert driving_left.val().Volume() > 0
        assert driven_front.val().Volume() > 0

        # Outer plates should not intersect each other
        assert not shapes_intersect(driving_left, driven_front), (
            "Driving left and driven front plates should not intersect"
        )

    def test_has_four_plates_non_cantilevered(self, default_params):
        """Non-cantilevered housing should consist of four separate plates."""
        gen = UpperHousingGenerator(default_params)

        driving_left = gen.generate_driving_left_plate()
        driving_right = gen.generate_driving_right_plate()
        driven_front = gen.generate_driven_front_plate()
        driven_back = gen.generate_driven_back_plate()

        # All should be valid
        assert driving_left.val().Volume() > 0
        assert driving_right.val().Volume() > 0
        assert driven_front.val().Volume() > 0
        assert driven_back.val().Volume() > 0

        # Driving plates should not intersect each other
        assert not shapes_intersect(driving_left, driving_right), (
            "Driving left and right plates should not intersect"
        )

        # Driven plates should not intersect each other
        assert not shapes_intersect(driven_front, driven_back), (
            "Driven front and back plates should not intersect"
        )
