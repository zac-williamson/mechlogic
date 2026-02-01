"""Selector mechanism generator.

Creates a gear selector assembly with:
- Two spur gears that freely rotate on a common axle
- A dog clutch between them that slides along the axle
- A shift lever to move the clutch
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .gear_spur import SpurGearGenerator
from .dog_clutch import DogClutchGenerator
from .shift_lever import ShiftLeverGenerator
from .layout import LayoutCalculator, SelectorLayout


class SelectorMechanismGenerator:
    """Generator for a gear selector mechanism assembly.

    Creates two spur gears on a common axle with a sliding dog clutch
    between them. The clutch can engage either gear to transfer drive.
    """

    def __init__(self, include_axle: bool = True, include_lever: bool = True):
        """Initialize the selector mechanism generator.

        Args:
            include_axle: Whether to include the selector axle.
            include_lever: Whether to include the shift lever.
        """
        self.include_axle = include_axle
        self.include_lever = include_lever

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
        placement_clutch = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="dog_clutch")

        gear_a = gear_a_gen.generate(spec, placement_a)
        gear_b = gear_b_gen.generate(spec, placement_b)
        dog_clutch = clutch_gen.generate(spec, placement_clutch)

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

        clutch_rotated = dog_clutch.rotate((0, 0, 0), (0, 1, 0), 90)
        assy.add(
            clutch_rotated,
            name=f"{name_prefix}dog_clutch" if name_prefix else "dog_clutch",
            loc=cq.Location(cq.Vector(ox + layout.clutch_center, oy, oz)),
            color=cq.Color("forestgreen"),
        )

        if self.include_axle:
            self._add_axle(assy, spec, layout, origin, name_prefix)

        if self.include_lever:
            self._add_lever(assy, spec, layout, origin, name_prefix)

    def _add_axle(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        layout: SelectorLayout,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add the selector axle to the assembly."""
        ox, oy, oz = origin
        axle_start = ox + layout.gear_a_center - layout.face_width / 2 - 10
        axle_end = ox + layout.gear_b_center + layout.face_width / 2 + 10
        axle_length = axle_end - axle_start

        axle = (
            cq.Workplane('YZ')
            .center(oy, oz)
            .circle(layout.shaft_diameter / 2)
            .extrude(axle_length)
            .translate((axle_start, 0, 0))
        )
        assy.add(
            axle,
            name=f"{name_prefix}selector_axle" if name_prefix else "selector_axle",
            color=cq.Color("gray")
        )

    def _add_lever(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        layout: SelectorLayout,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add the shift lever to the assembly."""
        ox, oy, oz = origin
        lever_gen = ShiftLeverGenerator()
        placement_lever = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="shift_lever")
        shift_lever = lever_gen.generate(spec, placement_lever)

        assy.add(
            shift_lever,
            name=f"{name_prefix}shift_lever" if name_prefix else "shift_lever",
            loc=cq.Location(cq.Vector(ox + layout.clutch_center, oy, oz)),
            color=cq.Color("red"),
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
            notes="Assembly: 2 spur gears + dog clutch + shift lever",
        )
