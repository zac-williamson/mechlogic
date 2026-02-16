"""Gear rack generator - creates a linear rack with tooth sections.

Creates a rack that can mesh with spur gears, with configurable
sections of teeth and flat areas.
"""

import math
import cadquery as cq
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class RackSection:
    """A section of the gear rack."""
    length: float       # Length in mm
    has_teeth: bool     # True for toothed section, False for flat


@dataclass
class GearRackParams:
    """Parameters for a gear rack."""

    module: float = 1.5              # Gear module (must match mating gear)
    pressure_angle: float = 20.0     # Pressure angle in degrees
    rack_height: float = 10.0        # Total height of rack body
    rack_width: float = 15.0         # Width (thickness) of rack
    double_sided: bool = False       # If True, add teeth on both top and bottom faces

    # Sections: list of (length_mm, has_teeth) tuples
    # Default: 5cm flat, 5cm teeth, 20cm flat, 5cm teeth, 5cm flat
    sections: List[RackSection] = field(default_factory=lambda: [
        RackSection(50.0, False),   # 5cm flat
        RackSection(50.0, True),    # 5cm teeth
        RackSection(200.0, False),  # 20cm flat
        RackSection(50.0, True),    # 5cm teeth
        RackSection(50.0, False),   # 5cm flat
    ])


class GearRackGenerator:
    """Generator for gear racks with configurable tooth sections."""

    def __init__(self, params: Optional[GearRackParams] = None):
        """Initialize the generator.

        Args:
            params: Rack parameters. Uses defaults if not provided.
        """
        self.params = params or GearRackParams()

    def _create_tooth_profile(self) -> List[Tuple[float, float]]:
        """Create the 2D profile for a single rack tooth.

        Returns:
            List of (x, y) points defining the tooth profile.
            X is along rack length, Y is height.
            Y=0 is at the tooth root (bottom), tooth extends upward.
        """
        p = self.params
        m = p.module
        alpha = math.radians(p.pressure_angle)

        # Rack tooth geometry (standard involute rack)
        pitch = math.pi * m                    # Circular pitch
        addendum = m                           # Tooth height above pitch line
        dedendum = 1.25 * m                    # Tooth depth below pitch line
        tooth_height = addendum + dedendum     # Total tooth height

        # Tooth thickness at pitch line
        tooth_thickness = pitch / 2

        # Calculate tooth profile points
        # The tooth is symmetric about its centerline
        tan_alpha = math.tan(alpha)

        # Half-width at tip
        tip_half_width = tooth_thickness / 2 - addendum * tan_alpha

        # Half-width at root
        root_half_width = tooth_thickness / 2 + dedendum * tan_alpha

        # Profile points with root at Y=0, tip at Y=tooth_height
        # This way teeth sit ON TOP of the body without overlapping
        points = [
            (-root_half_width, 0),              # Bottom left (root)
            (-tip_half_width, tooth_height),    # Top left (tip)
            (tip_half_width, tooth_height),     # Top right (tip)
            (root_half_width, 0),               # Bottom right (root)
        ]

        return points

    def generate(self) -> cq.Workplane:
        """Generate the gear rack.

        The rack is oriented with:
        - X axis: along the rack length
        - Y axis: perpendicular (rack width direction)
        - Z axis: tooth height direction (teeth point up in +Z)

        The rack starts at X=0 and extends in +X direction.
        Rack body sits from Z=0 to Z=rack_height.
        Teeth protrude above the body (tips above rack_height).

        Returns:
            CadQuery Workplane with the gear rack geometry.
        """
        p = self.params
        m = p.module
        pitch = math.pi * m
        addendum = m
        dedendum = 1.25 * m

        # Calculate total length
        total_length = sum(s.length for s in p.sections)

        # Create base rack body
        # Body from Z=0 to Z=rack_height
        rack = (
            cq.Workplane('XY')
            .rect(total_length, p.rack_width, centered=False)
            .extrude(p.rack_height)
            .translate((0, -p.rack_width / 2, 0))
        )

        # Get tooth profile (root at Z=0)
        tooth_profile = self._create_tooth_profile()

        # Position teeth with root at top of rack body
        tooth_root_z = p.rack_height

        # Process each section
        current_x = 0.0
        for section in p.sections:
            if section.has_teeth:
                # Calculate number of teeth that fit in this section
                num_teeth = int(section.length / pitch)

                # Center the teeth in the section
                teeth_total_length = num_teeth * pitch
                start_offset = (section.length - teeth_total_length) / 2

                # Create teeth for this section
                for i in range(num_teeth):
                    tooth_center_x = current_x + start_offset + (i + 0.5) * pitch

                    # Create tooth on TOP face (Z = rack_height, pointing up)
                    top_tooth_points = [
                        (tooth_center_x + px, tooth_root_z + pz)
                        for px, pz in tooth_profile
                    ]

                    top_tooth = (
                        cq.Workplane('XZ')
                        .polyline(top_tooth_points)
                        .close()
                        .extrude(p.rack_width)
                        .translate((0, p.rack_width / 2, 0))  # Center on Y=0
                    )

                    rack = rack.union(top_tooth)

                    # Create tooth on BOTTOM face if double-sided (Z = 0, pointing down)
                    if p.double_sided:
                        # Mirror the tooth profile: root at Z=0, extending in -Z
                        bottom_tooth_points = [
                            (tooth_center_x + px, -pz)  # Flip Z to point downward
                            for px, pz in tooth_profile
                        ]

                        bottom_tooth = (
                            cq.Workplane('XZ')
                            .polyline(bottom_tooth_points)
                            .close()
                            .extrude(p.rack_width)
                            .translate((0, p.rack_width / 2, 0))  # Center on Y=0
                        )

                        rack = rack.union(bottom_tooth)

            current_x += section.length

        return rack

    def get_dimensions(self) -> dict:
        """Get rack dimensions for reference."""
        p = self.params
        total_length = sum(s.length for s in p.sections)
        pitch = math.pi * p.module

        toothed_sections = [s for s in p.sections if s.has_teeth]
        teeth_per_side = sum(int(s.length / pitch) for s in toothed_sections)
        total_teeth = teeth_per_side * 2 if p.double_sided else teeth_per_side

        return {
            'module': p.module,
            'pressure_angle': p.pressure_angle,
            'pitch': pitch,
            'total_length': total_length,
            'rack_height': p.rack_height,
            'rack_width': p.rack_width,
            'double_sided': p.double_sided,
            'teeth_per_side': teeth_per_side,
            'total_teeth': total_teeth,
            'num_sections': len(p.sections),
            'toothed_sections': len(toothed_sections),
        }


def main():
    """Generate and export a gear rack."""
    # Create double-sided rack with: 5cm flat, 5cm teeth, 20cm flat, 5cm teeth, 5cm flat
    params = GearRackParams(
        module=1.5,
        pressure_angle=20.0,
        rack_height=10.0,
        rack_width=15.0,
        double_sided=True,  # Teeth on both top and bottom faces
        sections=[
            RackSection(50.0, False),   # 5cm flat
            RackSection(50.0, True),    # 5cm teeth
            RackSection(200.0, False),  # 20cm flat
            RackSection(50.0, True),    # 5cm teeth
            RackSection(50.0, False),   # 5cm flat
        ],
    )

    gen = GearRackGenerator(params)
    rack = gen.generate()

    dims = gen.get_dimensions()
    print("Gear Rack:")
    print(f"  Module: {dims['module']} mm")
    print(f"  Pressure angle: {dims['pressure_angle']}°")
    print(f"  Pitch: {dims['pitch']:.3f} mm")
    print(f"  Total length: {dims['total_length']:.1f} mm ({dims['total_length']/10:.0f} cm)")
    print(f"  Rack height: {dims['rack_height']:.1f} mm")
    print(f"  Rack width: {dims['rack_width']:.1f} mm")
    print(f"  Double-sided: {dims['double_sided']}")
    print(f"  Teeth per side: {dims['teeth_per_side']}")
    print(f"  Total teeth: {dims['total_teeth']}")
    print()
    print("Sections:")
    x = 0
    for i, section in enumerate(params.sections):
        section_type = "teeth" if section.has_teeth else "flat"
        print(f"  {i+1}. {section.length/10:.0f}cm {section_type} (X={x:.0f} to {x+section.length:.0f})")
        x += section.length

    cq.exporters.export(rack, "gear_rack.step")
    print("\nExported: gear_rack.step")


if __name__ == "__main__":
    main()
