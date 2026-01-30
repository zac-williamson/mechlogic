"""Kinematic model for logic verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, List, Dict, Tuple


class LogicValue(IntEnum):
    """Logic values encoded as rotation direction."""

    ZERO = 0  # Clockwise
    ONE = 1  # Counterclockwise


@dataclass
class GearPath:
    """A path through the gear train from input to output."""

    path_id: str
    input_name: str
    output_name: str
    gear_stages: list[str]  # List of gear part IDs in the path
    total_ratio: float = 1.0  # Combined gear ratio (negative = inversion)


@dataclass
class KinematicModel:
    """Kinematic model for verifying logic behavior."""

    # Truth table: (A, B, S) -> O
    # Values are LogicValue (0=CW, 1=CCW)
    truth_table: dict[tuple[int, int, int], int] = field(default_factory=dict)

    # Gear paths for each selector state
    paths: dict[str, GearPath] = field(default_factory=dict)

    # Which path is active for each S value
    active_path: dict[int, str] = field(default_factory=dict)

    @classmethod
    def create_mux(cls) -> "KinematicModel":
        """Create kinematic model for a 2:1 MUX (O = S ? B : A)."""
        model = cls()

        # Define gear paths
        model.paths["path_a"] = GearPath(
            path_id="path_a",
            input_name="a",
            output_name="o",
            gear_stages=["gear_a", "dog_clutch"],
            total_ratio=1.0,  # Direct pass-through
        )
        model.paths["path_b"] = GearPath(
            path_id="path_b",
            input_name="b",
            output_name="o",
            gear_stages=["gear_b", "dog_clutch"],
            total_ratio=1.0,  # Direct pass-through
        )

        # S=0 (CW) -> clutch engages A path
        # S=1 (CCW) -> clutch engages B path
        model.active_path[0] = "path_a"
        model.active_path[1] = "path_b"

        # Build truth table
        # When S=0: O = A (clutch engages gear_a)
        # When S=1: O = B (clutch engages gear_b)
        for a in (0, 1):
            for b in (0, 1):
                # S=0: O follows A
                model.truth_table[(a, b, 0)] = a
                # S=1: O follows B
                model.truth_table[(a, b, 1)] = b

        return model

    def get_output(self, a: int, b: int, s: int) -> Optional[int]:
        """Get expected output for given inputs."""
        return self.truth_table.get((a, b, s))

    def get_active_path(self, s: int) -> Optional[GearPath]:
        """Get the active gear path for a given S value."""
        path_id = self.active_path.get(s)
        if path_id:
            return self.paths.get(path_id)
        return None

    def verify_truth_table(self) -> list[str]:
        """Verify the truth table is complete and consistent. Returns list of errors."""
        errors = []

        # Check all input combinations are defined
        for a in (0, 1):
            for b in (0, 1):
                for s in (0, 1):
                    if (a, b, s) not in self.truth_table:
                        errors.append(f"Missing truth table entry for (A={a}, B={b}, S={s})")

        # Verify MUX behavior: S=0 -> O=A, S=1 -> O=B
        for a in (0, 1):
            for b in (0, 1):
                expected_s0 = a  # When S=0, O should equal A
                expected_s1 = b  # When S=1, O should equal B

                actual_s0 = self.truth_table.get((a, b, 0))
                actual_s1 = self.truth_table.get((a, b, 1))

                if actual_s0 is not None and actual_s0 != expected_s0:
                    errors.append(
                        f"MUX violation at (A={a}, B={b}, S=0): "
                        f"expected O={expected_s0}, got O={actual_s0}"
                    )
                if actual_s1 is not None and actual_s1 != expected_s1:
                    errors.append(
                        f"MUX violation at (A={a}, B={b}, S=1): "
                        f"expected O={expected_s1}, got O={actual_s1}"
                    )

        return errors
