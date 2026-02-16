"""Right motor mount plate for Input A and Input B motors.

This plate mounts to the right side of the housing (X = right plate outer face)
and holds two 130-size DC motors aligned with the A and B input axles.

Motor positions:
- Motor A: Y=0, Z=+36 (aligned with Input A axle)
- Motor B: Y=0, Z=-36 (aligned with Input B axle)
"""

import cadquery as cq
from dataclasses import dataclass
from typing import Optional

from ..models.spec import LogicElementSpec
from .motor_mount_params import Motor130Params, MotorMountParams
from .layout import LayoutCalculator
from .lower_housing import LowerHousingParams


@dataclass
class RightMotorMountLayout:
    """Calculated layout for right motor mount."""

    # Plate position and size
    plate_x: float          # X position (outer face of housing + offset)
    plate_center_y: float   # Y center of plate
    plate_center_z: float   # Z center of plate
    plate_width_y: float    # Width in Y direction
    plate_height_z: float   # Height in Z direction

    # Motor positions (Y, Z for each motor shaft center)
    motor_a_y: float
    motor_a_z: float
    motor_b_y: float
    motor_b_z: float

    # Mounting hole positions
    mounting_hole_positions: list  # List of (y, z) tuples


class RightMotorMountGenerator:
    """Generator for the right motor mount plate (A & B motors)."""

    def __init__(
        self,
        params: Optional[MotorMountParams] = None,
        spec: Optional[LogicElementSpec] = None,
    ):
        """Initialize the motor mount generator.

        Args:
            params: Direct motor mount parameters.
            spec: Logic element spec to derive positions from.
        """
        self.params = params or MotorMountParams()
        self.spec = spec
        self._layout: Optional[RightMotorMountLayout] = None

    def _calculate_layout(self) -> RightMotorMountLayout:
        """Calculate the motor mount layout from spec."""
        if self._layout is not None:
            return self._layout

        p = self.params
        motor = p.motor

        if self.spec is not None:
            # Get positions from spec
            mux_layout = LayoutCalculator.calculate_mux_layout(self.spec)
            housing_layout = LayoutCalculator.calculate_housing_layout(self.spec)

            motor_a_z = mux_layout.input_a_z  # Typically +36
            motor_b_z = mux_layout.input_b_z  # Typically -36
            motor_y = 0.0  # Both motors on same Y as input axles

            # Plate X position: outside of right housing plate with gap for coupling
            housing_right_outer = housing_layout.right_plate_x + housing_layout.plate_thickness / 2
            plate_x = housing_right_outer + p.housing_gap
        else:
            # Default positions
            motor_a_z = 36.0
            motor_b_z = -36.0
            motor_y = 0.0
            plate_x = 48.0  # Default position

        # Calculate plate size to cover both motors with margin
        motor_radius = motor.body_diameter / 2 + p.motor_body_clearance
        margin = p.mounting_hole_inset + p.mounting_hole_diameter / 2 + 5.0

        # Y extent: center on motor Y with margin for mounting holes
        plate_width_y = motor.body_diameter + 2 * margin
        plate_center_y = motor_y

        # Z extent: from motor B bottom to motor A top
        z_min = motor_b_z - motor_radius - margin
        z_max = motor_a_z + motor_radius + margin
        plate_height_z = z_max - z_min
        plate_center_z = (z_min + z_max) / 2

        # Mounting hole positions (corners of plate)
        hole_inset = p.mounting_hole_inset
        mounting_holes = [
            (plate_center_y - plate_width_y / 2 + hole_inset, z_min + hole_inset),
            (plate_center_y + plate_width_y / 2 - hole_inset, z_min + hole_inset),
            (plate_center_y - plate_width_y / 2 + hole_inset, z_max - hole_inset),
            (plate_center_y + plate_width_y / 2 - hole_inset, z_max - hole_inset),
        ]

        self._layout = RightMotorMountLayout(
            plate_x=plate_x,
            plate_center_y=plate_center_y,
            plate_center_z=plate_center_z,
            plate_width_y=plate_width_y,
            plate_height_z=plate_height_z,
            motor_a_y=motor_y,
            motor_a_z=motor_a_z,
            motor_b_y=motor_y,
            motor_b_z=motor_b_z,
            mounting_hole_positions=mounting_holes,
        )

        return self._layout

    def _create_motor_pocket(
        self,
        motor_y: float,
        motor_z: float,
        pocket_depth: float,
    ) -> cq.Workplane:
        """Create a D-shaped motor pocket with tab slots for anti-rotation.

        The pocket shape matches the motor body:
        - Circular section for the round motor body
        - Flat cuts on two sides matching the motor's flat sides
        - Tab slots extending from the flats

        Args:
            motor_y: Y position of motor center
            motor_z: Z position of motor center
            pocket_depth: How deep the pocket goes into the plate

        Returns:
            Solid representing the pocket (to be subtracted from plate)
        """
        p = self.params
        motor = p.motor

        # Motor body pocket dimensions
        body_radius = motor.body_diameter / 2 + p.motor_body_clearance
        flat_half_width = motor.flat_width / 2 + p.motor_body_clearance

        # Create D-shaped pocket by starting with cylinder and cutting flats
        # First create the full cylinder
        cylinder = (
            cq.Workplane('YZ')
            .center(motor_y, motor_z)
            .circle(body_radius)
            .extrude(pocket_depth)
        )

        # Cut off material outside the flat region
        # We keep only the region where |Y - motor_y| <= flat_half_width
        # Cut a box on the -Y side beyond the flat
        cut_box_minus_y = (
            cq.Workplane('YZ')
            .center(motor_y - flat_half_width - body_radius, motor_z)
            .rect(body_radius * 2, body_radius * 2)
            .extrude(pocket_depth)
        )
        # Cut a box on the +Y side beyond the flat
        cut_box_plus_y = (
            cq.Workplane('YZ')
            .center(motor_y + flat_half_width + body_radius, motor_z)
            .rect(body_radius * 2, body_radius * 2)
            .extrude(pocket_depth)
        )

        pocket = cylinder.cut(cut_box_minus_y).cut(cut_box_plus_y)

        # Add tab slots if enabled
        if p.include_tab_slots:
            tab_width = motor.tab_width + p.tab_clearance * 2
            tab_length = motor.tab_length + p.tab_clearance
            tab_thickness = motor.tab_thickness + p.tab_clearance * 2

            # Tab slots extend from the flat sides in ±Y direction
            # Positioned at the motor center Z
            for y_dir in [-1, 1]:
                tab_slot = (
                    cq.Workplane('YZ')
                    .center(motor_y + y_dir * (flat_half_width + tab_length / 2), motor_z)
                    .rect(tab_length, tab_width)
                    .extrude(tab_thickness)
                )
                pocket = pocket.union(tab_slot)

        return pocket

    def generate(self) -> cq.Workplane:
        """Generate the right motor mount plate.

        Creates a plate with D-shaped motor pockets that prevent rotation,
        including tab slots for motor mounting tabs and screw holes.

        Returns:
            CadQuery Workplane with the motor mount plate.
        """
        layout = self._calculate_layout()
        p = self.params
        motor = p.motor

        # Create the base plate (in YZ plane, extruded in -X)
        plate = (
            cq.Workplane('YZ')
            .center(layout.plate_center_y, layout.plate_center_z)
            .rect(layout.plate_width_y, layout.plate_height_z)
            .extrude(-p.plate_thickness)  # Extrude in -X (away from housing)
            .translate((layout.plate_x, 0, 0))
        )

        # Cut motor pockets (D-shaped with tab slots)
        motor_positions = [
            (layout.motor_a_y, layout.motor_a_z),
            (layout.motor_b_y, layout.motor_b_z),
        ]

        for motor_y, motor_z in motor_positions:
            pocket = self._create_motor_pocket(motor_y, motor_z, p.motor_pocket_depth)
            # Position pocket at +X face of plate (inner face toward housing)
            pocket_positioned = pocket.translate((layout.plate_x, 0, 0))
            plate = plate.cut(pocket_positioned)

        # Add shaft through-holes
        shaft_hole_diameter = motor.shaft_diameter + 2 * p.shaft_clearance
        motor_positions_relative = [
            (layout.motor_a_y - layout.plate_center_y, layout.motor_a_z - layout.plate_center_z),
            (layout.motor_b_y - layout.plate_center_y, layout.motor_b_z - layout.plate_center_z),
        ]
        plate = (
            plate
            .faces(">X")
            .workplane()
            .pushPoints(motor_positions_relative)
            .hole(shaft_hole_diameter)
        )

        # Add tab screw holes (through-holes for M2 screws to secure motor tabs)
        if p.include_tab_slots:
            flat_half_width = motor.flat_width / 2 + p.motor_body_clearance
            tab_screw_offset = flat_half_width + motor.tab_hole_offset

            tab_screw_positions = []
            for motor_y, motor_z in motor_positions:
                # Two screw holes per motor (one on each side)
                tab_screw_positions.append(
                    (motor_y - tab_screw_offset - layout.plate_center_y,
                     motor_z - layout.plate_center_z)
                )
                tab_screw_positions.append(
                    (motor_y + tab_screw_offset - layout.plate_center_y,
                     motor_z - layout.plate_center_z)
                )

            plate = (
                plate
                .faces(">X")
                .workplane()
                .pushPoints(tab_screw_positions)
                .hole(p.tab_screw_diameter)
            )

        # Add mounting holes (through-holes for bolts to attach to housing)
        mounting_hole_points = [
            (y - layout.plate_center_y, z - layout.plate_center_z)
            for y, z in layout.mounting_hole_positions
        ]
        plate = (
            plate
            .faces(">X")
            .workplane()
            .pushPoints(mounting_hole_points)
            .hole(p.mounting_hole_diameter)
        )

        # Add self-supporting structure if enabled
        if p.self_supporting:
            plate = self._add_self_supporting_structure(plate, layout)

        return plate

    def _add_self_supporting_structure(
        self,
        plate: cq.Workplane,
        layout: RightMotorMountLayout,
    ) -> cq.Workplane:
        """Add base plate, gussets, and feet for self-supporting structure.

        Creates an L-bracket design where the vertical plate (motor mount)
        is supported by a horizontal base plate with triangular gussets.

        For the RIGHT mount (positioned at positive X, with housing to the left):
        - The vertical plate's +X face faces the motors
        - The base extends in +X direction (away from housing)

        Args:
            plate: The vertical motor mount plate
            layout: Layout information

        Returns:
            Combined plate with self-supporting structure
        """
        p = self.params

        # Calculate dimensions
        # Vertical plate: spans from (plate_x - plate_thickness) to plate_x
        # The +X face is at plate_x (where motor pockets are)
        vertical_plate_front_x = layout.plate_x

        # Base plate extends in +X direction (away from housing, toward motor side)
        base_x_start = vertical_plate_front_x              # Attached to vertical plate
        base_x_end = base_x_start + p.base_depth           # Extends in +X (away from housing)
        base_center_x = (base_x_start + base_x_end) / 2

        # Base Y extent matches vertical plate
        base_y_min = layout.plate_center_y - layout.plate_width_y / 2
        base_y_max = layout.plate_center_y + layout.plate_width_y / 2
        base_width_y = layout.plate_width_y
        base_center_y = layout.plate_center_y

        # Base Z position: at the bottom of the vertical plate
        base_z_min = layout.plate_center_z - layout.plate_height_z / 2
        base_z_top = base_z_min + p.base_thickness

        # Create base plate (horizontal, in XY plane)
        base = (
            cq.Workplane('XY')
            .center(base_center_x, base_center_y)
            .rect(p.base_depth, base_width_y)
            .extrude(p.base_thickness)
            .translate((0, 0, base_z_min))
        )

        # Add triangular gussets for rigidity
        # Gussets are in XZ plane, connecting vertical and horizontal plates
        gusset_height = min(layout.plate_height_z * 0.4, 30.0)  # Limit gusset height
        gusset_depth = min(p.base_depth * 0.8, 30.0)  # Limit gusset depth

        # Position gussets along Y axis
        if p.gusset_count >= 2:
            gusset_y_positions = [
                base_y_min + base_width_y * 0.2,
                base_y_max - base_width_y * 0.2,
            ]
        else:
            gusset_y_positions = [base_center_y]

        for gusset_y in gusset_y_positions:
            # Create triangular gusset profile (extends in +X direction from vertical plate)
            gusset = (
                cq.Workplane('XZ')
                .moveTo(base_x_start, base_z_top)  # At vertical plate base
                .lineTo(base_x_start + gusset_depth, base_z_top)  # Extends in +X
                .lineTo(base_x_start, base_z_top + gusset_height)  # Up the vertical plate
                .close()
                .extrude(p.gusset_thickness)
                .translate((0, gusset_y - p.gusset_thickness / 2, 0))
            )
            base = base.union(gusset)

        # Add feet for stability (cylindrical standoffs under base)
        if p.foot_height > 0:
            foot_inset = p.foot_diameter / 2 + 3.0  # Inset from edges
            foot_positions = [
                (base_x_start + foot_inset, base_y_min + foot_inset),
                (base_x_start + foot_inset, base_y_max - foot_inset),
                (base_x_end - foot_inset, base_y_min + foot_inset),
                (base_x_end - foot_inset, base_y_max - foot_inset),
            ]

            for foot_x, foot_y in foot_positions:
                foot = (
                    cq.Workplane('XY')
                    .center(foot_x, foot_y)
                    .circle(p.foot_diameter / 2)
                    .extrude(-p.foot_height)
                    .translate((0, 0, base_z_min))
                )
                base = base.union(foot)

        # Union base structure with vertical plate
        return plate.union(base)

    def get_layout(self) -> RightMotorMountLayout:
        """Get the calculated layout."""
        return self._calculate_layout()

    def get_motor_shaft_positions(self) -> list:
        """Get the motor shaft centerline positions.

        Returns:
            List of (x, y, z) tuples for each motor shaft center
            (at the plate face where shaft enters).
        """
        layout = self._calculate_layout()
        return [
            (layout.plate_x, layout.motor_a_y, layout.motor_a_z),
            (layout.plate_x, layout.motor_b_y, layout.motor_b_z),
        ]
