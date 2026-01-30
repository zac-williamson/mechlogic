"""Generate a combined selector mechanism with bevel gear control.

Creates:
- Selector mechanism: two spur gears, dog clutch, shift lever
- Bevel gear pair: driven gear axle connects to shift lever pivot
- Rotating the driving bevel gear moves the shift lever to select gears
"""

import math
import cadquery as cq
import yaml

from src.mechlogic.models.spec import LogicElementSpec
from src.mechlogic.models.geometry import PartPlacement, PartType
from src.mechlogic.generators.gear_spur import SpurGearGenerator
from src.mechlogic.generators.dog_clutch import DogClutchGenerator
from src.mechlogic.generators.shift_lever import ShiftLeverGenerator
from src.mechlogic.generators.gear_bevel import BevelGearGenerator


def main():
    # Load the example spec
    with open("examples/mux_2to1.yaml") as f:
        spec_data = yaml.safe_load(f)

    spec = LogicElementSpec.model_validate(spec_data)

    # ==========================================================================
    # Calculate dimensions
    # ==========================================================================

    # Selector mechanism dimensions
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    shaft_diameter = spec.primary_shaft_diameter
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    # Calculate selector positions along X-axis
    clutch_half_span = clutch_width / 2 + dog_tooth_height
    gear_teeth_end = face_width + dog_tooth_height

    gear_a_center = 0
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span
    engagement_travel = gear_spacing + dog_tooth_height
    gear_b_center = clutch_center + engagement_travel + clutch_half_span

    # Shift lever pivot location
    gear_od = spec.gears.module * spec.gears.coaxial_teeth
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27  # Distance from clutch axis to pivot (must match shift_lever.py)

    # Bevel gear dimensions
    bevel_module = spec.gears.module
    bevel_teeth = spec.gears.bevel_teeth
    bevel_gen = BevelGearGenerator(gear_id="driving")
    cone_distance = bevel_gen.get_cone_distance(spec)
    mesh_distance = cone_distance * 0.79
    tooth_angle = 360.0 / bevel_teeth

    print(f"Combined Selector Mechanism Layout:")
    print(f"  Selector axis: X")
    print(f"  Gear A center: X = {gear_a_center:.1f} mm")
    print(f"  Clutch center: X = {clutch_center:.1f} mm")
    print(f"  Gear B center: X = {gear_b_center:.1f} mm")
    print(f"  Lever pivot: Y = {pivot_y:.1f} mm above clutch axis")
    print(f"")
    print(f"  Bevel gear mesh distance: {mesh_distance:.1f} mm")
    print(f"  Bevel control axis: X (parallel to selector)")

    # ==========================================================================
    # Generate components
    # ==========================================================================

    # Selector components
    gear_a_gen = SpurGearGenerator(gear_id="a")
    gear_b_gen = SpurGearGenerator(gear_id="b")
    clutch_gen = DogClutchGenerator()
    lever_gen = ShiftLeverGenerator()

    placement_a = PartPlacement(part_type=PartType.GEAR_A, part_id="gear_a")
    placement_b = PartPlacement(part_type=PartType.GEAR_B, part_id="gear_b")
    placement_clutch = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="dog_clutch")
    placement_lever = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="shift_lever")

    gear_a = gear_a_gen.generate(spec, placement_a)
    gear_b = gear_b_gen.generate(spec, placement_b)
    dog_clutch = clutch_gen.generate(spec, placement_clutch)
    shift_lever = lever_gen.generate(spec, placement_lever)

    # Bevel gear components
    driving_bevel_gen = BevelGearGenerator(gear_id="driving")
    driven_bevel_gen = BevelGearGenerator(gear_id="driven")

    driving_bevel_placement = PartPlacement(part_type=PartType.BEVEL_DRIVE, part_id="bevel_driving")
    driven_bevel_placement = PartPlacement(part_type=PartType.BEVEL_DRIVEN, part_id="bevel_driven")

    driving_bevel = driving_bevel_gen.generate(spec, driving_bevel_placement)
    driven_bevel = driven_bevel_gen.generate(spec, driven_bevel_placement)

    # ==========================================================================
    # Create assembly
    # ==========================================================================

    assy = cq.Assembly()

    # --- Selector mechanism components (rotated so axle is along X) ---

    # Gear A
    gear_a_rotated = gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        gear_a_rotated,
        name="gear_a",
        loc=cq.Location(cq.Vector(gear_a_center, 0, 0)),
        color=cq.Color("steelblue"),
    )

    # Gear B
    gear_b_rotated = gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        gear_b_rotated,
        name="gear_b",
        loc=cq.Location(cq.Vector(gear_b_center, 0, 0)),
        color=cq.Color("darkorange"),
    )

    # Dog clutch
    clutch_rotated = dog_clutch.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        clutch_rotated,
        name="dog_clutch",
        loc=cq.Location(cq.Vector(clutch_center, 0, 0)),
        color=cq.Color("forestgreen"),
    )

    # Selector axle
    axle_start = gear_a_center - face_width / 2 - 10
    axle_end = gear_b_center + face_width / 2 + 10
    axle_length = axle_end - axle_start

    selector_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(axle_length)
        .translate((axle_start, 0, 0))
    )

    assy.add(
        selector_axle,
        name="selector_axle",
        color=cq.Color("gray"),
    )

    # Shift lever - positioned at clutch location
    assy.add(
        shift_lever,
        name="shift_lever",
        loc=cq.Location(cq.Vector(clutch_center, 0, 0)),
        color=cq.Color("red"),
    )

    # --- Bevel gear pair (driven axle connects to shift lever pivot) ---

    # The shift lever pivot is at:
    #   X = clutch_center
    #   Y = pivot_y
    #   Z = 0
    # The pivot rotates around the Z-axis
    # Apex of both bevel cones should meet at the pivot point

    mesh_offset_angle = tooth_angle / 2

    # Driven bevel gear: on Z-axis, teeth pointing +Z toward apex
    # Position at Z = -mesh_distance so teeth reach the apex at Z = 0
    # (default orientation has teeth pointing +Z, so no flip needed)
    assy.add(
        driven_bevel,
        name="driven_bevel",
        loc=cq.Location(cq.Vector(clutch_center, pivot_y, -mesh_distance)),
        color=cq.Color("gold"),
    )

    # Driving bevel gear: on X-axis, teeth facing +X toward apex
    # Flip 180° around X, add mesh alignment, rotate to X-axis orientation
    driving_rotated = (
        driving_bevel
        .rotate((0, 0, 0), (1, 0, 0), 180)  # Flip so teeth point other way
        .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)  # Mesh alignment
        .rotate((0, 0, 0), (0, 1, 0), -90)  # Rotate to X-axis orientation
    )

    # Position at X = clutch_center - mesh_distance (near gear A)
    assy.add(
        driving_rotated,
        name="driving_bevel",
        loc=cq.Location(cq.Vector(clutch_center - mesh_distance, pivot_y, 0)),
        color=cq.Color("purple"),
    )

    # --- Axles for bevel gears ---

    # Driven bevel axle: along Z-axis through the lever pivot
    # This connects to the shift lever pivot hole
    # Extends from gear (at Z = -mesh_distance) through pivot (Z = 0)
    bevel_axle_length = 40.0
    driven_bevel_axle = (
        cq.Workplane('XY')
        .circle(shaft_diameter / 2)
        .extrude(bevel_axle_length)
        .translate((clutch_center, pivot_y, -mesh_distance - 10))  # Start below gear
    )

    assy.add(
        driven_bevel_axle,
        name="driven_bevel_axle",
        color=cq.Color("slategray"),
    )

    # Driving bevel axle: along X-axis (input control), extending toward -X
    driving_bevel_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(-bevel_axle_length)  # Extend toward -X (toward gear A)
        .translate((clutch_center - mesh_distance, pivot_y, 0))
    )

    assy.add(
        driving_bevel_axle,
        name="driving_bevel_axle",
        color=cq.Color("slategray"),
    )

    # ==========================================================================
    # Export
    # ==========================================================================

    assy.save("combined_selector.step")
    print(f"\nExported: combined_selector.step")

    print(f"\nAssembly info:")
    print(f"  Gear A (blue): Input gear on selector axle")
    print(f"  Gear B (orange): Input gear on selector axle")
    print(f"  Dog clutch (green): Slides to engage A or B")
    print(f"  Shift lever (red): Fork engages clutch groove")
    print(f"  Driven bevel (gold): Axle connects to lever pivot")
    print(f"  Driving bevel (purple): Control input - rotate to shift gears")
    print(f"")
    print(f"Operation:")
    print(f"  Rotating the purple driving bevel gear rotates the gold driven gear,")
    print(f"  which rotates the shift lever around its pivot, moving the dog clutch")
    print(f"  along the selector axle to engage either gear A or gear B.")


if __name__ == "__main__":
    main()
