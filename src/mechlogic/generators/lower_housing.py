"""Lower housing for mux selector - enclosure design.

Creates a rectangular enclosure with:
- Left and right plates (YZ planes) with holes for axles
- Front and back walls (XY planes) to complete the enclosure

Axle holes:
- Selector axle (Y=0, Z=0)
- Input A axle (Y=0, Z=+36)
- Input B axle (Y=0, Z=-36)

All three axles run along the X-axis.
"""

from typing import Optional
import cadquery as cq
from dataclasses import dataclass

from ..models.spec import LogicElementSpec
from .layout import LayoutCalculator, SplitSnapParams


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
    axle_clearance: float = 0.3  # Clearance for rotation (per side)

    # Bearing pocket for selector axle (recessed mount)
    # The selector axle terminates inside the housing, supported by bearing pockets
    selector_bearing_pocket_depth: float = 5.0  # How deep the pocket goes into the wall
    selector_bearing_pocket_clearance: float = 0.3  # Extra clearance for bearing fit

    # Plate dimensions
    plate_thickness: float = 8.0  # X dimension of each plate
    plate_y_min: float = -18.0  # Bottom Y of plates (for stackability)
    plate_y_max: float = 10.0   # Top Y of plates
    plate_margin: float = 15.0  # Extra material around outermost holes in Z

    # Plate X positions (where the plates are located along X)
    left_plate_x: float = -20.0  # Left plate center X
    right_plate_x: float = 40.0  # Right plate center X

    # Connection bolt positions for joining to upper housing
    # [(x, z)] bolt centers; populated by from_spec()
    connection_bolt_positions: list = None
    connection_bolt_diameter: float = 3.2   # M3 clearance
    connection_flange_depth: float = 15.0   # Z extent of flange tabs
    connection_flange_height: float = 8.0   # Y extent of flange tabs

    @property
    def plate_height(self) -> float:
        """Calculate plate height from Y bounds."""
        return self.plate_y_max - self.plate_y_min

    @classmethod
    def from_spec(cls, spec: LogicElementSpec) -> "LowerHousingParams":
        """Create housing params from a spec.

        Derives plate positions from device_length_x and other values from spec.
        The plate Y extent is set for stackability:
        - Bottom at -spur_gear_radius (so stacked units can mesh via spur gears)
        - Top at +spur_gear_radius/2 (leaves room for mechanism)

        The selector axle uses bearing pockets (recessed mounts) instead of
        through-holes, freeing up the external space for linking gears.
        """
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)
        mux_layout = LayoutCalculator.calculate_mux_layout(spec)
        spur_gear_radius = LayoutCalculator.calculate_spur_gear_radius(spec)

        # Calculate plate margin to clear input gears
        # Gears extend radially from their axle position
        gear_od = spec.gears.module * spec.gears.coaxial_teeth + 2 * spec.gears.module
        gear_radius = gear_od / 2
        gear_clearance = 5.0  # Clearance between gear and wall
        plate_margin = gear_radius + gear_clearance

        # Plate Y bounds for stackability
        # Bottom: spur_gear_radius below selector axle (Y=0)
        # Top: some margin above selector axle
        plate_y_min = -spur_gear_radius
        plate_y_max = spur_gear_radius / 2  # Leaves room for shift lever

        # Bearing pocket depth - axle sits inside this pocket
        # Should be deep enough for secure support but not go through the wall
        bearing_pocket_depth = min(5.0, housing_layout.plate_thickness - 2.0)

        # Connection bolt layout for joining to upper housing
        conn = LayoutCalculator.calculate_connection_layout(spec)

        return cls(
            selector_axle_y=0.0,
            selector_axle_z=0.0,
            input_a_y=0.0,
            input_a_z=mux_layout.input_a_z,
            input_b_y=0.0,
            input_b_z=mux_layout.input_b_z,
            axle_diameter=spec.primary_shaft_diameter,
            axle_clearance=spec.tolerances.shaft_clearance,
            selector_bearing_pocket_depth=bearing_pocket_depth,
            selector_bearing_pocket_clearance=spec.tolerances.shaft_clearance,
            plate_thickness=max(housing_layout.plate_thickness, 6.0),
            plate_y_min=plate_y_min,
            plate_y_max=plate_y_max,
            plate_margin=plate_margin,
            left_plate_x=housing_layout.left_plate_x,
            right_plate_x=housing_layout.right_plate_x,
            connection_bolt_positions=conn.bolt_positions,
            connection_bolt_diameter=conn.bolt_diameter,
            connection_flange_depth=conn.flange_depth,
            connection_flange_height=conn.flange_height,
        )


class LowerHousingGenerator:
    """Generator for lower housing plates."""

    def __init__(self, params: Optional[LowerHousingParams] = None, spec: Optional[LogicElementSpec] = None):
        """Initialize the housing generator.

        Args:
            params: Direct housing parameters (takes precedence if provided).
            spec: Logic element spec to derive parameters from.
        """
        if params is not None:
            self.params = params
        elif spec is not None:
            self.params = LowerHousingParams.from_spec(spec)
        else:
            self.params = LowerHousingParams()

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

    def generate_plate(self, plate_x: float, is_left_plate: bool = True) -> cq.Workplane:
        """Generate a single plate at the given X position.

        The plate is in the YZ plane, with thickness in X.
        Input axles get through-holes.
        Selector axle: left plate gets bearing pocket, right plate gets through-hole
        (for axle insertion from the side opposite the flexure).

        Args:
            plate_x: X position of the plate center.
            is_left_plate: True for left plate, False for right plate.
                          Left plate has bearing pocket, right plate has through-hole.
        """
        p = self.params
        z_min, z_max = self._calculate_plate_z_extent()

        plate_depth = z_max - z_min  # Z dimension
        plate_center_z = (z_min + z_max) / 2

        # Y bounds from params (for stackability)
        plate_center_y = (p.plate_y_min + p.plate_y_max) / 2
        plate_height = p.plate_y_max - p.plate_y_min

        # Create the plate
        plate = (
            cq.Workplane('YZ')
            .center(plate_center_y, plate_center_z)
            .rect(plate_height, plate_depth)
            .extrude(p.plate_thickness)
            .translate((plate_x - p.plate_thickness / 2, 0, 0))
        )

        # Input axles get through-holes
        input_hole_diameter = p.axle_diameter + p.axle_clearance * 2
        input_positions = [
            (p.input_a_y, p.input_a_z),
            (p.input_b_y, p.input_b_z),
        ]
        input_hole_points = [(ay - plate_center_y, az - plate_center_z) for ay, az in input_positions]

        plate = (
            plate
            .faces(">X")
            .workplane()
            .pushPoints(input_hole_points)
            .hole(input_hole_diameter)
        )

        # Selector axle handling:
        # - Left plate (flexure side): bearing pocket for secure mounting
        # - Right plate: through-hole for axle insertion
        selector_hole_diameter = p.axle_diameter + p.selector_bearing_pocket_clearance * 2
        selector_y = p.selector_axle_y
        selector_z = p.selector_axle_z

        # Both plates: through-hole for selector axle
        # (C-clips now provide axial retention, so bearing pockets are unnecessary)
        selector_hole_point = [(selector_y - plate_center_y, selector_z - plate_center_z)]
        plate = (
            plate
            .faces(">X")
            .workplane()
            .pushPoints(selector_hole_point)
            .hole(selector_hole_diameter)
        )

        # Add connection flange tabs for bolting to upper housing
        if p.connection_bolt_positions:
            overlap = 1.0  # Overlap into plate to ensure solid union
            for bx, bz in p.connection_bolt_positions:
                if abs(bx - plate_x) > 0.1:
                    continue  # Only add flanges for this plate's X position

                # Tab extends upward from plate top, outward in Z
                tab = (
                    cq.Workplane('XY')
                    .box(p.plate_thickness,
                         p.connection_flange_height + overlap,
                         p.connection_flange_depth, centered=False)
                    .translate((
                        bx - p.plate_thickness / 2,
                        p.plate_y_max - overlap,
                        bz - p.connection_flange_depth / 2,
                    ))
                )
                plate = plate.union(tab)

                # M3 through-hole (Y-axis) from top of tab through the plate
                hole_height = (p.plate_y_max + p.connection_flange_height
                               - p.plate_y_min + 2)
                bolt_hole = (
                    cq.Workplane('XY')
                    .circle(p.connection_bolt_diameter / 2)
                    .extrude(hole_height)
                    .rotate((0, 0, 0), (1, 0, 0), -90)
                    .translate((bx, p.plate_y_min - 1, bz))
                )
                plate = plate.cut(bolt_hole)

        return plate

    def generate_left_plate(self) -> cq.Workplane:
        """Generate the left plate."""
        return self.generate_plate(self.params.left_plate_x, is_left_plate=True)

    def generate_right_plate(self) -> cq.Workplane:
        """Generate the right plate."""
        return self.generate_plate(self.params.right_plate_x, is_left_plate=False)

    def generate_front_wall(self) -> cq.Workplane:
        """Generate the front wall (XY plane at Z_min).

        The front wall spans from left plate to right plate in X,
        and has the same height as the side plates in Y.
        """
        p = self.params
        z_min, z_max = self._calculate_plate_z_extent()

        # Wall dimensions
        # X: from left plate left face to right plate right face
        x_min = p.left_plate_x - p.plate_thickness / 2
        x_max = p.right_plate_x + p.plate_thickness / 2
        width = x_max - x_min
        center_x = (x_min + x_max) / 2

        # Y: same bounds as side plates
        height = p.plate_y_max - p.plate_y_min
        center_y = (p.plate_y_min + p.plate_y_max) / 2

        # Z: wall centered on z_min
        wall_z = z_min

        wall = (
            cq.Workplane('XY')
            .center(center_x, center_y)
            .rect(width, height)
            .extrude(p.plate_thickness)
            .translate((0, 0, wall_z - p.plate_thickness / 2))
        )

        return wall

    def generate_back_wall(self) -> cq.Workplane:
        """Generate the back wall (XY plane at Z_max).

        The back wall spans from left plate to right plate in X,
        and has the same height as the side plates in Y.
        """
        p = self.params
        z_min, z_max = self._calculate_plate_z_extent()

        # Wall dimensions
        # X: from left plate left face to right plate right face
        x_min = p.left_plate_x - p.plate_thickness / 2
        x_max = p.right_plate_x + p.plate_thickness / 2
        width = x_max - x_min
        center_x = (x_min + x_max) / 2

        # Y: same bounds as side plates
        height = p.plate_y_max - p.plate_y_min
        center_y = (p.plate_y_min + p.plate_y_max) / 2

        # Z: wall centered on z_max
        wall_z = z_max

        wall = (
            cq.Workplane('XY')
            .center(center_x, center_y)
            .rect(width, height)
            .extrude(p.plate_thickness)
            .translate((0, 0, wall_z - p.plate_thickness / 2))
        )

        return wall

    def generate(self) -> tuple[cq.Workplane, cq.Workplane]:
        """Generate the complete lower housing enclosure.

        Returns:
            Tuple of (left_right_plates, front_back_walls) for separate coloring.
        """
        # Side plates (with axle holes)
        left = self.generate_left_plate()
        right = self.generate_right_plate()
        side_plates = left.union(right)

        # Front and back walls (no holes)
        front = self.generate_front_wall()
        back = self.generate_back_wall()
        front_back_walls = front.union(back)

        return side_plates, front_back_walls

    def get_plate_positions(self) -> dict:
        """Return the plate and wall positions for reference."""
        p = self.params
        z_min, z_max = self._calculate_plate_z_extent()

        # Calculate selector axle extent (terminates inside bearing pockets)
        left_inner_face = p.left_plate_x + p.plate_thickness / 2
        right_inner_face = p.right_plate_x - p.plate_thickness / 2
        selector_axle_start = left_inner_face - p.selector_bearing_pocket_depth
        selector_axle_end = right_inner_face + p.selector_bearing_pocket_depth

        return {
            'left_plate_x': p.left_plate_x,
            'right_plate_x': p.right_plate_x,
            'front_wall_z': z_min,
            'back_wall_z': z_max,
            'plate_thickness': p.plate_thickness,
            'plate_height': p.plate_height,
            'plate_y_min': p.plate_y_min,
            'plate_y_max': p.plate_y_max,
            'z_min': z_min,
            'z_max': z_max,
            'axle_positions': self._get_axle_positions(),
            'hole_diameter': p.axle_diameter + p.axle_clearance * 2,
            # Selector axle bearing pocket info
            'selector_bearing_pocket_depth': p.selector_bearing_pocket_depth,
            'selector_axle_start': selector_axle_start,
            'selector_axle_end': selector_axle_end,
            'selector_axle_y': p.selector_axle_y,
            'selector_axle_z': p.selector_axle_z,
        }


    def generate_split(
        self,
        split_x: Optional[float] = None,
        snap: Optional[SplitSnapParams] = None,
    ) -> tuple[cq.Workplane, cq.Workplane]:
        """Generate lower housing split into left and right halves.

        Generates the full housing, cuts it at split_x, then adds
        tongue-and-groove snap features to the cut faces.

        Args:
            split_x: X coordinate of the split plane. Defaults to midpoint.
            snap: Snap feature parameters. Defaults to SplitSnapParams().

        Returns:
            Tuple of (left_half, right_half).
        """
        if split_x is None:
            split_x = (self.params.left_plate_x + self.params.right_plate_x) / 2
        if snap is None:
            snap = SplitSnapParams()

        # Generate full housing as single solid
        side_plates, front_back_walls = self.generate()
        housing = side_plates.union(front_back_walls)

        # Cut into halves
        left_half = self._cut_half(housing, split_x, keep_left=True)
        right_half = self._cut_half(housing, split_x, keep_left=False)

        # Add snap features to the front and back wall cut faces
        p = self.params
        z_min, z_max = self._calculate_plate_z_extent()
        wall_locations_z = [z_min, z_max]  # Front and back wall centers

        # Use actual wall Y bounds (not bounding box which includes flanges)
        left_half = self._add_snap_tongues(
            left_half, split_x, wall_locations_z, snap, p.plate_thickness,
            snap.tongue_width_lower,
            wall_y_min=p.plate_y_min, wall_y_max=p.plate_y_max,
        )
        right_half = self._add_snap_grooves(
            right_half, split_x, wall_locations_z, snap, p.plate_thickness,
            snap.tongue_width_lower,
            wall_y_min=p.plate_y_min, wall_y_max=p.plate_y_max,
        )

        return left_half, right_half

    @staticmethod
    def _cut_half(
        housing: cq.Workplane, split_x: float, keep_left: bool,
    ) -> cq.Workplane:
        """Cut housing at split_x, keeping left or right half.

        Uses a large box to intersect with the desired half-space.
        """
        bb = housing.val().BoundingBox()
        box_size = 500  # Large enough to cover any housing

        if keep_left:
            # Keep everything with X < split_x
            cutter = (
                cq.Workplane('XY')
                .box(box_size, box_size, box_size, centered=False)
                .translate((split_x - box_size, bb.ymin - 100, bb.zmin - 100))
            )
        else:
            # Keep everything with X > split_x
            cutter = (
                cq.Workplane('XY')
                .box(box_size, box_size, box_size, centered=False)
                .translate((split_x, bb.ymin - 100, bb.zmin - 100))
            )
        return housing.intersect(cutter)

    @staticmethod
    def _add_snap_tongues(
        half: cq.Workplane,
        split_x: float,
        wall_z_positions: list[float],
        snap: SplitSnapParams,
        wall_thickness: float,
        tongue_width: float,
        wall_y_min: float = None,
        wall_y_max: float = None,
    ) -> cq.Workplane:
        """Add tongue protrusions to the left half at each wall cut face.

        Each tongue runs most of the wall's Y height (minus inset) and
        protrudes in +X from the cut face. A small detent bump sits on
        each Z-face of the tongue for click retention.

        Args:
            wall_y_min: Bottom Y of the walls (not flanges). If None, uses BB.
            wall_y_max: Top Y of the walls (not flanges). If None, uses BB.
        """
        if wall_y_min is None or wall_y_max is None:
            bb = half.val().BoundingBox()
            wall_y_min = wall_y_min if wall_y_min is not None else bb.ymin
            wall_y_max = wall_y_max if wall_y_max is not None else bb.ymax

        y_lo = wall_y_min + snap.wall_inset
        y_hi = wall_y_max - snap.wall_inset
        tongue_height = y_hi - y_lo
        tongue_center_y = (y_lo + y_hi) / 2

        for wz in wall_z_positions:
            # Tongue: centered on wall Z, runs tongue_height in Y, protrudes in +X
            tongue = (
                cq.Workplane('XY')
                .box(snap.tongue_protrusion, tongue_height, tongue_width,
                     centered=False)
                .translate((split_x, y_lo, wz - tongue_width / 2))
            )
            half = half.union(tongue)

            # Detent bumps on front (+Z) and back (-Z) faces of tongue
            bump_x = split_x + snap.tongue_protrusion / 2
            for z_sign in [-1, 1]:
                bump_z = wz + z_sign * tongue_width / 2
                bump = (
                    cq.Workplane('XY')
                    .sphere(snap.detent_radius)
                    .translate((bump_x, tongue_center_y, bump_z))
                )
                half = half.union(bump)

        return half

    @staticmethod
    def _add_snap_grooves(
        half: cq.Workplane,
        split_x: float,
        wall_z_positions: list[float],
        snap: SplitSnapParams,
        wall_thickness: float,
        tongue_width: float,
        wall_y_min: float = None,
        wall_y_max: float = None,
    ) -> cq.Workplane:
        """Add groove slots to the right half at each wall cut face.

        Each groove matches the tongue with clearance added. A matching
        detent ridge channel is cut for engagement.

        The groove is cut INTO the right half starting at split_x and
        extending in +X by tongue_protrusion, so the left half's tongue
        can slide in from -X.

        Args:
            wall_y_min: Bottom Y of the walls (not flanges). If None, uses BB.
            wall_y_max: Top Y of the walls (not flanges). If None, uses BB.
        """
        if wall_y_min is None or wall_y_max is None:
            bb = half.val().BoundingBox()
            wall_y_min = wall_y_min if wall_y_min is not None else bb.ymin
            wall_y_max = wall_y_max if wall_y_max is not None else bb.ymax

        y_lo = wall_y_min + snap.wall_inset - snap.tongue_clearance
        y_hi = wall_y_max - snap.wall_inset + snap.tongue_clearance
        groove_height = y_hi - y_lo
        groove_center_y = (y_lo + y_hi) / 2

        groove_width = tongue_width + 2 * snap.tongue_clearance

        for wz in wall_z_positions:
            # Groove: cut into right half starting at split_x, extending in +X
            groove = (
                cq.Workplane('XY')
                .box(snap.tongue_protrusion, groove_height, groove_width,
                     centered=False)
                .translate((split_x, y_lo, wz - groove_width / 2))
            )
            half = half.cut(groove)

            # Detent ridge channels — match bump positions on tongue
            bump_x = split_x + snap.tongue_protrusion / 2
            for z_sign in [-1, 1]:
                bump_z = wz + z_sign * tongue_width / 2
                ridge = (
                    cq.Workplane('XY')
                    .sphere(snap.detent_radius + snap.tongue_clearance)
                    .translate((bump_x, groove_center_y, bump_z))
                )
                half = half.cut(ridge)

        return half


def main():
    """Generate and export the lower housing."""
    params = LowerHousingParams()
    gen = LowerHousingGenerator(params)

    side_plates, front_back_walls = gen.generate()
    housing = side_plates.union(front_back_walls)
    info = gen.get_plate_positions()

    print("Lower Housing Enclosure:")
    print(f"  Left plate X: {info['left_plate_x']} mm")
    print(f"  Right plate X: {info['right_plate_x']} mm")
    print(f"  Front wall Z: {info['front_wall_z']:.1f} mm")
    print(f"  Back wall Z: {info['back_wall_z']:.1f} mm")
    print(f"  Plate thickness: {info['plate_thickness']} mm")
    print(f"  Plate height (Y): {info['plate_height']} mm")
    print(f"  Hole diameter: {info['hole_diameter']} mm")
    print()
    print("  Axle holes at (Y, Z):")
    for y, z in info['axle_positions']:
        print(f"    ({y}, {z})")

    cq.exporters.export(housing, "lower_housing.step")
    print("\nExported: lower_housing.step")


if __name__ == "__main__":
    main()
