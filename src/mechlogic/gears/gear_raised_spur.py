"""Raised spur gear generator.

Creates a spur gear with a spacer/hub extension on top.
Useful for offsetting the gear from a mounting surface.
"""

import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class RaisedSpurGearParams:
    """Parameters for a raised spur gear."""

    # Gear parameters
    module: float = 1.5              # Gear module
    teeth: int = 24                  # Number of teeth
    face_width: float = 8.0          # Width of gear
    bore_diameter: float = 2.0       # Central hole diameter

    # Spacer/hub parameters
    spacer_height: float = 11.0      # Height of spacer on top of gear
    spacer_diameter: float = 0.0     # Spacer diameter (0 = auto, use small hub)


class RaisedSpurGearGenerator:
    """Generator for spur gear with spacer extension on top."""

    def __init__(self, params: Optional[RaisedSpurGearParams] = None):
        """Initialize the generator.

        Args:
            params: Gear parameters. Uses defaults if not provided.
        """
        self.params = params or RaisedSpurGearParams()

    def generate(self) -> cq.Workplane:
        """Generate the raised spur gear.

        The gear is at the bottom (Z=0 to Z=face_width),
        spacer extends upward from the gear.

        Returns:
            CadQuery Workplane with the raised gear geometry.
        """
        p = self.params

        # Calculate gear dimensions
        pitch_diameter = p.module * p.teeth
        root_diameter = pitch_diameter - 2.5 * p.module

        # Spacer diameter: if not specified, use a small hub
        # Default to about 1/3 of root diameter, but at least bore + 4mm
        if p.spacer_diameter > 0:
            spacer_diameter = p.spacer_diameter
        else:
            spacer_diameter = max(root_diameter / 3, p.bore_diameter + 4.0)

        # Ensure spacer is larger than bore
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        # Create the spur gear
        gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.face_width,
            bore_d=p.bore_diameter,
        )
        gear = cq.Workplane('XY').gear(gear_obj)

        # Create the spacer on top
        spacer = (
            cq.Workplane('XY')
            .circle(spacer_diameter / 2)
            .circle(p.bore_diameter / 2)
            .extrude(p.spacer_height)
            .translate((0, 0, p.face_width))
        )

        # Combine gear and spacer
        result = gear.union(spacer)

        return result

    def get_dimensions(self) -> dict:
        """Get gear dimensions for reference."""
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        # Calculate actual spacer diameter
        if p.spacer_diameter > 0:
            spacer_diameter = p.spacer_diameter
        else:
            spacer_diameter = max(root_diameter / 3, p.bore_diameter + 4.0)
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        total_height = p.face_width + p.spacer_height

        return {
            'module': p.module,
            'teeth': p.teeth,
            'pitch_diameter': pitch_diameter,
            'outer_diameter': outer_diameter,
            'root_diameter': root_diameter,
            'bore_diameter': p.bore_diameter,
            'face_width': p.face_width,
            'spacer_height': p.spacer_height,
            'spacer_diameter': spacer_diameter,
            'total_height': total_height,
        }


def main():
    """Generate and export a raised spur gear."""
    params = RaisedSpurGearParams(
        module=1.5,
        teeth=24,
        face_width=8.0,
        bore_diameter=2.0,
        spacer_height=11.0,
    )

    gen = RaisedSpurGearGenerator(params)
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Raised Spur Gear:")
    print(f"  Module: {dims['module']} mm")
    print(f"  Teeth: {dims['teeth']}")
    print(f"  Pitch diameter: {dims['pitch_diameter']:.2f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.2f} mm")
    print(f"  Bore diameter: {dims['bore_diameter']:.2f} mm")
    print()
    print(f"  Gear face width: {dims['face_width']:.1f} mm")
    print(f"  Spacer height: {dims['spacer_height']:.1f} mm")
    print(f"  Spacer diameter: {dims['spacer_diameter']:.2f} mm")
    print(f"  Total height: {dims['total_height']:.1f} mm")

    cq.exporters.export(gear, "raised_spur_gear.step")
    print("\nExported: raised_spur_gear.step")


if __name__ == "__main__":
    main()
