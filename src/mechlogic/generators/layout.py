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
class HousingLayout:
    """Calculated positions for housing plates and axles."""
    left_plate_x: float
    right_plate_x: float
    plate_thickness: float
    axle_start_x: float
    axle_end_x: float
    axle_length: float
    device_length_x: float
    axle_overhang: float


@dataclass
class MuxLayout:
    """Calculated positions for a complete mux assembly."""
    selector: SelectorLayout
    bevel: BevelLayout
    housing: HousingLayout
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

        The mechanism is centered between the housing plates along the X-axis.
        The centering accounts for actual gear geometry after 90° rotation:
        - Gear A: positioned at its left edge, extends right with dog teeth on right
        - Gear B: positioned at its body left edge, dog teeth extend to the left

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
        plate_thickness = spec.geometry.housing_thickness

        clutch_half_span = clutch_width / 2 + dog_tooth_height
        gear_teeth_end = face_width + dog_tooth_height

        # Calculate uncentered positions first
        # These positions represent where the gear's X=0 point lands after rotation
        gear_a_uncentered = 0
        clutch_uncentered = gear_teeth_end + gear_spacing + clutch_half_span
        engagement_travel = gear_spacing + dog_tooth_height
        gear_b_uncentered = clutch_uncentered + engagement_travel + clutch_half_span

        # Calculate actual mechanism bounding box edges (after rotation)
        # Gear A: left edge at position, right edge at position + face_width + dog_tooth_height
        # Gear B: left edge at position - dog_tooth_height, right edge at position + face_width
        mechanism_left_edge = gear_a_uncentered  # Gear A left edge
        mechanism_right_edge = gear_b_uncentered + face_width  # Gear B right edge

        # Housing inner faces (where mechanism should fit between)
        left_plate_inner = plate_thickness / 2
        right_plate_inner = spec.geometry.device_length_x - plate_thickness / 2

        # Calculate offset to center mechanism between housing inner faces
        mechanism_center = (mechanism_left_edge + mechanism_right_edge) / 2
        housing_center = (left_plate_inner + right_plate_inner) / 2
        centering_offset = housing_center - mechanism_center

        # Apply centering offset
        gear_a_center = gear_a_uncentered + centering_offset
        clutch_center = clutch_uncentered + centering_offset
        gear_b_center = gear_b_uncentered + centering_offset

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

        The pivot Y is set equal to the spur gear pitch diameter so that
        the driven bevel gear axle is positioned one pitch diameter above
        the selector gear axle, allowing them to mesh.

        Args:
            spec: The logic element specification.

        Returns:
            Y coordinate of the pivot point.
        """
        spur_pitch_diameter = spec.gears.module * spec.gears.coaxial_teeth
        return spur_pitch_diameter

    @staticmethod
    def calculate_spur_gear_radius(spec: LogicElementSpec) -> float:
        """Calculate the spur gear pitch radius.

        This is used for housing dimensions to enable stackability -
        mux units can be stacked with spur gears connecting input axles.

        Args:
            spec: The logic element specification.

        Returns:
            Pitch radius of spur gears.
        """
        spur_pitch_diameter = spec.gears.module * spec.gears.coaxial_teeth
        return spur_pitch_diameter / 2

    @staticmethod
    def calculate_housing_layout(spec: LogicElementSpec) -> HousingLayout:
        """Calculate positions for housing plates and axles.

        Args:
            spec: The logic element specification.

        Returns:
            HousingLayout with plate and axle positions.
        """
        device_length_x = spec.geometry.device_length_x
        axle_overhang = spec.geometry.axle_overhang
        plate_thickness = spec.geometry.housing_thickness

        # Housing plates at start and end of device
        left_plate_x = 0.0
        right_plate_x = device_length_x

        # Axles extend past housing plates by axle_overhang
        axle_start_x = left_plate_x - axle_overhang
        axle_end_x = right_plate_x + axle_overhang
        axle_length = axle_end_x - axle_start_x

        return HousingLayout(
            left_plate_x=left_plate_x,
            right_plate_x=right_plate_x,
            plate_thickness=plate_thickness,
            axle_start_x=axle_start_x,
            axle_end_x=axle_end_x,
            axle_length=axle_length,
            device_length_x=device_length_x,
            axle_overhang=axle_overhang,
        )

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
        housing = LayoutCalculator.calculate_housing_layout(spec)
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
            housing=housing,
            pivot_y=pivot_y,
            input_a_x=input_a_x,
            input_a_z=input_a_z,
            input_b_x=input_b_x,
            input_b_z=input_b_z,
            spur_pitch_diameter=spur_pitch_diameter,
        )
