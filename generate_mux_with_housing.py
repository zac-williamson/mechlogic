"""Generate the complete mux selector with housing assembly."""

import cadquery as cq
import yaml

from src.mechlogic.models.spec import LogicElementSpec
from src.mechlogic.models.geometry import PartPlacement, PartType
from src.mechlogic.generators.gear_spur import SpurGearGenerator
from src.mechlogic.generators.dog_clutch import DogClutchGenerator
from src.mechlogic.generators.shift_lever import ShiftLeverGenerator
from src.mechlogic.generators.gear_bevel import BevelGearGenerator
from src.mechlogic.generators.lower_housing import LowerHousingGenerator, LowerHousingParams


def main():
    # Load spec
    with open("examples/mux_2to1.yaml") as f:
        spec_data = yaml.safe_load(f)
    spec = LogicElementSpec.model_validate(spec_data)

    # Calculate positions (same as generate_mux_selector.py)
    module = spec.gears.module
    coaxial_teeth = spec.gears.coaxial_teeth
    bevel_teeth = spec.gears.bevel_teeth
    shaft_diameter = spec.primary_shaft_diameter

    spur_pitch_diameter = module * coaxial_teeth
    face_width = spec.geometry.gear_face_width
    clutch_width = spec.geometry.clutch_width
    gear_spacing = spec.geometry.gear_spacing
    dog_tooth_height = spec.gears.dog_clutch.tooth_height

    clutch_half_span = clutch_width / 2 + dog_tooth_height
    gear_teeth_end = face_width + dog_tooth_height

    gear_a_center = 0
    clutch_center = gear_teeth_end + gear_spacing + clutch_half_span
    gear_b_center = clutch_center + (gear_spacing + dog_tooth_height) + clutch_half_span

    selector_axle_y = 0
    selector_axle_z = 0
    mesh_distance_spur = spur_pitch_diameter

    input_a_x, input_a_y, input_a_z = gear_a_center, 0, mesh_distance_spur
    input_b_x, input_b_y, input_b_z = gear_b_center, 0, -mesh_distance_spur

    gear_od = spur_pitch_diameter
    clutch_od = gear_od * 0.4
    pivot_y = clutch_od / 2 + 27

    bevel_gen = BevelGearGenerator(gear_id="driving")
    bevel_mesh_distance = bevel_gen.get_cone_distance(spec) * 0.79
    bevel_tooth_angle = 360.0 / bevel_teeth

    # Generate mechanism components
    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="test")

    gear_a_gen = SpurGearGenerator(gear_id="a")
    gear_b_gen = SpurGearGenerator(gear_id="b")
    clutch_gen = DogClutchGenerator()
    lever_gen = ShiftLeverGenerator()
    driving_bevel_gen = BevelGearGenerator(gear_id="driving")
    driven_bevel_gen = BevelGearGenerator(gear_id="driven")

    gear_a = gear_a_gen.generate(spec, placement)
    gear_b = gear_b_gen.generate(spec, placement)
    dog_clutch = clutch_gen.generate(spec, placement)
    shift_lever = lever_gen.generate(spec, placement)
    input_gear_a = gear_a_gen.generate(spec, placement)
    input_gear_b = gear_b_gen.generate(spec, placement)
    driving_bevel = driving_bevel_gen.generate(spec, placement)
    driven_bevel = driven_bevel_gen.generate(spec, placement)

    # Generate housing
    housing_params = LowerHousingParams()
    housing_gen = LowerHousingGenerator(housing_params)
    housing_bottom, housing_top = housing_gen.generate()

    # Create assembly
    assy = cq.Assembly()

    # Add housing (semi-transparent)
    assy.add(housing_bottom, name="housing_bottom", color=cq.Color(0.7, 0.7, 0.7, 0.3))
    assy.add(housing_top, name="housing_top", color=cq.Color(0.6, 0.6, 0.6, 0.3))

    # Add mechanism components

    # Gear A
    gear_a_rotated = gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(gear_a_rotated, name="gear_a",
             loc=cq.Location(cq.Vector(gear_a_center, selector_axle_y, selector_axle_z)),
             color=cq.Color("steelblue"))

    # Gear B
    gear_b_rotated = gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(gear_b_rotated, name="gear_b",
             loc=cq.Location(cq.Vector(gear_b_center, selector_axle_y, selector_axle_z)),
             color=cq.Color("darkorange"))

    # Dog clutch
    clutch_rotated = dog_clutch.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(clutch_rotated, name="dog_clutch",
             loc=cq.Location(cq.Vector(clutch_center, selector_axle_y, selector_axle_z)),
             color=cq.Color("forestgreen"))

    # Shift lever
    assy.add(shift_lever, name="shift_lever",
             loc=cq.Location(cq.Vector(clutch_center, selector_axle_y, selector_axle_z)),
             color=cq.Color("red"))

    # Input gear A
    input_a_rotated = input_gear_a.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(input_a_rotated, name="input_gear_a",
             loc=cq.Location(cq.Vector(input_a_x, input_a_y, input_a_z)),
             color=cq.Color("lightsteelblue"))

    # Input gear B
    input_b_rotated = input_gear_b.rotate((0, 0, 0), (0, 1, 0), 90)
    assy.add(input_b_rotated, name="input_gear_b",
             loc=cq.Location(cq.Vector(input_b_x, input_b_y, input_b_z)),
             color=cq.Color("sandybrown"))

    # Driven bevel
    assy.add(driven_bevel, name="driven_bevel",
             loc=cq.Location(cq.Vector(clutch_center, pivot_y, -bevel_mesh_distance)),
             color=cq.Color("gold"))

    # Driving bevel
    mesh_offset_angle = bevel_tooth_angle / 2
    driving_bevel_rotated = (
        driving_bevel
        .rotate((0, 0, 0), (1, 0, 0), 180)
        .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)
        .rotate((0, 0, 0), (0, 1, 0), -90)
    )
    assy.add(driving_bevel_rotated, name="driving_bevel",
             loc=cq.Location(cq.Vector(clutch_center - bevel_mesh_distance, pivot_y, 0)),
             color=cq.Color("purple"))

    # Axles (simplified as cylinders)
    axle_length = 80

    # Selector axle
    selector_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(axle_length)
        .translate((-axle_length/2 + clutch_center, selector_axle_y, selector_axle_z))
    )
    assy.add(selector_axle, name="selector_axle", color=cq.Color("gray"))

    # Input A axle
    input_a_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(30)
        .translate((input_a_x - 15, input_a_y, input_a_z))
    )
    assy.add(input_a_axle, name="input_a_axle", color=cq.Color("gray"))

    # Input B axle
    input_b_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(30)
        .translate((input_b_x - 15, input_b_y, input_b_z))
    )
    assy.add(input_b_axle, name="input_b_axle", color=cq.Color("gray"))

    # Driving bevel axle
    driving_bevel_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(-50)
        .translate((clutch_center - bevel_mesh_distance, pivot_y, 0))
    )
    assy.add(driving_bevel_axle, name="driving_bevel_axle", color=cq.Color("gray"))

    # Driven bevel axle
    driven_bevel_axle = (
        cq.Workplane('XY')
        .circle(shaft_diameter / 2)
        .extrude(50)
        .translate((clutch_center, pivot_y, -bevel_mesh_distance - 15))
    )
    assy.add(driven_bevel_axle, name="driven_bevel_axle", color=cq.Color("gray"))

    # Export
    assy.save("mux_complete_assembly.step")
    print("Exported: mux_complete_assembly.step")

    print(f"\nAssembly includes:")
    print(f"  - Housing (bottom + top halves)")
    print(f"  - Selector mechanism (gears A, B, clutch, lever)")
    print(f"  - Input gears A and B")
    print(f"  - Bevel gear pair")
    print(f"  - All axles")


if __name__ == "__main__":
    main()
