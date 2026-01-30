"""Tests for bevel gear generator."""

import pytest
import math

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


class TestBevelGearGenerator:
    """Tests for BevelGearGenerator."""

    def test_import(self):
        from mechlogic.generators.gear_bevel import BevelGearGenerator
        assert BevelGearGenerator is not None

    def test_driving_gear_is_conical(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driving")
        placement = PartPlacement(
            part_type=PartType.BEVEL_DRIVE,
            part_id="bevel_driving",
        )

        gear = gen.generate(spec, placement)
        bb = gear.val().BoundingBox()

        # Gear should be conical - height (Z) should be significant
        # Face width = 2.5 * module = 2.5 * 1.5 = 3.75mm
        face_width = 2.5 * spec.gears.module
        assert bb.zlen >= face_width * 0.8, f"Z height {bb.zlen} too small for conical gear"

        # Pitch diameter at back = module * teeth = 1.5 * 16 = 24mm
        pitch_dia = spec.gears.module * spec.gears.bevel_teeth
        # With addendum, outer diameter slightly larger
        assert bb.xlen >= pitch_dia * 0.9, f"X diameter {bb.xlen} too small"
        assert bb.ylen >= pitch_dia * 0.9, f"Y diameter {bb.ylen} too small"

    def test_gear_has_teeth(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driving")
        placement = PartPlacement(
            part_type=PartType.BEVEL_DRIVE,
            part_id="bevel_driving",
        )

        gear = gen.generate(spec, placement)

        actual_volume = gear.val().Volume()

        # Basic sanity checks - gear should have positive volume
        assert actual_volume > 0, f"Gear volume should be positive: {actual_volume:.1f}"

        # Gear should have reasonable volume for a 16-tooth bevel gear
        # Rough estimate: at least 200 mm^3 for a gear with ~24mm pitch diameter
        assert actual_volume > 200, f"Gear volume too small: {actual_volume:.1f}"

    def test_metadata_driving(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driving")
        meta = gen.get_metadata(spec)

        assert meta.part_type == PartType.BEVEL_DRIVE
        assert meta.dimensions["teeth"] == 16
        assert meta.dimensions["module"] == 1.5
        assert meta.dimensions["cone_angle"] == 45.0

    def test_invalid_gear_id(self):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        with pytest.raises(ValueError, match="must be 'driving' or 'driven'"):
            BevelGearGenerator(gear_id="invalid")
