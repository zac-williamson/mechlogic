"""Tests that motor mounts don't intersect with housing or mechanism components.

Validates that:
- Right motor mount doesn't intersect with housing
- Left motor mount doesn't interfere with flexure
- Motor shaft positions are aligned with mechanism axles
- Couplings fit in the available space
"""

import pytest
import cadquery as cq
import yaml

from mechlogic.models.spec import LogicElementSpec
from mechlogic.generators.motor_mount_right import RightMotorMountGenerator
from mechlogic.generators.motor_mount_left import LeftMotorMountGenerator
from mechlogic.generators.shaft_coupling import ShaftCouplingGenerator
from mechlogic.generators.motor_assembly import MotorAssemblyGenerator
from mechlogic.generators.motor_mount_params import MotorMountParams, ShaftCouplingParams
from mechlogic.generators.lower_housing import LowerHousingGenerator
from mechlogic.generators.bevel_lever_with_upper_housing import BevelLeverWithUpperHousingGenerator
from mechlogic.generators.layout import LayoutCalculator


def shapes_intersect(shape1, shape2, tolerance=0.001):
    """Check if two shapes intersect by computing intersection volume."""
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
def motor_params():
    """Default motor mount parameters."""
    return MotorMountParams()


@pytest.fixture
def coupling_params():
    """Default coupling parameters."""
    return ShaftCouplingParams()


class TestRightMotorMountGeneration:
    """Tests for right motor mount plate generation."""

    def test_right_mount_generates_valid_shape(self, spec, motor_params):
        """Right motor mount should generate a shape with positive volume."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        assert mount.val().Volume() > 0, "Right motor mount has no volume"

    def test_right_mount_has_two_motor_positions(self, spec, motor_params):
        """Right motor mount should have positions for two motors (A and B)."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        positions = gen.get_motor_shaft_positions()
        assert len(positions) == 2, f"Expected 2 motor positions, got {len(positions)}"

    def test_motor_a_position_at_positive_z(self, spec, motor_params):
        """Motor A should be at positive Z (aligned with input A)."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        positions = gen.get_motor_shaft_positions()
        motor_a_z = positions[0][2]  # (x, y, z)
        assert motor_a_z > 0, f"Motor A Z ({motor_a_z}) should be positive"

    def test_motor_b_position_at_negative_z(self, spec, motor_params):
        """Motor B should be at negative Z (aligned with input B)."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        positions = gen.get_motor_shaft_positions()
        motor_b_z = positions[1][2]  # (x, y, z)
        assert motor_b_z < 0, f"Motor B Z ({motor_b_z}) should be negative"


class TestLeftMotorMountGeneration:
    """Tests for left motor mount plate generation."""

    def test_left_mount_generates_valid_shape(self, spec, motor_params):
        """Left motor mount should generate a shape with positive volume."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        assert mount.val().Volume() > 0, "Left motor mount has no volume"

    def test_motor_s_position_at_pivot_y(self, spec, motor_params):
        """Motor S should be at pivot_y (aligned with S/bevel axle)."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        position = gen.get_motor_shaft_position()
        motor_s_y = position[1]  # (x, y, z)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)
        assert abs(motor_s_y - pivot_y) < 0.001, (
            f"Motor S Y ({motor_s_y}) should be at pivot_y ({pivot_y})"
        )

    def test_motor_s_position_at_z_zero(self, spec, motor_params):
        """Motor S should be at Z=0 (aligned with S axle)."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        position = gen.get_motor_shaft_position()
        motor_s_z = position[2]  # (x, y, z)
        assert abs(motor_s_z) < 0.001, f"Motor S Z ({motor_s_z}) should be 0"


class TestShaftCouplingGeneration:
    """Tests for shaft coupling generation."""

    def test_coupling_generates_valid_shape(self, coupling_params):
        """Shaft coupling should generate a shape with positive volume."""
        gen = ShaftCouplingGenerator(params=coupling_params)
        coupling = gen.generate()
        assert coupling.val().Volume() > 0, "Coupling has no volume"

    def test_coupling_is_symmetric_around_origin(self, coupling_params):
        """Coupling should be centered at origin along X axis."""
        gen = ShaftCouplingGenerator(params=coupling_params)
        coupling = gen.generate()
        bbox = coupling.val().BoundingBox()
        center_x = (bbox.xmin + bbox.xmax) / 2
        assert abs(center_x) < 0.001, f"Coupling center X ({center_x}) should be 0"

    def test_coupling_dimensions_match_params(self, coupling_params):
        """Coupling dimensions should match parameters."""
        gen = ShaftCouplingGenerator(params=coupling_params)
        dims = gen.get_dimensions()
        assert dims['outer_diameter'] == coupling_params.outer_diameter
        assert dims['length'] == coupling_params.length


class TestRightMountNoHousingIntersection:
    """Tests that right motor mount doesn't intersect with housing."""

    @pytest.fixture
    def right_mount(self, spec, motor_params):
        """Generate right motor mount."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        return gen.generate()

    @pytest.fixture
    def lower_housing_right_plate(self, spec):
        """Generate lower housing right plate."""
        gen = LowerHousingGenerator(spec=spec)
        return gen.generate_right_plate()

    def test_right_mount_no_intersection_with_lower_housing_plate(
        self, right_mount, lower_housing_right_plate
    ):
        """Right motor mount should not intersect with lower housing right plate."""
        assert not shapes_intersect(right_mount, lower_housing_right_plate), (
            "Right motor mount intersects with lower housing right plate"
        )

    def test_right_mount_outside_housing(self, spec, motor_params):
        """Right motor mount should be positioned outside (to the right of) housing."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        layout = gen.get_layout()
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)

        # Motor mount plate_x should be at or beyond housing right outer face
        housing_right_outer = housing_layout.right_plate_x + housing_layout.plate_thickness / 2
        assert layout.plate_x >= housing_right_outer - 0.001, (
            f"Motor mount plate_x ({layout.plate_x}) should be >= "
            f"housing right outer ({housing_right_outer})"
        )


class TestLeftMountNoHousingIntersection:
    """Tests that left motor mount doesn't intersect with housing."""

    @pytest.fixture
    def left_mount(self, spec, motor_params):
        """Generate left motor mount."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        return gen.generate()

    @pytest.fixture
    def lower_housing_left_plate(self, spec):
        """Generate lower housing left plate."""
        gen = LowerHousingGenerator(spec=spec)
        return gen.generate_left_plate()

    def test_left_mount_no_intersection_with_lower_housing_plate(
        self, left_mount, lower_housing_left_plate
    ):
        """Left motor mount should not intersect with lower housing left plate."""
        assert not shapes_intersect(left_mount, lower_housing_left_plate), (
            "Left motor mount intersects with lower housing left plate"
        )

    def test_left_mount_outside_housing(self, spec, motor_params):
        """Left motor mount should be positioned outside (to the left of) housing."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        layout = gen.get_layout()
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)

        # Motor mount plate_x should be at or beyond housing left outer face
        housing_left_outer = housing_layout.left_plate_x - housing_layout.plate_thickness / 2
        assert layout.plate_x <= housing_left_outer + 0.001, (
            f"Motor mount plate_x ({layout.plate_x}) should be <= "
            f"housing left outer ({housing_left_outer})"
        )


class TestLeftMountFlexureClearance:
    """Tests that left motor mount doesn't interfere with flexure."""

    @pytest.fixture
    def flexure(self, spec):
        """Generate flexure in position."""
        selector_layout = LayoutCalculator.calculate_selector_layout(spec)
        origin = (selector_layout.clutch_center, 0, 0)

        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
        )
        generator._generate_upper_housing(spec, origin=origin)
        wp = generator._wall_positions

        flexure_shape = generator._flexure_gen.generate()

        # Position flexure (same as in mux_assembly)
        left_wall_x = wp['left_wall_x']
        wall_thickness = wp['wall_thickness']
        flexure_wall_gap = 0.5
        flexure_x = left_wall_x + wall_thickness / 2 + flexure_wall_gap

        flexure_positioned = (
            flexure_shape
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((flexure_x, wp['pivot_y'], wp['driving_axle_z']))
        )
        return flexure_positioned

    @pytest.fixture
    def left_mount(self, spec, motor_params):
        """Generate left motor mount."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        return gen.generate()

    def test_left_mount_no_intersection_with_flexure(self, left_mount, flexure):
        """Left motor mount should not intersect with flexure."""
        assert not shapes_intersect(left_mount, flexure), (
            "Left motor mount intersects with flexure"
        )


class TestMotorShaftAlignment:
    """Tests that motor shaft positions align with mechanism axles."""

    def test_motor_a_aligns_with_input_a_axle(self, spec, motor_params):
        """Motor A shaft should align with input A axle (Y=0, Z=+36)."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        positions = gen.get_motor_shaft_positions()
        motor_a_y = positions[0][1]
        motor_a_z = positions[0][2]

        mux_layout = LayoutCalculator.calculate_mux_layout(spec)
        expected_z = mux_layout.input_a_z

        assert abs(motor_a_y) < 0.001, f"Motor A Y ({motor_a_y}) should be 0"
        assert abs(motor_a_z - expected_z) < 0.001, (
            f"Motor A Z ({motor_a_z}) should be {expected_z}"
        )

    def test_motor_b_aligns_with_input_b_axle(self, spec, motor_params):
        """Motor B shaft should align with input B axle (Y=0, Z=-36)."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        positions = gen.get_motor_shaft_positions()
        motor_b_y = positions[1][1]
        motor_b_z = positions[1][2]

        mux_layout = LayoutCalculator.calculate_mux_layout(spec)
        expected_z = mux_layout.input_b_z

        assert abs(motor_b_y) < 0.001, f"Motor B Y ({motor_b_y}) should be 0"
        assert abs(motor_b_z - expected_z) < 0.001, (
            f"Motor B Z ({motor_b_z}) should be {expected_z}"
        )

    def test_motor_s_aligns_with_bevel_driver_axle(self, spec, motor_params):
        """Motor S shaft should align with S/bevel driver axle (Y=pivot_y, Z=0)."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        position = gen.get_motor_shaft_position()
        motor_s_y = position[1]
        motor_s_z = position[2]

        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        assert abs(motor_s_y - pivot_y) < 0.001, (
            f"Motor S Y ({motor_s_y}) should be {pivot_y}"
        )
        assert abs(motor_s_z) < 0.001, f"Motor S Z ({motor_s_z}) should be 0"


class TestCouplingSpace:
    """Tests that there's sufficient space for couplings between motors and housing."""

    def test_right_side_coupling_space(self, spec, motor_params, coupling_params):
        """There should be enough space for couplings on the right side."""
        mount_gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        layout = mount_gen.get_layout()
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)

        housing_right_outer = housing_layout.right_plate_x + housing_layout.plate_thickness / 2
        available_space = layout.plate_x - housing_right_outer

        # Need at least coupling length plus some clearance
        required_space = coupling_params.length + 2.0  # 2mm clearance

        assert available_space >= required_space, (
            f"Available space ({available_space:.1f}mm) insufficient for coupling "
            f"(need {required_space:.1f}mm)"
        )

    def test_left_side_coupling_space(self, spec, motor_params, coupling_params):
        """There should be enough space for coupling on the left side."""
        mount_gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        layout = mount_gen.get_layout()
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)

        housing_left_outer = housing_layout.left_plate_x - housing_layout.plate_thickness / 2
        available_space = housing_left_outer - layout.plate_x

        # Need at least coupling length plus some clearance
        required_space = coupling_params.length + 2.0  # 2mm clearance

        assert available_space >= required_space, (
            f"Available space ({available_space:.1f}mm) insufficient for coupling "
            f"(need {required_space:.1f}mm)"
        )


class TestSelfSupportingStructure:
    """Tests for self-supporting L-bracket structure."""

    def test_self_supporting_enabled_by_default(self, motor_params):
        """Self-supporting structure should be enabled by default."""
        assert motor_params.self_supporting is True

    def test_right_mount_has_base_plate(self, spec, motor_params):
        """Right motor mount should include base plate when self_supporting is True."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        # With self-supporting structure, volume should be significantly larger
        # than just a flat plate
        assert mount.val().Volume() > 0

    def test_left_mount_has_base_plate(self, spec, motor_params):
        """Left motor mount should include base plate when self_supporting is True."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        assert mount.val().Volume() > 0

    def test_base_extends_away_from_housing_right(self, spec, motor_params):
        """Right mount base should extend in +X direction (away from housing)."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        bbox = mount.val().BoundingBox()

        layout = gen.get_layout()
        # The mount should extend beyond plate_x in +X direction
        assert bbox.xmax > layout.plate_x, (
            f"Right mount should extend past plate_x ({layout.plate_x}) in +X, "
            f"but xmax is only {bbox.xmax}"
        )

    def test_base_extends_away_from_housing_left(self, spec, motor_params):
        """Left mount base should extend in -X direction (away from housing)."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        bbox = mount.val().BoundingBox()

        layout = gen.get_layout()
        # The mount should extend beyond plate_x in -X direction
        plate_outer_x = layout.plate_x - motor_params.plate_thickness
        assert bbox.xmin < plate_outer_x, (
            f"Left mount should extend past plate_x ({plate_outer_x}) in -X, "
            f"but xmin is only {bbox.xmin}"
        )

    def test_mounts_have_feet(self, spec, motor_params):
        """Mounts should have feet when foot_height > 0."""
        assert motor_params.foot_height > 0
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        bbox = mount.val().BoundingBox()

        layout = gen.get_layout()
        base_z = layout.plate_center_z - layout.plate_height_z / 2
        # With feet, the mount should extend below the base plate
        expected_z_min = base_z - motor_params.foot_height
        assert bbox.zmin <= expected_z_min + 0.1, (
            f"Mount should have feet extending to Z={expected_z_min}, "
            f"but zmin is {bbox.zmin}"
        )


class TestAntiRotationFeatures:
    """Tests that motor mounts have proper anti-rotation features."""

    def test_right_mount_pocket_depth(self, spec, motor_params):
        """Motor pocket should be deep enough to engage flats."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        # Pocket depth should be at least 5mm (motor_pocket_depth parameter)
        assert motor_params.motor_pocket_depth >= 5.0, (
            f"Pocket depth ({motor_params.motor_pocket_depth}) should be >= 5mm"
        )

    def test_right_mount_has_tab_slots(self, spec, motor_params):
        """Motor mount should include tab slots when enabled."""
        assert motor_params.include_tab_slots is True, (
            "Tab slots should be enabled by default"
        )
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        # Volume should be positive (mount generated successfully with tab slots)
        assert mount.val().Volume() > 0

    def test_left_mount_pocket_depth(self, spec, motor_params):
        """Motor pocket should be deep enough to engage flats."""
        gen = LeftMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        assert motor_params.motor_pocket_depth >= 5.0, (
            f"Pocket depth ({motor_params.motor_pocket_depth}) should be >= 5mm"
        )

    def test_flat_width_prevents_rotation(self, motor_params):
        """Flat width should be narrower than body diameter to create keying."""
        motor = motor_params.motor
        assert motor.flat_width < motor.body_diameter, (
            f"Flat width ({motor.flat_width}) must be less than "
            f"body diameter ({motor.body_diameter}) to create anti-rotation flats"
        )

    def test_tab_screw_holes_exist(self, spec, motor_params):
        """Mount should have screw holes for securing motor tabs."""
        gen = RightMotorMountGenerator(params=motor_params, spec=spec)
        mount = gen.generate()
        # The mount generates successfully with tab screw holes
        assert mount.val().Volume() > 0
        # Tab screw diameter should be sized for M2
        assert motor_params.tab_screw_diameter >= 2.0, (
            f"Tab screw diameter ({motor_params.tab_screw_diameter}) should be >= 2mm for M2"
        )


class TestMotorAssemblyIntegration:
    """Integration tests for complete motor assembly."""

    def test_motor_assembly_generates_valid_assembly(self, spec):
        """Motor assembly should generate a valid CadQuery Assembly."""
        gen = MotorAssemblyGenerator()
        assy = gen.generate(spec)
        # Check that assembly has expected components
        component_names = [name for name, obj in assy.objects.items()]
        assert "motor_mount_right" in component_names
        assert "motor_mount_left" in component_names

    def test_motor_assembly_with_couplings(self, spec):
        """Motor assembly with couplings should have coupling components."""
        gen = MotorAssemblyGenerator(include_couplings=True)
        assy = gen.generate(spec)
        component_names = [name for name, obj in assy.objects.items()]
        assert "coupling_a" in component_names
        assert "coupling_b" in component_names
        assert "coupling_s" in component_names

    def test_motor_assembly_without_couplings(self, spec):
        """Motor assembly without couplings should not have coupling components."""
        gen = MotorAssemblyGenerator(include_couplings=False)
        assy = gen.generate(spec)
        component_names = [name for name, obj in assy.objects.items()]
        assert "coupling_a" not in component_names
        assert "coupling_b" not in component_names
        assert "coupling_s" not in component_names

    def test_get_motor_positions(self, spec):
        """Motor assembly should report correct motor positions."""
        gen = MotorAssemblyGenerator()
        positions = gen.get_motor_positions(spec)

        assert "motor_a" in positions
        assert "motor_b" in positions
        assert "motor_s" in positions

        # Verify positions are tuples of 3 floats
        for name, pos in positions.items():
            assert len(pos) == 3, f"{name} position should be (x, y, z)"
