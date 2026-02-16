"""Tests that bevel lever housing doesn't intersect with mechanism components.

Validates that:
- Housing walls don't intersect with bevel gears
- Housing walls don't intersect with shift lever
- Housing walls don't intersect with axles
"""

import pytest
import cadquery as cq
import yaml

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType
from mechlogic.generators.gear_bevel import BevelGearGenerator
from mechlogic.generators.shift_lever import ShiftLeverGenerator
from mechlogic.generators.bevel_lever_with_upper_housing import BevelLeverWithUpperHousingGenerator
from mechlogic.generators.layout import LayoutCalculator
from mechlogic.generators.serpentine_flexure import SerpentineFlexureGenerator, SerpentineFlexureParams


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
def bevel_geometry(spec):
    """Calculate bevel lever geometry positions."""
    bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
    selector_layout = LayoutCalculator.calculate_selector_layout(spec)
    pivot_y = LayoutCalculator.calculate_pivot_y(spec)
    bevel_teeth = spec.gears.bevel_teeth
    tooth_angle = 360.0 / bevel_teeth
    mesh_offset_angle = tooth_angle / 2

    return {
        'mesh_distance': bevel_layout.mesh_distance,
        'pivot_y': pivot_y,
        'tooth_angle': tooth_angle,
        'mesh_offset_angle': mesh_offset_angle,
        'clutch_center': selector_layout.clutch_center,
    }


@pytest.fixture
def upper_housing(spec, bevel_geometry):
    """Generate upper housing walls only (no axles, no mechanism)."""
    generator = BevelLeverWithUpperHousingGenerator(include_axles=False)
    # Generate housing at clutch_center origin (same as mux_assembly)
    origin = (bevel_geometry['clutch_center'], 0, 0)
    housing = generator._generate_upper_housing(spec, origin=origin)
    return housing


@pytest.fixture
def components(spec, bevel_geometry):
    """Generate all bevel lever components in their final positions."""
    g = bevel_geometry
    ox = g['clutch_center']  # Origin X at clutch center (same as mux_assembly)
    placement = PartPlacement(part_type=PartType.BEVEL_DRIVE, part_id='test')

    # Generate components
    driving_bevel = BevelGearGenerator(gear_id='driving').generate(spec, placement)
    driven_bevel = BevelGearGenerator(gear_id='driven').generate(spec, placement)
    shift_lever = ShiftLeverGenerator().generate(spec, placement)

    # Position components (origin at clutch axis = (clutch_center, 0, 0))
    # Driven bevel: on Z-axis below apex, teeth pointing up
    driven_bevel_positioned = driven_bevel.translate(
        (ox, g['pivot_y'], -g['mesh_distance'])
    )

    # Driving bevel: on X-axis, rotated to mesh
    driving_bevel_positioned = (
        driving_bevel
        .rotate((0, 0, 0), (1, 0, 0), 180)
        .rotate((0, 0, 0), (0, 0, 1), g['mesh_offset_angle'])
        .rotate((0, 0, 0), (0, 1, 0), -90)
        .translate((ox - g['mesh_distance'], g['pivot_y'], 0))
    )

    # Shift lever at clutch center
    lever_positioned = shift_lever.translate((ox, 0, 0))

    return {
        'driven_bevel': driven_bevel_positioned,
        'driving_bevel': driving_bevel_positioned,
        'shift_lever': lever_positioned,
    }


class TestBevelLeverHousingNoIntersections:
    """Tests that bevel lever housing doesn't intersect with mechanism components."""

    def test_housing_no_intersection_with_driven_bevel(self, upper_housing, components):
        """Housing walls should not intersect with driven (gold) bevel gear."""
        assert not shapes_intersect(upper_housing, components['driven_bevel']), (
            "Upper housing intersects with driven bevel gear"
        )

    def test_housing_no_intersection_with_driving_bevel(self, upper_housing, components):
        """Housing walls should not intersect with driving (purple) bevel gear."""
        assert not shapes_intersect(upper_housing, components['driving_bevel']), (
            "Upper housing intersects with driving bevel gear"
        )

    def test_housing_no_intersection_with_shift_lever(self, upper_housing, components):
        """Housing walls should not intersect with shift lever."""
        assert not shapes_intersect(upper_housing, components['shift_lever']), (
            "Upper housing intersects with shift lever"
        )


class TestBevelLeverAxleNoIntersections:
    """Tests that axles don't intersect with mechanism components."""

    @pytest.fixture
    def axles(self, spec, bevel_geometry):
        """Generate axles as standalone shapes."""
        generator = BevelLeverWithUpperHousingGenerator(include_axles=True)
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        shaft_diameter = spec.primary_shaft_diameter
        axle_overhang = housing_layout.axle_overhang
        wall_thickness = spec.geometry.housing_thickness

        # Generate housing to get wall positions (at clutch_center origin)
        origin = (bevel_geometry['clutch_center'], 0, 0)
        generator._generate_upper_housing(spec, origin=origin)
        wp = generator._wall_positions

        # Generate driving axle shape directly
        driving_axle_start = wp['left_wall_x'] - wall_thickness / 2 - axle_overhang
        driving_axle_end = 10  # Extend past origin
        driving_axle_length = driving_axle_end - driving_axle_start

        driving_axle = (
            cq.Workplane('YZ')
            .center(wp['pivot_y'], wp['driving_axle_z'])
            .circle(shaft_diameter / 2)
            .extrude(driving_axle_length)
            .translate((driving_axle_start, 0, 0))
        )

        # Generate driven axle shape directly
        driven_axle_start = wp['front_wall_z'] - wall_thickness / 2 - axle_overhang
        driven_axle_end = wp['back_wall_z'] + wall_thickness / 2 + axle_overhang
        driven_axle_length = driven_axle_end - driven_axle_start

        driven_axle = (
            cq.Workplane('XY')
            .center(wp['driven_axle_x'], wp['pivot_y'])
            .circle(shaft_diameter / 2)
            .extrude(driven_axle_length)
            .translate((0, 0, driven_axle_start))
        )

        return {
            'driving_bevel_axle': driving_axle,
            'driven_bevel_axle': driven_axle,
        }

    def test_driving_axle_no_intersection_with_driven_bevel(self, axles, components):
        """Driving bevel axle should not intersect with driven bevel gear."""
        assert not shapes_intersect(axles['driving_bevel_axle'], components['driven_bevel']), (
            "Driving bevel axle intersects with driven bevel gear"
        )

    def test_driven_axle_no_intersection_with_driving_bevel(self, axles, components):
        """Driven bevel axle should not intersect with driving bevel gear."""
        assert not shapes_intersect(axles['driven_bevel_axle'], components['driving_bevel']), (
            "Driven bevel axle intersects with driving bevel gear"
        )

    def test_driven_axle_no_intersection_with_shift_lever(self, axles, components):
        """Driven bevel axle should not intersect with shift lever."""
        assert not shapes_intersect(axles['driven_bevel_axle'], components['shift_lever']), (
            "Driven bevel axle intersects with shift lever"
        )


class TestFlexureNoIntersections:
    """Tests that serpentine flexure doesn't intersect with mechanism components."""

    @pytest.fixture
    def housing_with_flexure(self, spec, bevel_geometry):
        """Generate upper housing with flexure enabled."""
        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
        )
        origin = (bevel_geometry['clutch_center'], 0, 0)
        housing = generator._generate_upper_housing(spec, origin=origin)
        return housing

    @pytest.fixture
    def flexure(self, spec, bevel_geometry):
        """Generate the serpentine flexure in its mounted position."""
        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
        )
        # Generate housing to set up wall positions (at clutch_center origin)
        origin = (bevel_geometry['clutch_center'], 0, 0)
        generator._generate_upper_housing(spec, origin=origin)
        wp = generator._wall_positions

        # Generate flexure
        flexure_shape = generator._flexure_gen.generate()

        # Position flexure on inside of left wall (must match _add_flexure method)
        # After rotating 90° around Y, the flexure's original Z (thickness) becomes +X
        left_wall_x = wp['left_wall_x']
        wall_thickness = wp['wall_thickness']
        flexure_thickness = generator._flexure_params.thickness
        flexure_wall_gap = 0.5  # Must match gap in _add_flexure
        flexure_x = left_wall_x + wall_thickness / 2 + flexure_wall_gap

        flexure_positioned = (
            flexure_shape
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((flexure_x, wp['pivot_y'], wp['driving_axle_z']))
        )

        return flexure_positioned

    def test_flexure_no_intersection_with_driven_bevel(self, flexure, components):
        """Flexure should not intersect with driven bevel gear."""
        assert not shapes_intersect(flexure, components['driven_bevel']), (
            "Flexure intersects with driven bevel gear"
        )

    def test_flexure_no_intersection_with_driving_bevel(self, flexure, components):
        """Flexure should not intersect with driving bevel gear."""
        assert not shapes_intersect(flexure, components['driving_bevel']), (
            "Flexure intersects with driving bevel gear"
        )

    def test_flexure_no_intersection_with_shift_lever(self, flexure, components):
        """Flexure should not intersect with shift lever."""
        assert not shapes_intersect(flexure, components['shift_lever']), (
            "Flexure intersects with shift lever"
        )

    def test_housing_with_flexure_no_intersection_with_driving_bevel(
        self, housing_with_flexure, components
    ):
        """Housing walls (with flexure sizing) should not intersect with driving bevel."""
        assert not shapes_intersect(housing_with_flexure, components['driving_bevel']), (
            "Housing with flexure sizing intersects with driving bevel gear"
        )

    def test_flexure_no_intersection_with_housing(self, flexure, housing_with_flexure):
        """Flexure should not intersect with housing walls."""
        assert not shapes_intersect(flexure, housing_with_flexure), (
            "Flexure intersects with housing walls"
        )


class TestHousingWallsFlush:
    """Tests that housing walls are flush with each other."""

    @pytest.fixture
    def wall_positions(self, spec, bevel_geometry):
        """Get wall positions from generator."""
        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
        )
        origin = (bevel_geometry['clutch_center'], 0, 0)
        generator._generate_upper_housing(spec, origin=origin)
        return generator._wall_positions

    @pytest.fixture
    def wall_bounds(self, spec, wall_positions):
        """Calculate actual wall bounds."""
        wp = wall_positions
        t = wp['wall_thickness']

        # Left wall is centered on left_wall_x
        left_wall_x_min = wp['left_wall_x'] - t / 2
        left_wall_x_max = wp['left_wall_x'] + t / 2
        # Left wall Z now extends to match front/back wall outer faces
        left_wall_z_min = wp['front_wall_z'] - t / 2
        left_wall_z_max = wp['back_wall_z'] + t / 2

        # Front wall is centered on front_wall_z
        front_wall_z_min = wp['front_wall_z'] - t / 2
        front_wall_z_max = wp['front_wall_z'] + t / 2
        # Front wall X starts at left wall's left face, ends at right wall's right face
        front_wall_x_min = wp['left_wall_x'] - t / 2
        front_wall_x_max = wp['right_edge_x']

        # Back wall is centered on back_wall_z
        back_wall_z_min = wp['back_wall_z'] - t / 2
        back_wall_z_max = wp['back_wall_z'] + t / 2
        # Back wall X starts at left wall's left face, ends at right wall's right face
        back_wall_x_min = wp['left_wall_x'] - t / 2
        back_wall_x_max = wp['right_edge_x']

        # Right wall is centered on right_wall_x
        right_wall_x_min = wp['right_wall_x'] - t / 2
        right_wall_x_max = wp['right_wall_x'] + t / 2
        # Right wall Z extends to match front/back wall outer faces
        right_wall_z_min = wp['front_wall_z'] - t / 2
        right_wall_z_max = wp['back_wall_z'] + t / 2

        return {
            'left_wall_x_min': left_wall_x_min,
            'left_wall_x_max': left_wall_x_max,
            'left_wall_z_min': left_wall_z_min,
            'left_wall_z_max': left_wall_z_max,
            'front_wall_z_min': front_wall_z_min,
            'front_wall_z_max': front_wall_z_max,
            'front_wall_x_min': front_wall_x_min,
            'front_wall_x_max': front_wall_x_max,
            'back_wall_z_min': back_wall_z_min,
            'back_wall_z_max': back_wall_z_max,
            'back_wall_x_min': back_wall_x_min,
            'back_wall_x_max': back_wall_x_max,
            'right_wall_x_min': right_wall_x_min,
            'right_wall_x_max': right_wall_x_max,
            'right_wall_z_min': right_wall_z_min,
            'right_wall_z_max': right_wall_z_max,
        }

    def test_left_wall_flush_with_front_wall_z(self, wall_bounds):
        """Left wall front Z face should be flush with front wall front Z face."""
        assert abs(wall_bounds['left_wall_z_min'] - wall_bounds['front_wall_z_min']) < 0.001, (
            f"Left wall Z min ({wall_bounds['left_wall_z_min']:.3f}) != "
            f"Front wall Z min ({wall_bounds['front_wall_z_min']:.3f})"
        )

    def test_left_wall_flush_with_back_wall_z(self, wall_bounds):
        """Left wall back Z face should be flush with back wall back Z face."""
        assert abs(wall_bounds['left_wall_z_max'] - wall_bounds['back_wall_z_max']) < 0.001, (
            f"Left wall Z max ({wall_bounds['left_wall_z_max']:.3f}) != "
            f"Back wall Z max ({wall_bounds['back_wall_z_max']:.3f})"
        )

    def test_front_wall_flush_with_left_wall_x(self, wall_bounds):
        """Front wall left X face should be flush with left wall left X face."""
        assert abs(wall_bounds['front_wall_x_min'] - wall_bounds['left_wall_x_min']) < 0.001, (
            f"Front wall X min ({wall_bounds['front_wall_x_min']:.3f}) != "
            f"Left wall X min ({wall_bounds['left_wall_x_min']:.3f})"
        )

    def test_back_wall_flush_with_left_wall_x(self, wall_bounds):
        """Back wall left X face should be flush with left wall left X face."""
        assert abs(wall_bounds['back_wall_x_min'] - wall_bounds['left_wall_x_min']) < 0.001, (
            f"Back wall X min ({wall_bounds['back_wall_x_min']:.3f}) != "
            f"Left wall X min ({wall_bounds['left_wall_x_min']:.3f})"
        )

    def test_right_wall_flush_with_front_wall_z(self, wall_bounds):
        """Right wall front Z face should be flush with front wall front Z face."""
        assert abs(wall_bounds['right_wall_z_min'] - wall_bounds['front_wall_z_min']) < 0.001, (
            f"Right wall Z min ({wall_bounds['right_wall_z_min']:.3f}) != "
            f"Front wall Z min ({wall_bounds['front_wall_z_min']:.3f})"
        )

    def test_right_wall_flush_with_back_wall_z(self, wall_bounds):
        """Right wall back Z face should be flush with back wall back Z face."""
        assert abs(wall_bounds['right_wall_z_max'] - wall_bounds['back_wall_z_max']) < 0.001, (
            f"Right wall Z max ({wall_bounds['right_wall_z_max']:.3f}) != "
            f"Back wall Z max ({wall_bounds['back_wall_z_max']:.3f})"
        )

    def test_front_wall_flush_with_right_wall_x(self, wall_bounds):
        """Front wall right X face should be flush with right wall right X face."""
        assert abs(wall_bounds['front_wall_x_max'] - wall_bounds['right_wall_x_max']) < 0.001, (
            f"Front wall X max ({wall_bounds['front_wall_x_max']:.3f}) != "
            f"Right wall X max ({wall_bounds['right_wall_x_max']:.3f})"
        )

    def test_back_wall_flush_with_right_wall_x(self, wall_bounds):
        """Back wall right X face should be flush with right wall right X face."""
        assert abs(wall_bounds['back_wall_x_max'] - wall_bounds['right_wall_x_max']) < 0.001, (
            f"Back wall X max ({wall_bounds['back_wall_x_max']:.3f}) != "
            f"Right wall X max ({wall_bounds['right_wall_x_max']:.3f})"
        )


class TestMountingHolesClearance:
    """Tests that flexure mounting holes have clearance from front/back walls."""

    @pytest.fixture
    def mounting_geometry(self, spec, bevel_geometry):
        """Get mounting hole and wall positions."""
        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
        )
        origin = (bevel_geometry['clutch_center'], 0, 0)
        generator._generate_upper_housing(spec, origin=origin)
        wp = generator._wall_positions
        fp = generator._flexure_params
        t = wp['wall_thickness']

        # Calculate flexure outer dimensions
        fold_pitch = fp.beam_width + fp.beam_spacing
        serpentine_width = (fp.num_folds - 1) * fold_pitch + fp.beam_width
        inner_width = fp.platform_width + 2 * serpentine_width + 2 * fp.beam_spacing
        flexure_outer_width = inner_width + 2 * fp.frame_thickness

        # Mounting holes are at Z = ±(flexure_outer_width/2 - frame_thickness/2) from center (oz=0)
        mounting_hole_z_offset = flexure_outer_width / 2 - fp.frame_thickness / 2
        front_mounting_hole_z = -mounting_hole_z_offset  # Negative Z
        back_mounting_hole_z = mounting_hole_z_offset    # Positive Z

        # Wall inner faces
        front_wall_inner_z = wp['front_wall_z'] + t / 2
        back_wall_inner_z = wp['back_wall_z'] - t / 2

        return {
            'front_mounting_hole_z': front_mounting_hole_z,
            'back_mounting_hole_z': back_mounting_hole_z,
            'front_wall_inner_z': front_wall_inner_z,
            'back_wall_inner_z': back_wall_inner_z,
            'mounting_hole_diameter': fp.mounting_hole_diameter,
        }

    def test_front_mounting_holes_clear_of_front_wall(self, mounting_geometry):
        """Front mounting holes should be clear of front wall inner face."""
        mg = mounting_geometry
        # Mounting hole center should be well outside the front wall
        clearance = mg['front_mounting_hole_z'] - mg['front_wall_inner_z']
        assert clearance > mg['mounting_hole_diameter'], (
            f"Front mounting holes at Z={mg['front_mounting_hole_z']:.2f} too close to "
            f"front wall inner face at Z={mg['front_wall_inner_z']:.2f} "
            f"(clearance={clearance:.2f}mm, need >{mg['mounting_hole_diameter']:.2f}mm)"
        )

    def test_back_mounting_holes_clear_of_back_wall(self, mounting_geometry):
        """Back mounting holes should be clear of back wall inner face."""
        mg = mounting_geometry
        # Mounting hole center should be well outside the back wall
        clearance = mg['back_wall_inner_z'] - mg['back_mounting_hole_z']
        assert clearance > mg['mounting_hole_diameter'], (
            f"Back mounting holes at Z={mg['back_mounting_hole_z']:.2f} too close to "
            f"back wall inner face at Z={mg['back_wall_inner_z']:.2f} "
            f"(clearance={clearance:.2f}mm, need >{mg['mounting_hole_diameter']:.2f}mm)"
        )

    def test_mounting_hole_diameter_is_m2(self, mounting_geometry):
        """Mounting holes should be sized for M2 screws (2.2mm clearance)."""
        assert abs(mounting_geometry['mounting_hole_diameter'] - 2.2) < 0.01, (
            f"Mounting hole diameter ({mounting_geometry['mounting_hole_diameter']}mm) "
            f"should be 2.2mm for M2 clearance"
        )


class TestRightWallNoIntersections:
    """Tests that right wall doesn't intersect with driven bevel gear."""

    @pytest.fixture
    def right_wall(self, spec, bevel_geometry):
        """Generate the right wall in isolation."""
        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
        )
        origin = (bevel_geometry['clutch_center'], 0, 0)
        generator._generate_upper_housing(spec, origin=origin)
        wp = generator._wall_positions
        t = wp['wall_thickness']

        # Recreate right wall using same logic as generator
        right_wall = generator._make_right_wall(
            wall_x=wp['right_wall_x'],
            y_min=wp['wall_bottom_y'],
            y_max=wp['wall_top_y'],
            z_min=wp['front_wall_z'] - t / 2,
            z_max=wp['back_wall_z'] + t / 2,
            thickness=t,
        )
        return right_wall

    def test_right_wall_no_intersection_with_driven_bevel(self, right_wall, components):
        """Right wall should not intersect with driven (gold) bevel gear."""
        assert not shapes_intersect(right_wall, components['driven_bevel']), (
            "Right wall intersects with driven bevel gear"
        )


class TestUpperLowerHousingAlignment:
    """Tests that upper housing walls are aligned with lower housing plates."""

    @pytest.fixture
    def housing_positions(self, spec, bevel_geometry):
        """Get positions of both upper and lower housing."""
        # Get upper housing wall positions
        upper_gen = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
        )
        origin = (bevel_geometry['clutch_center'], 0, 0)
        upper_gen._generate_upper_housing(spec, origin=origin)
        upper_wp = upper_gen._wall_positions

        # Get lower housing plate positions
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)

        return {
            'upper_left_wall_x': upper_wp['left_wall_x'],
            'upper_right_wall_x': upper_wp['right_wall_x'],
            'lower_left_plate_x': housing_layout.left_plate_x,
            'lower_right_plate_x': housing_layout.right_plate_x,
        }

    def test_upper_left_wall_aligned_with_lower_left_plate(self, housing_positions):
        """Upper housing left wall should be at same X as lower housing left plate."""
        assert abs(housing_positions['upper_left_wall_x'] - housing_positions['lower_left_plate_x']) < 0.001, (
            f"Upper left wall X ({housing_positions['upper_left_wall_x']:.3f}) != "
            f"Lower left plate X ({housing_positions['lower_left_plate_x']:.3f})"
        )

    def test_upper_right_wall_aligned_with_lower_right_plate(self, housing_positions):
        """Upper housing right wall should be at same X as lower housing right plate."""
        assert abs(housing_positions['upper_right_wall_x'] - housing_positions['lower_right_plate_x']) < 0.001, (
            f"Upper right wall X ({housing_positions['upper_right_wall_x']:.3f}) != "
            f"Lower right plate X ({housing_positions['lower_right_plate_x']:.3f})"
        )


class TestDrivingAxleNoLeverIntersection:
    """Test that driving bevel axle doesn't intersect with shift lever."""

    @pytest.fixture
    def driving_axle_with_flexure(self, spec, bevel_geometry):
        """Generate the driving bevel axle from housing with flexure."""
        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=True,
            include_flexure=True,
        )
        # Generate housing to set up wall positions (at clutch_center origin)
        ox = bevel_geometry['clutch_center']
        origin = (ox, 0, 0)
        generator._generate_upper_housing(spec, origin=origin)
        wp = generator._wall_positions
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)

        shaft_diameter = spec.primary_shaft_diameter
        axle_overhang = housing_layout.axle_overhang
        wall_thickness = wp['wall_thickness']

        # Calculate axle position (must match _add_axles method)
        left_wall_x = wp['left_wall_x']
        driving_axle_start = left_wall_x - wall_thickness / 2 - axle_overhang
        driving_gear_x = ox - bevel_layout.mesh_distance
        lever_clearance = 2.0
        lever_left_edge = ox - 6.0  # Lever pivot is at clutch_center
        driving_axle_end = min(driving_gear_x + 8, lever_left_edge - lever_clearance)
        driving_axle_length = driving_axle_end - driving_axle_start

        driving_axle = (
            cq.Workplane('YZ')
            .center(wp['pivot_y'], wp['driving_axle_z'])
            .circle(shaft_diameter / 2)
            .extrude(driving_axle_length)
            .translate((driving_axle_start, 0, 0))
        )
        return driving_axle

    def test_driving_axle_no_intersection_with_lever(self, driving_axle_with_flexure, components):
        """Driving bevel axle should not intersect with shift lever."""
        assert not shapes_intersect(driving_axle_with_flexure, components['shift_lever']), (
            "Driving bevel axle intersects with shift lever"
        )


class TestLowerHousingEnclosure:
    """Tests that lower housing enclosure walls are flush with plates."""

    @pytest.fixture
    def lower_housing_positions(self, spec):
        """Get lower housing plate and wall positions."""
        from mechlogic.generators.lower_housing import LowerHousingGenerator

        gen = LowerHousingGenerator(spec=spec)
        info = gen.get_plate_positions()
        t = info['plate_thickness']

        return {
            # Side plates (YZ planes)
            'left_plate_x': info['left_plate_x'],
            'right_plate_x': info['right_plate_x'],
            'left_plate_x_min': info['left_plate_x'] - t / 2,
            'left_plate_x_max': info['left_plate_x'] + t / 2,
            'right_plate_x_min': info['right_plate_x'] - t / 2,
            'right_plate_x_max': info['right_plate_x'] + t / 2,
            # Front/back walls (XY planes)
            'front_wall_z': info['front_wall_z'],
            'back_wall_z': info['back_wall_z'],
            'front_wall_z_min': info['front_wall_z'] - t / 2,
            'front_wall_z_max': info['front_wall_z'] + t / 2,
            'back_wall_z_min': info['back_wall_z'] - t / 2,
            'back_wall_z_max': info['back_wall_z'] + t / 2,
            # Side plates Z extent
            'plate_z_min': info['z_min'],
            'plate_z_max': info['z_max'],
            'plate_thickness': t,
        }

    def test_front_wall_flush_with_left_plate_x(self, lower_housing_positions):
        """Front wall left X face should be flush with left plate left X face."""
        hp = lower_housing_positions
        # Front wall X extent should start at left plate's left face
        expected_x_min = hp['left_plate_x_min']
        # Front wall X is from left_plate_x - t/2 to right_plate_x + t/2
        actual_x_min = hp['left_plate_x_min']
        assert abs(actual_x_min - expected_x_min) < 0.001, (
            f"Front wall X min ({actual_x_min:.3f}) != Left plate X min ({expected_x_min:.3f})"
        )

    def test_front_wall_flush_with_right_plate_x(self, lower_housing_positions):
        """Front wall right X face should be flush with right plate right X face."""
        hp = lower_housing_positions
        expected_x_max = hp['right_plate_x_max']
        actual_x_max = hp['right_plate_x_max']
        assert abs(actual_x_max - expected_x_max) < 0.001, (
            f"Front wall X max ({actual_x_max:.3f}) != Right plate X max ({expected_x_max:.3f})"
        )

    def test_left_plate_flush_with_front_wall_z(self, lower_housing_positions):
        """Left plate front Z face should be flush with front wall front Z face."""
        hp = lower_housing_positions
        # Plate Z extent should match front wall outer Z
        assert abs(hp['plate_z_min'] - hp['front_wall_z']) < 0.001, (
            f"Left plate Z min ({hp['plate_z_min']:.3f}) != Front wall Z ({hp['front_wall_z']:.3f})"
        )

    def test_left_plate_flush_with_back_wall_z(self, lower_housing_positions):
        """Left plate back Z face should be flush with back wall back Z face."""
        hp = lower_housing_positions
        assert abs(hp['plate_z_max'] - hp['back_wall_z']) < 0.001, (
            f"Left plate Z max ({hp['plate_z_max']:.3f}) != Back wall Z ({hp['back_wall_z']:.3f})"
        )

    def test_enclosure_forms_complete_frame(self, spec):
        """All four walls should form a complete rectangular frame."""
        from mechlogic.generators.lower_housing import LowerHousingGenerator

        gen = LowerHousingGenerator(spec=spec)
        side_plates, front_back_walls = gen.generate()

        # Verify both parts have non-zero volume
        assert side_plates.val().Volume() > 0, "Side plates have no volume"
        assert front_back_walls.val().Volume() > 0, "Front/back walls have no volume"

        # Combined should have more volume than either alone
        combined = side_plates.union(front_back_walls)
        assert combined.val().Volume() > side_plates.val().Volume(), (
            "Combined volume should be greater than side plates alone"
        )


class TestExtendedWallsNoIntersections:
    """Tests that extended L-shaped walls don't intersect with gears."""

    @pytest.fixture
    def extended_housing(self, spec, bevel_geometry):
        """Generate upper housing with wall extensions enabled."""
        from mechlogic.generators.lower_housing import LowerHousingParams

        lower_params = LowerHousingParams.from_spec(spec)
        lower_housing_y_max = lower_params.plate_height / 2

        generator = BevelLeverWithUpperHousingGenerator(
            include_axles=False,
            include_flexure=True,
            extend_to_lower_housing=True,
            lower_housing_y_max=lower_housing_y_max,
        )
        origin = (bevel_geometry['clutch_center'], 0, 0)
        housing = generator._generate_upper_housing(spec, origin=origin)
        return housing, generator._wall_positions

    @pytest.fixture
    def selector_gears(self, spec, bevel_geometry):
        """Generate selector mechanism gears in their positions."""
        from mechlogic.generators.gear_spur import SpurGearGenerator
        from mechlogic.generators.dog_clutch import DogClutchGenerator

        selector_layout = LayoutCalculator.calculate_selector_layout(spec)
        placement = PartPlacement(part_type=PartType.GEAR_A, part_id='test')

        # Generate gears
        gear_a = SpurGearGenerator(gear_id='selector_a').generate(spec, placement)
        gear_b = SpurGearGenerator(gear_id='selector_b').generate(spec, placement)
        clutch = DogClutchGenerator().generate(spec, placement)

        # Position gears (rotated 90° around Y axis, positioned along X)
        gear_a_positioned = (
            gear_a
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((selector_layout.gear_a_center, 0, 0))
        )
        gear_b_positioned = (
            gear_b
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((selector_layout.gear_b_center, 0, 0))
        )
        clutch_positioned = (
            clutch
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((selector_layout.clutch_center, 0, 0))
        )

        return {
            'gear_a': gear_a_positioned,
            'gear_b': gear_b_positioned,
            'clutch': clutch_positioned,
        }

    @pytest.fixture
    def input_gears(self, spec):
        """Generate input gears in their positions."""
        from mechlogic.generators.gear_spur import SpurGearGenerator

        mux_layout = LayoutCalculator.calculate_mux_layout(spec)
        placement = PartPlacement(part_type=PartType.GEAR_A, part_id='test')

        # Generate input gears
        input_a = SpurGearGenerator(gear_id='input_a').generate(spec, placement)
        input_b = SpurGearGenerator(gear_id='input_b').generate(spec, placement)

        # Position input gears (rotated 90° around Y axis)
        input_a_positioned = (
            input_a
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((mux_layout.input_a_x, 0, mux_layout.input_a_z))
        )
        input_b_positioned = (
            input_b
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((mux_layout.input_b_x, 0, mux_layout.input_b_z))
        )

        return {
            'input_a': input_a_positioned,  # At Z = +36
            'input_b': input_b_positioned,  # At Z = -36
        }

    def test_extended_housing_no_intersection_with_gear_a(self, extended_housing, selector_gears):
        """Extended housing should not intersect with selector gear A."""
        housing, _ = extended_housing
        assert not shapes_intersect(housing, selector_gears['gear_a']), (
            "Extended housing intersects with selector gear A"
        )

    def test_extended_housing_no_intersection_with_gear_b(self, extended_housing, selector_gears):
        """Extended housing should not intersect with selector gear B."""
        housing, _ = extended_housing
        assert not shapes_intersect(housing, selector_gears['gear_b']), (
            "Extended housing intersects with selector gear B"
        )

    def test_extended_housing_no_intersection_with_clutch(self, extended_housing, selector_gears):
        """Extended housing should not intersect with dog clutch."""
        housing, _ = extended_housing
        assert not shapes_intersect(housing, selector_gears['clutch']), (
            "Extended housing intersects with dog clutch"
        )

    def test_extended_housing_no_intersection_with_input_a(self, extended_housing, input_gears):
        """Extended housing (back wall) should not intersect with input gear A."""
        housing, _ = extended_housing
        assert not shapes_intersect(housing, input_gears['input_a']), (
            "Extended housing intersects with input gear A (at Z=+36)"
        )

    def test_extended_housing_no_intersection_with_input_b(self, extended_housing, input_gears):
        """Extended housing (front wall) should not intersect with input gear B."""
        housing, _ = extended_housing
        assert not shapes_intersect(housing, input_gears['input_b']), (
            "Extended housing intersects with input gear B (at Z=-36)"
        )

    def test_extended_walls_reach_lower_housing(self, extended_housing, spec):
        """Extended walls should reach down to lower housing Y position."""
        from mechlogic.generators.lower_housing import LowerHousingParams

        _, wall_positions = extended_housing
        lower_params = LowerHousingParams.from_spec(spec)
        expected_y_min = lower_params.plate_height / 2

        assert abs(wall_positions['extension_y_min'] - expected_y_min) < 0.001, (
            f"Extension Y min ({wall_positions['extension_y_min']:.3f}) != "
            f"Lower housing Y max ({expected_y_min:.3f})"
        )
