"""Serpentine/meander flexure generator for compliant Y-axis motion."""

import cadquery as cq
from dataclasses import dataclass


@dataclass
class SerpentineFlexureParams:
    """Parameters for serpentine flexure design."""

    # Axle hole
    axle_diameter: float = 6.0

    # Floating platform (holds the axle)
    platform_width: float = 14.0   # X dimension
    platform_height: float = 10.0  # Y dimension

    # Serpentine beam parameters
    beam_width: float = 0.8        # Width of each beam segment (thin for flexibility)
    beam_spacing: float = 2.5      # Gap between parallel beam segments
    num_folds: int = 4             # Number of U-turns on each side (more = more compliance)
    segment_length: float = 15.0   # Length of each straight segment (Y direction)

    # Outer frame
    frame_thickness: float = 5.0   # Width of frame walls

    # Z thickness (entire part)
    thickness: float = 5.0         # Z dimension

    # Mounting holes in frame (optional)
    mounting_hole_diameter: float = 4.0
    include_mounting_holes: bool = True


class SerpentineFlexureGenerator:
    """Generator for serpentine/meander flexure.

    Creates a flexure where a central platform is connected to the frame
    by serpentine (zigzag) beams. The folded beam path provides high
    compliance in a compact footprint.

    Layout (top view, XY plane):

        ┌─────────────────────────────────┐
        │  Frame                          │
        │  ┌──╗ ╔══╗ ╔══╗ ╔──┐           │
        │  │  ║ ║  ║ ║  ║ ║  │           │
        │  │  ╚═╝  ╚═╝  ╚═╝  │           │
        │  │                  │           │
        ├──┤     ┌──────┐     ├───────────┤
        │  │     │  (○) │     │           │  ← Platform with axle
        ├──┤     └──────┘     ├───────────┤
        │  │                  │           │
        │  │  ╔═╗  ╔═╗  ╔═╗  │           │
        │  │  ║ ║  ║ ║  ║ ║  │           │
        │  └──╝ ╚══╝ ╚══╝ ╚──┘           │
        │                                 │
        └─────────────────────────────────┘

    The serpentine path on each side gives a much longer effective beam
    length, allowing more deflection in a compact space.
    """

    def __init__(self, params: SerpentineFlexureParams = None):
        self.params = params or SerpentineFlexureParams()

    def _create_serpentine_beam(self, start_x: float, direction: int) -> cq.Workplane:
        """Create one serpentine beam structure.

        Args:
            start_x: X position where beam connects to platform
            direction: +1 for right side, -1 for left side

        Returns:
            CadQuery workplane with the serpentine beam
        """
        p = self.params

        # Calculate dimensions
        fold_pitch = p.beam_width + p.beam_spacing  # Distance between fold centers
        total_folds_width = (p.num_folds - 1) * fold_pitch + p.beam_width

        # Start building the serpentine path
        # We'll create it as a series of rectangles and unions

        segments = []

        # Current position tracking
        x = start_x
        y_bottom = -p.segment_length / 2
        y_top = p.segment_length / 2

        for i in range(p.num_folds):
            # Vertical segment
            seg = (
                cq.Workplane("XY")
                .center(x, 0)
                .rect(p.beam_width, p.segment_length)
                .extrude(p.thickness)
            )
            segments.append(seg)

            # Horizontal connector to next fold (except for last fold)
            if i < p.num_folds - 1:
                # Alternate between top and bottom connections
                if i % 2 == 0:
                    # Connect at top
                    conn_y = y_top - p.beam_width / 2
                else:
                    # Connect at bottom
                    conn_y = y_bottom + p.beam_width / 2

                conn_x = x + direction * fold_pitch / 2
                conn = (
                    cq.Workplane("XY")
                    .center(conn_x, conn_y)
                    .rect(fold_pitch, p.beam_width)
                    .extrude(p.thickness)
                )
                segments.append(conn)

                x += direction * fold_pitch

        # Union all segments
        result = segments[0]
        for seg in segments[1:]:
            result = result.union(seg)

        return result

    def generate(self) -> cq.Workplane:
        """Generate the serpentine flexure."""
        p = self.params

        # Calculate overall dimensions
        fold_pitch = p.beam_width + p.beam_spacing
        serpentine_width = (p.num_folds - 1) * fold_pitch + p.beam_width

        # Inner cavity dimensions
        inner_width = p.platform_width + 2 * serpentine_width + 2 * p.beam_spacing
        inner_height = p.segment_length + 2 * p.beam_width

        # Outer frame dimensions
        outer_width = inner_width + 2 * p.frame_thickness
        outer_height = inner_height + 2 * p.frame_thickness

        # Create outer frame
        frame = (
            cq.Workplane("XY")
            .rect(outer_width, outer_height)
            .extrude(p.thickness)
        )

        # Cut out inner cavity
        frame = (
            frame
            .faces(">Z")
            .workplane()
            .rect(inner_width, inner_height)
            .cutThruAll()
        )

        # Create the floating platform
        platform = (
            cq.Workplane("XY")
            .rect(p.platform_width, p.platform_height)
            .extrude(p.thickness)
        )

        # Cut axle hole
        platform = (
            platform
            .faces(">Z")
            .workplane()
            .hole(p.axle_diameter)
        )

        # Create serpentine beams on each side
        # Right side beam (connects platform +X edge to frame +X edge)
        right_start_x = p.platform_width / 2 + p.beam_spacing + p.beam_width / 2
        right_beam = self._create_serpentine_beam(right_start_x, direction=1)

        # Left side beam (connects platform -X edge to frame -X edge)
        left_start_x = -(p.platform_width / 2 + p.beam_spacing + p.beam_width / 2)
        left_beam = self._create_serpentine_beam(left_start_x, direction=-1)

        # Connection from platform to first fold of each beam
        # Right connection
        right_conn_x = (p.platform_width / 2 + right_start_x) / 2
        right_conn = (
            cq.Workplane("XY")
            .center(right_conn_x, 0)
            .rect(p.beam_spacing + p.beam_width, p.beam_width)
            .extrude(p.thickness)
        )

        # Left connection
        left_conn_x = -(p.platform_width / 2 - left_start_x) / 2
        left_conn = (
            cq.Workplane("XY")
            .center(left_conn_x, 0)
            .rect(p.beam_spacing + p.beam_width, p.beam_width)
            .extrude(p.thickness)
        )

        # Connection from last fold to frame
        # Right side - last fold is at:
        last_fold_x_right = right_start_x + (p.num_folds - 1) * fold_pitch
        frame_inner_x = inner_width / 2

        # Connect last fold to frame
        if p.num_folds % 2 == 1:
            # Last fold ends at top
            conn_y = p.segment_length / 2 - p.beam_width / 2
        else:
            # Last fold ends at bottom
            conn_y = -p.segment_length / 2 + p.beam_width / 2

        right_frame_conn_x = (last_fold_x_right + frame_inner_x) / 2
        right_frame_conn_width = frame_inner_x - last_fold_x_right + p.beam_width
        right_frame_conn = (
            cq.Workplane("XY")
            .center(right_frame_conn_x, conn_y)
            .rect(right_frame_conn_width, p.beam_width)
            .extrude(p.thickness)
        )

        # Left side frame connection
        last_fold_x_left = left_start_x - (p.num_folds - 1) * fold_pitch
        left_frame_conn_x = (last_fold_x_left + (-frame_inner_x)) / 2
        left_frame_conn_width = abs(-frame_inner_x - last_fold_x_left) + p.beam_width
        left_frame_conn = (
            cq.Workplane("XY")
            .center(left_frame_conn_x, conn_y)
            .rect(left_frame_conn_width, p.beam_width)
            .extrude(p.thickness)
        )

        # Union all parts
        result = frame.union(platform)
        result = result.union(right_beam).union(left_beam)
        result = result.union(right_conn).union(left_conn)
        result = result.union(right_frame_conn).union(left_frame_conn)

        # Add mounting holes if requested
        if p.include_mounting_holes:
            hole_x = outer_width / 2 - p.frame_thickness / 2
            hole_y = outer_height / 2 - p.frame_thickness / 2

            hole_positions = [
                (hole_x, hole_y),
                (-hole_x, hole_y),
                (hole_x, -hole_y),
                (-hole_x, -hole_y),
            ]

            for hx, hy in hole_positions:
                result = (
                    result
                    .faces(">Z")
                    .workplane()
                    .center(hx, hy)
                    .hole(p.mounting_hole_diameter)
                )

        return result

    def get_effective_beam_length(self) -> float:
        """Calculate the effective beam length of the serpentine path."""
        p = self.params

        # Each side has:
        # - num_folds vertical segments of length segment_length
        # - (num_folds - 1) horizontal connectors of length fold_pitch
        fold_pitch = p.beam_width + p.beam_spacing

        vertical_length = p.num_folds * p.segment_length
        horizontal_length = (p.num_folds - 1) * fold_pitch

        # Total for one side
        one_side = vertical_length + horizontal_length

        # Both sides in parallel, so effective length is one_side
        # (parallel springs: 1/k_total = 1/k1 + 1/k2, but same length so k_total = 2*k)
        return one_side

    def get_stiffness_estimate(self, elastic_modulus: float = 2000.0) -> float:
        """Estimate Y-axis stiffness.

        Args:
            elastic_modulus: Material elastic modulus in MPa

        Returns:
            Estimated stiffness in N/mm
        """
        p = self.params

        # Effective beam length from serpentine path
        L = self.get_effective_beam_length()
        w = p.beam_width
        t = p.thickness

        # Two serpentine beams in parallel
        # Simplified cantilever model: k = E * w * t^3 / L^3
        k = 2 * elastic_modulus * w * (t ** 3) / (L ** 3)

        return k

    def get_max_deflection_estimate(self, yield_strength: float = 50.0) -> float:
        """Estimate maximum safe deflection.

        Args:
            yield_strength: Material yield strength in MPa

        Returns:
            Estimated max deflection in mm
        """
        p = self.params

        L = self.get_effective_beam_length()
        t = p.thickness
        E = 2000.0  # Assume PLA

        # delta_max ≈ sigma_y * L^2 / (6 * E * t)
        delta_max = yield_strength * (L ** 2) / (6 * E * t)

        return delta_max


def generate_test_serpentine():
    """Generate a test serpentine flexure."""
    params = SerpentineFlexureParams(
        axle_diameter=6.0,
        platform_width=14.0,
        platform_height=10.0,
        beam_width=0.8,
        beam_spacing=2.5,
        num_folds=4,
        segment_length=15.0,
        frame_thickness=5.0,
        thickness=5.0,
    )

    gen = SerpentineFlexureGenerator(params)
    flexure = gen.generate()

    # Print estimates
    L_eff = gen.get_effective_beam_length()
    k = gen.get_stiffness_estimate()
    d = gen.get_max_deflection_estimate()

    # Calculate overall size
    fold_pitch = params.beam_width + params.beam_spacing
    serpentine_width = (params.num_folds - 1) * fold_pitch + params.beam_width
    inner_width = params.platform_width + 2 * serpentine_width + 2 * params.beam_spacing
    inner_height = params.segment_length + 2 * params.beam_width
    outer_width = inner_width + 2 * params.frame_thickness
    outer_height = inner_height + 2 * params.frame_thickness

    print(f"Serpentine Flexure:")
    print(f"  Folds per side: {params.num_folds}")
    print(f"  Segment length: {params.segment_length} mm")
    print(f"  Beam width: {params.beam_width} mm")
    print(f"  Effective beam length: {L_eff:.1f} mm")
    print(f"  Overall size: {outer_width:.0f}mm × {outer_height:.0f}mm × {params.thickness}mm")
    print(f"  Estimated stiffness: {k:.2f} N/mm")
    print(f"  Estimated max deflection: {d:.2f} mm")

    return flexure


if __name__ == "__main__":
    flexure = generate_test_serpentine()
    cq.exporters.export(flexure, "serpentine_flexure.step")
    print("\nExported: serpentine_flexure.step")
