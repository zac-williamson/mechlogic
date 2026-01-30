"""Tests for housing generator."""

import pytest

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType


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
            "dog_clutch": {"teeth": 6, "tooth_height": 2.0, "engagement_depth": 1.5},
        },
        "geometry": {
            "axle_length": 60.0,
            "housing_thickness": 4.0,
            "lever_throw": 8.0,
            "clutch_width": 10.0,
            "gear_face_width": 8.0,
            "gear_spacing": 3.0,
        },
        "flexure": {"thickness": 1.2, "length": 15.0, "max_deflection": 2.0},
    }


@pytest.fixture
def spec(spec_data):
    return LogicElementSpec.model_validate(spec_data)


class TestHousingGenerator:
    """Tests for HousingGenerator."""

    def test_front_housing_has_cutouts(self, spec):
        from mechlogic.generators.housing import HousingGenerator

        gen = HousingGenerator(is_front=True)
        placement = PartPlacement(
            part_type=PartType.HOUSING_FRONT,
            part_id="housing_front",
        )

        housing = gen.generate(spec, placement)

        # Front housing should have more material removed than back
        # (lever pivot bore + S-axis cutout + flexure mount holes)
        bb = housing.val().BoundingBox()
        bounding_volume = bb.xlen * bb.ylen * bb.zlen
        actual_volume = housing.val().Volume()

        # Should have some material removed (holes, cutouts)
        # The ratio depends on plate size vs cutout size; verify cutouts exist
        assert actual_volume < bounding_volume * 0.99

    def test_back_housing_simpler(self, spec):
        from mechlogic.generators.housing import HousingGenerator

        gen_front = HousingGenerator(is_front=True)
        gen_back = HousingGenerator(is_front=False)

        placement_f = PartPlacement(part_type=PartType.HOUSING_FRONT, part_id="f")
        placement_b = PartPlacement(part_type=PartType.HOUSING_BACK, part_id="b")

        front = gen_front.generate(spec, placement_f)
        back = gen_back.generate(spec, placement_b)

        # Back housing should have more material (fewer cutouts)
        front_vol = front.val().Volume()
        back_vol = back.val().Volume()

        assert back_vol > front_vol
