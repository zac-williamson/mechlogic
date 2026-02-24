"""Dog clutch generator.

Uses D-flat interface between inner core and outer sleeve for rotation
transfer while allowing axial sliding.
"""

import math

import cadquery as cq

from typing import Optional

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .layout import LayoutCalculator
from .axle_profile import make_d_flat_cylinder, add_d_flat_to_bore


class DogClutchGenerator:
    """Generator for the sliding dog clutch.

    Inner-to-outer interface uses D-flat (flat chord on +Y side) instead of
    square, avoiding diagonal scaling issues at larger shaft diameters.
    """

    # Inner core outer diameter = shaft_dia + CORE_OD_OFFSET
    CORE_OD_OFFSET = 3.0

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a sliding dog clutch (single-piece version).

        The clutch has:
        - A central bore that slides on the main axle
        - Dog teeth on both faces for engaging either gear
        - A circumferential groove for the lever fork to engage
        """
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        clutch_spec = spec.gears.dog_clutch

        # Clutch dimensions
        clutch_width = spec.geometry.clutch_width
        gear_od = spec.gears.module * spec.gears.coaxial_teeth + 2 * spec.gears.module
        clutch_od = gear_od * 0.4

        bore_dia = shaft_dia + clearance

        # Groove for lever fork
        groove_width = 4.0
        groove_depth = 2.0

        # Create main body
        clutch = (
            cq.Workplane("XY")
            .cylinder(clutch_width, clutch_od / 2)
            # Central bore
            .faces(">Z")
            .workplane()
            .hole(bore_dia)
        )

        # Add circumferential groove for lever
        groove_dia = clutch_od - groove_depth * 2
        groove = (
            cq.Workplane("XY")
            .cylinder(groove_width, clutch_od / 2)
            .faces(">Z")
            .workplane()
            .hole(groove_dia)
        )
        clutch = clutch.cut(groove)

        # Dog teeth on both faces
        tooth_count = clutch_spec.teeth
        tooth_height = clutch_spec.tooth_height

        tooth_outer = clutch_od / 2
        tooth_inner = bore_dia / 2 + 1.5  # Inner radius (clearance from bore)

        tooth_angle = 360.0 / tooth_count
        tooth_arc = tooth_angle * 0.45

        def add_dog_teeth(workplane: cq.Workplane, z_base: float, z_dir: int) -> cq.Workplane:
            for i in range(tooth_count):
                start_angle = i * tooth_angle

                tooth = (
                    cq.Workplane("XY")
                    .workplane(offset=z_base)
                    .moveTo(tooth_inner * math.cos(math.radians(start_angle)),
                           tooth_inner * math.sin(math.radians(start_angle)))
                    .radiusArc(
                        (tooth_inner * math.cos(math.radians(start_angle + tooth_arc)),
                         tooth_inner * math.sin(math.radians(start_angle + tooth_arc))),
                        tooth_inner
                    )
                    .lineTo(tooth_outer * math.cos(math.radians(start_angle + tooth_arc)),
                           tooth_outer * math.sin(math.radians(start_angle + tooth_arc)))
                    .radiusArc(
                        (tooth_outer * math.cos(math.radians(start_angle)),
                         tooth_outer * math.sin(math.radians(start_angle))),
                        -tooth_outer
                    )
                    .close()
                    .extrude(tooth_height * z_dir)
                )
                workplane = workplane.union(tooth)

            return workplane

        clutch = add_dog_teeth(clutch, clutch_width / 2, 1)
        clutch = add_dog_teeth(clutch, -clutch_width / 2, -1)

        return clutch

    # Retaining flange parameters
    FLANGE_THICKNESS = 1.0
    PIP_CLEARANCE = 0.6

    def generate_inner_core(self, spec: LogicElementSpec) -> cq.Workplane:
        """Generate the inner core that slides onto the selector axle.

        The inner core has:
        - A D-flat sliding-fit bore for the selector axle (retained by C-clips)
        - A D-flat outer cylinder (shaft_dia + 3.0mm diameter) for rotation coupling
        """
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        d_flat_depth = spec.tolerances.d_flat_depth
        layout = LayoutCalculator.calculate_selector_layout(spec)

        bore_dia = shaft_dia + clearance  # e.g. 6.0 + 0.2 = 6.2mm
        core_od = shaft_dia + self.CORE_OD_OFFSET  # e.g. 6.0 + 3.0 = 9.0mm

        # Total length: clutch_width + 2 * engagement_travel + 2mm margin
        clutch_width = spec.geometry.clutch_width
        engagement_travel = layout.engagement_travel
        core_length = clutch_width + 2 * engagement_travel + 2.0

        # Build D-flat outer cylinder for the full length
        core = make_d_flat_cylinder(core_od, core_length, d_flat_depth)

        # Sliding-fit D-flat bore through everything
        bore_hole = (
            cq.Workplane("XY")
            .circle(bore_dia / 2)
            .extrude(core_length / 2 + 1, both=True)
        )
        core = core.cut(bore_hole)

        # Add D-flat fill to the bore
        core = add_d_flat_to_bore(core, bore_dia, d_flat_depth, core_length)

        return core

    def generate_clutch_print_in_place(self, spec: LogicElementSpec) -> cq.Workplane:
        """Generate inner core + outer sleeve as a print-in-place compound.

        Uses PIP_CLEARANCE (0.4mm/side) instead of shaft_clearance so layers
        don't fuse across the gap. The retaining flanges keep the sleeve captured.
        """
        inner = self.generate_inner_core(spec)
        outer = self.generate_outer_sleeve(spec, clearance_override=self.PIP_CLEARANCE)

        compound = cq.Compound.makeCompound([inner.val(), outer.val()])
        return cq.Workplane().newObject([compound])

    def generate_outer_sleeve(
        self, spec: LogicElementSpec, clearance_override: Optional[float] = None,
    ) -> cq.Workplane:
        """Generate the outer sleeve that slides on the inner core.

        Same outer profile and features as the single-piece clutch (cylindrical OD,
        dog teeth on both faces, lever groove) but with a D-flat bore instead of
        circular to couple rotation from the inner core while allowing axial sliding.

        Uses shaft_clearance by default (two-piece assembly). Pass clearance_override
        for print-in-place compound.
        """
        shaft_dia = spec.primary_shaft_diameter
        clearance = clearance_override if clearance_override is not None else spec.tolerances.shaft_clearance
        d_flat_depth = spec.tolerances.d_flat_depth
        clutch_spec = spec.gears.dog_clutch

        clutch_width = spec.geometry.clutch_width
        gear_od = spec.gears.module * spec.gears.coaxial_teeth + 2 * spec.gears.module
        clutch_od = gear_od * 0.4

        # D-flat bore: inner core OD + clearance
        core_od = shaft_dia + self.CORE_OD_OFFSET  # 9.0mm
        d_flat_bore_dia = core_od + 2 * clearance  # 9.0 + 0.4 = 9.4mm (PIP) or 9.4 (assembly)

        # Groove for lever fork
        groove_width = 4.0
        groove_depth = 2.0

        # Create main cylindrical body
        sleeve = (
            cq.Workplane("XY")
            .cylinder(clutch_width, clutch_od / 2)
        )

        # Cut circular bore, then add D-flat fill
        bore_hole = (
            cq.Workplane("XY")
            .circle(d_flat_bore_dia / 2)
            .extrude(clutch_width / 2 + 1, both=True)
        )
        sleeve = sleeve.cut(bore_hole)

        # Add D-flat fill to create D-shaped bore
        sleeve = add_d_flat_to_bore(sleeve, d_flat_bore_dia, d_flat_depth, clutch_width)

        # Add circumferential groove for lever
        groove_dia = clutch_od - groove_depth * 2
        groove = (
            cq.Workplane("XY")
            .cylinder(groove_width, clutch_od / 2)
            .faces(">Z")
            .workplane()
            .hole(groove_dia)
        )
        sleeve = sleeve.cut(groove)

        # Dog teeth on both faces
        tooth_count = clutch_spec.teeth
        tooth_height = clutch_spec.tooth_height

        tooth_outer = clutch_od / 2
        # Inner radius must clear inner core OD with enough gap to prevent PIP fusing
        tooth_inner = d_flat_bore_dia / 2 + 1.5

        tooth_angle = 360.0 / tooth_count
        tooth_arc = tooth_angle * 0.45

        def add_dog_teeth(workplane: cq.Workplane, z_base: float, z_dir: int) -> cq.Workplane:
            for i in range(tooth_count):
                start_angle = i * tooth_angle

                tooth = (
                    cq.Workplane("XY")
                    .workplane(offset=z_base)
                    .moveTo(tooth_inner * math.cos(math.radians(start_angle)),
                           tooth_inner * math.sin(math.radians(start_angle)))
                    .radiusArc(
                        (tooth_inner * math.cos(math.radians(start_angle + tooth_arc)),
                         tooth_inner * math.sin(math.radians(start_angle + tooth_arc))),
                        tooth_inner
                    )
                    .lineTo(tooth_outer * math.cos(math.radians(start_angle + tooth_arc)),
                           tooth_outer * math.sin(math.radians(start_angle + tooth_arc)))
                    .radiusArc(
                        (tooth_outer * math.cos(math.radians(start_angle)),
                         tooth_outer * math.sin(math.radians(start_angle))),
                        -tooth_outer
                    )
                    .close()
                    .extrude(tooth_height * z_dir)
                )
                workplane = workplane.union(tooth)

            return workplane

        sleeve = add_dog_teeth(sleeve, clutch_width / 2, 1)
        sleeve = add_dog_teeth(sleeve, -clutch_width / 2, -1)

        return sleeve

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        gear_od = spec.gears.module * spec.gears.coaxial_teeth + 2 * spec.gears.module
        clutch_od = gear_od * 0.4

        return PartMetadata(
            part_id=PartType.DOG_CLUTCH.value,
            part_type=PartType.DOG_CLUTCH,
            name="Sliding Dog Clutch",
            material="PLA",
            count=1,
            dimensions={
                "outer_diameter": clutch_od,
                "bore_diameter": spec.primary_shaft_diameter + spec.tolerances.shaft_clearance,
                "width": spec.geometry.clutch_width,
                "tooth_count": spec.gears.dog_clutch.teeth,
                "tooth_height": spec.gears.dog_clutch.tooth_height,
            },
        )
