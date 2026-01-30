"""Generate a gear selector mechanism.

Creates:
- Two spur gears that freely rotate on a common axle
- A dog clutch between them that slides along the axle
- The dog clutch engages with inner teeth on either gear to transfer drive
"""

import math
import cadquery as cq
import yaml

from src.mechlogic.models.spec import LogicElementSpec
from src.mechlogic.models.geometry import PartPlacement, PartType
from src.mechlogic.generators.gear_spur import SpurGearGenerator
from src.mechlogic.generators.dog_clutch import DogClutchGenerator
from src.mechlogic.generators.shift_lever import ShiftLeverGenerator


def main():
    # Load the example spec
    with open("examples/mux_2to1.yaml") as f:
        spec_data = yaml.safe_load(f)

    spec = LogicElementSpec.model_validate(spec_data)

    # Get dimensions from spec
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    shaft_diameter = spec.primary_shaft_diameter
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    # Calculate positions along the axle (X-axis)
    # Layout: [Gear A] [gap] [Dog Clutch] [gap] [Gear B]
    # The dog clutch can slide to engage either gear
    #
    # After rotation, components span in X:
    #   Gear: 0 to face_width (body) + dog_tooth_height (teeth) = 0 to 10
    #   Clutch: center ± (clutch_width/2 + dog_tooth_height) = center ± 7
    #
    # In NEUTRAL position, clutch teeth should have a gap from gear teeth
    # Engagement travel = gear_spacing + dog_tooth_height

    clutch_half_span = clutch_width / 2 + dog_tooth_height  # How far clutch extends from center
    gear_teeth_end = face_width + dog_tooth_height  # Where gear teeth end

    gear_a_center = 0
    # Neutral: clutch teeth tip at gear_teeth_end + gear_spacing
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span

    # Engagement travel distance
    engagement_travel = gear_spacing + dog_tooth_height

    # Gear B positioning:
    # After rotation, gear B spans from (center - dog_tooth_height) to (center + face_width)
    # with teeth at the low-X side (toward clutch)
    # When clutch engages (+engagement_travel), clutch teeth reach: clutch_center + clutch_half_span
    # Gear B teeth should be at that position
    # Gear B teeth are at gear_b_center - dog_tooth_height to gear_b_center
    # So: gear_b_center = clutch_center + engagement_travel + clutch_half_span
    gear_b_center = clutch_center + engagement_travel + clutch_half_span

    print(f"Selector Mechanism Layout:")
    print(f"  Gear face width: {face_width} mm")
    print(f"  Clutch width: {clutch_width} mm")
    print(f"  Dog tooth height: {dog_tooth_height} mm")
    print(f"  Gear spacing: {gear_spacing} mm")
    print(f"  Engagement travel: {engagement_travel} mm")
    print(f"")
    print(f"  Gear A center: X = {gear_a_center:.1f} mm")
    print(f"  Clutch center (neutral): X = {clutch_center:.1f} mm")
    print(f"  Gear B center: X = {gear_b_center:.1f} mm")
    print(f"")
    print(f"  Clutch engaged with A: X = {clutch_center - engagement_travel:.1f} mm")
    print(f"  Clutch engaged with B: X = {clutch_center + engagement_travel:.1f} mm")

    # Generate components
    gear_a_gen = SpurGearGenerator(gear_id="a")
    gear_b_gen = SpurGearGenerator(gear_id="b")
    clutch_gen = DogClutchGenerator()

    placement_a = PartPlacement(part_type=PartType.GEAR_A, part_id="gear_a")
    placement_b = PartPlacement(part_type=PartType.GEAR_B, part_id="gear_b")
    placement_clutch = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="dog_clutch")

    gear_a = gear_a_gen.generate(spec, placement_a)
    gear_b = gear_b_gen.generate(spec, placement_b)
    dog_clutch = clutch_gen.generate(spec, placement_clutch)

    # Create assembly
    assy = cq.Assembly()

    # The spur gears and clutch are built with Z as the axle direction
    # We need to rotate them 90° so the axle is along X

    # Gear A: rotate to align with X-axis, position at gear_a_center
    gear_a_rotated = gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        gear_a_rotated,
        name="gear_a",
        loc=cq.Location(cq.Vector(gear_a_center, 0, 0)),
        color=cq.Color("steelblue"),
    )

    # Gear B: rotate to align with X-axis, position at gear_b_center
    gear_b_rotated = gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        gear_b_rotated,
        name="gear_b",
        loc=cq.Location(cq.Vector(gear_b_center, 0, 0)),
        color=cq.Color("darkorange"),
    )

    # Dog clutch: rotate to align with X-axis, position at clutch_center
    clutch_rotated = dog_clutch.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        clutch_rotated,
        name="dog_clutch",
        loc=cq.Location(cq.Vector(clutch_center, 0, 0)),
        color=cq.Color("forestgreen"),
    )

    # Add the axle through all components
    axle_start = gear_a_center - face_width / 2 - 10
    axle_end = gear_b_center + face_width / 2 + 10
    axle_length = axle_end - axle_start

    axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(axle_length)
        .translate((axle_start, 0, 0))
    )

    assy.add(
        axle,
        name="selector_axle",
        color=cq.Color("gray"),
    )

    # Add shift lever
    lever_gen = ShiftLeverGenerator()
    placement_lever = PartPlacement(part_type=PartType.DOG_CLUTCH, part_id="shift_lever")
    shift_lever = lever_gen.generate(spec, placement_lever)

    # Position lever at the clutch location
    # The lever fork engages the clutch groove
    assy.add(
        shift_lever,
        name="shift_lever",
        loc=cq.Location(cq.Vector(clutch_center, 0, 0)),
        color=cq.Color("red"),
    )

    # Export shift lever individually
    cq.exporters.export(shift_lever, "selector_shift_lever.step")

    # Export
    assy.save("selector_mechanism.step")
    print(f"\nExported: selector_mechanism.step")

    # Also export individual components
    cq.exporters.export(gear_a, "selector_gear_a.step")
    cq.exporters.export(gear_b, "selector_gear_b.step")
    cq.exporters.export(dog_clutch, "selector_dog_clutch.step")
    print("Exported: selector_gear_a.step")
    print("Exported: selector_gear_b.step")
    print("Exported: selector_dog_clutch.step")
    print("Exported: selector_shift_lever.step")

    print(f"\nMechanism info:")
    print(f"  Gear A (blue): Freely rotates on axle, dog teeth face toward clutch")
    print(f"  Gear B (orange): Freely rotates on axle, dog teeth face toward clutch")
    print(f"  Dog clutch (green): Slides on axle, engages either gear")
    print(f"  Shift lever (red): Rotates to move clutch, fork engages groove")
    print(f"  Axle (gray): Fixed, clutch is keyed to it")


if __name__ == "__main__":
    main()
