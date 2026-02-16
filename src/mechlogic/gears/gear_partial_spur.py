"""Partial spur gear generator - creates a gear with teeth on only a portion of the circumference.

Uses cq_gears for proper involute tooth profiles, then cuts away teeth
to leave only the specified fraction.
"""

import math
import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class PartialSpurGearParams:
    """Parameters for a partial spur gear."""

    module: float = 1.5          # Gear module
    teeth: int = 24              # Total teeth if it were a full gear
    face_width: float = 8.0      # Width/thickness of the gear
    bore_diameter: float = 2.0   # Central hole diameter
    tooth_fraction: float = 0.25 # Fraction of circumference with teeth (0.25 = 1/4)
    hub_diameter: float = 0.0    # Hub diameter (0 = auto-calculate)
    hub_height: float = 0.0      # Hub extension height (0 = no hub extension)


class PartialSpurGearGenerator:
    """Generator for spur gears with teeth on only part of the circumference.

    Creates a gear where only a fraction of the wheel has teeth,
    useful for intermittent motion mechanisms, Geneva drives, etc.
    """

    def __init__(self, params: Optional[PartialSpurGearParams] = None):
        """Initialize the generator.

        Args:
            params: Gear parameters. Uses defaults if not provided.
        """
        self.params = params or PartialSpurGearParams()

    def generate(self) -> cq.Workplane:
        """Generate the partial spur gear.

        The gear is centered at the origin with teeth extending in +Z.

        Returns:
            CadQuery Workplane with the partial gear geometry.
        """
        p = self.params

        # Calculate gear dimensions
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module  # Addendum
        root_diameter = pitch_diameter - 2.5 * p.module  # Dedendum

        # Hub diameter: if not specified, use root diameter minus margin
        hub_diameter = p.hub_diameter if p.hub_diameter > 0 else root_diameter - 2.0

        # Ensure hub is larger than bore
        hub_diameter = max(hub_diameter, p.bore_diameter + 4.0)

        # Create full spur gear using cq_gears
        gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.face_width,
            bore_d=p.bore_diameter,
        )

        full_gear = cq.Workplane('XY').gear(gear_obj)

        # Calculate the angle for the toothed section
        tooth_angle = 360.0 * p.tooth_fraction  # Degrees

        # Create a sector mask for the toothed portion
        # The sector is a pie slice from the center
        # We'll keep teeth from 0° to tooth_angle
        sector_radius = outer_diameter / 2 + 5  # Extend beyond gear

        # Create the toothed sector (pie slice)
        # Using points to create a fan shape
        num_points = max(int(tooth_angle / 5), 10)  # At least 10 points for smooth arc
        sector_points = [(0, 0)]  # Center point

        for i in range(num_points + 1):
            angle = math.radians(i * tooth_angle / num_points)
            x = sector_radius * math.cos(angle)
            y = sector_radius * math.sin(angle)
            sector_points.append((x, y))

        sector_points.append((0, 0))  # Close back to center

        # Create sector solid
        toothed_sector = (
            cq.Workplane('XY')
            .polyline(sector_points)
            .close()
            .extrude(p.face_width)
        )

        # Intersect gear with sector to keep only toothed portion
        partial_teeth = full_gear.intersect(toothed_sector)

        # Create the solid hub (full circle at root diameter)
        # This provides the structural core of the gear
        hub = (
            cq.Workplane('XY')
            .circle(hub_diameter / 2)
            .circle(p.bore_diameter / 2)  # Bore hole
            .extrude(p.face_width)
        )

        # Union the partial teeth with the hub
        partial_gear = hub.union(partial_teeth)

        # Add hub extension if specified
        if p.hub_height > 0:
            hub_extension = (
                cq.Workplane('XY')
                .circle(hub_diameter / 2)
                .circle(p.bore_diameter / 2)
                .extrude(p.hub_height)
                .translate((0, 0, p.face_width))
            )
            partial_gear = partial_gear.union(hub_extension)

        return partial_gear

    def get_dimensions(self) -> dict:
        """Get gear dimensions for reference.

        Returns:
            Dictionary with gear dimensions.
        """
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        # Calculate actual number of teeth in the partial section
        teeth_in_section = int(p.teeth * p.tooth_fraction)

        return {
            'module': p.module,
            'total_teeth': p.teeth,
            'teeth_in_section': teeth_in_section,
            'tooth_fraction': p.tooth_fraction,
            'tooth_angle_degrees': 360.0 * p.tooth_fraction,
            'pitch_diameter': pitch_diameter,
            'outer_diameter': outer_diameter,
            'root_diameter': root_diameter,
            'face_width': p.face_width,
            'bore_diameter': p.bore_diameter,
        }


def main():
    """Generate and export a partial spur gear."""
    # Create a 1/4 tooth gear (25% of teeth)
    params = PartialSpurGearParams(
        module=1.5,
        teeth=24,
        face_width=8.0,
        bore_diameter=2.0,
        tooth_fraction=0.25,  # 1/4 of the teeth
    )

    gen = PartialSpurGearGenerator(params)
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Partial Spur Gear:")
    print(f"  Module: {dims['module']} mm")
    print(f"  Total teeth (if full): {dims['total_teeth']}")
    print(f"  Teeth in section: {dims['teeth_in_section']}")
    print(f"  Tooth angle: {dims['tooth_angle_degrees']}°")
    print(f"  Pitch diameter: {dims['pitch_diameter']:.2f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.2f} mm")

    cq.exporters.export(gear, "partial_spur_gear_quarter.step")
    print("\nExported: partial_spur_gear_quarter.step")


if __name__ == "__main__":
    main()
