"""Tests for layout solver bevel gear positioning."""

import pytest

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartType
from mechlogic.assembly.layout import LayoutSolver


@pytest.fixture
def spec_data():
    return {
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
                "teeth": 6,
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
            "gear_spacing": 3.0,
        },
        "flexure": {
            "thickness": 1.2,
            "length": 15.0,
            "max_deflection": 2.0,
        },
    }


@pytest.fixture
def spec(spec_data):
    return LogicElementSpec.model_validate(spec_data)


class TestLayoutBevelGears:
    """Tests for bevel gear layout."""

    def test_layout_includes_bevel_driving(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        assert "bevel_driving" in model.parts
        assert model.parts["bevel_driving"].part_type == PartType.BEVEL_DRIVE

    def test_layout_includes_bevel_driven(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        assert "bevel_driven" in model.parts
        assert model.parts["bevel_driven"].part_type == PartType.BEVEL_DRIVEN

    def test_layout_includes_lever_pivot(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        assert "lever_pivot" in model.parts
        assert model.parts["lever_pivot"].part_type == PartType.LEVER_PIVOT

    def test_bevel_gears_perpendicular(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        driving = model.parts["bevel_driving"]
        driven = model.parts["bevel_driven"]

        # Driving gear on S-axis (rotated 90 deg around X)
        # Driven gear on lever axis (no rotation or different)
        # Their rotations should differ by 90 degrees on one axis
        assert driving.rotation != driven.rotation

    def test_bevel_apexes_meet(self, spec):
        """Verify bevel gear pitch cone apexes meet at the same point."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driving = model.parts["bevel_driving"]
        driven = model.parts["bevel_driven"]

        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pitch_radius = (module * teeth) / 2

        # Calculate apex positions
        # Driven bevel: axis along Z, apex at Z = origin_z + pitch_radius
        driven_apex_y = driven.origin[1]
        driven_apex_z = driven.origin[2] + pitch_radius

        # Driving bevel: axis along Y (after 90° X rotation), apex at Y = origin_y - pitch_radius
        driving_apex_y = driving.origin[1] - pitch_radius
        driving_apex_z = driving.origin[2]

        # Apexes should meet at the same point
        apex_y_diff = abs(driven_apex_y - driving_apex_y)
        apex_z_diff = abs(driven_apex_z - driving_apex_z)

        assert apex_y_diff < 1.0, \
            f"Apex Y positions differ by {apex_y_diff}mm (driven={driven_apex_y}, driving={driving_apex_y})"
        assert apex_z_diff < 1.0, \
            f"Apex Z positions differ by {apex_z_diff}mm (driven={driven_apex_z}, driving={driving_apex_z})"

        # X positions should match (both on centerline)
        dx = abs(driving.origin[0] - driven.origin[0])
        assert dx < 0.1, f"Bevels should be on same X centerline, dx={dx}"

    def test_driven_bevel_at_lever_pivot(self, spec):
        """Verify driven bevel is at the lever pivot location."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driven = model.parts["bevel_driven"]
        pivot = model.parts["lever_pivot"]

        # Driven bevel should share Y coordinate with lever pivot
        assert abs(driven.origin[1] - pivot.origin[1]) < 1.0, \
            "Driven bevel should be at lever pivot Y position"

    def test_layout_includes_flexure_block(self, spec):
        """Verify flexure block is included in layout."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        assert "flexure_block" in model.parts
        assert model.parts["flexure_block"].part_type == PartType.FLEXURE_BLOCK

    def test_bevel_gears_y_separated_for_mesh(self, spec):
        """Verify bevel gears have proper Y separation for mesh contact."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driving = model.parts["bevel_driving"]
        driven = model.parts["bevel_driven"]

        # Driving gear (on S-axis, rotated 90°) should be above driven gear
        # Y separation should allow pitch circles to touch
        dy = driving.origin[1] - driven.origin[1]
        bevel_pitch_radius = (spec.gears.module * spec.gears.bevel_teeth) / 2
        face_width = 2.5 * spec.gears.module

        # Driving is above driven, separation should be roughly face_width + pitch_radius
        assert dy >= face_width, \
            f"Bevel gears Y separation {dy} too small for mesh, need >= {face_width}"

    def test_lever_pivot_aligned_with_driven_bevel(self, spec):
        """Verify lever pivot axle passes through driven bevel bore."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driven = model.parts["bevel_driven"]
        lever_pivot = model.parts["lever_pivot"]

        # Lever pivot should be at same Y and Z as driven bevel (to pass through bore)
        dy = abs(driven.origin[1] - lever_pivot.origin[1])
        dz = abs(driven.origin[2] - lever_pivot.origin[2])

        assert dy < 1.0, f"Lever pivot Y should match driven bevel Y, diff={dy}"
        assert dz < 1.0, f"Lever pivot Z should match driven bevel Z, diff={dz}"

    def test_flexure_mounted_to_housing(self, spec):
        """Verify flexure is positioned at front housing outer face."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        flexure = model.parts["flexure_block"]
        housing_front = model.parts["housing_front"]

        # Flexure should be at or near the front housing Z position
        # (mounted to outer face, so slightly in front)
        housing_z = housing_front.origin[2]
        housing_t = spec.geometry.housing_thickness

        # Flexure origin should be near the outer face of housing
        expected_z = housing_z - housing_t / 2
        assert abs(flexure.origin[2] - expected_z) < 5.0, \
            f"Flexure Z {flexure.origin[2]} not near housing outer face {expected_z}"
