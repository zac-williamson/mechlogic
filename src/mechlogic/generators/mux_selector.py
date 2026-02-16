"""2-to-1 multiplexer selector mechanism generator.

Creates a complete 2-to-1 mux mechanism with:
- Two input shafts (A, B) that drive the selector gears
- Input A drives gear A via meshing spur gears (offset in +Z)
- Input B drives gear B via meshing spur gears (offset in -Z)
- Bevel gear pair for shift control
- Dog clutch selects between A and B for the output
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .gear_spur import SpurGearGenerator
from .layout import LayoutCalculator, MuxLayout
from .combined_selector import CombinedSelectorGenerator


class MuxSelectorGenerator:
    """Generator for a 2-to-1 multiplexer selector mechanism.

    Creates a mechanism where two input shafts (A, B) can be selected
    by the position of a bevel-gear-controlled dog clutch.

    Composes CombinedSelectorGenerator and adds input gears.
    """

    def __init__(self, include_axles: bool = True):
        """Initialize the mux selector generator.

        Args:
            include_axles: Whether to include axles in the assembly.
        """
        self.include_axles = include_axles

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate a 2-to-1 mux selector assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the complete mux mechanism.
        """
        assy = cq.Assembly()
        self.add_to_assembly(assy, spec, origin=(0, 0, 0))
        return assy

    def add_to_assembly(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        origin: tuple[float, float, float] = (0, 0, 0),
        name_prefix: str = "",
    ) -> None:
        """Add mux selector mechanism to an existing assembly.

        Args:
            assy: The assembly to add components to.
            spec: The logic element specification.
            origin: The (x, y, z) origin point.
            name_prefix: Optional prefix for component names.
        """
        ox, oy, oz = origin
        layout = LayoutCalculator.calculate_mux_layout(spec)

        # Add combined selector (selector mechanism + bevel pair)
        combined_gen = CombinedSelectorGenerator(include_axles=self.include_axles)
        combined_gen.add_to_assembly(assy, spec, origin=origin, name_prefix=name_prefix)

        # Add input gears
        self._add_input_gears(assy, spec, layout, origin, name_prefix)

        if self.include_axles:
            self._add_input_axles(assy, spec, layout, origin, name_prefix)

    def _add_input_gears(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        layout: MuxLayout,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add input gears to the assembly."""
        ox, oy, oz = origin

        gear_a_gen = SpurGearGenerator(gear_id="a")
        gear_b_gen = SpurGearGenerator(gear_id="b")
        placement_generic = PartPlacement(part_type=PartType.GEAR_A, part_id="input")

        # Input gear A (above Gear A)
        input_gear_a = gear_a_gen.generate(spec, placement_generic)
        input_a_rotated = input_gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
        assy.add(
            input_a_rotated,
            name=f"{name_prefix}input_gear_a" if name_prefix else "input_gear_a",
            loc=cq.Location(cq.Vector(ox + layout.input_a_x, oy, oz + layout.input_a_z)),
            color=cq.Color("lightsteelblue"),
        )

        # Input gear B (below Gear B)
        input_gear_b = gear_b_gen.generate(spec, placement_generic)
        input_b_rotated = input_gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
        assy.add(
            input_b_rotated,
            name=f"{name_prefix}input_gear_b" if name_prefix else "input_gear_b",
            loc=cq.Location(cq.Vector(ox + layout.input_b_x, oy, oz + layout.input_b_z)),
            color=cq.Color("sandybrown"),
        )

    def _add_input_axles(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        layout: MuxLayout,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add input axles to the assembly."""
        ox, oy, oz = origin
        shaft_diameter = layout.selector.shaft_diameter

        # Use housing layout for axle positions
        axle_start = ox + layout.housing.axle_start_x
        axle_length = layout.housing.axle_length

        # Input A axle
        input_a_axle = (
            cq.Workplane('YZ')
            .center(oy, oz + layout.input_a_z)
            .circle(shaft_diameter / 2)
            .extrude(axle_length)
            .translate((axle_start, 0, 0))
        )
        assy.add(
            input_a_axle,
            name=f"{name_prefix}input_a_axle" if name_prefix else "input_a_axle",
            color=cq.Color("gray")
        )

        # Input B axle
        input_b_axle = (
            cq.Workplane('YZ')
            .center(oy, oz + layout.input_b_z)
            .circle(shaft_diameter / 2)
            .extrude(axle_length)
            .translate((axle_start, 0, 0))
        )
        assy.add(
            input_b_axle,
            name=f"{name_prefix}input_b_axle" if name_prefix else "input_b_axle",
            color=cq.Color("gray")
        )

    def get_layout(self, spec: LogicElementSpec) -> MuxLayout:
        """Get the layout for this mux mechanism."""
        return LayoutCalculator.calculate_mux_layout(spec)

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        layout = LayoutCalculator.calculate_mux_layout(spec)

        return PartMetadata(
            part_id="mux_selector",
            part_type=PartType.GEAR_A,
            name="2-to-1 Mux Selector Mechanism",
            material="PLA",
            count=1,
            dimensions={
                "gear_a_x": layout.selector.gear_a_center,
                "gear_b_x": layout.selector.gear_b_center,
                "input_a_z": layout.input_a_z,
                "input_b_z": layout.input_b_z,
                "pivot_y": layout.pivot_y,
            },
            notes="Assembly: 2-input mux with bevel gear selector control",
        )
