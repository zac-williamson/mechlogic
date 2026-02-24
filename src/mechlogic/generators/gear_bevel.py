"""Bevel gear generator using the cq_gears library.

This module wraps the canonical cq_gears BevelGear implementation, which uses
proper spherical involute tooth profiles for accurate bevel gear geometry.

References:
    - https://github.com/meadiode/cq_gears (CadQuery involute gear library)
"""

import math

import cadquery as cq
from cq_gears import BevelGear

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .axle_profile import add_d_flat_to_bore


class BevelGearGenerator:
    """Generator for bevel gears (90-degree axis conversion).

    Uses cq_gears library for canonical involute bevel gear generation.
    For a 1:1 ratio gear pair at 90° shaft angle, each gear has a 45° cone angle.
    """

    def __init__(self, gear_id: str = "driving"):
        if gear_id not in ("driving", "driven"):
            raise ValueError("gear_id must be 'driving' or 'driven'")
        self.gear_id = gear_id

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a bevel gear with proper involute teeth and hub."""
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance

        # Calculate geometry
        cone_angle = 45.0  # 1:1 ratio at 90° shaft angle
        face_width = self.get_face_width(spec)
        bore_dia = shaft_dia + clearance
        bore_radius = bore_dia / 2

        # Hub dimensions - extends backward from the gear
        hub_height = face_width * 1.5  # Hub length
        hub_outer_radius = bore_radius + 3.0  # Wall thickness around bore

        # Create bevel gear using cq_gears
        gear_obj = BevelGear(
            module=module,
            teeth_number=teeth,
            cone_angle=cone_angle,
            face_width=face_width,
            bore_d=bore_dia,
        )

        # Build the gear body
        gear = cq.Workplane('XY').gear(gear_obj)

        # Add D-flat fill to bore for rotation lock
        # cq_gears BevelGear body starts at Z=0; center the fill on the gear body
        d_flat_depth = spec.tolerances.d_flat_depth
        gear_bb = gear.val().BoundingBox()
        bore_center_z = (gear_bb.zmin + gear_bb.zmax) / 2
        bore_length = gear_bb.zmax - gear_bb.zmin
        gear = add_d_flat_to_bore(gear, bore_dia, d_flat_depth, bore_length, z_offset=bore_center_z)

        return gear

    def get_cone_distance(self, spec: LogicElementSpec) -> float:
        """Calculate the pitch cone distance (apex to pitch circle)."""
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pitch_radius = (module * teeth) / 2
        return pitch_radius / math.sin(math.radians(45.0))

    def get_face_width(self, spec: LogicElementSpec) -> float:
        """Calculate face width (tooth length along cone surface).

        Standard practice: face width should not exceed ~30% of cone distance
        or 10x the module.
        """
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pitch_radius = (module * teeth) / 2
        cone_distance = pitch_radius / math.sin(math.radians(45.0))
        return min(cone_distance * 0.30, 10 * module)

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Return metadata for this gear."""
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pitch_dia = module * teeth
        cone_distance = self.get_cone_distance(spec)
        face_width = self.get_face_width(spec)
        shaft_dia = spec.primary_shaft_diameter
        bore_dia = shaft_dia + spec.tolerances.shaft_clearance

        part_type = PartType.BEVEL_DRIVE if self.gear_id == "driving" else PartType.BEVEL_DRIVEN

        return PartMetadata(
            part_id=part_type.value,
            part_type=part_type,
            name=f"Bevel Gear ({self.gear_id})",
            material="PLA",
            count=1,
            dimensions={
                "module": module,
                "teeth": teeth,
                "pitch_diameter": pitch_dia,
                "cone_angle": 45.0,
                "cone_distance": cone_distance,
                "face_width": face_width,
                "bore_diameter": bore_dia,
                "shaft_diameter": shaft_dia,
            },
        )
