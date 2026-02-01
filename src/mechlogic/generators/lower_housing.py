"""Lower housing for mux selector - minimal plate design.

Creates two vertical plates (YZ planes) with holes for:
- Selector axle (Y=0, Z=0)
- Input A axle (Y=0, Z=+36)
- Input B axle (Y=0, Z=-36)

All three axles run along the X-axis.
"""

import cadquery as cq
from dataclasses import dataclass


@dataclass
class LowerHousingParams:
    """Parameters for the lower housing plates."""

    # Axle positions (Y, Z coordinates - all axles along X)
    selector_axle_y: float = 0.0
    selector_axle_z: float = 0.0

    input_a_y: float = 0.0
    input_a_z: float = 36.0  # Above selector

    input_b_y: float = 0.0
    input_b_z: float = -36.0  # Below selector

    # Axle dimensions
    axle_diameter: float = 6.0
    axle_clearance: float = 0.2  # Clearance for rotation (per side)

    # Plate dimensions
    plate_thickness: float = 8.0  # X dimension of each plate
    plate_height: float = 20.0  # Y dimension (centered on axles)
    plate_margin: float = 15.0  # Extra material around outermost holes in Z

    # Plate X positions (where the plates are located along X)
    left_plate_x: float = -20.0  # Left plate center X
    right_plate_x: float = 40.0  # Right plate center X


class LowerHousingGenerator:
    """Generator for lower housing plates."""

    def __init__(self, params: LowerHousingParams = None):
        self.params = params or LowerHousingParams()

    def _get_axle_positions(self) -> list:
        """Return list of (y, z) positions for all axles."""
        p = self.params
        return [
            (p.selector_axle_y, p.selector_axle_z),
            (p.input_a_y, p.input_a_z),
            (p.input_b_y, p.input_b_z),
        ]

    def _calculate_plate_z_extent(self) -> tuple:
        """Calculate the Z extent needed to cover all axle holes."""
        p = self.params
        axle_positions = self._get_axle_positions()

        z_coords = [z for (y, z) in axle_positions]
        z_min = min(z_coords) - p.plate_margin
        z_max = max(z_coords) + p.plate_margin

        return z_min, z_max

    def generate_plate(self, plate_x: float) -> cq.Workplane:
        """Generate a single plate at the given X position.

        The plate is in the YZ plane, with thickness in X.
        """
        p = self.params
        z_min, z_max = self._calculate_plate_z_extent()

        plate_depth = z_max - z_min  # Z dimension
        plate_center_z = (z_min + z_max) / 2

        # Create the plate
        plate = (
            cq.Workplane('YZ')
            .center(0, plate_center_z)
            .rect(p.plate_height, plate_depth)
            .extrude(p.plate_thickness)
            .translate((plate_x - p.plate_thickness / 2, 0, 0))
        )

        # Cut holes for each axle - use pushPoints to cut all at once
        # This avoids face selection issues after cutting the first hole
        hole_diameter = p.axle_diameter + p.axle_clearance * 2
        axle_positions = self._get_axle_positions()

        # Calculate hole positions relative to plate center
        # On the >X face, local coords are (Y, Z-plate_center_z)
        hole_points = [(ay, az - plate_center_z) for ay, az in axle_positions]

        plate = (
            plate
            .faces(">X")
            .workplane()
            .pushPoints(hole_points)
            .hole(hole_diameter)
        )

        return plate

    def generate_left_plate(self) -> cq.Workplane:
        """Generate the left plate."""
        return self.generate_plate(self.params.left_plate_x)

    def generate_right_plate(self) -> cq.Workplane:
        """Generate the right plate."""
        return self.generate_plate(self.params.right_plate_x)

    def generate(self) -> cq.Workplane:
        """Generate both plates as a single solid."""
        left = self.generate_left_plate()
        right = self.generate_right_plate()
        return left.union(right)

    def get_plate_positions(self) -> dict:
        """Return the plate positions for reference."""
        p = self.params
        z_min, z_max = self._calculate_plate_z_extent()

        return {
            'left_plate_x': p.left_plate_x,
            'right_plate_x': p.right_plate_x,
            'plate_thickness': p.plate_thickness,
            'plate_height': p.plate_height,
            'z_min': z_min,
            'z_max': z_max,
            'axle_positions': self._get_axle_positions(),
            'hole_diameter': p.axle_diameter + p.axle_clearance * 2,
        }


def main():
    """Generate and export the lower housing."""
    params = LowerHousingParams()
    gen = LowerHousingGenerator(params)

    housing = gen.generate()
    info = gen.get_plate_positions()

    print("Lower Housing Plates:")
    print(f"  Left plate X: {info['left_plate_x']} mm")
    print(f"  Right plate X: {info['right_plate_x']} mm")
    print(f"  Plate thickness: {info['plate_thickness']} mm")
    print(f"  Plate height (Y): {info['plate_height']} mm")
    print(f"  Plate Z extent: {info['z_min']:.1f} to {info['z_max']:.1f} mm")
    print(f"  Hole diameter: {info['hole_diameter']} mm")
    print()
    print("  Axle holes at (Y, Z):")
    for y, z in info['axle_positions']:
        print(f"    ({y}, {z})")

    cq.exporters.export(housing, "lower_housing.step")
    print("\nExported: lower_housing.step")


if __name__ == "__main__":
    main()
