"""Housing plate generators."""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class HousingGenerator:
    """Generator for housing plates (front and back)."""

    def __init__(self, is_front: bool = True):
        """Initialize generator.

        Args:
            is_front: True for front plate, False for back plate
        """
        self.is_front = is_front

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a housing plate with bearing holes.

        Front plate has:
        - Central bore for main axle
        - Lever pivot bore (for driven bevel connection)
        - Square cutout for S-axis (flexure mounts here)
        - Flexure mounting holes (4x M3)
        - Corner mounting holes

        Back plate has:
        - Central bore for main axle
        - Corner mounting holes
        """
        thickness = spec.geometry.housing_thickness
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance

        # Calculate plate dimensions based on gear size
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        bevel_pitch_radius = (spec.gears.module * spec.gears.bevel_teeth) / 2
        plate_width = gear_od + 20
        plate_height = gear_od + 40  # Extra height for bevel/flexure area

        bore_dia = shaft_dia + clearance

        # S-axis Y offset (where flexure mounts)
        s_offset_y = gear_od / 2 + 15

        # Lever pivot Y position (offset from S-axis by bevel pitch radius)
        lever_pivot_y = s_offset_y - bevel_pitch_radius

        # Create base plate
        plate = (
            cq.Workplane("XY")
            .box(plate_width, plate_height, thickness)
            .faces(">Z")
            .workplane()
            .hole(bore_dia)  # Main axle bore at center
        )

        if self.is_front:
            # Add lever pivot bore
            plate = (
                plate.faces(">Z")
                .workplane()
                .center(0, lever_pivot_y)
                .hole(bore_dia)
            )

            # Add square cutout for S-axis (NOT a bore - flexure supports the shaft)
            cutout_size = 22.0  # Slightly larger than flexure mounting plate
            plate = (
                plate.faces(">Z")
                .workplane()
                .center(0, s_offset_y)
                .rect(cutout_size, cutout_size)
                .cutThruAll()
            )

            # Add flexure mounting holes (4x M3 around the cutout)
            mount_hole_dia = 3.2
            mount_offset = cutout_size / 2 + 3  # Just outside cutout
            flexure_mount_positions = [
                (mount_offset, s_offset_y + mount_offset),
                (-mount_offset, s_offset_y + mount_offset),
                (mount_offset, s_offset_y - mount_offset),
                (-mount_offset, s_offset_y - mount_offset),
            ]

            for x, y in flexure_mount_positions:
                plate = (
                    plate.faces(">Z")
                    .workplane()
                    .center(x, y)
                    .hole(mount_hole_dia)
                )

        # Add corner mounting holes (both plates)
        mount_inset = 8
        mount_hole_dia = 3.2
        corner_positions = [
            (plate_width / 2 - mount_inset, plate_height / 2 - mount_inset),
            (-plate_width / 2 + mount_inset, plate_height / 2 - mount_inset),
            (plate_width / 2 - mount_inset, -plate_height / 2 + mount_inset),
            (-plate_width / 2 + mount_inset, -plate_height / 2 + mount_inset),
        ]

        for x, y in corner_positions:
            plate = plate.faces(">Z").workplane().center(x, y).hole(mount_hole_dia)

        return plate

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        plate_width = gear_od + 20
        plate_height = gear_od + 30

        part_type = PartType.HOUSING_FRONT if self.is_front else PartType.HOUSING_BACK
        name = "Housing Front Plate" if self.is_front else "Housing Back Plate"

        return PartMetadata(
            part_id=part_type.value,
            part_type=part_type,
            name=name,
            material="PLA",
            count=1,
            dimensions={
                "width": plate_width,
                "height": plate_height,
                "thickness": spec.geometry.housing_thickness,
            },
        )
