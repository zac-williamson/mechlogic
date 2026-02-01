"""Shared layout calculations for assembly generators.

Centralizes position and dimension calculations used across multiple generators.
"""

from dataclasses import dataclass

from ..models.spec import LogicElementSpec
from .gear_bevel import BevelGearGenerator


@dataclass
class SelectorLayout:
    """Calculated positions for a selector mechanism."""
    gear_a_center: float
    clutch_center: float
    gear_b_center: float
    engagement_travel: float
    face_width: float
    shaft_diameter: float


@dataclass
class BevelLayout:
    """Calculated positions for a bevel gear pair."""
    mesh_distance: float
    tooth_angle: float
    cone_distance: float


@dataclass
class MuxLayout:
    """Calculated positions for a complete mux assembly."""
    selector: SelectorLayout
    bevel: BevelLayout
    pivot_y: float
    input_a_x: float
    input_a_z: float
    input_b_x: float
    input_b_z: float
    spur_pitch_diameter: float


class LayoutCalculator:
    """Calculates component positions for mechanical assemblies."""

    @staticmethod
    def calculate_selector_layout(spec: LogicElementSpec) -> SelectorLayout:
        """Calculate positions for selector mechanism components.

        Args:
            spec: The logic element specification.

        Returns:
            SelectorLayout with all position values.
        """
        face_width = spec.geometry.gear_face_width
        clutch_width = spec.geometry.clutch_width
        gear_spacing = spec.geometry.gear_spacing
        shaft_diameter = spec.primary_shaft_diameter
        dog_tooth_height = spec.gears.dog_clutch.tooth_height

        clutch_half_span = clutch_width / 2 + dog_tooth_height
        gear_teeth_end = face_width + dog_tooth_height

        gear_a_center = 0
        clutch_center = gear_teeth_end + gear_spacing + clutch_half_span
        engagement_travel = gear_spacing + dog_tooth_height
        gear_b_center = clutch_center + engagement_travel + clutch_half_span

        return SelectorLayout(
            gear_a_center=gear_a_center,
            clutch_center=clutch_center,
            gear_b_center=gear_b_center,
            engagement_travel=engagement_travel,
            face_width=face_width,
            shaft_diameter=shaft_diameter,
        )

    @staticmethod
    def calculate_bevel_layout(spec: LogicElementSpec) -> BevelLayout:
        """Calculate positions for bevel gear pair.

        Args:
            spec: The logic element specification.

        Returns:
            BevelLayout with mesh distance and angles.
        """
        bevel_gen = BevelGearGenerator(gear_id="driving")
        cone_distance = bevel_gen.get_cone_distance(spec)
        mesh_distance = cone_distance * 0.79
        tooth_angle = 360.0 / spec.gears.bevel_teeth

        return BevelLayout(
            mesh_distance=mesh_distance,
            tooth_angle=tooth_angle,
            cone_distance=cone_distance,
        )

    @staticmethod
    def calculate_pivot_y(spec: LogicElementSpec) -> float:
        """Calculate the shift lever pivot Y position.

        Args:
            spec: The logic element specification.

        Returns:
            Y coordinate of the pivot point.
        """
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        clutch_od = gear_od * 0.4
        return clutch_od / 2 + 27  # Must match shift_lever.py

    @staticmethod
    def calculate_mux_layout(spec: LogicElementSpec) -> MuxLayout:
        """Calculate complete layout for a mux assembly.

        Args:
            spec: The logic element specification.

        Returns:
            MuxLayout with all position values.
        """
        selector = LayoutCalculator.calculate_selector_layout(spec)
        bevel = LayoutCalculator.calculate_bevel_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        # Input gear positions
        spur_pitch_diameter = spec.gears.module * spec.gears.coaxial_teeth
        input_a_x = selector.gear_a_center
        input_a_z = spur_pitch_diameter  # Above gear A
        input_b_x = selector.gear_b_center
        input_b_z = -spur_pitch_diameter  # Below gear B

        return MuxLayout(
            selector=selector,
            bevel=bevel,
            pivot_y=pivot_y,
            input_a_x=input_a_x,
            input_a_z=input_a_z,
            input_b_x=input_b_x,
            input_b_z=input_b_z,
            spur_pitch_diameter=spur_pitch_diameter,
        )
