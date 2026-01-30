"""Generate a bevel gear pair submodel with proper meshing alignment.

Creates two identical bevel gears positioned at 90° to each other,
with their pitch cones meeting at a common apex for proper meshing.
"""

import math
import cadquery as cq
import yaml

from src.mechlogic.models.spec import LogicElementSpec
from src.mechlogic.models.geometry import PartPlacement, PartType
from src.mechlogic.generators.gear_bevel import BevelGearGenerator


def main():
    # Load the example spec
    with open("examples/mux_2to1.yaml") as f:
        spec_data = yaml.safe_load(f)

    spec = LogicElementSpec.model_validate(spec_data)

    # Create generators
    driving_gen = BevelGearGenerator(gear_id="driving")
    driven_gen = BevelGearGenerator(gear_id="driven")

    # Generate gears
    driving_placement = PartPlacement(
        part_type=PartType.BEVEL_DRIVE,
        part_id="bevel_driving",
    )
    driven_placement = PartPlacement(
        part_type=PartType.BEVEL_DRIVEN,
        part_id="bevel_driven",
    )

    driving_gear = driving_gen.generate(spec, driving_placement)
    driven_gear = driven_gen.generate(spec, driven_placement)

    # Get geometry info for positioning
    module = spec.gears.module
    teeth = spec.gears.bevel_teeth
    pitch_radius = (module * teeth) / 2
    cone_angle = 45.0  # degrees
    cone_distance = driving_gen.get_cone_distance(spec)
    face_width = driving_gen.get_face_width(spec)
    tooth_angle = 360.0 / teeth

    print(f"Bevel Gear Pair Geometry:")
    print(f"  Module: {module} mm")
    print(f"  Teeth: {teeth}")
    print(f"  Pitch diameter: {module * teeth:.2f} mm")
    print(f"  Pitch radius: {pitch_radius:.2f} mm")
    print(f"  Cone angle: {cone_angle}°")
    print(f"  Cone distance: {cone_distance:.2f} mm")
    print(f"  Face width: {face_width:.2f} mm")
    print(f"  Tooth angle: {tooth_angle:.2f}°")

    # ==========================================================================
    # Position gears for 90° meshing
    #
    # cq_gears bevel gear orientation:
    #   - Teeth point toward +Z (small end at top)
    #   - Hub extends in -Z direction
    #   - Gear back face (large end of teeth) is near Z=0
    #
    # For meshing, both pitch cone apexes must meet at a common point.
    # The apex is located at distance = cone_distance from the pitch circle,
    # measured along the cone surface (which at 45° means along Z-axis too).
    #
    # Gear back face is at Z ≈ 0, so apex is at approximately Z = cone_distance
    # ==========================================================================

    # Create assembly with gears meshing at the origin area
    assy = cq.Assembly()

    # Driving gear: on Z-axis, teeth pointing up (+Z)
    # The mesh offset is empirically determined to bring teeth into contact
    # (cone_distance positions apexes together, but teeth don't reach that far)
    mesh_distance = cone_distance * 0.79  # Adjusted for proper tooth engagement
    driving_offset = -mesh_distance

    assy.add(
        driving_gear,
        name="driving_gear",
        loc=cq.Location(cq.Vector(0, 0, driving_offset)),
        color=cq.Color("steelblue"),
    )

    # Driven gear: on X-axis (rotated 90° around Y-axis)
    # The gear must be flipped so teeth face toward the driving gear
    # Also rotate around its axis by half a tooth pitch for proper mesh interleaving
    mesh_offset_angle = tooth_angle / 2  # Rotate to align teeth with gaps

    # Pre-rotate: flip 180° around X to point teeth inward, then mesh alignment around Z
    driven_rotated = (
        driven_gear
        .rotate((0, 0, 0), (1, 0, 0), 180)  # Flip so teeth point other way
        .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)  # Mesh alignment
    )

    # Position: rotate 90° around Y, then translate along -X
    assy.add(
        driven_rotated,
        name="driven_gear",
        loc=cq.Location(
            cq.Vector(-mesh_distance, 0, 0),  # Translate along -X
            cq.Vector(0, 1, 0),  # Rotation axis (Y)
            -90  # Rotation angle
        ),
        color=cq.Color("darkorange"),
    )

    # Create axles through the gears
    shaft_diameter = spec.primary_shaft_diameter  # 6.0mm
    axle_length = 50.0  # Length of each axle

    # Driving axle: along Z-axis
    # Truncate so it doesn't intersect with the driven axle (which is at Z=0)
    # Stop at Z = -(shaft_diameter/2 + clearance) to clear the other axle
    axle_clearance = 0.5
    driving_axle_top = -(shaft_diameter / 2 + axle_clearance)  # Where axle stops (just below driven axle)
    driving_axle_bottom = -mesh_distance - 30  # Extend 30mm below the gear
    driving_axle_length = driving_axle_top - driving_axle_bottom

    driving_axle = (
        cq.Workplane('XY')
        .workplane(offset=driving_axle_bottom)
        .circle(shaft_diameter / 2)
        .extrude(driving_axle_length)
    )

    assy.add(
        driving_axle,
        name="driving_axle",
        color=cq.Color("gray"),
    )

    # Driven axle: along X-axis (after 90° rotation)
    driven_axle = (
        cq.Workplane('YZ')
        .circle(shaft_diameter / 2)
        .extrude(axle_length)
        .translate((-mesh_distance - axle_length / 2, 0, 0))
    )

    assy.add(
        driven_axle,
        name="driven_axle",
        color=cq.Color("gray"),
    )


    # Export assembly
    assy.save("bevel_gear_pair.step")
    print(f"\nExported: bevel_gear_pair.step")

    # Also export individual gears for reference
    cq.exporters.export(driving_gear, "bevel_driving.step")
    cq.exporters.export(driven_gear, "bevel_driven.step")
    print("Exported: bevel_driving.step")
    print("Exported: bevel_driven.step")

    print(f"\nAssembly info:")
    print(f"  Driving gear: Blue, on Z-axis (teeth up)")
    print(f"  Driven gear: Orange, on X-axis (teeth toward -X)")
    print(f"  Apex: At origin (0, 0, 0)")
    print(f"  Shaft angle: 90°")


if __name__ == "__main__":
    main()
