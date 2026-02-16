"""Stacked gear generator - full spur gear with partial spur gear on top.

Creates a compound gear with:
- Bottom: Full spur gear (all teeth)
- Middle: Solid spacer disc
- Top: Partial spur gear (fraction of teeth)

Useful for intermittent motion mechanisms.
"""

import math
import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class StackedGearParams:
    """Parameters for a stacked gear assembly."""

    # Common parameters
    module: float = 1.5              # Gear module (same for both gears)
    teeth: int = 24                  # Number of teeth (same for both)
    bore_diameter: float = 2.6       # Central hole diameter (snug fit on 2mm axle)

    # Bottom gear (full)
    bottom_face_width: float = 8.0   # Width of bottom gear

    # Spacer
    spacer_height: float = 2.0       # Height of spacer between gears
    spacer_diameter: float = 0.0     # Spacer diameter (0 = auto, use root diameter)

    # Top gear (partial)
    top_face_width: float = 8.0      # Width of top gear
    top_teeth_count: int = 6         # Exact number of teeth on top gear (0 = use tooth_fraction)
    tooth_fraction: float = 0.25     # Fraction of teeth on top gear (only used if top_teeth_count=0)

    # Optional: offset angle for the partial gear teeth
    top_gear_angle_offset: float = 0.0  # Degrees to rotate top gear teeth


class StackedGearGenerator:
    """Generator for stacked full + partial spur gear assembly.

    Creates a single solid part with a full gear on bottom and
    a partial gear on top, separated by a spacer.
    """

    def __init__(self, params: Optional[StackedGearParams] = None):
        """Initialize the generator.

        Args:
            params: Gear parameters. Uses defaults if not provided.
        """
        self.params = params or StackedGearParams()

    def generate(self) -> cq.Workplane:
        """Generate the stacked gear assembly.

        The assembly is centered at origin with:
        - Bottom gear from Z=0 to Z=bottom_face_width
        - Spacer from Z=bottom_face_width to Z=bottom_face_width+spacer_height
        - Top gear from Z=spacer_top to Z=spacer_top+top_face_width

        Returns:
            CadQuery Workplane with the stacked gear geometry.
        """
        p = self.params

        # Calculate gear dimensions
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        # Spacer diameter: default to top_face_width (small hub, printable)
        spacer_diameter = p.spacer_diameter if p.spacer_diameter > 0 else p.top_face_width

        # Ensure spacer is larger than bore
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        # Z positions
        bottom_z_start = 0
        bottom_z_end = p.bottom_face_width
        spacer_z_start = bottom_z_end
        spacer_z_end = spacer_z_start + p.spacer_height
        top_z_start = spacer_z_end
        top_z_end = top_z_start + p.top_face_width

        # === Create bottom gear (full teeth) ===
        bottom_gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.bottom_face_width,
            bore_d=p.bore_diameter,
        )
        bottom_gear = cq.Workplane('XY').gear(bottom_gear_obj)

        # === Create spacer disc ===
        spacer = (
            cq.Workplane('XY')
            .circle(spacer_diameter / 2)
            .circle(p.bore_diameter / 2)
            .extrude(p.spacer_height)
            .translate((0, 0, spacer_z_start))
        )

        # === Create top gear (partial teeth) with bridge supports ===
        # Instead of separate top teeth + bridge, create one tall gear spanning
        # from bottom gear top through spacer to top gear top. Intersect with
        # sector so teeth connect continuously to the bottom gear.
        tooth_pitch_angle = 360.0 / p.teeth

        if p.top_teeth_count > 0:
            teeth_in_section = p.top_teeth_count
            tooth_angle = teeth_in_section * tooth_pitch_angle
        else:
            tooth_angle = 360.0 * p.tooth_fraction
            teeth_in_section = int(p.teeth * p.tooth_fraction)

        # Create sector mask for the toothed portion
        sector_radius = outer_diameter / 2 + 5
        num_points = max(int(tooth_angle / 5), 10)

        # Offset start angle by half a tooth pitch to align sector edges with
        # tooth boundaries (between teeth, not through teeth centers)
        half_tooth = tooth_pitch_angle / 2
        start_angle = p.top_gear_angle_offset - half_tooth

        sector_points = [(0, 0)]
        for i in range(num_points + 1):
            angle = math.radians(start_angle + i * tooth_angle / num_points)
            x = sector_radius * math.cos(angle)
            y = sector_radius * math.sin(angle)
            sector_points.append((x, y))
        sector_points.append((0, 0))

        # Create a single gear spanning spacer + top gear height
        # This sits directly on top of the bottom gear so teeth are continuous
        combined_height = p.spacer_height + p.top_face_width
        tall_gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=combined_height,
            bore_d=p.bore_diameter,
        )
        tall_gear_full = cq.Workplane('XY').gear(tall_gear_obj)

        # Build mask: pie sector for teeth + full hub ring around bore
        # Union them so the intersection produces one connected solid
        toothed_sector = (
            cq.Workplane('XY')
            .polyline(sector_points)
            .close()
            .extrude(combined_height)
        )
        hub_ring = (
            cq.Workplane('XY')
            .circle(spacer_diameter / 2)
            .extrude(combined_height)
        )
        mask = toothed_sector.union(hub_ring)

        # Intersect gear with combined mask: partial teeth + hub, all connected
        top_section = tall_gear_full.intersect(mask)
        top_section = top_section.translate((0, 0, spacer_z_start))

        # === Combine all parts ===
        return bottom_gear.union(spacer).union(top_section)

    def get_dimensions(self) -> dict:
        """Get gear dimensions for reference."""
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
            'top_teeth_count': p.top_teeth_count,
            'teeth_in_partial_section': teeth_in_section,
        }


def main():
    """Generate and export a stacked gear."""
    # Create stacked gear with exactly 6 teeth on top
    params = StackedGearParams(
        module=1.5,
        teeth=24,
        bore_diameter=2.6,
        bottom_face_width=8.0,
        spacer_height=2.0,
        top_face_width=8.0,
        top_teeth_count=6,  # Exactly 6 full teeth on top gear
    )

    gen = StackedGearGenerator(params)
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Stacked Gear Assembly:")
    print(f"  Module: {dims['module']} mm")
    print(f"  Teeth: {dims['teeth']}")
    print(f"  Pitch diameter: {dims['pitch_diameter']:.2f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.2f} mm")
    print(f"  Bore diameter: {dims['bore_diameter']:.2f} mm")
    print()
    print("  Bottom gear (full): {:.1f} mm".format(dims['bottom_face_width']))
    print("  Spacer: {:.1f} mm".format(dims['spacer_height']))
    print("  Top gear (partial): {:.1f} mm ({} full teeth)".format(
        dims['top_face_width'],
        dims['teeth_in_partial_section']
    ))
    print("  Total height: {:.1f} mm".format(dims['total_height']))

    cq.exporters.export(gear, "stacked_gear.step")
    print("\nExported: stacked_gear.step")


if __name__ == "__main__":
    main()
