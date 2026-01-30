"""Tests for specification parsing and validation."""

import pytest
import yaml
from pathlib import Path

from mechlogic.models.spec import (
    LogicElementSpec,
    GearSpec,
    DogClutchSpec,
    GeometrySpec,
    FlexureSpec,
    ToleranceSpec,
)


class TestDogClutchSpec:
    """Tests for DogClutchSpec validation."""

    def test_valid_dog_clutch(self):
        spec = DogClutchSpec(teeth=6, tooth_height=2.0, engagement_depth=1.5)
        assert spec.teeth == 6
        assert spec.tooth_height == 2.0
        assert spec.engagement_depth == 1.5

    def test_engagement_exceeds_height(self):
        with pytest.raises(ValueError, match="engagement_depth cannot exceed"):
            DogClutchSpec(teeth=6, tooth_height=2.0, engagement_depth=3.0)

    def test_too_few_teeth(self):
        with pytest.raises(ValueError):
            DogClutchSpec(teeth=2, tooth_height=2.0, engagement_depth=1.0)


class TestFlexureSpec:
    """Tests for FlexureSpec validation."""

    def test_valid_flexure(self):
        spec = FlexureSpec(thickness=1.2, length=15.0, max_deflection=2.0)
        assert spec.thickness == 1.2
        assert spec.length == 15.0

    def test_excessive_deflection(self):
        with pytest.raises(ValueError, match="max_deflection too large"):
            FlexureSpec(thickness=1.2, length=15.0, max_deflection=10.0)


class TestLogicElementSpec:
    """Tests for full LogicElementSpec validation."""

    @pytest.fixture
    def valid_spec_data(self):
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

    def test_valid_spec(self, valid_spec_data):
        spec = LogicElementSpec.model_validate(valid_spec_data)
        assert spec.element.name == "test_mux"
        assert spec.element.type == "mux"
        assert spec.primary_shaft_diameter == 6.0

    def test_missing_mux_input(self, valid_spec_data):
        del valid_spec_data["inputs"]["s"]
        with pytest.raises(ValueError, match="MUX element requires inputs"):
            LogicElementSpec.model_validate(valid_spec_data)

    def test_missing_output(self, valid_spec_data):
        valid_spec_data["output"] = {"x": {"shaft_diameter": 6.0}}
        with pytest.raises(ValueError, match="MUX element requires output"):
            LogicElementSpec.model_validate(valid_spec_data)

    def test_insufficient_lever_throw(self, valid_spec_data):
        valid_spec_data["geometry"]["lever_throw"] = 2.0  # Too small
        with pytest.raises(ValueError, match="lever_throw"):
            LogicElementSpec.model_validate(valid_spec_data)

    def test_default_tolerances(self, valid_spec_data):
        spec = LogicElementSpec.model_validate(valid_spec_data)
        assert spec.tolerances.shaft_clearance == 0.2
        assert spec.tolerances.gear_backlash == 0.15


class TestYAMLParsing:
    """Tests for YAML file parsing."""

    def test_parse_example_file(self):
        example_path = Path(__file__).parent.parent / "examples" / "mux_2to1.yaml"
        if not example_path.exists():
            pytest.skip("Example file not found")

        with open(example_path) as f:
            data = yaml.safe_load(f)

        spec = LogicElementSpec.model_validate(data)
        assert spec.element.name == "mux_2to1"
        assert spec.gears.coaxial_teeth == 24
