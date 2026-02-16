"""Big spur gear generator.

Creates a large spur gear with the same tooth size (module) as the standard gear
but with more teeth for a larger diameter.
"""

import math
import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class BigSpurGearParams:
    """Parameters for a big spur gear."""

    # Gear parameters
    module: float = 1.5              # Gear module (same as regular gear)
    teeth: int = 143                 # Number of teeth (calculated for big diameter)
    face_width: float = 8.0          # Width of gear
    bore_diameter: float = 6.0       # Central hole diameter


class BigSpurGearGenerator:
    """Generator for a big spur gear."""

    def __init__(self, params: Optional[BigSpurGearParams] = None):
        """Initialize the generator.

        Args:
            params: Gear parameters. Uses defaults if not provided.
        """
        self.params = params or BigSpurGearParams()

    @staticmethod
    def calculate_teeth_from_formula(module: float = 1.5, regular_teeth: int = 24) -> int:
        """Calculate number of teeth using the formula.

        Formula: diameter = (150/sqrt(2)) + 3*d
        where d is the pitch diameter of the regular gear.

        Args:
            module: Gear module
            regular_teeth: Teeth count of regular gear

        Returns:
            Number of teeth for the big gear
        """
        regular_pitch_diameter = module * regular_teeth
        new_pitch_diameter = (150 / math.sqrt(2)) + 3 * regular_pitch_diameter
        teeth = round(new_pitch_diameter / module)
        return teeth

    def generate(self) -> cq.Workplane:
        """Generate the big spur gear.

        Returns:
            CadQuery Workplane with the gear geometry.
        """
        p = self.params

        # Create the spur gear
        gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.face_width,
            bore_d=p.bore_diameter,
        )
        gear = cq.Workplane('XY').gear(gear_obj)

        return gear

    def get_dimensions(self) -> dict:
        """Get gear dimensions for reference."""
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        return {
            'module': p.module,
            'teeth': p.teeth,
            'pitch_diameter': pitch_diameter,
            'outer_diameter': outer_diameter,
            'root_diameter': root_diameter,
            'bore_diameter': p.bore_diameter,
            'face_width': p.face_width,
        }


def main():
    """Generate and export a big spur gear."""
    # Calculate teeth using formula: (150/sqrt(2)) + 3*d
    # where d = pitch diameter of regular 24-tooth gear = 36mm
    module = 1.5
    regular_teeth = 24
    regular_pitch_diameter = module * regular_teeth  # 36mm

    # Formula interpretation: new_diameter = (150/sqrt(2)) + 3*d
    new_pitch_diameter = (150 / math.sqrt(2)) + 3 * regular_pitch_diameter
    teeth = round(new_pitch_diameter / module)

    print(f"Formula calculation:")
    print(f"  Regular gear pitch diameter (d): {regular_pitch_diameter:.2f} mm")
    print(f"  150/sqrt(2): {150/math.sqrt(2):.2f} mm")
    print(f"  3*d: {3*regular_pitch_diameter:.2f} mm")
    print(f"  New pitch diameter: {new_pitch_diameter:.2f} mm")
    print(f"  Teeth (rounded): {teeth}")
    print()

    params = BigSpurGearParams(
        module=module,
        teeth=teeth,
        face_width=8.0,
        bore_diameter=6.0,
    )

    gen = BigSpurGearGenerator(params)
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Big Spur Gear:")
    print(f"  Module: {dims['module']} mm")
    print(f"  Teeth: {dims['teeth']}")
    print(f"  Pitch diameter: {dims['pitch_diameter']:.2f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.2f} mm")
    print(f"  Bore diameter: {dims['bore_diameter']:.2f} mm")
    print(f"  Face width: {dims['face_width']:.1f} mm")

    cq.exporters.export(gear, "big_spur_gear.step")
    print("\nExported: big_spur_gear.step")


if __name__ == "__main__":
    main()
