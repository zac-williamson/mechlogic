"""Wide raised spur gear generator (48-tooth variant).

Identical to gear_raised_spur_wide but with 48 teeth (2x),
same module so the gear diameter doubles.
"""

import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class WideRaisedSpurGear48TParams:
    """Parameters for a 48-tooth wide raised spur gear."""

    module: float = 1.5
    teeth: int = 48
    face_width: float = 8.0
    bore_diameter: float = 2.6

    spacer_height: float = 11.0
    spacer_diameter: float = 0.0  # 0 = auto (2/3 root diameter)


class WideRaisedSpurGear48TGenerator:
    """Generator for 48-tooth spur gear with wide spacer extension on top."""

    def __init__(self, params: Optional[WideRaisedSpurGear48TParams] = None):
        self.params = params or WideRaisedSpurGear48TParams()

    def _auto_spacer_diameter(self) -> float:
        p = self.params
        root_diameter = p.module * p.teeth - 2.5 * p.module
        return max(root_diameter * 2 / 3, p.bore_diameter + 4.0)

    def generate(self) -> cq.Workplane:
        p = self.params

        if p.spacer_diameter > 0:
            spacer_diameter = p.spacer_diameter
        else:
            spacer_diameter = self._auto_spacer_diameter()
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        gear_obj = SpurGear(
            module=p.module, teeth_number=p.teeth,
            width=p.face_width, bore_d=p.bore_diameter,
        )
        gear = cq.Workplane('XY').gear(gear_obj)

        spacer = (
            cq.Workplane('XY')
            .circle(spacer_diameter / 2)
            .circle(p.bore_diameter / 2)
            .extrude(p.spacer_height)
            .translate((0, 0, p.face_width))
        )

        return gear.union(spacer)

    def get_dimensions(self) -> dict:
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        if p.spacer_diameter > 0:
            spacer_diameter = p.spacer_diameter
        else:
            spacer_diameter = self._auto_spacer_diameter()
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        return {
            'module': p.module, 'teeth': p.teeth,
            'pitch_diameter': pitch_diameter, 'outer_diameter': outer_diameter,
            'root_diameter': root_diameter, 'bore_diameter': p.bore_diameter,
            'face_width': p.face_width,
            'spacer_height': p.spacer_height,
            'spacer_diameter': spacer_diameter,
            'total_height': p.face_width + p.spacer_height,
        }


def main():
    gen = WideRaisedSpurGear48TGenerator()
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Wide Raised Spur Gear (48-tooth):")
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

    cq.exporters.export(gear, "raised_spur_gear_wide_48t.step")
    print("\nExported: raised_spur_gear_wide_48t.step")


if __name__ == "__main__":
    main()
