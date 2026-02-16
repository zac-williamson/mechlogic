"""Wide raised spur gear generator.

Identical to gear_raised_spur but with a default hub diameter
that is twice as large (2/3 of root diameter instead of 1/3).
"""

import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class WideRaisedSpurGearParams:
    """Parameters for a wide raised spur gear."""

    # Gear parameters
    module: float = 1.5              # Gear module
    teeth: int = 24                  # Number of teeth
    face_width: float = 8.0          # Width of gear
    bore_diameter: float = 2.6      # Central hole diameter (snug fit on 2mm axle)

    # Spacer/hub parameters
    spacer_height: float = 11.0      # Height of spacer on top of gear
    spacer_diameter: float = 0.0     # Spacer diameter (0 = auto, use wide hub)


class WideRaisedSpurGearGenerator:
    """Generator for spur gear with wide spacer extension on top."""

    def __init__(self, params: Optional[WideRaisedSpurGearParams] = None):
        self.params = params or WideRaisedSpurGearParams()

    def _auto_spacer_diameter(self) -> float:
        """Calculate the auto spacer diameter (2x the narrow variant)."""
        p = self.params
        root_diameter = p.module * p.teeth - 2.5 * p.module
        return max(root_diameter * 2 / 3, p.bore_diameter + 4.0)

    def generate(self) -> cq.Workplane:
        """Generate the wide raised spur gear.

        The gear is at the bottom (Z=0 to Z=face_width),
        spacer extends upward from the gear.

        Returns:
            CadQuery Workplane with the raised gear geometry.
        """
        p = self.params

        # Spacer diameter
        if p.spacer_diameter > 0:
            spacer_diameter = p.spacer_diameter
        else:
            spacer_diameter = self._auto_spacer_diameter()
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

        return gear.union(spacer)

    def get_dimensions(self) -> dict:
        """Get gear dimensions for reference."""
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        if p.spacer_diameter > 0:
            spacer_diameter = p.spacer_diameter
        else:
            spacer_diameter = self._auto_spacer_diameter()
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
    """Generate and export a wide raised spur gear."""
    gen = WideRaisedSpurGearGenerator()
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Wide Raised Spur Gear:")
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

    cq.exporters.export(gear, "raised_spur_gear_wide.step")
    print("\nExported: raised_spur_gear_wide.step")


if __name__ == "__main__":
    main()
