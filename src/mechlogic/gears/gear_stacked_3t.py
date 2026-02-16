"""Stacked gear generator (3-tooth variant).

Identical to gear_stacked but with 3 partial teeth on top instead of 6.
"""

import math
import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class StackedGear3TParams:
    """Parameters for a 3-tooth stacked gear assembly."""

    # Common parameters
    module: float = 1.5
    teeth: int = 24
    bore_diameter: float = 2.6

    # Bottom gear (full)
    bottom_face_width: float = 8.0

    # Spacer
    spacer_height: float = 2.0
    spacer_diameter: float = 0.0  # 0 = auto (top_face_width)

    # Top gear (partial)
    top_face_width: float = 8.0
    top_teeth_count: int = 3
    tooth_fraction: float = 0.125  # Fallback if top_teeth_count=0

    # Optional: offset angle for the partial gear teeth
    top_gear_angle_offset: float = 0.0


class StackedGear3TGenerator:
    """Generator for stacked gear with 3 partial teeth on top."""

    def __init__(self, params: Optional[StackedGear3TParams] = None):
        self.params = params or StackedGear3TParams()

    def generate(self) -> cq.Workplane:
        """Generate the stacked gear assembly."""
        p = self.params

        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        spacer_diameter = p.spacer_diameter if p.spacer_diameter > 0 else p.top_face_width
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        spacer_z_start = p.bottom_face_width
        top_z_start = spacer_z_start + p.spacer_height

        # === Bottom gear (full teeth) ===
        bottom_gear_obj = SpurGear(
            module=p.module, teeth_number=p.teeth,
            width=p.bottom_face_width, bore_d=p.bore_diameter,
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

        # === Top partial teeth with bridge ===
        tooth_pitch_angle = 360.0 / p.teeth

        if p.top_teeth_count > 0:
            teeth_in_section = p.top_teeth_count
            tooth_angle = teeth_in_section * tooth_pitch_angle
        else:
            tooth_angle = 360.0 * p.tooth_fraction
            teeth_in_section = int(p.teeth * p.tooth_fraction)

        sector_radius = outer_diameter / 2 + 5
        num_points = max(int(tooth_angle / 5), 10)
        half_tooth = tooth_pitch_angle / 2
        start_angle = p.top_gear_angle_offset - half_tooth

        sector_points = [(0, 0)]
        for i in range(num_points + 1):
            angle = math.radians(start_angle + i * tooth_angle / num_points)
            sector_points.append((sector_radius * math.cos(angle),
                                  sector_radius * math.sin(angle)))
        sector_points.append((0, 0))

        combined_height = p.spacer_height + p.top_face_width
        tall_gear_obj = SpurGear(
            module=p.module, teeth_number=p.teeth,
            width=combined_height, bore_d=p.bore_diameter,
        )
        tall_gear_full = cq.Workplane('XY').gear(tall_gear_obj)

        toothed_sector = (
            cq.Workplane('XY').polyline(sector_points).close()
            .extrude(combined_height)
        )
        hub_ring = cq.Workplane('XY').circle(spacer_diameter / 2).extrude(combined_height)
        mask = toothed_sector.union(hub_ring)

        top_section = tall_gear_full.intersect(mask)
        top_section = top_section.translate((0, 0, spacer_z_start))

        return bottom_gear.union(spacer).union(top_section)

    def get_dimensions(self) -> dict:
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        if p.top_teeth_count > 0:
            teeth_in_section = p.top_teeth_count
        else:
            teeth_in_section = int(p.teeth * p.tooth_fraction)
        total_height = p.bottom_face_width + p.spacer_height + p.top_face_width

        return {
            'module': p.module, 'teeth': p.teeth,
            'pitch_diameter': pitch_diameter, 'outer_diameter': outer_diameter,
            'root_diameter': root_diameter, 'bore_diameter': p.bore_diameter,
            'bottom_face_width': p.bottom_face_width,
            'spacer_height': p.spacer_height,
            'top_face_width': p.top_face_width,
            'total_height': total_height,
            'top_teeth_count': p.top_teeth_count,
            'teeth_in_partial_section': teeth_in_section,
        }


def main():
    gen = StackedGear3TGenerator()
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Stacked Gear (3-tooth):")
    print(f"  Module: {dims['module']} mm")
    print(f"  Teeth: {dims['teeth']}")
    print(f"  Pitch diameter: {dims['pitch_diameter']:.2f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.2f} mm")
    print(f"  Bore diameter: {dims['bore_diameter']:.2f} mm")
    print()
    print(f"  Bottom gear (full): {dims['bottom_face_width']:.1f} mm")
    print(f"  Spacer: {dims['spacer_height']:.1f} mm")
    print(f"  Top gear (partial): {dims['top_face_width']:.1f} mm ({dims['teeth_in_partial_section']} full teeth)")
    print(f"  Total height: {dims['total_height']:.1f} mm")

    cq.exporters.export(gear, "stacked_gear_3t.step")
    print("\nExported: stacked_gear_3t.step")


if __name__ == "__main__":
    main()
