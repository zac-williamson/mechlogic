"""Lever generator for clutch actuation."""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class LeverGenerator:
    """Generator for the lever that moves the dog clutch."""

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a pivoting lever.

        The lever has:
        - A pivot hole at one end
        - A fork at the other end that engages the clutch groove
        - Sufficient length to convert bevel gear rotation to linear clutch motion
        """
        lever_throw = spec.geometry.lever_throw
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance

        # Lever dimensions
        lever_length = lever_throw * 3  # Lever arm length
        lever_width = 8.0
        lever_thickness = 4.0
        pivot_hole_dia = shaft_dia + clearance

        # Fork dimensions (engages clutch groove)
        fork_gap = spec.geometry.clutch_width + 2  # Clearance around clutch
        fork_depth = 10.0
        fork_thickness = 3.0

        # Create lever body
        lever = (
            cq.Workplane("XY")
            .box(lever_length, lever_width, lever_thickness)
        )

        # Add pivot hole at one end
        pivot_x = -lever_length / 2 + lever_width / 2
        lever = (
            lever.faces(">Z")
            .workplane()
            .center(pivot_x, 0)
            .hole(pivot_hole_dia)
        )

        # Add fork at other end
        # The fork is two prongs that straddle the clutch
        fork_x = lever_length / 2 - fork_depth / 2

        # Create fork by adding two prongs
        prong = (
            cq.Workplane("XY")
            .center(fork_x, fork_gap / 2 + fork_thickness / 2)
            .box(fork_depth, fork_thickness, lever_thickness)
        )
        lever = lever.union(prong)

        prong2 = (
            cq.Workplane("XY")
            .center(fork_x, -fork_gap / 2 - fork_thickness / 2)
            .box(fork_depth, fork_thickness, lever_thickness)
        )
        lever = lever.union(prong2)

        return lever

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        lever_length = spec.geometry.lever_throw * 3

        return PartMetadata(
            part_id=PartType.LEVER.value,
            part_type=PartType.LEVER,
            name="Clutch Actuation Lever",
            material="PLA",
            count=1,
            dimensions={
                "length": lever_length,
                "width": 8.0,
                "thickness": 4.0,
                "throw": spec.geometry.lever_throw,
            },
        )
