"""Bevel gear pair assembly generator.

Creates two identical bevel gears positioned at 90° to each other,
with their pitch cones meeting at a common apex for proper meshing.
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .gear_bevel import BevelGearGenerator
from .layout import LayoutCalculator, BevelLayout


class BevelPairGenerator:
    """Generator for a meshing bevel gear pair assembly.

    Creates a driving and driven bevel gear with proper mesh alignment
    and optional axles. The driving gear is on the Z-axis with teeth
    pointing up, and the driven gear is on the X-axis (90° arrangement).
    """

    def __init__(self, include_axles: bool = True):
        """Initialize the bevel pair generator.

        Args:
            include_axles: Whether to include axles in the assembly.
        """
        self.include_axles = include_axles

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate a bevel gear pair assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the meshing bevel gear pair.
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
        """Add bevel gear pair to an existing assembly.

        This allows other generators to compose bevel pairs into larger assemblies.

        Args:
            assy: The assembly to add components to.
            spec: The logic element specification.
            origin: The (x, y, z) origin point for the bevel pair apex.
            name_prefix: Optional prefix for component names.
        """
        layout = LayoutCalculator.calculate_bevel_layout(spec)
        ox, oy, oz = origin

        # Generate gears
        driving_gen = BevelGearGenerator(gear_id="driving")
        driven_gen = BevelGearGenerator(gear_id="driven")

        driving_placement = PartPlacement(part_type=PartType.BEVEL_DRIVE, part_id="bevel_driving")
        driven_placement = PartPlacement(part_type=PartType.BEVEL_DRIVEN, part_id="bevel_driven")

        driving_gear = driving_gen.generate(spec, driving_placement)
        driven_gear = driven_gen.generate(spec, driven_placement)

        # Driving gear: on Z-axis, teeth pointing up (+Z)
        assy.add(
            driving_gear,
            name=f"{name_prefix}driving_bevel" if name_prefix else "driving_gear",
            loc=cq.Location(cq.Vector(ox, oy, oz - layout.mesh_distance)),
            color=cq.Color("steelblue"),
        )

        # Driven gear: rotated for mesh
        driven_rotated = self._rotate_driven_gear(driven_gear, layout)
        assy.add(
            driven_rotated,
            name=f"{name_prefix}driven_bevel" if name_prefix else "driven_gear",
            loc=cq.Location(
                cq.Vector(ox - layout.mesh_distance, oy, oz),
                cq.Vector(0, 1, 0),
                -90
            ),
            color=cq.Color("darkorange"),
        )

        if self.include_axles:
            self._add_axles(assy, spec, layout, origin, name_prefix)

    def _rotate_driven_gear(self, gear: cq.Workplane, layout: BevelLayout) -> cq.Workplane:
        """Apply rotation sequence to driven gear for proper mesh alignment."""
        mesh_offset_angle = layout.tooth_angle / 2
        return (
            gear
            .rotate((0, 0, 0), (1, 0, 0), 180)  # Flip to point teeth inward
            .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)  # Mesh alignment
        )

    def _add_axles(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        layout: BevelLayout,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add axles to the assembly."""
        ox, oy, oz = origin
        shaft_diameter = spec.primary_shaft_diameter
        axle_clearance = 0.5

        # Driving axle: along Z-axis, truncated to avoid intersection
        driving_axle_top = oz - (shaft_diameter / 2 + axle_clearance)
        driving_axle_bottom = oz - layout.mesh_distance - 30
        driving_axle_length = driving_axle_top - driving_axle_bottom

        driving_axle = (
            cq.Workplane('XY')
            .workplane(offset=driving_axle_bottom)
            .center(ox, oy)
            .circle(shaft_diameter / 2)
            .extrude(driving_axle_length)
        )
        assy.add(
            driving_axle,
            name=f"{name_prefix}driving_axle" if name_prefix else "driving_axle",
            color=cq.Color("gray")
        )

        # Driven axle: along X-axis
        axle_length = 50.0
        driven_axle = (
            cq.Workplane('YZ')
            .center(oy, oz)
            .circle(shaft_diameter / 2)
            .extrude(axle_length)
            .translate((ox - layout.mesh_distance - axle_length / 2, 0, 0))
        )
        assy.add(
            driven_axle,
            name=f"{name_prefix}driven_axle" if name_prefix else "driven_axle",
            color=cq.Color("gray")
        )

    def get_mesh_distance(self, spec: LogicElementSpec) -> float:
        """Get the mesh distance for positioning gears."""
        return LayoutCalculator.calculate_bevel_layout(spec).mesh_distance

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        layout = LayoutCalculator.calculate_bevel_layout(spec)

        return PartMetadata(
            part_id="bevel_pair",
            part_type=PartType.BEVEL_DRIVE,
            name="Bevel Gear Pair (90° mesh)",
            material="PLA",
            count=1,
            dimensions={
                "cone_distance": layout.cone_distance,
                "mesh_distance": layout.mesh_distance,
                "shaft_angle": 90.0,
            },
            notes="Assembly: 2 bevel gears meshing at 90°",
        )
