"""Double gear generator - two full spur gears separated by a spacer disk.

Creates a compound gear with:
- Bottom: Full spur gear
- Middle: Solid spacer disc
- Top: Full spur gear

Both gears share the same module and tooth count but can have
different face widths. The teeth are aligned (no angular offset).
"""

import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class DoubleGearParams:
    """Parameters for a double gear assembly."""

    # Common parameters
    module: float = 1.5              # Gear module (same for both gears)
    teeth: int = 24                  # Number of teeth (same for both)
    bore_diameter: float = 2.0       # Central hole diameter

    # Bottom gear
    bottom_face_width: float = 8.0   # Width of bottom gear

    # Spacer
    spacer_height: float = 2.0       # Height of spacer between gears
    spacer_diameter: float = 0.0     # Spacer diameter (0 = auto, use root diameter)

    # Top gear
    top_face_width: float = 8.0      # Width of top gear


class DoubleGearGenerator:
    """Generator for double full spur gear assembly.

    Creates a single solid part with two full spur gears
    separated by a spacer disc.
    """

    def __init__(self, params: Optional[DoubleGearParams] = None):
        self.params = params or DoubleGearParams()

    def generate(self) -> cq.Workplane:
        """Generate the double gear assembly.

        The assembly is centered at origin with:
        - Bottom gear from Z=0 to Z=bottom_face_width
        - Spacer from Z=bottom_face_width to Z=bottom_face_width+spacer_height
        - Top gear from Z=spacer_top to Z=spacer_top+top_face_width

        Returns:
            CadQuery Workplane with the double gear geometry.
        """
        p = self.params

        # Calculate gear dimensions
        pitch_diameter = p.module * p.teeth
        root_diameter = pitch_diameter - 2.5 * p.module

        # Spacer diameter: use root diameter if not specified
        spacer_diameter = p.spacer_diameter if p.spacer_diameter > 0 else root_diameter
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        # Z positions
        spacer_z_start = p.bottom_face_width
        top_z_start = spacer_z_start + p.spacer_height

        # === Bottom gear (full teeth) ===
        bottom_gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.bottom_face_width,
            bore_d=p.bore_diameter,
        )
        bottom_gear = cq.Workplane('XY').gear(bottom_gear_obj)

        # === Spacer disc ===
        spacer = (
            cq.Workplane('XY')
            .circle(spacer_diameter / 2)
            .circle(p.bore_diameter / 2)
            .extrude(p.spacer_height)
            .translate((0, 0, spacer_z_start))
        )

        # === Top gear (full teeth) ===
        top_gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.top_face_width,
            bore_d=p.bore_diameter,
        )
        top_gear = cq.Workplane('XY').gear(top_gear_obj)
        top_gear = top_gear.translate((0, 0, top_z_start))

        # === Combine all parts ===
        return bottom_gear.union(spacer).union(top_gear)

    def get_dimensions(self) -> dict:
        """Get gear dimensions for reference."""
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module
        total_height = p.bottom_face_width + p.spacer_height + p.top_face_width

        return {
            'module': p.module,
            'teeth': p.teeth,
            'pitch_diameter': pitch_diameter,
            'outer_diameter': outer_diameter,
            'root_diameter': root_diameter,
            'bore_diameter': p.bore_diameter,
            'bottom_face_width': p.bottom_face_width,
            'spacer_height': p.spacer_height,
            'top_face_width': p.top_face_width,
            'total_height': total_height,
        }


def main():
    """Generate and export a double gear."""
    params = DoubleGearParams(
        module=1.5,
        teeth=24,
        bore_diameter=2.0,
        bottom_face_width=8.0,
        spacer_height=2.0,
        top_face_width=8.0,
    )

    gen = DoubleGearGenerator(params)
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Double Gear Assembly:")
    print(f"  Module: {dims['module']} mm")
    print(f"  Teeth: {dims['teeth']}")
    print(f"  Pitch diameter: {dims['pitch_diameter']:.2f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.2f} mm")
    print(f"  Bore diameter: {dims['bore_diameter']:.2f} mm")
    print()
    print(f"  Bottom gear: {dims['bottom_face_width']:.1f} mm")
    print(f"  Spacer: {dims['spacer_height']:.1f} mm")
    print(f"  Top gear: {dims['top_face_width']:.1f} mm")
    print(f"  Total height: {dims['total_height']:.1f} mm")

    cq.exporters.export(gear, "double_gear.step")
    print("\nExported: double_gear.step")


if __name__ == "__main__":
    main()
