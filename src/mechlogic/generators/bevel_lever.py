"""Bevel gear pair with shift lever generator.

Creates the shift control mechanism consisting of:
- A bevel gear pair that converts input rotation to lever rotation
- A shift lever that moves the dog clutch

The driven bevel gear axle connects to the lever pivot, so rotating
the driving bevel gear rotates the lever around its pivot axis.
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .gear_bevel import BevelGearGenerator
from .shift_lever import ShiftLeverGenerator
from .layout import LayoutCalculator, BevelLayout


class BevelLeverGenerator:
    """Generator for bevel gear pair with shift lever.

    The bevel gear apex is positioned at the lever pivot point.
    The driven bevel gear's axle connects to the lever pivot hole.
    """

    def __init__(self, include_axles: bool = True):
        """Initialize the bevel lever generator.

        Args:
            include_axles: Whether to include axles in the assembly.
        """
        self.include_axles = include_axles

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate a bevel gear pair with shift lever assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the bevel gears and lever.
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
        """Add bevel gear pair and shift lever to an existing assembly.

        The origin is at the clutch axis (where the lever fork engages).
        The bevel apex is positioned at the lever pivot point above the origin.

        Args:
            assy: The assembly to add components to.
            spec: The logic element specification.
            origin: The (x, y, z) origin point (at clutch axis).
            name_prefix: Optional prefix for component names.
        """
        ox, oy, oz = origin
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        # Generate bevel gears
        driving_gen = BevelGearGenerator(gear_id="driving")
        driven_gen = BevelGearGenerator(gear_id="driven")

        driving_placement = PartPlacement(part_type=PartType.BEVEL_DRIVE, part_id="bevel_driving")
        driven_placement = PartPlacement(part_type=PartType.BEVEL_DRIVEN, part_id="bevel_driven")

        driving_gear = driving_gen.generate(spec, driving_placement)
        driven_gear = driven_gen.generate(spec, driven_placement)

        # Bevel apex is at (ox, oy + pivot_y, oz)
        # Driven gear: on Z-axis below apex, teeth pointing up
        assy.add(
            driven_gear,
            name=f"{name_prefix}driven_bevel" if name_prefix else "driven_bevel",
            loc=cq.Location(cq.Vector(ox, oy + pivot_y, oz - bevel_layout.mesh_distance)),
            color=cq.Color("gold"),
        )

        # Driving gear: on X-axis, rotated to mesh
        mesh_offset_angle = bevel_layout.tooth_angle / 2
        driving_rotated = (
            driving_gear
            .rotate((0, 0, 0), (1, 0, 0), 180)
            .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)
            .rotate((0, 0, 0), (0, 1, 0), -90)
        )
        assy.add(
            driving_rotated,
            name=f"{name_prefix}driving_bevel" if name_prefix else "driving_bevel",
            loc=cq.Location(cq.Vector(ox - bevel_layout.mesh_distance, oy + pivot_y, oz)),
            color=cq.Color("purple"),
        )

        # Add shift lever - positioned at the origin (clutch axis)
        lever_gen = ShiftLeverGenerator()
        placement_lever = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="shift_lever")
        shift_lever = lever_gen.generate(spec, placement_lever)

        assy.add(
            shift_lever,
            name=f"{name_prefix}shift_lever" if name_prefix else "shift_lever",
            loc=cq.Location(cq.Vector(ox, oy, oz)),
            color=cq.Color("red"),
        )

        if self.include_axles:
            self._add_axles(assy, spec, bevel_layout, pivot_y, origin, name_prefix)

    def _add_axles(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        bevel_layout: BevelLayout,
        pivot_y: float,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add bevel gear axles to the assembly."""
        ox, oy, oz = origin
        shaft_diameter = spec.primary_shaft_diameter
        bevel_axle_length = 40.0

        # Driven bevel axle: along Z-axis through lever pivot
        driven_bevel_axle = (
            cq.Workplane('XY')
            .center(ox, oy + pivot_y)
            .circle(shaft_diameter / 2)
            .extrude(bevel_axle_length)
            .translate((0, 0, oz - bevel_layout.mesh_distance - 10))
        )
        assy.add(
            driven_bevel_axle,
            name=f"{name_prefix}driven_bevel_axle" if name_prefix else "driven_bevel_axle",
            color=cq.Color("slategray")
        )

        # Driving bevel axle: along X-axis, extending toward -X
        driving_bevel_axle = (
            cq.Workplane('YZ')
            .center(oy + pivot_y, oz)
            .circle(shaft_diameter / 2)
            .extrude(-bevel_axle_length)
            .translate((ox - bevel_layout.mesh_distance, 0, 0))
        )
        assy.add(
            driving_bevel_axle,
            name=f"{name_prefix}driving_bevel_axle" if name_prefix else "driving_bevel_axle",
            color=cq.Color("slategray")
        )

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        return PartMetadata(
            part_id="bevel_lever",
            part_type=PartType.BEVEL_DRIVE,
            name="Bevel Gear Shift Control",
            material="PLA",
            count=1,
            dimensions={
                "bevel_mesh_distance": bevel_layout.mesh_distance,
                "pivot_y": pivot_y,
            },
            notes="Assembly: bevel gear pair + shift lever",
        )
