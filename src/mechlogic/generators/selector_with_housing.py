"""Selector mechanism with lower housing generator.

Creates the selector mechanism (gears + clutch) with lower housing plates,
without the bevel lever control system.
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .layout import LayoutCalculator
from .selector_mechanism import SelectorMechanismGenerator
from .lower_housing import LowerHousingGenerator


class SelectorWithHousingGenerator:
    """Generator for selector mechanism with lower housing.

    Creates a gear selector (2 spur gears + dog clutch) inside
    lower housing plates. Does not include the bevel lever control.

    This is useful for testing the selector mechanism independently
    of the bevel lever control system.
    """

    def __init__(
        self,
        include_axle: bool = True,
        housing_transparent: bool = False,
    ):
        """Initialize the generator.

        Args:
            include_axle: Whether to include the selector axle.
            housing_transparent: Whether to render housing semi-transparent.
        """
        self.include_axle = include_axle
        self.housing_transparent = housing_transparent

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate selector mechanism with housing assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the mechanism and housing.
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
        """Add selector mechanism and housing to an existing assembly.

        Args:
            assy: The assembly to add components to.
            spec: The logic element specification.
            origin: The (x, y, z) origin point.
            name_prefix: Optional prefix for component names.
        """
        # Add lower housing first (behind mechanism visually)
        self._add_housing(assy, spec, name_prefix)

        # Add selector mechanism
        selector_gen = SelectorMechanismGenerator(include_axle=self.include_axle)
        selector_gen.add_to_assembly(assy, spec, origin=origin, name_prefix=name_prefix)

    def _add_housing(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        name_prefix: str,
    ) -> None:
        """Add lower housing enclosure to the assembly."""
        housing_gen = LowerHousingGenerator(spec=spec)

        # Generate all housing parts
        left_plate = housing_gen.generate_left_plate()
        right_plate = housing_gen.generate_right_plate()
        front_wall = housing_gen.generate_front_wall()
        back_wall = housing_gen.generate_back_wall()

        if self.housing_transparent:
            side_color = cq.Color(0.7, 0.7, 0.7, 0.3)
            wall_color = cq.Color(0.6, 0.6, 0.6, 0.3)
        else:
            side_color = cq.Color(0.7, 0.7, 0.7)
            wall_color = cq.Color(0.6, 0.6, 0.6)

        assy.add(
            left_plate,
            name=f"{name_prefix}housing_left" if name_prefix else "housing_left",
            color=side_color,
        )
        assy.add(
            right_plate,
            name=f"{name_prefix}housing_right" if name_prefix else "housing_right",
            color=side_color,
        )
        assy.add(
            front_wall,
            name=f"{name_prefix}housing_front" if name_prefix else "housing_front",
            color=wall_color,
        )
        assy.add(
            back_wall,
            name=f"{name_prefix}housing_back" if name_prefix else "housing_back",
            color=wall_color,
        )

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        selector_layout = LayoutCalculator.calculate_selector_layout(spec)
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)

        return PartMetadata(
            part_id="selector_with_housing",
            part_type=PartType.GEAR_A,
            name="Selector Mechanism with Lower Housing",
            material="PLA",
            count=1,
            dimensions={
                "gear_a_x": selector_layout.gear_a_center,
                "clutch_x": selector_layout.clutch_center,
                "gear_b_x": selector_layout.gear_b_center,
                "left_plate_x": housing_layout.left_plate_x,
                "right_plate_x": housing_layout.right_plate_x,
            },
            notes="Assembly: selector mechanism (gears + clutch) with lower housing plates",
        )
