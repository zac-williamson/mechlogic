"""Spur gear generator using cq_gears for proper involute teeth."""

import math

import cadquery as cq
from cq_gears import SpurGear

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class SpurGearGenerator:
    """Generator for spur gears with dog clutch face teeth.

    Uses cq_gears library for proper involute tooth profiles.
    The gear has:
    - Outer teeth for meshing (true involute profile)
    - Inner dog teeth for clutch engagement
    - Central bore for the axle
    """

    def __init__(self, gear_id: str = "a"):
        """Initialize generator.

        Args:
            gear_id: "a" or "b" to identify which coaxial gear
        """
        self.gear_id = gear_id

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a spur gear with inner dog teeth."""
        module = spec.gears.module
        teeth = spec.gears.coaxial_teeth
        face_width = spec.geometry.gear_face_width
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        dog_spec = spec.gears.dog_clutch

        # Gear dimensions
        pitch_dia = module * teeth
        bore_dia = shaft_dia + clearance

        # Dog teeth ring dimensions (inner portion of gear)
        dog_ring_od = pitch_dia * 0.35  # Inner ring for dog clutch
        dog_ring_id = bore_dia + 4  # Leave wall around bore

        # Create spur gear using cq_gears for proper involute teeth
        gear_obj = SpurGear(
            module=module,
            teeth_number=teeth,
            width=face_width,
            bore_d=bore_dia,
        )

        # Build the gear
        gear_profile = cq.Workplane('XY').gear(gear_obj)

        # Add internal dog teeth on the face facing the clutch
        # These are teeth that protrude from the gear face, with slots between them
        # The clutch teeth engage in the slots
        dog_tooth_count = dog_spec.teeth
        dog_tooth_height = dog_spec.tooth_height

        # Internal ring dimensions - where the dog teeth are located
        dog_ring_outer = pitch_dia * 0.4  # Outer radius of dog tooth ring
        dog_ring_inner = bore_dia + 2  # Inner radius (clearance from bore)

        # Each tooth is a sector of the ring
        tooth_angle = 360.0 / dog_tooth_count  # Degrees per tooth+gap
        tooth_arc = tooth_angle * 0.45  # Tooth takes 45% of the space, gap is 55%

        # Determine which face to add teeth to
        # cq_gears SpurGear goes from Z=0 to Z=face_width
        # For gear_a, dog teeth face +Z (toward clutch) - add at top face (Z=face_width)
        # For gear_b, dog teeth face -Z (toward clutch) - add at bottom face (Z=0)
        if self.gear_id == "a":
            z_base = face_width  # Top face
            z_dir = 1  # Extrude upward
        else:
            z_base = 0  # Bottom face
            z_dir = -1  # Extrude downward

        # Create dog teeth as radial segments
        for i in range(dog_tooth_count):
            start_angle = i * tooth_angle

            # Create a tooth as a cylindrical sector
            tooth = (
                cq.Workplane("XY")
                .workplane(offset=z_base)
                .moveTo(dog_ring_inner * math.cos(math.radians(start_angle)),
                       dog_ring_inner * math.sin(math.radians(start_angle)))
                .radiusArc(
                    (dog_ring_inner * math.cos(math.radians(start_angle + tooth_arc)),
                     dog_ring_inner * math.sin(math.radians(start_angle + tooth_arc))),
                    dog_ring_inner
                )
                .lineTo(dog_ring_outer * math.cos(math.radians(start_angle + tooth_arc)),
                       dog_ring_outer * math.sin(math.radians(start_angle + tooth_arc)))
                .radiusArc(
                    (dog_ring_outer * math.cos(math.radians(start_angle)),
                     dog_ring_outer * math.sin(math.radians(start_angle))),
                    -dog_ring_outer
                )
                .close()
                .extrude(dog_tooth_height * z_dir)
            )

            gear_profile = gear_profile.union(tooth)

        return gear_profile

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        module = spec.gears.module
        teeth = spec.gears.coaxial_teeth
        pitch_dia = module * teeth
        outer_dia = pitch_dia + 2 * module

        part_type = PartType.GEAR_A if self.gear_id == "a" else PartType.GEAR_B

        return PartMetadata(
            part_id=part_type.value,
            part_type=part_type,
            name=f"Coaxial Gear {self.gear_id.upper()}",
            material="PLA",
            count=1,
            dimensions={
                "module": module,
                "teeth": teeth,
                "pitch_diameter": pitch_dia,
                "outer_diameter": outer_dia,
                "face_width": spec.geometry.gear_face_width,
                "bore_diameter": spec.primary_shaft_diameter + spec.tolerances.shaft_clearance,
            },
        )
