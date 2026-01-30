"""Tests for flexure block generator."""

import pytest

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType


@pytest.fixture
def spec_data():
    """Return valid specification data."""
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


class TestFlexureBlockGenerator:
    """Tests for FlexureBlockGenerator."""

    def test_import(self):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator
        assert FlexureBlockGenerator is not None

    def test_generates_solid(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)

        # Should produce valid geometry
        assert block is not None
        assert block.val().isValid()

    def test_beam_length_matches_spec(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)
        bb = block.val().BoundingBox()

        # Total length in Y = plate/2 (10) + beam (15) + boss (10) = 35 from center
        # Full Y extent ~45mm (plate extends -10 to +10, beam/boss extend to +35)
        expected_min_length = spec.flexure.length + 15
        assert bb.ylen >= expected_min_length

    def test_has_bearing_bore(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)

        # Volume should be less than solid block (bore removed)
        bb = block.val().BoundingBox()
        bounding_volume = bb.xlen * bb.ylen * bb.zlen
        actual_volume = block.val().Volume()

        assert actual_volume < bounding_volume * 0.9  # At least 10% removed

    def test_has_mounting_holes(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)

        # Check that volume is reduced by mounting holes
        # Mounting plate is approximately 20x20x4mm with 4 holes of 3.2mm dia
        # Each hole removes about 32mm^3, total ~128mm^3
        bb = block.val().BoundingBox()
        bounding_volume = bb.xlen * bb.ylen * bb.zlen
        actual_volume = block.val().Volume()

        # Should have significant material removed (bore + mounting holes)
        assert actual_volume < bounding_volume * 0.85

    def test_metadata(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        meta = gen.get_metadata(spec)

        assert meta.part_type == PartType.FLEXURE_BLOCK
        assert meta.dimensions["beam_thickness"] == 1.2
        assert meta.dimensions["beam_length"] == 15.0
        assert "layer lines" in meta.notes.lower()
