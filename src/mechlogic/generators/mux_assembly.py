"""Complete mux assembly generator with housing.

Creates the complete 2-to-1 multiplexer assembly including:
- All mechanism components (gears, clutch, lever, bevels)
- Housing (lower housing + upper housing with flexure)
- All axles
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .layout import LayoutCalculator
from .mux_selector import MuxSelectorGenerator
from .lower_housing import LowerHousingGenerator, LowerHousingParams
from .bevel_lever_with_upper_housing import BevelLeverWithUpperHousingGenerator


class MuxAssemblyGenerator:
    """Generator for a complete mux assembly with housing.

    Creates the full 2-to-1 multiplexer mechanism inside a housing,
    ready for 3D printing and assembly.

    Composes MuxSelectorGenerator and adds housing.
    """

    def __init__(
        self,
        include_housing: bool = True,
        housing_transparent: bool = True,
        include_upper_housing: bool = True,
        include_flexure: bool = True,
        split_housing: bool = False,
    ):
        """Initialize the mux assembly generator.

        Args:
            include_housing: Whether to include lower housing in the assembly.
            housing_transparent: Whether to render housing semi-transparent.
            include_upper_housing: Whether to include upper housing (bevel housing).
            include_flexure: Whether to include serpentine flexure on upper housing.
            split_housing: Whether to split housings into left/right halves.
        """
        self.include_housing = include_housing
        self.housing_transparent = housing_transparent
        self.include_upper_housing = include_upper_housing
        self.include_flexure = include_flexure
        self.split_housing = split_housing

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate the complete mux assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the complete mechanism with housing.
        """
        assy = cq.Assembly()

        # Add lower housing first (so it's behind the mechanism visually)
        if self.include_housing:
            self._add_lower_housing(assy, spec)

        # Add upper housing (bevel lever housing with flexure)
        if self.include_upper_housing:
            self._add_upper_housing(assy, spec)

        # Add the complete mux selector mechanism
        # Bevel axles come from BevelLeverWithUpperHousingGenerator (properly sized
        # with D-flat profiles and retention grooves), not BevelLeverGenerator
        mux_gen = MuxSelectorGenerator(include_axles=True, include_bevel_axles=False)
        mux_gen.add_to_assembly(assy, spec, origin=(0, 0, 0))

        return assy

    def _add_lower_housing(self, assy: cq.Assembly, spec: LogicElementSpec) -> None:
        """Add lower housing enclosure to the assembly."""
        housing_gen = LowerHousingGenerator(spec=spec)

        if self.split_housing:
            left_half, right_half = housing_gen.generate_split()
            alpha = 0.3 if self.housing_transparent else 1.0
            assy.add(left_half, name="lower_housing_left",
                     color=cq.Color(0.7, 0.7, 0.7, alpha))
            assy.add(right_half, name="lower_housing_right",
                     color=cq.Color(0.6, 0.6, 0.6, alpha))
        else:
            side_plates, front_back_walls = housing_gen.generate()
            if self.housing_transparent:
                assy.add(side_plates, name="housing_side_plates", color=cq.Color(0.7, 0.7, 0.7, 0.3))
                assy.add(front_back_walls, name="housing_front_back", color=cq.Color(0.6, 0.6, 0.6, 0.3))
            else:
                assy.add(side_plates, name="housing_side_plates", color=cq.Color(0.75, 0.75, 0.75))
                assy.add(front_back_walls, name="housing_front_back", color=cq.Color(0.5, 0.5, 0.5))

    def _add_upper_housing(self, assy: cq.Assembly, spec: LogicElementSpec) -> None:
        """Add upper housing (bevel lever housing with flexure) to the assembly.

        The upper housing is positioned at the clutch center, same as the bevel lever.
        The walls are extended down to connect with the lower housing.
        """
        selector_layout = LayoutCalculator.calculate_selector_layout(spec)

        # Upper housing origin is at clutch center (same as bevel lever)
        origin = (selector_layout.clutch_center, 0, 0)

        # Get lower housing Y position for wall extension
        from .lower_housing import LowerHousingParams
        lower_params = LowerHousingParams.from_spec(spec)
        lower_housing_y_max = lower_params.plate_y_max  # Top of lower housing

        # Generate upper housing with or without flexure, with wall extension
        # Option A: Only left/right walls extend down (no L-shaped front/back)
        upper_housing_gen = BevelLeverWithUpperHousingGenerator(
            include_axles=True,  # Bevel axles with D-flat profiles and grooves
            include_flexure=self.include_flexure,
            extend_to_lower_housing=True,
            lower_housing_y_max=lower_housing_y_max,
            l_shaped_front_back=False,  # Option A: simpler wall extension
        )

        if self.split_housing:
            left_half, right_half = upper_housing_gen.generate_split_upper_housing(spec, origin)
            alpha = 0.3 if self.housing_transparent else 1.0
            assy.add(left_half, name="upper_housing_left",
                     color=cq.Color(0.7, 0.7, 0.7, alpha))
            assy.add(right_half, name="upper_housing_right",
                     color=cq.Color(0.6, 0.6, 0.6, alpha))
        else:
            upper_housing = upper_housing_gen._generate_upper_housing(spec, origin)
            if self.housing_transparent:
                assy.add(upper_housing, name="upper_housing", color=cq.Color(0.7, 0.7, 0.7, 0.3))
            else:
                assy.add(upper_housing, name="upper_housing", color=cq.Color(0.7, 0.7, 0.7))

        # Add bevel axles (D-flat profiles with retention grooves)
        upper_housing_gen._add_axles(assy, spec, origin, "")

        # Add flexure if enabled
        if self.include_flexure:
            self._add_flexure(assy, spec, upper_housing_gen, origin)

    def _add_flexure(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        housing_gen: BevelLeverWithUpperHousingGenerator,
        origin: tuple[float, float, float],
    ) -> None:
        """Add serpentine flexure to the assembly."""
        wp = housing_gen._wall_positions

        # Generate flexure
        flexure_shape = housing_gen._flexure_gen.generate()

        # Position flexure on inside of left wall (must match _add_flexure in BevelLeverWithUpperHousingGenerator)
        left_wall_x = wp['left_wall_x']
        wall_thickness = wp['wall_thickness']
        flexure_thickness = housing_gen._flexure_params.thickness
        flexure_wall_gap = 0.5  # Must match gap in _add_flexure
        flexure_x = left_wall_x + wall_thickness / 2 + flexure_wall_gap

        flexure_positioned = (
            flexure_shape
            .rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((flexure_x, wp['pivot_y'], wp['driving_axle_z']))
        )

        assy.add(
            flexure_positioned,
            name="serpentine_flexure",
            color=cq.Color(0.2, 0.6, 0.2),  # Green
        )

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
