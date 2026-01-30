"""Shift lever generator for dog clutch engagement."""

import math
import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class ShiftLeverGenerator:
    """Generator for the shift lever that moves the dog clutch.

    The lever has:
    - A square pivot block at the top with a hole for the pivot axle
    - A thin rectangular arm extending down
    - A fork at the bottom that engages the dog clutch groove

    The lever is built in the YZ plane with thickness in X (to fit in groove).
    The fork opens toward -Y so the lever can be assembled by sliding down.
    The lever rotates around Z axis, which moves the fork in the X direction
    (along the clutch axis) to engage the gears.
    """

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a shift lever with fork for dog clutch engagement."""
        # Clutch dimensions
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        clutch_od = gear_od * 0.4

        # Groove dimensions (must match dog_clutch.py)
        groove_width = 4.0
        groove_depth = 2.0
        groove_inner_radius = (clutch_od - groove_depth * 2) / 2

        # Lever dimensions - thickness in X to fit in groove
        lever_thickness = groove_width - 1.5  # 2.5mm to fit in 4mm groove with clearance

        # Arm connecting pivot to fork
        arm_width = 6.0

        # Pivot block at top
        pivot_block_size = 12.0
        pivot_hole_dia = 6.0
        pivot_block_thickness = pivot_hole_dia * 2
        pivot_y = clutch_od / 2 + 27  # Distance from clutch axis to pivot (increased by 2mm)

        # Fork dimensions - fits INSIDE the clutch groove
        fork_clearance = 0.5
        fork_inner_radius = groove_inner_radius + fork_clearance
        fork_outer_radius = clutch_od / 2 - fork_clearance

        # Build lever in YZ plane, extrude in X direction
        # Y is vertical (up), Z is horizontal, X is thickness (into groove)

        # Pivot block - built in YZ plane with thickness in X (like arm and fork)
        pivot_block = (
            cq.Workplane("YZ")
            .rect(pivot_block_size, arm_width)
            .extrude(pivot_block_thickness)
            .translate((-pivot_block_thickness / 2, pivot_y, 0))
        )

        # Cut pivot hole along Z axis using explicit cylinder subtraction
        pivot_hole = (
            cq.Workplane("XY")
            .circle(pivot_hole_dia / 2)
            .extrude(pivot_block_size * 2)
            .translate((0, pivot_y, -pivot_block_size))
        )
        pivot_block = pivot_block.cut(pivot_hole)

        # Arm - connects pivot block to fork area
        arm_top = pivot_y - pivot_block_size / 2
        arm_bottom = fork_outer_radius + 1  # Just above the fork
        arm_height = arm_top - arm_bottom

        arm = (
            cq.Workplane("YZ")
            .rect(arm_height, arm_width)
            .extrude(lever_thickness)
            .translate((-lever_thickness / 2, arm_bottom + arm_height / 2, 0))
        )

        # Fork - C-shape opening downward (-Y direction)
        # Create as a ring in YZ plane
        fork_ring = (
            cq.Workplane("YZ")
            .circle(fork_outer_radius)
            .circle(fork_inner_radius)
            .extrude(lever_thickness)
            .translate((-lever_thickness / 2, 0, 0))
        )

        # Cut away bottom half to create opening facing -Y
        cut_box = (
            cq.Workplane("YZ")
            .rect(fork_outer_radius * 2, fork_outer_radius * 3)
            .extrude(lever_thickness * 2)
            .translate((-lever_thickness, -fork_outer_radius, 0))
        )
        fork = fork_ring.cut(cut_box)

        # Connecting piece between arm bottom and fork top
        connector_height = arm_bottom - fork_outer_radius
        connector = (
            cq.Workplane("YZ")
            .rect(connector_height + 1, arm_width)  # Overlap for solid union
            .extrude(lever_thickness)
            .translate((-lever_thickness / 2, fork_outer_radius + connector_height / 2 - 0.5, 0))
        )

        # Combine all parts
        lever = pivot_block.union(arm).union(connector).union(fork)

        return lever

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        return PartMetadata(
            part_id="shift_lever",
            part_type=PartType.DOG_CLUTCH,
            name="Shift Lever",
            material="PLA",
            count=1,
            dimensions={
                "pivot_hole_diameter": 6.0,
                "lever_thickness": 3.5,
            },
        )
