"""Upper housing for mux selector - minimal plate design.

Creates plates with holes for the bevel gear axles:
- Driving bevel axle: runs along X-axis at (Y=pivot_y, Z=0)
- Driven bevel axle: runs along Z-axis at (X=clutch_center, Y=pivot_y)

The driving bevel axle uses YZ plates (like lower housing).
The driven bevel axle uses XY plates.
"""

import cadquery as cq
from dataclasses import dataclass


@dataclass
class UpperHousingParams:
    """Parameters for the upper housing plates."""

    # Driving bevel gear position (gear body center, axle runs along X)
    driving_bevel_x: float = 8.0   # clutch_center - bevel_mesh_distance (12-tooth)
    driving_bevel_y: float = 34.2  # pivot_y
    driving_bevel_z: float = 0.0

    # Driven bevel gear position (gear body center, axle runs along Z)
    driven_bevel_x: float = 18.0   # clutch_center
    driven_bevel_y: float = 34.2   # pivot_y
    driven_bevel_z: float = -10.0  # -bevel_mesh_distance (12-tooth)

    # Bevel gear clearance (distance from gear body to plate)
    bevel_gear_radius: float = 10.0  # Approximate gear body radius (for 12-tooth bevel)
    gear_clearance: float = 2.0      # Extra clearance from gear body

    # Axle dimensions
    axle_diameter: float = 6.0
    axle_clearance: float = 0.2  # Clearance for rotation (per side)

    # Plate dimensions
    plate_thickness: float = 6.0
    plate_size: float = 14.0  # Width/height of plates around holes

    # Optional explicit plate positions (if None, calculated from gear positions)
    _driving_left_plate_x: float = None
    _driving_right_plate_x: float = None
    _driven_front_plate_z: float = None
    _driven_back_plate_z: float = None

    @property
    def driving_left_plate_x(self) -> float:
        """X position for left driving bevel plate (away from gear)."""
        if self._driving_left_plate_x is not None:
            return self._driving_left_plate_x
        return self.driving_bevel_x - self.bevel_gear_radius - self.gear_clearance - 5

    @property
    def driving_right_plate_x(self) -> float:
        """X position for right driving bevel plate (away from gear)."""
        if self._driving_right_plate_x is not None:
            return self._driving_right_plate_x
        return self.driving_bevel_x + self.bevel_gear_radius + self.gear_clearance + 3

    @property
    def driven_front_plate_z(self) -> float:
        """Z position for front driven bevel plate (away from gear)."""
        if self._driven_front_plate_z is not None:
            return self._driven_front_plate_z
        return self.driven_bevel_z - self.bevel_gear_radius - self.gear_clearance - 5

    @property
    def driven_back_plate_z(self) -> float:
        """Z position for back driven bevel plate (away from gear)."""
        if self._driven_back_plate_z is not None:
            return self._driven_back_plate_z
        return self.driven_bevel_z + self.bevel_gear_radius + self.gear_clearance + 3


class UpperHousingGenerator:
    """Generator for upper housing plates."""

    def __init__(self, params: UpperHousingParams = None):
        self.params = params or UpperHousingParams()

    def generate_driving_plate(self, plate_x: float) -> cq.Workplane:
        """Generate a YZ plate for the driving bevel axle at given X position."""
        p = self.params
        hole_diameter = p.axle_diameter + p.axle_clearance * 2

        # Create plate in YZ plane
        plate = (
            cq.Workplane('YZ')
            .center(p.driving_bevel_y, p.driving_bevel_z)
            .rect(p.plate_size, p.plate_size)
            .extrude(p.plate_thickness)
            .translate((plate_x - p.plate_thickness / 2, 0, 0))
        )

        # Cut hole for axle
        plate = (
            plate
            .faces(">X")
            .workplane()
            .hole(hole_diameter)
        )

        return plate

    def generate_driving_left_plate(self) -> cq.Workplane:
        """Generate the left plate for driving bevel axle."""
        return self.generate_driving_plate(self.params.driving_left_plate_x)

    def generate_driving_right_plate(self) -> cq.Workplane:
        """Generate the right plate for driving bevel axle."""
        return self.generate_driving_plate(self.params.driving_right_plate_x)

    def generate_driven_plate(self, plate_z: float) -> cq.Workplane:
        """Generate an XY plate for the driven bevel axle at given Z position."""
        p = self.params
        hole_diameter = p.axle_diameter + p.axle_clearance * 2

        # Create plate in XY plane
        plate = (
            cq.Workplane('XY')
            .center(p.driven_bevel_x, p.driven_bevel_y)
            .rect(p.plate_size, p.plate_size)
            .extrude(p.plate_thickness)
            .translate((0, 0, plate_z - p.plate_thickness / 2))
        )

        # Cut hole for axle
        plate = (
            plate
            .faces(">Z")
            .workplane()
            .hole(hole_diameter)
        )

        return plate

    def generate_driven_front_plate(self) -> cq.Workplane:
        """Generate the front plate for driven bevel axle."""
        return self.generate_driven_plate(self.params.driven_front_plate_z)

    def generate_driven_back_plate(self) -> cq.Workplane:
        """Generate the back plate for driven bevel axle."""
        return self.generate_driven_plate(self.params.driven_back_plate_z)

    def generate(self, cantilevered: bool = True) -> cq.Workplane:
        """Generate upper housing plates as a single solid.

        Args:
            cantilevered: If True (default), only generate outer plates to avoid
                         axle intersection at the lever pivot. If False, generate
                         all 4 plates (may cause axle intersection issues).
        """
        driving_left = self.generate_driving_left_plate()
        driven_front = self.generate_driven_front_plate()

        result = driving_left.union(driven_front)

        if not cantilevered:
            # Add inner plates (warning: axles will intersect if both extend fully)
            driving_right = self.generate_driving_right_plate()
            driven_back = self.generate_driven_back_plate()
            result = result.union(driving_right)
            result = result.union(driven_back)

        return result

    def get_plate_positions(self) -> dict:
        """Return the plate positions for reference."""
        p = self.params
        return {
            'driving_bevel_y': p.driving_bevel_y,
            'driving_bevel_z': p.driving_bevel_z,
            'driven_bevel_x': p.driven_bevel_x,
            'driven_bevel_y': p.driven_bevel_y,
            'driving_left_plate_x': p.driving_left_plate_x,
            'driving_right_plate_x': p.driving_right_plate_x,
            'driven_front_plate_z': p.driven_front_plate_z,
            'driven_back_plate_z': p.driven_back_plate_z,
            'hole_diameter': p.axle_diameter + p.axle_clearance * 2,
        }


def main():
    """Generate and export the upper housing."""
    params = UpperHousingParams()
    gen = UpperHousingGenerator(params)

    housing = gen.generate()
    info = gen.get_plate_positions()

    print("Upper Housing Plates:")
    print(f"  Driving bevel axle at Y={info['driving_bevel_y']}, Z={info['driving_bevel_z']}")
    print(f"    Left plate X: {info['driving_left_plate_x']} mm")
    print(f"    Right plate X: {info['driving_right_plate_x']} mm")
    print()
    print(f"  Driven bevel axle at X={info['driven_bevel_x']}, Y={info['driven_bevel_y']}")
    print(f"    Front plate Z: {info['driven_front_plate_z']} mm")
    print(f"    Back plate Z: {info['driven_back_plate_z']} mm")
    print()
    print(f"  Hole diameter: {info['hole_diameter']} mm")

    cq.exporters.export(housing, "upper_housing.step")
    print("\nExported: upper_housing.step")


if __name__ == "__main__":
    main()
