"""Complete mux assembly generator with housing.

Creates the complete 2-to-1 multiplexer assembly including:
- All mechanism components (gears, clutch, lever, bevels)
- Housing (bottom and top halves)
- All axles
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .layout import LayoutCalculator
from .mux_selector import MuxSelectorGenerator
from .lower_housing import LowerHousingGenerator, LowerHousingParams


class MuxAssemblyGenerator:
    """Generator for a complete mux assembly with housing.

    Creates the full 2-to-1 multiplexer mechanism inside a housing,
    ready for 3D printing and assembly.

    Composes MuxSelectorGenerator and adds housing.
    """

    def __init__(self, include_housing: bool = True, housing_transparent: bool = True):
        """Initialize the mux assembly generator.

        Args:
            include_housing: Whether to include housing in the assembly.
            housing_transparent: Whether to render housing semi-transparent.
        """
        self.include_housing = include_housing
        self.housing_transparent = housing_transparent

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate the complete mux assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the complete mechanism with housing.
        """
        assy = cq.Assembly()

        # Add housing first (so it's behind the mechanism visually)
        if self.include_housing:
            self._add_housing(assy)

        # Add the complete mux selector mechanism
        mux_gen = MuxSelectorGenerator(include_axles=True)
        mux_gen.add_to_assembly(assy, spec, origin=(0, 0, 0))

        return assy

    def _add_housing(self, assy: cq.Assembly) -> None:
        """Add housing to the assembly."""
        housing_params = LowerHousingParams()
        housing_gen = LowerHousingGenerator(housing_params)
        housing_bottom, housing_top = housing_gen.generate()

        if self.housing_transparent:
            assy.add(housing_bottom, name="housing_bottom", color=cq.Color(0.7, 0.7, 0.7, 0.3))
            assy.add(housing_top, name="housing_top", color=cq.Color(0.6, 0.6, 0.6, 0.3))
        else:
            assy.add(housing_bottom, name="housing_bottom", color=cq.Color(0.75, 0.75, 0.75))
            assy.add(housing_top, name="housing_top", color=cq.Color(0.5, 0.5, 0.5))

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        layout = LayoutCalculator.calculate_mux_layout(spec)

        return PartMetadata(
            part_id="mux_assembly",
            part_type=PartType.HOUSING_FRONT,
            name="Complete 2-to-1 Mux Assembly",
            material="PLA",
            count=1,
            dimensions={
                "gear_a_x": layout.selector.gear_a_center,
                "gear_b_x": layout.selector.gear_b_center,
                "clutch_x": layout.selector.clutch_center,
                "pivot_y": layout.pivot_y,
            },
            notes="Complete assembly with housing, mechanism, and axles",
        )
