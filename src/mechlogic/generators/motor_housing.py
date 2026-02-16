"""Two-part motor housing for Type 130 DC motor.

A clamshell enclosure that fully wraps around the motor body.
Split horizontally into upper and lower halves that bolt together.
The D-shaped bore prevents motor rotation. A vertical mounting plate
on the front face (shaft side) provides bolt holes for attachment.

Coordinate system:
- X axis: motor axis (shaft points in -X)
- Y axis: flat sides face +/-Y
- Z axis: vertical (split at Z=0)
"""

import cadquery as cq
from dataclasses import dataclass, field
from typing import Optional

from .motor_mount_params import Motor130Params


@dataclass
class MotorHousingParams:
    """Parameters for two-part motor housing enclosure."""

    motor: Motor130Params = field(default_factory=Motor130Params)

    # Clearances
    bore_clearance: float = 0.3        # Clearance around motor body (per side)
    shaft_clearance: float = 0.3       # Clearance for shaft through-hole
    tab_clearance: float = 0.2         # Clearance around mounting tabs

    # Wall thickness
    wall_thickness: float = 3.5        # Wall thickness around the bore
    front_wall_thickness: float = 3.0  # Front face (shaft side) thickness
    rear_wall_thickness: float = 3.0   # Rear face thickness

    # Flange dimensions (screw flanges on the sides)
    flange_width: float = 10.0         # Width of each flange (extending from body in Y)
    flange_thickness: float = 4.0      # Thickness of flange (in Z)
    screw_diameter: float = 3.2        # M3 clearance hole
    screw_counterbore_diameter: float = 6.0  # M3 SHCS head
    screw_counterbore_depth: float = 3.0
    num_screws_per_side: int = 2       # Screws along each side

    # Front mounting plate (YZ plane, perpendicular to motor axis)
    mount_plate_thickness: float = 4.0        # Thickness along X
    mount_plate_width: float = 50.0           # Width in Y (extends beyond housing)
    mount_plate_height: float = 50.0          # Height in Z (extends beyond housing)
    mount_bolt_diameter: float = 3.2          # M3 clearance holes
    mount_bolt_inset: float = 5.0             # Distance from plate edge to bolt center
    mount_bolt_cols: int = 2                  # Bolt columns (in Y)
    mount_bolt_rows: int = 3                  # Bolt rows (in Z)

    # Wire exit
    wire_slot_width: float = 4.0       # Width of wire exit slot on rear face
    wire_slot_height: float = 3.0      # Height of wire exit slot

    # Tab handling
    include_tab_recesses: bool = True   # Whether to include recesses for motor tabs


class MotorHousingGenerator:
    """Generator for two-part motor housing enclosure."""

    def __init__(self, params: Optional[MotorHousingParams] = None):
        self.params = params or MotorHousingParams()

    def _housing_length(self) -> float:
        """Total housing length along X."""
        p = self.params
        return p.motor.body_length + p.front_wall_thickness + p.rear_wall_thickness

    def _bore_radius(self) -> float:
        return self.params.motor.body_diameter / 2 + self.params.bore_clearance

    def _bore_flat_hw(self) -> float:
        return self.params.motor.flat_width / 2 + self.params.bore_clearance

    def _outer_radius(self) -> float:
        return self._bore_radius() + self.params.wall_thickness

    def _outer_flat_hw(self) -> float:
        return self._bore_flat_hw() + self.params.wall_thickness

    def _create_d_shape(
        self, radius: float, flat_hw: float, length: float, x_offset: float = 0.0
    ) -> cq.Workplane:
        """Create a D-shaped extrusion (circle with Y-clamped flats).

        Args:
            radius: Circle radius
            flat_hw: Half-width of the flat region (Y clamp)
            length: Extrusion length along X
            x_offset: Offset along X axis
        """
        # Start with circle in YZ plane, extrude in +X
        shape = (
            cq.Workplane('YZ')
            .circle(radius)
            .extrude(length)
            .translate((x_offset, 0, 0))
        )

        # Cut +Y beyond flat
        cut_plus_y = (
            cq.Workplane('YZ')
            .center(flat_hw + radius, 0)
            .rect(radius * 2, radius * 2)
            .extrude(length)
            .translate((x_offset, 0, 0))
        )
        # Cut -Y beyond flat
        cut_minus_y = (
            cq.Workplane('YZ')
            .center(-(flat_hw + radius), 0)
            .rect(radius * 2, radius * 2)
            .extrude(length)
            .translate((x_offset, 0, 0))
        )

        return shape.cut(cut_plus_y).cut(cut_minus_y)

    def _create_full_shell(self) -> cq.Workplane:
        """Create the complete housing shell (both halves, before splitting)."""
        p = self.params
        motor = p.motor
        length = self._housing_length()

        # Outer shell
        shell = self._create_d_shape(
            self._outer_radius(), self._outer_flat_hw(), length
        )

        # Cut bore (D-shaped, only motor body length, offset by front wall)
        bore = self._create_d_shape(
            self._bore_radius(), self._bore_flat_hw(),
            motor.body_length, p.front_wall_thickness
        )
        shell = shell.cut(bore)

        # Cut shaft through-hole in front face
        shaft_hole_dia = motor.shaft_diameter + 2 * p.shaft_clearance
        shaft_hole = (
            cq.Workplane('YZ')
            .circle(shaft_hole_dia / 2)
            .extrude(p.front_wall_thickness + 1)
            .translate((-0.5, 0, 0))
        )
        shell = shell.cut(shaft_hole)

        # Cut tab recesses if enabled
        if p.include_tab_recesses:
            shell = self._cut_tab_recesses(shell)

        # Cut wire exit slot in rear face
        wire_slot = (
            cq.Workplane('YZ')
            .rect(p.wire_slot_width, p.wire_slot_height)
            .extrude(p.rear_wall_thickness + 1)
            .translate((length - p.rear_wall_thickness - 0.5, 0, 0))
        )
        shell = shell.cut(wire_slot)

        return shell

    def _cut_tab_recesses(self, shell: cq.Workplane) -> cq.Workplane:
        """Cut recesses for motor mounting tabs into the bore walls."""
        p = self.params
        motor = p.motor

        bore_flat_hw = self._bore_flat_hw()
        tab_w = motor.tab_width + p.tab_clearance * 2
        tab_l = motor.tab_length + p.tab_clearance
        tab_t = motor.tab_thickness + p.tab_clearance * 2

        # Tabs are on the flat sides, at motor mid-length
        tab_x_center = p.front_wall_thickness + motor.body_length / 2

        for y_dir in [-1, 1]:
            tab_y = y_dir * (bore_flat_hw + tab_l / 2)
            tab_recess = (
                cq.Workplane('YZ')
                .center(tab_y, 0)
                .rect(tab_l, tab_w)
                .extrude(tab_t)
                .translate((tab_x_center - tab_t / 2, 0, 0))
            )
            shell = shell.cut(tab_recess)

        return shell

    def _create_flanges(self, z_direction: float) -> cq.Workplane:
        """Create screw flanges at the parting plane.

        Args:
            z_direction: +1 for upper half flanges, -1 for lower half flanges
        """
        p = self.params
        length = self._housing_length()
        outer_flat_hw = self._outer_flat_hw()

        flanges = None

        for y_sign in [-1, 1]:
            # Flange extends from outer wall edge in +/-Y
            flange_y_start = y_sign * outer_flat_hw
            flange_y_center = y_sign * (outer_flat_hw + p.flange_width / 2)

            # Flange is a rectangular block at Z=0
            if z_direction < 0:
                # Lower half: flange extends from Z=0 downward
                flange_z_center = -p.flange_thickness / 2
            else:
                # Upper half: flange extends from Z=0 upward
                flange_z_center = p.flange_thickness / 2

            flange = (
                cq.Workplane('XY')
                .center(length / 2, flange_y_center)
                .rect(length, p.flange_width)
                .extrude(p.flange_thickness)
                .translate((0, 0, flange_z_center - p.flange_thickness / 2))
            )

            if flanges is None:
                flanges = flange
            else:
                flanges = flanges.union(flange)

        return flanges

    def _screw_positions(self) -> list:
        """Calculate screw hole positions as (x, y) tuples."""
        p = self.params
        length = self._housing_length()
        outer_flat_hw = self._outer_flat_hw()

        # Screw X positions: evenly spaced along housing length
        if p.num_screws_per_side == 1:
            x_positions = [length / 2]
        else:
            margin = p.front_wall_thickness + 3.0
            spacing = (length - 2 * margin) / (p.num_screws_per_side - 1)
            x_positions = [margin + i * spacing for i in range(p.num_screws_per_side)]

        # Screw Y positions: centered in each flange
        y_positions = [
            -(outer_flat_hw + p.flange_width / 2),
            +(outer_flat_hw + p.flange_width / 2),
        ]

        positions = []
        for x in x_positions:
            for y in y_positions:
                positions.append((x, y))

        return positions

    def _cut_screw_holes(
        self, part: cq.Workplane, counterbore: bool, z_direction: float
    ) -> cq.Workplane:
        """Cut screw holes into flanges.

        Args:
            part: The half to cut holes into
            counterbore: If True, add counterbore from outside face
            z_direction: +1 for upper half, -1 for lower half
        """
        p = self.params

        for x, y in self._screw_positions():
            # Through-hole
            hole = (
                cq.Workplane('XY')
                .center(x, y)
                .circle(p.screw_diameter / 2)
                .extrude(p.flange_thickness + 1)
                .translate((0, 0, -p.flange_thickness / 2 - 0.5 if z_direction < 0
                           else -0.5))
            )
            part = part.cut(hole)

            # Counterbore (on outside face)
            if counterbore:
                if z_direction > 0:
                    # Upper half: counterbore from top
                    cb_z = p.flange_thickness - p.screw_counterbore_depth
                else:
                    # Lower half: counterbore from bottom
                    cb_z = -p.flange_thickness
                cb = (
                    cq.Workplane('XY')
                    .center(x, y)
                    .circle(p.screw_counterbore_diameter / 2)
                    .extrude(p.screw_counterbore_depth)
                    .translate((0, 0, cb_z))
                )
                part = part.cut(cb)

        return part

    def _create_mount_plate(self) -> cq.Workplane:
        """Create the front mounting plate in the YZ plane.

        The plate is centered on Y=0, Z=0 (motor axis center) and sits
        at the front face of the housing (X=0). It extends in -X direction
        (away from housing, toward the mux).
        """
        p = self.params

        plate = (
            cq.Workplane('YZ')
            .rect(p.mount_plate_width, p.mount_plate_height)
            .extrude(p.mount_plate_thickness)
            .translate((-p.mount_plate_thickness, 0, 0))
        )

        return plate

    def _mount_bolt_positions(self) -> list:
        """Calculate mount plate bolt positions as (y, z) tuples.

        Bolts are arranged in a grid on the mounting plate, but only
        in the region outside the housing body footprint.
        """
        p = self.params
        inset = p.mount_bolt_inset

        # Y positions: evenly spaced across plate width
        if p.mount_bolt_cols == 1:
            y_positions = [0.0]
        else:
            y_min = -p.mount_plate_width / 2 + inset
            y_max = p.mount_plate_width / 2 - inset
            y_spacing = (y_max - y_min) / (p.mount_bolt_cols - 1)
            y_positions = [y_min + i * y_spacing for i in range(p.mount_bolt_cols)]

        # Z positions: evenly spaced across plate height
        if p.mount_bolt_rows == 1:
            z_positions = [0.0]
        else:
            z_min = -p.mount_plate_height / 2 + inset
            z_max = p.mount_plate_height / 2 - inset
            z_spacing = (z_max - z_min) / (p.mount_bolt_rows - 1)
            z_positions = [z_min + i * z_spacing for i in range(p.mount_bolt_rows)]

        # Only include positions outside the housing body envelope
        outer_radius = self._outer_radius()
        outer_flat_hw = self._outer_flat_hw()

        positions = []
        for y in y_positions:
            for z in z_positions:
                # Check if this position is inside the housing cross-section
                # (D-shape: circle clamped by flats)
                inside_circle = (y**2 + z**2) < (outer_radius + 1.0)**2
                inside_flats = abs(y) < (outer_flat_hw + 1.0)
                if inside_circle and inside_flats:
                    continue
                positions.append((y, z))

        return positions

    def _cut_mount_bolt_holes(self, part: cq.Workplane) -> cq.Workplane:
        """Cut through-holes in the mounting plate for bolts."""
        p = self.params

        for y, z in self._mount_bolt_positions():
            hole = (
                cq.Workplane('YZ')
                .center(y, z)
                .circle(p.mount_bolt_diameter / 2)
                .extrude(p.mount_plate_thickness + 1)
                .translate((-p.mount_plate_thickness - 0.5, 0, 0))
            )
            part = part.cut(hole)

        return part

    def generate_lower(self) -> cq.Workplane:
        """Generate the lower half of the motor housing."""
        p = self.params
        outer_radius = self._outer_radius()
        length = self._housing_length()
        outer_flat_hw = self._outer_flat_hw()

        # Start with full shell
        shell = self._create_full_shell()

        # Add flanges extending downward from Z=0
        flanges = self._create_flanges(z_direction=-1)
        shell = shell.union(flanges)

        # Add front mounting plate
        mount_plate = self._create_mount_plate()
        shell = shell.union(mount_plate)

        # Cut away everything above Z=0 (keep lower half)
        # Must cover the full extent including mounting plate
        max_extent_y = max(outer_flat_hw + p.flange_width, p.mount_plate_width / 2) + 5
        max_extent_x = p.mount_plate_thickness + 5
        cut_block = (
            cq.Workplane('XY')
            .center(length / 2 - max_extent_x / 2, 0)
            .rect(length + max_extent_x * 2, max_extent_y * 2)
            .extrude(max(outer_radius, p.mount_plate_height / 2) + 10)
            .translate((-max_extent_x, 0, 0))
        )
        lower = shell.cut(cut_block)

        # Cut screw holes (through-holes, no counterbore)
        lower = self._cut_screw_holes(lower, counterbore=False, z_direction=-1)

        # Cut shaft through-hole in mounting plate
        shaft_hole_dia = p.motor.shaft_diameter + 2 * p.shaft_clearance
        shaft_plate_hole = (
            cq.Workplane('YZ')
            .circle(shaft_hole_dia / 2)
            .extrude(p.mount_plate_thickness + 1)
            .translate((-p.mount_plate_thickness - 0.5, 0, 0))
        )
        lower = lower.cut(shaft_plate_hole)

        # Cut mount bolt holes (only those in the lower half, Z < 0)
        lower = self._cut_mount_bolt_holes(lower)

        return lower

    def generate_upper(self) -> cq.Workplane:
        """Generate the upper half of the motor housing."""
        p = self.params
        outer_radius = self._outer_radius()
        length = self._housing_length()
        outer_flat_hw = self._outer_flat_hw()

        # Start with full shell
        shell = self._create_full_shell()

        # Add flanges extending upward from Z=0
        flanges = self._create_flanges(z_direction=+1)
        shell = shell.union(flanges)

        # Add front mounting plate
        mount_plate = self._create_mount_plate()
        shell = shell.union(mount_plate)

        # Cut away everything below Z=0 (keep upper half)
        max_extent_y = max(outer_flat_hw + p.flange_width, p.mount_plate_width / 2) + 5
        max_extent_x = p.mount_plate_thickness + 5
        cut_block = (
            cq.Workplane('XY')
            .center(length / 2 - max_extent_x / 2, 0)
            .rect(length + max_extent_x * 2, max_extent_y * 2)
            .extrude(max(outer_radius, p.mount_plate_height / 2) + 10)
            .translate((-max_extent_x, 0, -(max(outer_radius, p.mount_plate_height / 2) + 10)))
        )
        upper = shell.cut(cut_block)

        # Cut screw holes (with counterbore from top)
        upper = self._cut_screw_holes(upper, counterbore=True, z_direction=+1)

        # Cut shaft through-hole in mounting plate
        shaft_hole_dia = p.motor.shaft_diameter + 2 * p.shaft_clearance
        shaft_plate_hole = (
            cq.Workplane('YZ')
            .circle(shaft_hole_dia / 2)
            .extrude(p.mount_plate_thickness + 1)
            .translate((-p.mount_plate_thickness - 0.5, 0, 0))
        )
        upper = upper.cut(shaft_plate_hole)

        # Cut mount bolt holes (only those in the upper half, Z > 0)
        upper = self._cut_mount_bolt_holes(upper)

        return upper

    def generate(self) -> cq.Assembly:
        """Generate both halves as a CadQuery Assembly.

        Returns:
            CadQuery Assembly with motor_housing_lower and motor_housing_upper.
        """
        lower = self.generate_lower()
        upper = self.generate_upper()

        assy = cq.Assembly()
        assy.add(lower, name="motor_housing_lower", color=cq.Color(0.5, 0.5, 0.5))
        assy.add(upper, name="motor_housing_upper", color=cq.Color(0.7, 0.7, 0.7))
        return assy

    def get_dimensions(self) -> dict:
        """Get housing dimensions for reference."""
        p = self.params
        length = self._housing_length()

        return {
            'bore_diameter': self._bore_radius() * 2,
            'bore_flat_width': self._bore_flat_hw() * 2,
            'outer_diameter': self._outer_radius() * 2,
            'outer_flat_width': self._outer_flat_hw() * 2,
            'housing_length': length,
            'wall_thickness': p.wall_thickness,
            'flange_width': p.flange_width,
            'total_width': self._outer_flat_hw() * 2 + p.flange_width * 2,
            'total_height': self._outer_radius() * 2,
            'num_screws': p.num_screws_per_side * 2,
            'mount_plate_width': p.mount_plate_width,
            'mount_plate_height': p.mount_plate_height,
            'mount_bolt_count': len(self._mount_bolt_positions()),
        }


def main():
    """Generate and export the motor housing."""
    params = MotorHousingParams()
    gen = MotorHousingGenerator(params)

    dims = gen.get_dimensions()
    print("Motor Housing (Type 130 DC Motor):")
    print(f"  Bore diameter: {dims['bore_diameter']:.1f} mm")
    print(f"  Bore flat width: {dims['bore_flat_width']:.1f} mm")
    print(f"  Outer diameter: {dims['outer_diameter']:.1f} mm")
    print(f"  Housing length: {dims['housing_length']:.1f} mm")
    print(f"  Wall thickness: {dims['wall_thickness']:.1f} mm")
    print(f"  Total width (with flanges): {dims['total_width']:.1f} mm")
    print(f"  Total height: {dims['total_height']:.1f} mm")
    print(f"  Screws: {dims['num_screws']}x M3")
    print(f"  Mount plate: {dims['mount_plate_width']:.0f}x{dims['mount_plate_height']:.0f} mm")
    print(f"  Mount bolts: {dims['mount_bolt_count']}x M3")

    bolt_positions = gen._mount_bolt_positions()
    print(f"  Bolt positions (Y, Z): {[(f'{y:.1f}', f'{z:.1f}') for y, z in bolt_positions]}")

    # Generate individual halves
    lower = gen.generate_lower()
    upper = gen.generate_upper()

    cq.exporters.export(lower, "motor_housing_lower.step")
    print("\nExported: motor_housing_lower.step")

    cq.exporters.export(upper, "motor_housing_upper.step")
    print("Exported: motor_housing_upper.step")

    # Generate combined assembly
    assy = gen.generate()
    assy.save("motor_housing.step")
    print("Exported: motor_housing.step (assembly)")


if __name__ == "__main__":
    main()
