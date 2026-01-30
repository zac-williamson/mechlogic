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
        # Use a tiny bore that we'll enlarge to go through the hub
        gear_obj = BevelGear(
            module=module,
            teeth_number=teeth,
            cone_angle=cone_angle,
            face_width=face_width,
            bore_d=0.1,  # Minimal bore - we'll cut proper one through hub
        )

        # Build the gear body
        gear = cq.Workplane('XY').gear(gear_obj)

        # Add hub extending backward (negative Z) from the gear back face
        # The gear is built with back face at Z=0
        hub = (
            cq.Workplane('XY')
            .circle(hub_outer_radius)
            .extrude(-hub_height)
        )
        gear = gear.union(hub)

        # Cut bore through entire gear + hub
        bore = (
            cq.Workplane('XY')
            .workplane(offset=-hub_height - 1)
            .circle(bore_radius)
            .extrude(face_width + hub_height + 10)
        )
        gear = gear.cut(bore)

        # Add M3 set screw hole in hub (radial hole perpendicular to axis)
        # M3 tap drill = 2.5mm, positioned at middle of hub
        set_screw_dia = 2.5  # M3 tap drill size
        set_screw_z = -hub_height / 2  # Middle of hub
        set_screw_hole = (
            cq.Workplane('XZ')
            .workplane(offset=0)  # Y=0 plane
            .center(0, set_screw_z)  # Position at hub center height
            .circle(set_screw_dia / 2)
            .extrude(hub_outer_radius + 1)  # Through the hub wall
        )
        gear = gear.cut(set_screw_hole)

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
