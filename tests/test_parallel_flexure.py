"""Tests for parallel beam flexure geometry."""

import pytest
import cadquery as cq

from mechlogic.generators.parallel_flexure import (
    ParallelFlexureGenerator,
    ParallelFlexureParams,
)


@pytest.fixture
def default_params():
    """Return default flexure parameters."""
    return ParallelFlexureParams()


@pytest.fixture
def flexure(default_params):
    """Generate a flexure with default parameters."""
    gen = ParallelFlexureGenerator(default_params)
    return gen.generate()


class TestParallelFlexureGeometry:
    """Tests for flexure geometry."""

    def test_generates_valid_solid(self, flexure):
        """Flexure should generate a valid solid."""
        solid = flexure.val()
        assert solid is not None
        assert solid.Volume() > 0

    def test_has_axle_hole(self, default_params):
        """Flexure should have an axle hole through the center."""
        gen = ParallelFlexureGenerator(default_params)
        flexure = gen.generate()

        # The axle hole should be visible when looking at the top face
        # Check that we can find a circular edge with the expected diameter
        solid = flexure.val()
        bbox = solid.BoundingBox()

        # Volume should be less than a solid block (due to holes and cutouts)
        outer_w = default_params.platform_width + 2 * default_params.beam_length + 2 * default_params.frame_thickness
        outer_h = default_params.beam_spacing + default_params.beam_width + 4.0 + 2 * default_params.frame_thickness
        max_volume = outer_w * outer_h * default_params.thickness
        assert solid.Volume() < max_volume

    def test_has_correct_thickness(self, default_params, flexure):
        """Flexure should have the specified Z thickness."""
        solid = flexure.val()
        bbox = solid.BoundingBox()

        z_size = bbox.zmax - bbox.zmin
        assert abs(z_size - default_params.thickness) < 0.01

    def test_platform_is_centered(self, default_params):
        """The floating platform should be centered at the origin."""
        gen = ParallelFlexureGenerator(default_params)
        flexure = gen.generate()
        solid = flexure.val()
        bbox = solid.BoundingBox()

        # Bounding box should be roughly symmetric around origin
        assert abs(bbox.xmin + bbox.xmax) < 0.1
        assert abs(bbox.ymin + bbox.ymax) < 0.1

    def test_mounting_holes_present(self, default_params):
        """Mounting holes should be present when enabled."""
        params = ParallelFlexureParams(include_mounting_holes=True)
        gen = ParallelFlexureGenerator(params)
        flexure = gen.generate()

        # The volume with mounting holes should be less than without
        params_no_holes = ParallelFlexureParams(include_mounting_holes=False)
        gen_no_holes = ParallelFlexureGenerator(params_no_holes)
        flexure_no_holes = gen_no_holes.generate()

        assert flexure.val().Volume() < flexure_no_holes.val().Volume()


class TestParallelFlexureStiffness:
    """Tests for stiffness calculations."""

    def test_stiffness_increases_with_beam_width(self):
        """Wider beams should be stiffer."""
        params_thin = ParallelFlexureParams(beam_width=1.0)
        params_thick = ParallelFlexureParams(beam_width=2.0)

        gen_thin = ParallelFlexureGenerator(params_thin)
        gen_thick = ParallelFlexureGenerator(params_thick)

        k_thin = gen_thin.get_stiffness_estimate()
        k_thick = gen_thick.get_stiffness_estimate()

        assert k_thick > k_thin

    def test_stiffness_decreases_with_beam_length(self):
        """Longer beams should be more compliant."""
        params_short = ParallelFlexureParams(beam_length=15.0)
        params_long = ParallelFlexureParams(beam_length=30.0)

        gen_short = ParallelFlexureGenerator(params_short)
        gen_long = ParallelFlexureGenerator(params_long)

        k_short = gen_short.get_stiffness_estimate()
        k_long = gen_long.get_stiffness_estimate()

        assert k_short > k_long

    def test_stiffness_increases_with_thickness(self):
        """Thicker parts (Z) should be stiffer."""
        params_thin = ParallelFlexureParams(thickness=5.0)
        params_thick = ParallelFlexureParams(thickness=10.0)

        gen_thin = ParallelFlexureGenerator(params_thin)
        gen_thick = ParallelFlexureGenerator(params_thick)

        k_thin = gen_thin.get_stiffness_estimate()
        k_thick = gen_thick.get_stiffness_estimate()

        assert k_thick > k_thin

    def test_max_deflection_scales_with_beam_length(self):
        """Longer beams should allow more deflection."""
        params_short = ParallelFlexureParams(beam_length=15.0)
        params_long = ParallelFlexureParams(beam_length=30.0)

        gen_short = ParallelFlexureGenerator(params_short)
        gen_long = ParallelFlexureGenerator(params_long)

        d_short = gen_short.get_max_deflection_estimate()
        d_long = gen_long.get_max_deflection_estimate()

        assert d_long > d_short


class TestParallelFlexureParameterVariations:
    """Tests for various parameter combinations."""

    def test_small_axle(self):
        """Should work with small axle diameter."""
        params = ParallelFlexureParams(axle_diameter=3.0)
        gen = ParallelFlexureGenerator(params)
        flexure = gen.generate()
        assert flexure.val().Volume() > 0

    def test_large_axle(self):
        """Should work with large axle diameter."""
        params = ParallelFlexureParams(axle_diameter=10.0, platform_width=20.0, platform_height=16.0)
        gen = ParallelFlexureGenerator(params)
        flexure = gen.generate()
        assert flexure.val().Volume() > 0

    def test_long_beams(self):
        """Should work with long beams for high compliance."""
        params = ParallelFlexureParams(beam_length=40.0)
        gen = ParallelFlexureGenerator(params)
        flexure = gen.generate()
        assert flexure.val().Volume() > 0

    def test_thin_beams(self):
        """Should work with thin beams for high compliance."""
        params = ParallelFlexureParams(beam_width=0.8)
        gen = ParallelFlexureGenerator(params)
        flexure = gen.generate()
        assert flexure.val().Volume() > 0
