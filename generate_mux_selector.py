"""Generate a 2-to-1 multiplexer selector mechanism.

This mechanism has:
- Two input shafts (A, B) that drive the selector gears
- Input A drives gear A via meshing spur gears (offset in +Z)
- Input B drives gear B via meshing spur gears (offset in -Z)
- Bevel gear pair for shift control (to be driven externally)
- Dog clutch selects between A and B for the output

Layout (side view, XZ plane at Y=0):

    Z (mm)
      ^
      |  +36  ----[Input A]------------------
      |              ↓
      |    0  ----[Gear A]═══[Clutch]═══[Gear B]----
      |                                    ↑
      | -36  -------------------------[Input B]----
      |
      └──────────────────────────────────────────► X (mm)
              0         18        28

Layout (front view, XY plane at Z=0):

    Y (mm)
      ^
      |  34.2  --[Driving Bevel]----[Driven Bevel]--
      |                                   |
      |                              [Shift Lever]
      |                                   |
      |    0  ----[Gear A]═══[Clutch]═══[Gear B]----
      |
      └──────────────────────────────────────────► X (mm)
              4.6       18        28
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

    # Gear parameters
    module = spec.gears.module
    coaxial_teeth = spec.gears.coaxial_teeth
    bevel_teeth = spec.gears.bevel_teeth
    shaft_diameter = spec.primary_shaft_diameter

    # Spur gear dimensions
    spur_pitch_radius = (module * coaxial_teeth) / 2
    spur_pitch_diameter = module * coaxial_teeth

    # Selector mechanism dimensions
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    # Calculate selector positions along X-axis
    clutch_half_span = clutch_width / 2 + dog_tooth_height
    gear_teeth_end = face_width + dog_tooth_height

    gear_a_center = 0
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span
    engagement_travel = gear_spacing + dog_tooth_height
    gear_b_center = clutch_center + engagement_travel + clutch_half_span

    # Selector axle position
    selector_axle_y = 0
    selector_axle_z = 0

    # Input gear positions - same X,Y as their target gears, offset in Z
    mesh_distance_spur = spur_pitch_diameter  # For same-size gears

    # Input A: above Gear A
    input_a_x = gear_a_center
    input_a_y = 0
    input_a_z = selector_axle_z + mesh_distance_spur

    # Input B: below Gear B
    input_b_x = gear_b_center
    input_b_y = 0
    input_b_z = selector_axle_z - mesh_distance_spur

    # Shift lever pivot location
    gear_od = spur_pitch_diameter
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27  # Must match shift_lever.py

    # Bevel gear dimensions
    bevel_gen = BevelGearGenerator(gear_id="driving")
    cone_distance = bevel_gen.get_cone_distance(spec)
    bevel_mesh_distance = cone_distance * 0.79
    bevel_tooth_angle = 360.0 / bevel_teeth

    print(f"2-to-1 Multiplexer Selector Layout:")
    print(f"  Module: {module} mm")
    print(f"  Spur pitch diameter: {spur_pitch_diameter:.1f} mm")
    print(f"  Mesh distance (Z offset): {mesh_distance_spur:.1f} mm")
    print(f"")
    print(f"  Selector axle: Y={selector_axle_y}, Z={selector_axle_z}")
    print(f"  Gear A: X={gear_a_center:.1f}")
    print(f"  Clutch: X={clutch_center:.1f}")
    print(f"  Gear B: X={gear_b_center:.1f}")
    print(f"")
    print(f"  Input A: X={input_a_x:.1f}, Y={input_a_y}, Z={input_a_z:.1f} (above Gear A)")
    print(f"  Input B: X={input_b_x:.1f}, Y={input_b_y}, Z={input_b_z:.1f} (below Gear B)")
    print(f"")
    print(f"  Lever pivot: X={clutch_center:.1f}, Y={pivot_y:.1f}")
    print(f"  Driving bevel: X={clutch_center - bevel_mesh_distance:.1f}, Y={pivot_y:.1f}")
    print(f"  Driven bevel: X={clutch_center:.1f}, Y={pivot_y:.1f}, Z={-bevel_mesh_distance:.1f}")

    # ==========================================================================
    # Generate components
    # ==========================================================================

    # Selector mechanism gears
    gear_a_gen = SpurGearGenerator(gear_id="a")
    gear_b_gen = SpurGearGenerator(gear_id="b")
    clutch_gen = DogClutchGenerator()
    lever_gen = ShiftLeverGenerator()

    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="test")

    gear_a = gear_a_gen.generate(spec, placement)
    gear_b = gear_b_gen.generate(spec, placement)
    dog_clutch = clutch_gen.generate(spec, placement)
    shift_lever = lever_gen.generate(spec, placement)

    # Input spur gears (same as selector gears)
    input_gear_a = gear_a_gen.generate(spec, placement)
    input_gear_b = gear_b_gen.generate(spec, placement)

    # Bevel gears
    driving_bevel_gen = BevelGearGenerator(gear_id="driving")
    driven_bevel_gen = BevelGearGenerator(gear_id="driven")

    driving_bevel = driving_bevel_gen.generate(spec, placement)
    driven_bevel = driven_bevel_gen.generate(spec, placement)

    # ==========================================================================
    # Create assembly
    # ==========================================================================

    assy = cq.Assembly()

    # --- Selector mechanism (at Y=0, Z=0) ---

    # Gear A
    gear_a_rotated = gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        gear_a_rotated,
        name="gear_a",
        loc=cq.Location(cq.Vector(gear_a_center, selector_axle_y, selector_axle_z)),
        color=cq.Color("steelblue"),
    )

    # Gear B
    gear_b_rotated = gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        gear_b_rotated,
        name="gear_b",
        loc=cq.Location(cq.Vector(gear_b_center, selector_axle_y, selector_axle_z)),
        color=cq.Color("darkorange"),
    )

    # Dog clutch
    clutch_rotated = dog_clutch.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        clutch_rotated,
        name="dog_clutch",
        loc=cq.Location(cq.Vector(clutch_center, selector_axle_y, selector_axle_z)),
        color=cq.Color("forestgreen"),
    )

    # Selector axle
    axle_start = gear_a_center - face_width / 2 - 10
    axle_end = gear_b_center + face_width / 2 + 10
    selector_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(axle_end - axle_start)
        .translate((axle_start, selector_axle_y, selector_axle_z))
    )
    assy.add(selector_axle, name="selector_axle", color=cq.Color("gray"))

    # Shift lever
    assy.add(
        shift_lever,
        name="shift_lever",
        loc=cq.Location(cq.Vector(clutch_center, selector_axle_y, selector_axle_z)),
        color=cq.Color("red"),
    )

    # --- Input A (above Gear A, at Z = +36) ---

    input_a_axle_start = input_a_x - face_width / 2 - 10
    input_a_axle_end = input_a_x + face_width / 2 + 10
    input_a_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(input_a_axle_end - input_a_axle_start)
        .translate((input_a_axle_start, input_a_y, input_a_z))
    )
    assy.add(input_a_axle, name="input_a_axle", color=cq.Color("gray"))

    input_a_rotated = input_gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        input_a_rotated,
        name="input_gear_a",
        loc=cq.Location(cq.Vector(input_a_x, input_a_y, input_a_z)),
        color=cq.Color("lightsteelblue"),
    )

    # --- Input B (below Gear B, at Z = -36) ---

    input_b_axle_start = input_b_x - face_width / 2 - 10
    input_b_axle_end = input_b_x + face_width / 2 + 10
    input_b_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(input_b_axle_end - input_b_axle_start)
        .translate((input_b_axle_start, input_b_y, input_b_z))
    )
    assy.add(input_b_axle, name="input_b_axle", color=cq.Color("gray"))

    input_b_rotated = input_gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(
        input_b_rotated,
        name="input_gear_b",
        loc=cq.Location(cq.Vector(input_b_x, input_b_y, input_b_z)),
        color=cq.Color("sandybrown"),
    )

    # --- Bevel gear pair (same configuration as combined_selector) ---

    # The shift lever pivot is at (clutch_center, pivot_y, 0)
    # Apex of both bevel cones meets at the pivot point

    mesh_offset_angle = bevel_tooth_angle / 2

    # Driven bevel gear: on Z-axis, teeth pointing +Z toward apex
    # Position at Z = -mesh_distance so teeth reach the apex at Z = 0
    assy.add(
        driven_bevel,
        name="driven_bevel",
        loc=cq.Location(cq.Vector(clutch_center, pivot_y, -bevel_mesh_distance)),
        color=cq.Color("gold"),
    )

    # Driving bevel gear: on X-axis, teeth facing +X toward apex
    driving_bevel_rotated = (
        driving_bevel
        .rotate((0, 0, 0), (1, 0, 0), 180)  # Flip so teeth point other way
        .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)  # Mesh alignment
        .rotate((0, 0, 0), (0, 1, 0), -90)  # Rotate to X-axis orientation
    )
    assy.add(
        driving_bevel_rotated,
        name="driving_bevel",
        loc=cq.Location(cq.Vector(clutch_center - bevel_mesh_distance, pivot_y, 0)),
        color=cq.Color("purple"),
    )

    # --- Bevel gear axles ---

    bevel_axle_length = 40.0

    # Driven bevel axle: along Z-axis through the lever pivot
    driven_bevel_axle = (
        cq.Workplane('XY')
        .circle(shaft_diameter / 2)
        .extrude(bevel_axle_length)
        .translate((clutch_center, pivot_y, -bevel_mesh_distance - 10))
    )
    assy.add(driven_bevel_axle, name="driven_bevel_axle", color=cq.Color("slategray"))

    # Driving bevel axle: along X-axis, extending toward -X
    driving_bevel_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(-bevel_axle_length)
        .translate((clutch_center - bevel_mesh_distance, pivot_y, 0))
    )
    assy.add(driving_bevel_axle, name="driving_bevel_axle", color=cq.Color("slategray"))

    # ==========================================================================
    # Export
    # ==========================================================================

    assy.save("mux_selector.step")
    print(f"\nExported: mux_selector.step")

    print(f"\nAssembly components:")
    print(f"  Gear A (blue): On selector axle, driven by Input A")
    print(f"  Gear B (orange): On selector axle, driven by Input B")
    print(f"  Input A gear (light blue): Above Gear A, meshes via Z offset")
    print(f"  Input B gear (tan): Below Gear B, meshes via Z offset")
    print(f"  Dog clutch (green): Slides to engage A or B")
    print(f"  Shift lever (red): Moves dog clutch")
    print(f"  Driving bevel (purple): Control input for shifting")
    print(f"  Driven bevel (gold): Connects to shift lever pivot")
    print(f"")
    print(f"Operation:")
    print(f"  - Rotating Input A turns Gear A")
    print(f"  - Rotating Input B turns Gear B")
    print(f"  - Rotating Driving Bevel shifts the dog clutch")
    print(f"  - Output comes from whichever gear the clutch engages")


if __name__ == "__main__":
    main()
