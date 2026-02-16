"""Triple-stacked gear generator.

Creates a compound gear with:
- Bottom: Full spur gear (all teeth)
- Spacer
- Middle: Partial spur gear (fraction of teeth)
- Spacer
- Top: Full spur gear (all teeth)

Useful for intermittent motion mechanisms where two full gears
need to be driven by a single partial gear.
"""

import math
import cadquery as cq
from cq_gears import SpurGear
from dataclasses import dataclass
from typing import Optional


@dataclass
class TripleStackedGearParams:
    """Parameters for a triple-stacked gear assembly."""

    # Common parameters
    module: float = 1.5              # Gear module (same for all gears)
    teeth: int = 24                  # Number of teeth (same for all)
    bore_diameter: float = 6.0       # Central hole diameter

    # Bottom gear (full)
    bottom_face_width: float = 8.0   # Width of bottom gear

    # First spacer (between bottom and middle)
    spacer1_height: float = 2.0      # Height of first spacer

    # Middle gear (partial)
    middle_face_width: float = 8.0   # Width of middle gear
    middle_teeth_count: int = 6      # Exact number of teeth on middle gear

    # Second spacer (between middle and top)
    spacer2_height: float = 2.0      # Height of second spacer

    # Top gear (full)
    top_face_width: float = 8.0      # Width of top gear

    # Spacer diameter (0 = auto, use root diameter)
    spacer_diameter: float = 0.0

    # Optional: offset angle for the partial gear teeth
    middle_gear_angle_offset: float = 0.0  # Degrees to rotate middle gear teeth


class TripleStackedGearGenerator:
    """Generator for triple-stacked gear assembly.

    Creates a single solid part with:
    - Full gear on bottom
    - Partial gear in middle
    - Full gear on top
    All separated by spacers.
    """

    def __init__(self, params: Optional[TripleStackedGearParams] = None):
        """Initialize the generator.

        Args:
            params: Gear parameters. Uses defaults if not provided.
        """
        self.params = params or TripleStackedGearParams()

    def generate(self) -> cq.Workplane:
        """Generate the triple-stacked gear assembly.

        The assembly is centered at origin with:
        - Bottom gear from Z=0 upward
        - First spacer
        - Middle gear (partial)
        - Second spacer
        - Top gear

        Returns:
            CadQuery Workplane with the triple-stacked gear geometry.
        """
        p = self.params

        # Calculate gear dimensions
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        # Spacer diameter: use root diameter if not specified
        spacer_diameter = p.spacer_diameter if p.spacer_diameter > 0 else root_diameter
        spacer_diameter = max(spacer_diameter, p.bore_diameter + 4.0)

        # Hub diameter for partial gear
        hub_diameter = root_diameter - 2.0
        hub_diameter = max(hub_diameter, p.bore_diameter + 4.0)

        # Z positions
        z = 0.0

        # === Bottom gear (full) ===
        bottom_z_start = z
        z += p.bottom_face_width

        # === First spacer ===
        spacer1_z_start = z
        z += p.spacer1_height

        # === Middle gear (partial) ===
        middle_z_start = z
        z += p.middle_face_width

        # === Second spacer ===
        spacer2_z_start = z
        z += p.spacer2_height

        # === Top gear (full) ===
        top_z_start = z

        # Create bottom gear (full teeth)
        bottom_gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.bottom_face_width,
            bore_d=p.bore_diameter,
        )
        bottom_gear = cq.Workplane('XY').gear(bottom_gear_obj)

        # Create first spacer
        spacer1 = (
            cq.Workplane('XY')
            .circle(spacer_diameter / 2)
            .circle(p.bore_diameter / 2)
            .extrude(p.spacer1_height)
            .translate((0, 0, spacer1_z_start))
        )

        # Create middle gear (partial teeth)
        middle_gear = self._create_partial_gear(
            face_width=p.middle_face_width,
            teeth_count=p.middle_teeth_count,
            angle_offset=p.middle_gear_angle_offset,
            hub_diameter=hub_diameter,
            outer_diameter=outer_diameter,
        )
        middle_gear = middle_gear.translate((0, 0, middle_z_start))

        # Create second spacer
        spacer2 = (
            cq.Workplane('XY')
            .circle(spacer_diameter / 2)
            .circle(p.bore_diameter / 2)
            .extrude(p.spacer2_height)
            .translate((0, 0, spacer2_z_start))
        )

        # Create top gear (full teeth)
        top_gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=p.top_face_width,
            bore_d=p.bore_diameter,
        )
        top_gear = (
            cq.Workplane('XY')
            .gear(top_gear_obj)
            .translate((0, 0, top_z_start))
        )

        # Combine all parts
        result = bottom_gear.union(spacer1).union(middle_gear).union(spacer2).union(top_gear)

        return result

    def _create_partial_gear(
        self,
        face_width: float,
        teeth_count: int,
        angle_offset: float,
        hub_diameter: float,
        outer_diameter: float,
    ) -> cq.Workplane:
        """Create a partial spur gear with specified number of teeth.

        Args:
            face_width: Width of the gear
            teeth_count: Number of teeth to include
            angle_offset: Angular offset in degrees
            hub_diameter: Diameter of the central hub
            outer_diameter: Outer diameter of full gear

        Returns:
            CadQuery Workplane with partial gear at Z=0
        """
        p = self.params

        # Create full gear
        gear_obj = SpurGear(
            module=p.module,
            teeth_number=p.teeth,
            width=face_width,
            bore_d=p.bore_diameter,
        )
        full_gear = cq.Workplane('XY').gear(gear_obj)

        # Calculate sector angle
        tooth_pitch_angle = 360.0 / p.teeth
        tooth_angle = teeth_count * tooth_pitch_angle

        # Create sector mask
        sector_radius = outer_diameter / 2 + 5
        num_points = max(int(tooth_angle / 5), 10)

        # Offset by half a tooth pitch to align with tooth boundaries
        half_tooth = tooth_pitch_angle / 2
        start_angle = angle_offset - half_tooth

        sector_points = [(0, 0)]
        for i in range(num_points + 1):
            angle = math.radians(start_angle + i * tooth_angle / num_points)
            x = sector_radius * math.cos(angle)
            y = sector_radius * math.sin(angle)
            sector_points.append((x, y))
        sector_points.append((0, 0))

        toothed_sector = (
            cq.Workplane('XY')
            .polyline(sector_points)
            .close()
            .extrude(face_width)
        )

        # Intersect to get partial teeth
        partial_teeth = full_gear.intersect(toothed_sector)

        # Create hub
        hub = (
            cq.Workplane('XY')
            .circle(hub_diameter / 2)
            .circle(p.bore_diameter / 2)
            .extrude(face_width)
        )

        # Combine
        return hub.union(partial_teeth)

    def get_dimensions(self) -> dict:
        """Get gear dimensions for reference."""
        p = self.params
        pitch_diameter = p.module * p.teeth
        outer_diameter = pitch_diameter + 2 * p.module
        root_diameter = pitch_diameter - 2.5 * p.module

        total_height = (
            p.bottom_face_width +
            p.spacer1_height +
            p.middle_face_width +
            p.spacer2_height +
            p.top_face_width
        )

        return {
            'module': p.module,
            'teeth': p.teeth,
            'pitch_diameter': pitch_diameter,
            'outer_diameter': outer_diameter,
            'root_diameter': root_diameter,
            'bore_diameter': p.bore_diameter,
            'bottom_face_width': p.bottom_face_width,
            'spacer1_height': p.spacer1_height,
            'middle_face_width': p.middle_face_width,
            'middle_teeth_count': p.middle_teeth_count,
            'spacer2_height': p.spacer2_height,
            'top_face_width': p.top_face_width,
            'total_height': total_height,
        }


def main():
    """Generate and export a triple-stacked gear."""
    params = TripleStackedGearParams(
        module=1.5,
        teeth=24,
        bore_diameter=6.0,
        bottom_face_width=8.0,
        spacer1_height=2.0,
        middle_face_width=8.0,
        middle_teeth_count=6,  # 6 full teeth on middle gear
        spacer2_height=2.0,
        top_face_width=8.0,
    )

    gen = TripleStackedGearGenerator(params)
    gear = gen.generate()

    dims = gen.get_dimensions()
    print("Triple-Stacked Gear Assembly:")
    print(f"  Module: {dims['module']} mm")
    print(f"  Teeth: {dims['teeth']}")
    print(f"  Pitch diameter: {dims['pitch_diameter']:.2f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.2f} mm")
    print(f"  Bore diameter: {dims['bore_diameter']:.2f} mm")
    print()
    print("  Layers (bottom to top):")
    print(f"    1. Bottom gear (full):    {dims['bottom_face_width']:.1f} mm")
    print(f"    2. Spacer:                {dims['spacer1_height']:.1f} mm")
    print(f"    3. Middle gear (partial): {dims['middle_face_width']:.1f} mm ({dims['middle_teeth_count']} teeth)")
    print(f"    4. Spacer:                {dims['spacer2_height']:.1f} mm")
    print(f"    5. Top gear (full):       {dims['top_face_width']:.1f} mm")
    print(f"  Total height: {dims['total_height']:.1f} mm")

    cq.exporters.export(gear, "triple_stacked_gear.step")
    print("\nExported: triple_stacked_gear.step")


if __name__ == "__main__":
    main()
