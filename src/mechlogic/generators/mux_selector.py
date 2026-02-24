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
from .axle_profile import make_d_flat_axle, add_groove_to_axle


class MuxSelectorGenerator:
    """Generator for a 2-to-1 multiplexer selector mechanism.

    Creates a mechanism where two input shafts (A, B) can be selected
    by the position of a bevel-gear-controlled dog clutch.

    Composes CombinedSelectorGenerator and adds input gears.
    """

    def __init__(self, include_axles: bool = True, include_bevel_axles: bool = True):
        """Initialize the mux selector generator.

        Args:
            include_axles: Whether to include selector/input axles in the assembly.
            include_bevel_axles: Whether to include bevel axles. Set False when
                an outer generator provides properly-sized bevel axles.
        """
        self.include_axles = include_axles
        self.include_bevel_axles = include_bevel_axles

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
        combined_gen = CombinedSelectorGenerator(
            include_axles=self.include_axles,
            include_bevel_axles=self.include_bevel_axles,
        )
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

        gear_a_gen = SpurGearGenerator(gear_id="a", include_dog_teeth=False)
        gear_b_gen = SpurGearGenerator(gear_id="b", include_dog_teeth=False)
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
        """Add input axles (D-flat profile) to the assembly.

        Housing walls provide axial retention for gears.
        """
        ox, oy, oz = origin
        shaft_diameter = layout.selector.shaft_diameter
        d_flat_depth = spec.tolerances.d_flat_depth

        axle_start = ox + layout.housing.axle_start_x
        axle_length = layout.housing.axle_length

        face_width = spec.geometry.gear_face_width
        groove_offset = 1.0  # mm from gear edge

        for axle_name, axle_z, gear_x in [
            ("input_a_axle", layout.input_a_z, layout.input_a_x),
            ("input_b_axle", layout.input_b_z, layout.input_b_x),
        ]:
            axle = make_d_flat_axle(shaft_diameter, axle_length, d_flat_depth)
            axle = axle.translate((axle_start, oy, oz + axle_z))

            # Add C-clip retention grooves flanking the gear
            groove_x_left = ox + gear_x - groove_offset
            groove_x_right = ox + gear_x + face_width + groove_offset
            axle = add_groove_to_axle(axle, groove_x_left, shaft_diameter)
            axle = add_groove_to_axle(axle, groove_x_right, shaft_diameter)

            assy.add(
                axle,
                name=f"{name_prefix}{axle_name}" if name_prefix else axle_name,
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
