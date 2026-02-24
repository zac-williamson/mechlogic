"""Selector mechanism generator.

Creates a gear selector assembly with:
- Two spur gears that freely rotate on a common axle
- A dog clutch between them that slides along the axle
- A shift lever to move the clutch

The selector axle is recessed (terminates inside bearing pockets in the
housing walls) to allow external gears to be mounted on the input axles
for linking purposes (e.g., X and inverse-X).
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .gear_spur import SpurGearGenerator
from .dog_clutch import DogClutchGenerator
from .layout import LayoutCalculator, SelectorLayout, HousingLayout
from .axle_profile import make_d_flat_axle, add_groove_to_axle


class SelectorMechanismGenerator:
    """Generator for a gear selector mechanism assembly.

    Creates two spur gears on a common axle with a sliding dog clutch
    between them. The clutch can engage either gear to transfer drive.

    Note: The shift lever is NOT included here. Use BevelLeverGenerator
    to add the shift control mechanism (bevel gears + lever).
    """

    def __init__(self, include_axle: bool = True, two_piece_clutch: bool = True):
        """Initialize the selector mechanism generator.

        Args:
            include_axle: Whether to include the selector axle.
            two_piece_clutch: If True, generate a two-piece dog clutch
                (inner core slides on axle, retained by C-clips + outer sleeve).
        """
        self.include_axle = include_axle
        self.two_piece_clutch = two_piece_clutch

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate a selector mechanism assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the selector mechanism.
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
        """Add selector mechanism to an existing assembly.

        This allows other generators to compose selector mechanisms into larger assemblies.

        Args:
            assy: The assembly to add components to.
            spec: The logic element specification.
            origin: The (x, y, z) origin point for the selector axis.
            name_prefix: Optional prefix for component names.
        """
        layout = LayoutCalculator.calculate_selector_layout(spec)
        ox, oy, oz = origin

        # Generate components
        gear_a_gen = SpurGearGenerator(gear_id="a")
        gear_b_gen = SpurGearGenerator(gear_id="b")
        clutch_gen = DogClutchGenerator()

        placement_a = PartPlacement(part_type=PartType.GEAR_A, part_id="gear_a")
        placement_b = PartPlacement(part_type=PartType.GEAR_B, part_id="gear_b")

        gear_a = gear_a_gen.generate(spec, placement_a)
        gear_b = gear_b_gen.generate(spec, placement_b)

        # Add components (rotated so axle is along X)
        gear_a_rotated = gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
        assy.add(
            gear_a_rotated,
            name=f"{name_prefix}gear_a" if name_prefix else "gear_a",
            loc=cq.Location(cq.Vector(ox + layout.gear_a_center, oy, oz)),
            color=cq.Color("steelblue"),
        )

        gear_b_rotated = gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
        assy.add(
            gear_b_rotated,
            name=f"{name_prefix}gear_b" if name_prefix else "gear_b",
            loc=cq.Location(cq.Vector(ox + layout.gear_b_center, oy, oz)),
            color=cq.Color("darkorange"),
        )

        if self.two_piece_clutch:
            inner_core = clutch_gen.generate_inner_core(spec)
            inner_core_rotated = inner_core.rotate((0, 0, 0), (0, 1, 0), 90)
            assy.add(
                inner_core_rotated,
                name=f"{name_prefix}clutch_inner_core" if name_prefix else "clutch_inner_core",
                loc=cq.Location(cq.Vector(ox + layout.clutch_center, oy, oz)),
                color=cq.Color("forestgreen"),
            )

            outer_sleeve = clutch_gen.generate_outer_sleeve(spec)
            outer_sleeve_rotated = outer_sleeve.rotate((0, 0, 0), (0, 1, 0), 90)
            assy.add(
                outer_sleeve_rotated,
                name=f"{name_prefix}clutch_outer_sleeve" if name_prefix else "clutch_outer_sleeve",
                loc=cq.Location(cq.Vector(ox + layout.clutch_center, oy, oz)),
                color=cq.Color("limegreen"),
            )
        else:
            placement_clutch = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="dog_clutch")
            dog_clutch = clutch_gen.generate(spec, placement_clutch)
            clutch_rotated = dog_clutch.rotate((0, 0, 0), (0, 1, 0), 90)
            assy.add(
                clutch_rotated,
                name=f"{name_prefix}dog_clutch" if name_prefix else "dog_clutch",
                loc=cq.Location(cq.Vector(ox + layout.clutch_center, oy, oz)),
                color=cq.Color("forestgreen"),
            )

        if self.include_axle:
            self._add_axle(assy, spec, layout, origin, name_prefix)

    def _add_axle(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        layout: SelectorLayout,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add the selector axle to the assembly.

        The selector axle is a D-flat profile along its full length.
        C-clips provide axial retention for gears.
        """
        ox, oy, oz = origin
        d_flat_depth = spec.tolerances.d_flat_depth
        shaft_dia = layout.shaft_diameter

        # Selector axle extends through both plates with overhang (same as input axles)
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)
        axle_start = ox + housing_layout.axle_start_x
        axle_length = housing_layout.axle_length

        # Build D-flat axle along X
        axle = make_d_flat_axle(shaft_dia, axle_length, d_flat_depth)
        axle = axle.translate((axle_start, oy, oz))

        # Add C-clip retention grooves outboard of each gear
        # Groove just left of gear A
        groove_offset = 1.0  # mm from gear edge
        groove_x_left = ox + layout.gear_a_center - groove_offset
        axle = add_groove_to_axle(axle, groove_x_left, shaft_dia)

        # Groove just right of gear B
        groove_x_right = ox + layout.gear_b_center + layout.face_width + groove_offset
        axle = add_groove_to_axle(axle, groove_x_right, shaft_dia)

        if self.two_piece_clutch:
            # C-clip grooves flanking the inner core for axial retention
            clutch_width = spec.geometry.clutch_width
            core_length = clutch_width + 2 * layout.engagement_travel + 2.0
            core_groove_left = ox + layout.clutch_center - core_length / 2 - 1.0
            core_groove_right = ox + layout.clutch_center + core_length / 2 + 1.0
            axle = add_groove_to_axle(axle, core_groove_left, shaft_dia)
            axle = add_groove_to_axle(axle, core_groove_right, shaft_dia)

        assy.add(
            axle,
            name=f"{name_prefix}selector_axle" if name_prefix else "selector_axle",
            color=cq.Color("gray")
        )

    def get_layout(self, spec: LogicElementSpec) -> SelectorLayout:
        """Get the layout for this selector mechanism."""
        return LayoutCalculator.calculate_selector_layout(spec)

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        layout = LayoutCalculator.calculate_selector_layout(spec)

        return PartMetadata(
            part_id="selector_mechanism",
            part_type=PartType.GEAR_A,
            name="Gear Selector Mechanism",
            material="PLA",
            count=1,
            dimensions={
                "gear_a_x": layout.gear_a_center,
                "clutch_x": layout.clutch_center,
                "gear_b_x": layout.gear_b_center,
                "engagement_travel": layout.engagement_travel,
            },
            notes="Assembly: 2 spur gears + dog clutch",
        )
