"""Integration tests for full assembly generation."""

import pytest
import tempfile
from pathlib import Path

from mechlogic.models.spec import LogicElementSpec
from mechlogic.assembly.builder import AssemblyBuilder


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


class TestFullAssembly:
    """Integration tests for complete assembly."""

    def test_build_assembly_succeeds(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        assert assembly is not None
        assert assembly.name == "test_mux"

    def test_assembly_contains_bevel_gears(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        part_names = [child.name for child in assembly.children]

        assert "bevel_driving" in part_names
        assert "bevel_driven" in part_names

    def test_assembly_contains_lever_pivot(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        part_names = [child.name for child in assembly.children]

        assert "lever_pivot" in part_names

    def test_assembly_contains_flexure_block(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        part_names = [child.name for child in assembly.children]

        assert "flexure_block" in part_names

    def test_bom_includes_new_parts(self, spec):
        builder = AssemblyBuilder(spec)
        builder.build()

        bom = builder.get_bom()
        part_ids = [item["part_id"] for item in bom]

        assert "bevel_driving" in part_ids
        assert "bevel_driven" in part_ids
        assert "lever_pivot" in part_ids
        assert "flexure_block" in part_ids

    def test_export_step(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "assembly.step"
            assembly.save(str(step_path))

            assert step_path.exists()
            assert step_path.stat().st_size > 0
