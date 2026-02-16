"""Motor mount assembly generator.

Composes motor housings, mount plates, and shaft couplings
to create a complete motor mounting system for the mux assembly.
"""

import cadquery as cq
from typing import Optional

from ..models.spec import LogicElementSpec
from ..models.geometry import PartMetadata, PartType
from .motor_mount_params import MotorMountParams, ShaftCouplingParams
from .motor_mount_right import RightMotorMountGenerator
from .motor_mount_left import LeftMotorMountGenerator
from .motor_housing import MotorHousingGenerator, MotorHousingParams
from .shaft_coupling import ShaftCouplingGenerator
from .layout import LayoutCalculator


class MotorAssemblyGenerator:
    """Generator for complete motor mount assembly."""

    def __init__(
        self,
        motor_params: Optional[MotorMountParams] = None,
        coupling_params: Optional[ShaftCouplingParams] = None,
        housing_params: Optional[MotorHousingParams] = None,
        include_couplings: bool = True,
    ):
        """Initialize the motor assembly generator.

        Args:
            motor_params: Parameters for motor mounts.
            coupling_params: Parameters for shaft couplings.
            housing_params: Parameters for clamshell motor housings.
            include_couplings: Whether to include shaft couplings in assembly.
        """
        self.motor_params = motor_params or MotorMountParams()
        self.coupling_params = coupling_params or ShaftCouplingParams()
        self.housing_params = housing_params or MotorHousingParams()
        self.include_couplings = include_couplings

    def _position_housing(
        self, spec: LogicElementSpec, motor_y: float, motor_z: float,
    ) -> cq.Assembly:
        """Generate and position a motor housing for a given axle.

        The housing is generated at origin (motor axis along X, shaft at X=0).
        Then translated so the mount plate front face sits at the axle end X,
        and the shaft center aligns with (motor_y, motor_z).

        Args:
            spec: Logic element specification.
            motor_y: Y position of the motor shaft center.
            motor_z: Z position of the motor shaft center.

        Returns:
            CadQuery Assembly with positioned upper and lower housing halves.
        """
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)
        axle_end_x = housing_layout.axle_end_x  # Right side axle end

        gen = MotorHousingGenerator(self.housing_params)
        lower = gen.generate_lower()
        upper = gen.generate_upper()

        # Housing is generated with:
        #   - Shaft exit at X=0, mount plate from X=0 to X=-plate_thickness
        #   - Motor center at Y=0, Z=0
        # We need:
        #   - Mount plate front face at X = axle_end_x
        #   - Motor center at Y=motor_y, Z=motor_z
        offset = cq.Vector(axle_end_x, motor_y, motor_z)

        assy = cq.Assembly()
        assy.add(lower, name="lower", loc=cq.Location(offset))
        assy.add(upper, name="upper", loc=cq.Location(offset))
        return assy

    def generate(self, spec: LogicElementSpec, placement=None) -> cq.Assembly:
        """Generate the complete motor mount assembly.

        Args:
            spec: Logic element specification.

        Returns:
            CadQuery Assembly with motor housings, mounts, and couplings.
        """
        assy = cq.Assembly()
        mux_layout = LayoutCalculator.calculate_mux_layout(spec)

        # Motor A: clamshell housing, positioned for Input A axle
        housing_a = self._position_housing(
            spec, motor_y=0.0, motor_z=mux_layout.input_a_z,
        )
        assy.add(housing_a, name="motor_housing_a",
                 color=cq.Color(0.5, 0.5, 0.5))

        # Motor B: clamshell housing, positioned for Input B axle
        housing_b = self._position_housing(
            spec, motor_y=0.0, motor_z=mux_layout.input_b_z,
        )
        assy.add(housing_b, name="motor_housing_b",
                 color=cq.Color(0.5, 0.5, 0.5))

        # Motor S: clamshell housing, positioned for selector/bevel axle
        housing_s = self._position_housing(
            spec, motor_y=mux_layout.pivot_y, motor_z=0.0,
        )
        assy.add(housing_s, name="motor_housing_s",
                 color=cq.Color(0.5, 0.5, 0.5))

        # Add shaft couplings if enabled
        if self.include_couplings:
            self._add_couplings(assy, spec, mux_layout)

        return assy

    def _add_couplings(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        mux_layout,
    ) -> None:
        """Add shaft couplings between motor housings and mux axles."""
        coupling_gen = ShaftCouplingGenerator(self.coupling_params)
        housing_layout = mux_layout.housing
        housing_right_outer = housing_layout.right_plate_x + housing_layout.plate_thickness / 2
        axle_end_x = housing_layout.axle_end_x

        # Coupling sits between housing right outer face and motor housing mount plate
        # Motor housing mount plate is at axle_end_x (with plate extending in -X)
        coupling_x = (housing_right_outer + axle_end_x) / 2

        # Coupling A
        coupling_a = coupling_gen.generate_positioned(
            position=(coupling_x, 0.0, mux_layout.input_a_z),
            motor_side='+X',
        )
        assy.add(coupling_a, name="coupling_a", color=cq.Color(0.7, 0.5, 0.2))

        # Coupling B
        coupling_b = coupling_gen.generate_positioned(
            position=(coupling_x, 0.0, mux_layout.input_b_z),
            motor_side='+X',
        )
        assy.add(coupling_b, name="coupling_b", color=cq.Color(0.7, 0.5, 0.2))

        # Coupling S
        coupling_s = coupling_gen.generate_positioned(
            position=(coupling_x, mux_layout.pivot_y, 0.0),
            motor_side='+X',
        )
        assy.add(coupling_s, name="coupling_s", color=cq.Color(0.7, 0.5, 0.2))

    def generate_housing_only(self, spec: LogicElementSpec, motor: str = 'a') -> cq.Assembly:
        """Generate just one motor housing, positioned.

        Args:
            spec: Logic element specification.
            motor: Which motor ('a', 'b', or 's').

        Returns:
            Positioned motor housing assembly.
        """
        mux_layout = LayoutCalculator.calculate_mux_layout(spec)

        if motor == 'a':
            return self._position_housing(spec, 0.0, mux_layout.input_a_z)
        elif motor == 'b':
            return self._position_housing(spec, 0.0, mux_layout.input_b_z)
        elif motor == 's':
            return self._position_housing(spec, mux_layout.pivot_y, 0.0)
        else:
            raise ValueError(f"Unknown motor '{motor}', expected 'a', 'b', or 's'")

    def generate_coupling_only(self) -> cq.Workplane:
        """Generate just the shaft coupling.

        Useful for testing and individual part export.
        """
        gen = ShaftCouplingGenerator(self.coupling_params)
        return gen.generate()

    def get_motor_positions(self, spec: LogicElementSpec) -> dict:
        """Get all motor shaft positions.

        Returns:
            Dictionary with motor positions (at mount plate face).
        """
        mux_layout = LayoutCalculator.calculate_mux_layout(spec)
        housing_layout = mux_layout.housing
        axle_end_x = housing_layout.axle_end_x

        return {
            'motor_a': (axle_end_x, 0.0, mux_layout.input_a_z),
            'motor_b': (axle_end_x, 0.0, mux_layout.input_b_z),
            'motor_s': (axle_end_x, mux_layout.pivot_y, 0.0),
        }

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        positions = self.get_motor_positions(spec)

        return PartMetadata(
            part_id="motor_assembly",
            part_type=PartType.HOUSING_FRONT,
            name="Motor Mount Assembly",
            material="PLA",
            count=1,
            dimensions={
                "motor_a_x": positions['motor_a'][0],
                "motor_a_z": positions['motor_a'][2],
                "motor_b_x": positions['motor_b'][0],
                "motor_b_z": positions['motor_b'][2],
                "motor_s_x": positions['motor_s'][0],
                "motor_s_y": positions['motor_s'][1],
            },
            notes="Clamshell motor housings with shaft couplings for 3x 130-size DC motors",
        )
