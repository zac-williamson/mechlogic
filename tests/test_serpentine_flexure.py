"""Tests for serpentine flexure geometry."""

import pytest
import cadquery as cq

from mechlogic.generators.serpentine_flexure import (
    SerpentineFlexureGenerator,
    SerpentineFlexureParams,
)


@pytest.fixture
def default_params():
    """Return default flexure parameters."""
    return SerpentineFlexureParams()


@pytest.fixture
def flexure(default_params):
    """Generate a flexure with default parameters."""
    gen = SerpentineFlexureGenerator(default_params)
    return gen.generate()


class TestSerpentineFlexureGeometry:
    """Tests for flexure geometry."""

    def test_generates_valid_solid(self, flexure):
        """Flexure should generate a valid solid."""
        solid = flexure.val()
        assert solid is not None
        assert solid.Volume() > 0

    def test_has_correct_thickness(self, default_params, flexure):
        """Flexure should have the specified Z thickness."""
        solid = flexure.val()
        bbox = solid.BoundingBox()

        z_size = bbox.zmax - bbox.zmin
        assert abs(z_size - default_params.thickness) < 0.01

    def test_is_centered(self, flexure):
        """Flexure should be centered at the origin."""
        solid = flexure.val()
        bbox = solid.BoundingBox()

        assert abs(bbox.xmin + bbox.xmax) < 0.1
        assert abs(bbox.ymin + bbox.ymax) < 0.1

    def test_mounting_holes_present(self):
        """Mounting holes should be present when enabled."""
        params_with = SerpentineFlexureParams(include_mounting_holes=True)
        params_without = SerpentineFlexureParams(include_mounting_holes=False)

        gen_with = SerpentineFlexureGenerator(params_with)
        gen_without = SerpentineFlexureGenerator(params_without)

        vol_with = gen_with.generate().val().Volume()
        vol_without = gen_without.generate().val().Volume()

        assert vol_with < vol_without


class TestSerpentineFlexureStiffness:
    """Tests for stiffness calculations."""

    def test_more_folds_means_more_compliance(self):
        """More folds should result in lower stiffness."""
        params_few = SerpentineFlexureParams(num_folds=3)
        params_many = SerpentineFlexureParams(num_folds=6)

        gen_few = SerpentineFlexureGenerator(params_few)
        gen_many = SerpentineFlexureGenerator(params_many)

        k_few = gen_few.get_stiffness_estimate()
        k_many = gen_many.get_stiffness_estimate()

        assert k_few > k_many

    def test_longer_segments_means_more_compliance(self):
        """Longer segments should result in lower stiffness."""
        params_short = SerpentineFlexureParams(segment_length=10.0)
        params_long = SerpentineFlexureParams(segment_length=25.0)

        gen_short = SerpentineFlexureGenerator(params_short)
        gen_long = SerpentineFlexureGenerator(params_long)

        k_short = gen_short.get_stiffness_estimate()
        k_long = gen_long.get_stiffness_estimate()

        assert k_short > k_long

    def test_effective_length_increases_with_folds(self):
        """More folds should increase effective beam length."""
        params_few = SerpentineFlexureParams(num_folds=3)
        params_many = SerpentineFlexureParams(num_folds=6)

        gen_few = SerpentineFlexureGenerator(params_few)
        gen_many = SerpentineFlexureGenerator(params_many)

        L_few = gen_few.get_effective_beam_length()
        L_many = gen_many.get_effective_beam_length()

        assert L_many > L_few

    def test_max_deflection_increases_with_folds(self):
        """More folds should allow more deflection."""
        params_few = SerpentineFlexureParams(num_folds=3)
        params_many = SerpentineFlexureParams(num_folds=6)

        gen_few = SerpentineFlexureGenerator(params_few)
        gen_many = SerpentineFlexureGenerator(params_many)

        d_few = gen_few.get_max_deflection_estimate()
        d_many = gen_many.get_max_deflection_estimate()

        assert d_many > d_few


class TestSerpentineFlexureForBevelDisengagement:
    """Tests specific to bevel gear disengagement use case."""

    def test_achieves_required_deflection(self):
        """Flexure should achieve >3.38mm deflection for bevel gear disengagement."""
        # Bevel gear whole depth = 3.38mm
        required_deflection = 3.38

        params = SerpentineFlexureParams(
            num_folds=4,
            segment_length=15.0,
            beam_width=0.8,
            thickness=5.0,
        )

        gen = SerpentineFlexureGenerator(params)
        max_deflection = gen.get_max_deflection_estimate()

        assert max_deflection > required_deflection, (
            f"Flexure max deflection ({max_deflection:.2f}mm) must exceed "
            f"bevel gear tooth depth ({required_deflection}mm)"
        )

    def test_reasonable_stiffness(self):
        """Flexure should have reasonable stiffness (not too soft)."""
        params = SerpentineFlexureParams(
            num_folds=4,
            segment_length=15.0,
            beam_width=0.8,
            thickness=5.0,
        )

        gen = SerpentineFlexureGenerator(params)
        k = gen.get_stiffness_estimate()

        # Should be stiff enough to return to center but soft enough to deflect
        assert 0.5 < k < 5.0, f"Stiffness {k:.2f} N/mm outside reasonable range"

    def test_compact_footprint(self):
        """Flexure should fit in a compact footprint."""
        params = SerpentineFlexureParams(
            num_folds=4,
            segment_length=15.0,
        )

        gen = SerpentineFlexureGenerator(params)
        flexure = gen.generate()

        bbox = flexure.val().BoundingBox()
        width = bbox.xmax - bbox.xmin
        height = bbox.ymax - bbox.ymin

        # Should be less than 60mm in each direction
        assert width < 60, f"Width {width:.0f}mm exceeds 60mm limit"
        assert height < 60, f"Height {height:.0f}mm exceeds 60mm limit"
