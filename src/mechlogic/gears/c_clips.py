"""C-clip (retaining clip) generator for small axles.

Generates a sheet of C-clips arranged in a grid for 3D printing.
Each clip is a flat ring with a gap that snaps onto an axle groove.
"""

import cadquery as cq
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CClipSpec:
    """Specification for one size of C-clip."""
    axle_diameter: float      # Nominal axle diameter
    count: int = 8            # How many to generate


@dataclass
class CClipParams:
    """Parameters for C-clip generation."""

    # Clip geometry
    wall_thickness: float = 1.5     # Radial thickness of the ring
    clip_thickness: float = 1.2     # Height/thickness of the clip (Z)
    gap_fraction: float = 0.7       # Gap opening as fraction of axle diameter
    clearance: float = 0.1          # Clearance on inner diameter (per side)

    # Layout
    spacing: float = 2.0            # Gap between clips in the grid
    cols: int = 8                   # Columns per row


def generate_c_clip(
    axle_diameter: float,
    wall_thickness: float = 1.5,
    clip_thickness: float = 1.2,
    gap_fraction: float = 0.7,
    clearance: float = 0.1,
) -> cq.Workplane:
    """Generate a single C-clip.

    Args:
        axle_diameter: Nominal axle diameter the clip fits.
        wall_thickness: Radial wall thickness of the ring.
        clip_thickness: Height of the clip.
        gap_fraction: Gap width as fraction of axle diameter.
        clearance: Radial clearance on inner bore.

    Returns:
        CadQuery Workplane with the C-clip.
    """
    inner_r = axle_diameter / 2 + clearance
    outer_r = inner_r + wall_thickness
    gap_width = axle_diameter * gap_fraction

    # Full annular ring
    ring = (
        cq.Workplane('XY')
        .circle(outer_r)
        .circle(inner_r)
        .extrude(clip_thickness)
    )

    # Cut the gap (rectangular slot from center outward in -Y)
    gap_cut = (
        cq.Workplane('XY')
        .center(0, -(inner_r + wall_thickness / 2))
        .rect(gap_width, wall_thickness + 2)
        .extrude(clip_thickness + 1)
        .translate((0, 0, -0.5))
    )
    clip = ring.cut(gap_cut)

    return clip


def generate_clip_sheet(
    specs: List[CClipSpec],
    params: CClipParams = None,
) -> cq.Workplane:
    """Generate a grid of C-clips for multiple axle sizes.

    Clips are arranged in rows (one row per axle size), columns
    up to params.cols per row.

    Args:
        specs: List of clip specifications (axle sizes + counts).
        params: Layout and geometry parameters.

    Returns:
        CadQuery Workplane with all clips arranged in a grid.
    """
    p = params or CClipParams()

    result = None
    y_offset = 0.0

    for spec in specs:
        inner_r = spec.axle_diameter / 2 + p.clearance
        outer_r = inner_r + p.wall_thickness
        cell_size = outer_r * 2 + p.spacing

        for i in range(spec.count):
            col = i % p.cols
            row = i // p.cols

            x = col * cell_size
            y = y_offset + row * cell_size

            clip = generate_c_clip(
                axle_diameter=spec.axle_diameter,
                wall_thickness=p.wall_thickness,
                clip_thickness=p.clip_thickness,
                gap_fraction=p.gap_fraction,
                clearance=p.clearance,
            )
            clip = clip.translate((x, y, 0))

            if result is None:
                result = clip
            else:
                result = result.union(clip)

        # Move to next row group
        rows_used = (spec.count + p.cols - 1) // p.cols
        y_offset += rows_used * cell_size

    return result


def main():
    specs = [
        CClipSpec(axle_diameter=2.0, count=8),
        CClipSpec(axle_diameter=2.2, count=8),
        CClipSpec(axle_diameter=2.4, count=8),
    ]
    params = CClipParams()

    print("C-Clip Sheet:")
    for spec in specs:
        inner_r = spec.axle_diameter / 2 + params.clearance
        outer_r = inner_r + params.wall_thickness
        gap = spec.axle_diameter * params.gap_fraction
        print(f"  {spec.axle_diameter:.1f}mm axle: {spec.count}x clips, "
              f"ID={inner_r*2:.1f}mm, OD={outer_r*2:.1f}mm, "
              f"gap={gap:.1f}mm, t={params.clip_thickness:.1f}mm")

    sheet = generate_clip_sheet(specs, params)

    cq.exporters.export(sheet, "c_clips.step")
    print(f"\nTotal: {sum(s.count for s in specs)} clips")
    print("Exported: c_clips.step")


if __name__ == "__main__":
    main()
