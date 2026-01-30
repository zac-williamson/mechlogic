"""Dog clutch generator."""

import math

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class DogClutchGenerator:
    """Generator for the sliding dog clutch."""

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a sliding dog clutch.

        The clutch has:
        - A central bore that slides on the main axle
        - Dog teeth on both faces for engaging either gear
        - A circumferential groove for the lever fork to engage
        """
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        clutch_spec = spec.gears.dog_clutch

        # Clutch dimensions
        clutch_width = spec.geometry.clutch_width
        # Outer diameter sized to reach gear inner ring
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        clutch_od = gear_od * 0.4  # Clutch engages inner portion of gear

        bore_dia = shaft_dia + clearance

        # Groove for lever fork
        groove_width = 4.0
        groove_depth = 2.0

        # Create main body
        clutch = (
            cq.Workplane("XY")
            .cylinder(clutch_width, clutch_od / 2)
            # Central bore
            .faces(">Z")
            .workplane()
            .hole(bore_dia)
        )

        # Add circumferential groove for lever
        groove_dia = clutch_od - groove_depth * 2
        groove = (
            cq.Workplane("XY")
            .cylinder(groove_width, clutch_od / 2)
            .faces(">Z")
            .workplane()
            .hole(groove_dia)
        )
        # Position groove at center
        clutch = clutch.cut(groove)

        # Add dog teeth on both faces as radial arc segments
        # Teeth are symmetric - same angular positions on both ends
        tooth_count = clutch_spec.teeth
        tooth_height = clutch_spec.tooth_height

        # Tooth ring dimensions
        tooth_outer = clutch_od / 2  # Outer radius of teeth
        tooth_inner = bore_dia / 2 + 2  # Inner radius (clearance from bore)

        # Each tooth is a sector - tooth takes 45% of space, gap is 55%
        tooth_angle = 360.0 / tooth_count
        tooth_arc = tooth_angle * 0.45

        def add_dog_teeth(workplane: cq.Workplane, z_base: float, z_dir: int) -> cq.Workplane:
            """Add dog teeth at specified Z position."""
            for i in range(tooth_count):
                start_angle = i * tooth_angle

                tooth = (
                    cq.Workplane("XY")
                    .workplane(offset=z_base)
                    .moveTo(tooth_inner * math.cos(math.radians(start_angle)),
                           tooth_inner * math.sin(math.radians(start_angle)))
                    .radiusArc(
                        (tooth_inner * math.cos(math.radians(start_angle + tooth_arc)),
                         tooth_inner * math.sin(math.radians(start_angle + tooth_arc))),
                        tooth_inner
                    )
                    .lineTo(tooth_outer * math.cos(math.radians(start_angle + tooth_arc)),
                           tooth_outer * math.sin(math.radians(start_angle + tooth_arc)))
                    .radiusArc(
                        (tooth_outer * math.cos(math.radians(start_angle)),
                         tooth_outer * math.sin(math.radians(start_angle))),
                        -tooth_outer
                    )
                    .close()
                    .extrude(tooth_height * z_dir)
                )
                workplane = workplane.union(tooth)

            return workplane

        # CadQuery cylinder is centered, so faces are at +/- clutch_width/2
        # Add teeth on +Z face (extending upward)
        clutch = add_dog_teeth(clutch, clutch_width / 2, 1)
        # Add teeth on -Z face (extending downward)
        clutch = add_dog_teeth(clutch, -clutch_width / 2, -1)

        return clutch

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        clutch_od = gear_od * 0.4

        return PartMetadata(
            part_id=PartType.DOG_CLUTCH.value,
            part_type=PartType.DOG_CLUTCH,
            name="Sliding Dog Clutch",
            material="PLA",
            count=1,
            dimensions={
                "outer_diameter": clutch_od,
                "bore_diameter": spec.primary_shaft_diameter + spec.tolerances.shaft_clearance,
                "width": spec.geometry.clutch_width,
                "tooth_count": spec.gears.dog_clutch.teeth,
                "tooth_height": spec.gears.dog_clutch.tooth_height,
            },
        )
