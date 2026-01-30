"""Tests for kinematic model."""

import pytest

from mechlogic.models.kinematic import KinematicModel, LogicValue


class TestKinematicModel:
    """Tests for KinematicModel."""

    def test_create_mux(self):
        model = KinematicModel.create_mux()

        # Check all truth table entries exist
        for a in (0, 1):
            for b in (0, 1):
                for s in (0, 1):
                    assert (a, b, s) in model.truth_table

    def test_mux_truth_table(self):
        model = KinematicModel.create_mux()

        # S=0: O = A
        assert model.get_output(0, 0, 0) == 0
        assert model.get_output(0, 1, 0) == 0
        assert model.get_output(1, 0, 0) == 1
        assert model.get_output(1, 1, 0) == 1

        # S=1: O = B
        assert model.get_output(0, 0, 1) == 0
        assert model.get_output(0, 1, 1) == 1
        assert model.get_output(1, 0, 1) == 0
        assert model.get_output(1, 1, 1) == 1

    def test_active_path(self):
        model = KinematicModel.create_mux()

        path_a = model.get_active_path(0)
        assert path_a is not None
        assert path_a.input_name == "a"

        path_b = model.get_active_path(1)
        assert path_b is not None
        assert path_b.input_name == "b"

    def test_verify_truth_table_valid(self):
        model = KinematicModel.create_mux()
        errors = model.verify_truth_table()
        assert len(errors) == 0

    def test_verify_truth_table_incomplete(self):
        model = KinematicModel()
        # Only partial truth table
        model.truth_table[(0, 0, 0)] = 0
        errors = model.verify_truth_table()
        assert len(errors) > 0
        assert any("Missing" in e for e in errors)

    def test_verify_truth_table_wrong_value(self):
        model = KinematicModel.create_mux()
        # Corrupt one entry
        model.truth_table[(0, 1, 0)] = 1  # Should be 0 (A value)
        errors = model.verify_truth_table()
        assert len(errors) > 0
        assert any("MUX violation" in e for e in errors)
