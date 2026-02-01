"""Combined selector mechanism with bevel gear control.

Creates a complete selector mechanism with:
- Selector mechanism: two spur gears, dog clutch, shift lever
- Bevel gear pair: driven gear axle connects to shift lever pivot
- Rotating the driving bevel gear moves the shift lever to select gears
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .layout import LayoutCalculator
from .selector_mechanism import SelectorMechanismGenerator
from .bevel_pair import BevelPairGenerator


class CombinedSelectorGenerator:
    """Generator for a selector mechanism with bevel gear control.

    Creates a gear selector that can be controlled by rotating a bevel gear.
    The bevel gear pair converts rotation to shift lever movement.

    Composes SelectorMechanismGenerator and BevelPairGenerator.
    """

    def __init__(self, include_axles: bool = True):
        """Initialize the combined selector generator.

        Args:
            include_axles: Whether to include axles in the assembly.
        """
        self.include_axles = include_axles

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate a combined selector mechanism assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the complete mechanism.
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
        """Add combined selector mechanism to an existing assembly.

        Args:
            assy: The assembly to add components to.
            spec: The logic element specification.
            origin: The (x, y, z) origin point.
            name_prefix: Optional prefix for component names.
        """
        ox, oy, oz = origin
        selector_layout = LayoutCalculator.calculate_selector_layout(spec)
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        # Add selector mechanism (without its own axle - we'll add our own)
        selector_gen = SelectorMechanismGenerator(
            include_axle=self.include_axles,
            include_lever=True
        )
        selector_gen.add_to_assembly(assy, spec, origin=origin, name_prefix=name_prefix)

        # Add bevel pair at the pivot point
        # The bevel apex should be at (clutch_center, pivot_y, 0)
        bevel_apex = (ox + selector_layout.clutch_center, oy + pivot_y, oz)

        bevel_gen = BevelPairGenerator(include_axles=self.include_axles)
        bevel_gen.add_to_assembly(
            assy, spec,
            origin=bevel_apex,
            name_prefix=f"{name_prefix}bevel_" if name_prefix else ""
        )

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        selector_layout = LayoutCalculator.calculate_selector_layout(spec)
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        return PartMetadata(
            part_id="combined_selector",
            part_type=PartType.GEAR_A,
            name="Combined Selector with Bevel Control",
            material="PLA",
            count=1,
            dimensions={
                "gear_a_x": selector_layout.gear_a_center,
                "clutch_x": selector_layout.clutch_center,
                "gear_b_x": selector_layout.gear_b_center,
                "pivot_y": pivot_y,
                "bevel_mesh_distance": bevel_layout.mesh_distance,
            },
            notes="Assembly: selector mechanism + bevel gear control pair",
        )
