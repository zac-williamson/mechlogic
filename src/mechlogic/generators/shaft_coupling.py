"""Shaft coupling for connecting motor shaft to mechanism shaft.

Creates a stepped-bore rigid coupling that connects:
- Motor shaft: 2mm diameter
- Mechanism shaft: 6mm diameter

The coupling has set screw holes for securing to both shafts.
"""

import cadquery as cq
from typing import Optional

from .motor_mount_params import ShaftCouplingParams


class ShaftCouplingGenerator:
    """Generator for motor-to-mechanism shaft couplings."""

    def __init__(self, params: Optional[ShaftCouplingParams] = None):
        """Initialize the coupling generator.

        Args:
            params: Coupling parameters. Uses defaults if not provided.
        """
        self.params = params or ShaftCouplingParams()

    def generate(self) -> cq.Workplane:
        """Generate the shaft coupling.

        The coupling is oriented along the X-axis:
        - Motor bore on -X side (smaller diameter)
        - Mechanism bore on +X side (larger diameter)
        - Center at origin

        Returns:
            CadQuery Workplane with the coupling geometry.
        """
        p = self.params

        # Create outer cylinder
        coupling = (
            cq.Workplane('YZ')
            .circle(p.outer_diameter / 2)
            .extrude(p.length)
            .translate((-p.length / 2, 0, 0))
        )

        # Cut motor shaft bore (-X side)
        motor_bore = (
            cq.Workplane('YZ')
            .circle(p.motor_shaft_diameter / 2)
            .extrude(p.motor_bore_length)
            .translate((-p.length / 2, 0, 0))
        )
        coupling = coupling.cut(motor_bore)

        # Cut mechanism shaft bore (+X side)
        mechanism_bore = (
            cq.Workplane('YZ')
            .circle(p.mechanism_shaft_diameter / 2)
            .extrude(p.mechanism_bore_length)
            .translate((p.length / 2 - p.mechanism_bore_length, 0, 0))
        )
        coupling = coupling.cut(mechanism_bore)

        # Add set screw holes by cutting cylinders from outside (+Y direction toward center)
        # Motor side set screw
        motor_set_screw_x = -p.length / 2 + p.motor_bore_length / 2
        motor_set_screw = (
            cq.Workplane('XZ')
            .center(motor_set_screw_x, 0)
            .circle(p.set_screw_diameter / 2)
            .extrude(-p.set_screw_depth)  # Extrude in -Y direction (toward center)
            .translate((0, p.outer_diameter / 2, 0))
        )
        coupling = coupling.cut(motor_set_screw)

        # Mechanism side set screw
        mechanism_set_screw_x = p.length / 2 - p.mechanism_bore_length / 2
        mechanism_set_screw = (
            cq.Workplane('XZ')
            .center(mechanism_set_screw_x, 0)
            .circle(p.set_screw_diameter / 2)
            .extrude(-p.set_screw_depth)  # Extrude in -Y direction (toward center)
            .translate((0, p.outer_diameter / 2, 0))
        )
        coupling = coupling.cut(mechanism_set_screw)

        return coupling

    def generate_positioned(
        self,
        position: tuple[float, float, float],
        motor_side: str = '-X',
    ) -> cq.Workplane:
        """Generate coupling positioned at a specific location.

        Args:
            position: (x, y, z) position for coupling center.
            motor_side: Which side the motor connects to.
                        '-X' means motor on left, '+X' means motor on right.

        Returns:
            Positioned coupling geometry.
        """
        coupling = self.generate()

        if motor_side == '+X':
            # Flip coupling so motor bore is on +X side
            coupling = coupling.rotate((0, 0, 0), (0, 1, 0), 180)

        coupling = coupling.translate(position)
        return coupling

    def get_dimensions(self) -> dict:
        """Get coupling dimensions for reference.

        Returns:
            Dictionary with coupling dimensions.
        """
        p = self.params
        return {
            'outer_diameter': p.outer_diameter,
            'length': p.length,
            'motor_bore_diameter': p.motor_shaft_diameter,
            'motor_bore_length': p.motor_bore_length,
            'mechanism_bore_diameter': p.mechanism_shaft_diameter,
            'mechanism_bore_length': p.mechanism_bore_length,
        }
