"""Flexure block generator (living hinge for overload protection)."""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class FlexureBlockGenerator:
    """Generator for flexure block with living hinge.

    Creates a compliant beam that mounts the driving bevel gear.
    When S-axis continues rotating after lever reaches end-of-travel,
    the flexure deflects to partially disengage the bevel mesh.

    Designed to be integrated (unioned) with the front housing plate.
    """

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate flexure block geometry.

        The flexure consists of:
        - Mounting plate with 4x M3 bolt holes (bolts to housing)
        - Thin beam (living hinge) oriented for radial deflection
        - Bearing boss at free end for S-shaft
        """
        flexure = spec.flexure
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        module = spec.gears.module

        # Flexure beam dimensions
        beam_thickness = flexure.thickness
        beam_length = flexure.length
        beam_width = 2.5 * module + 4  # Match bevel face width plus margin

        # Bearing boss dimensions
        boss_dia = shaft_dia + 6  # Wall around bearing
        boss_length = 10.0  # Length along S-axis
        bore_dia = shaft_dia + clearance

        # Mounting plate dimensions
        plate_size = 20.0  # Square plate
        plate_thickness = 4.0  # Thick enough for M3 threads
        mount_hole_dia = 3.2  # M3 clearance
        mount_inset = 4.0  # From edge to hole center

        # Create mounting plate (XY plane, centered at origin)
        plate = (
            cq.Workplane("XY")
            .box(plate_size, plate_size, plate_thickness)
        )

        # Add 4 mounting holes
        mount_positions = [
            (plate_size/2 - mount_inset, plate_size/2 - mount_inset),
            (-plate_size/2 + mount_inset, plate_size/2 - mount_inset),
            (plate_size/2 - mount_inset, -plate_size/2 + mount_inset),
            (-plate_size/2 + mount_inset, -plate_size/2 + mount_inset),
        ]

        for x, y in mount_positions:
            plate = (
                plate.faces(">Z")
                .workplane()
                .center(x, y)
                .hole(mount_hole_dia)
            )

        # Create thin beam extending in +Y direction (for radial deflection in X)
        # Beam sits on top of plate (+Z face)
        beam = (
            cq.Workplane("XY")
            .box(beam_thickness, beam_length, beam_width)
            .translate((0, beam_length/2 + plate_size/2, plate_thickness/2 + beam_width/2))
        )

        # Create bearing boss at end of beam
        # Boss extends in +Y direction from beam end
        boss_y = plate_size/2 + beam_length + boss_length/2
        boss = (
            cq.Workplane("XZ")  # Boss axis along Y
            .circle(boss_dia / 2)
            .extrude(boss_length)
            .translate((0, plate_size/2 + beam_length, plate_thickness/2 + beam_width/2))
        )

        # Union all parts
        flexure_block = plate.union(beam).union(boss)

        # Cut bearing bore through boss (along Y axis)
        bore = (
            cq.Workplane("XZ")
            .circle(bore_dia / 2)
            .extrude(boss_length + 2)
            .translate((0, plate_size/2 + beam_length - 1, plate_thickness/2 + beam_width/2))
        )
        flexure_block = flexure_block.cut(bore)

        return flexure_block

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        flexure = spec.flexure

        return PartMetadata(
            part_id=PartType.FLEXURE_BLOCK.value,
            part_type=PartType.FLEXURE_BLOCK,
            name="Flexure Block (Living Hinge)",
            material="PLA",
            count=1,
            dimensions={
                "beam_thickness": flexure.thickness,
                "beam_length": flexure.length,
                "max_deflection": flexure.max_deflection,
            },
            notes="Print with beam aligned to layer lines for compliance",
        )
