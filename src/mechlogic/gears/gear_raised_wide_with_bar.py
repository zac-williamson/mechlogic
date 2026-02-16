"""Wide raised spur gear with linkage bar on the bottom face.

Combines gear_raised_spur_wide with a linkage bar on the face
opposite the spacer. One bar hole is concentric with the gear
bore (on the axle), the other is at the far end of the bar.
"""

import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional

from .gear_raised_spur_wide import WideRaisedSpurGearGenerator, WideRaisedSpurGearParams
from .linkage_bar import generate_linkage_bar


@dataclass
class RaisedWideWithBarParams:
    """Parameters for wide raised spur gear + linkage bar."""

    # Gear params (delegated to WideRaisedSpurGearParams)
    gear: WideRaisedSpurGearParams = None

    # Bar params
    bar_length: float = 100.0
    bar_width: float = 10.0
    bar_thickness: float = 3.0
    bar_hole_diameter: float = 2.6

    def __post_init__(self):
        if self.gear is None:
            self.gear = WideRaisedSpurGearParams()


class RaisedWideWithBarGenerator:
    """Generator for wide raised spur gear with linkage bar underneath."""

    def __init__(self, params: Optional[RaisedWideWithBarParams] = None):
        self.params = params or RaisedWideWithBarParams()

    def generate(self) -> cq.Workplane:
        """Generate the combined gear + bar.

        Layout (Z axis):
        - Bar from Z=-bar_thickness to Z=0
        - Gear from Z=0 to Z=face_width
        - Spacer from Z=face_width to Z=face_width+spacer_height

        The bar is centered on the gear axis (one hole on axle).
        The bar extends in +X from the gear center.
        """
        p = self.params

        # Generate the gear
        gear_gen = WideRaisedSpurGearGenerator(p.gear)
        gear = gear_gen.generate()

        # Generate the bar
        bar = generate_linkage_bar(
            length=p.bar_length,
            width=p.bar_width,
            thickness=p.bar_thickness,
            hole_diameter=p.bar_hole_diameter,
        )

        # Position bar: one hole on gear axis, bar extending in +X
        # The bar is centered at origin by default with holes at +/-X.
        # Shift it so the -X hole lands on the gear axis (0,0).
        half_len = p.bar_length / 2
        half_w = p.bar_width / 2
        hole_offset = half_len - half_w  # Distance from bar center to hole center

        bar = bar.translate((hole_offset, 0, -p.bar_thickness))

        # Cut the bore through the bar (so the axle passes through)
        bore = (
            cq.Workplane('XY')
            .circle(p.gear.bore_diameter / 2)
            .extrude(p.bar_thickness + 1)
            .translate((0, 0, -p.bar_thickness - 0.5))
        )
        bar = bar.cut(bore)

        return gear.union(bar)

    def get_dimensions(self) -> dict:
        p = self.params
        gear_gen = WideRaisedSpurGearGenerator(p.gear)
        gear_dims = gear_gen.get_dimensions()

        half_len = p.bar_length / 2
        half_w = p.bar_width / 2
        hole_offset = half_len - half_w

        return {
            **gear_dims,
            'bar_length': p.bar_length,
            'bar_width': p.bar_width,
            'bar_thickness': p.bar_thickness,
            'bar_hole_diameter': p.bar_hole_diameter,
            'bar_far_hole_x': hole_offset * 2,  # Distance from axle to far hole
            'total_height': gear_dims['total_height'] + p.bar_thickness,
        }


def main():
    gen = RaisedWideWithBarGenerator()
    part = gen.generate()

    dims = gen.get_dimensions()
    print("Wide Raised Spur Gear + Linkage Bar:")
    print(f"  Gear: {dims['teeth']}T, OD {dims['outer_diameter']:.1f} mm")
    print(f"  Bore: {dims['bore_diameter']:.1f} mm")
    print(f"  Spacer: h={dims['spacer_height']:.1f} mm, d={dims['spacer_diameter']:.1f} mm")
    print(f"  Bar: {dims['bar_length']:.0f} x {dims['bar_width']:.0f} x {dims['bar_thickness']:.0f} mm")
    print(f"  Far hole distance from axle: {dims['bar_far_hole_x']:.1f} mm")
    print(f"  Total height: {dims['total_height']:.1f} mm")

    cq.exporters.export(part, "raised_spur_gear_wide_with_bar.step")
    print("\nExported: raised_spur_gear_wide_with_bar.step")


if __name__ == "__main__":
    main()
