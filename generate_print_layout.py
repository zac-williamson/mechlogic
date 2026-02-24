#!/usr/bin/env python3
"""Generate a flat print layout of all mux assembly parts.

Takes each part from the mux_complete_assembly and lays them out
on the XY plane (Z=0) with spacing for 3D printing.

Usage:
    python generate_print_layout.py [--output OUTPUT]
"""

import argparse
from pathlib import Path

import yaml
import cadquery as cq

from src.mechlogic.models.spec import LogicElementSpec
from src.mechlogic.models.geometry import PartPlacement, PartType
from src.mechlogic.generators.layout import LayoutCalculator
from src.mechlogic.generators.gear_spur import SpurGearGenerator
from src.mechlogic.generators.dog_clutch import DogClutchGenerator
from src.mechlogic.generators.gear_bevel import BevelGearGenerator
from src.mechlogic.generators.shift_lever import ShiftLeverGenerator
from src.mechlogic.generators.lower_housing import LowerHousingGenerator
from src.mechlogic.generators.bevel_lever_with_upper_housing import BevelLeverWithUpperHousingGenerator
from src.mechlogic.generators.serpentine_flexure import SerpentineFlexureGenerator
from src.mechlogic.generators.lower_housing import LowerHousingParams
from src.mechlogic.generators.axle_profile import (
    make_d_flat_axle, make_d_flat_axle_along_z, add_groove_to_axle, make_c_clip,
)
from src.mechlogic.generators.gear_bevel import BevelGearGenerator


def load_spec(spec_file: Path) -> LogicElementSpec:
    with open(spec_file) as f:
        data = yaml.safe_load(f)
    return LogicElementSpec.model_validate(data)


def generate_parts(spec: LogicElementSpec) -> list:
    """Generate all individual parts and return (name, shape, approx_size) tuples."""
    layout = LayoutCalculator.calculate_mux_layout(spec)
    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="print")

    parts = []

    # --- Coaxial Spur Gears (free-spinning on axle, engaged via dog clutch) ---
    gear_od = spec.gears.module * spec.gears.coaxial_teeth + 2 * spec.gears.module

    coaxial_a_gen = SpurGearGenerator(gear_id="a", free_spinning=True)
    coaxial_a = coaxial_a_gen.generate(spec, placement)
    parts.append(("gear_a", coaxial_a, gear_od))

    coaxial_b_gen = SpurGearGenerator(gear_id="b", free_spinning=True)
    coaxial_b = coaxial_b_gen.generate(spec, placement)
    # Flip so dog teeth point up (+Z) for printing without supports
    coaxial_b = coaxial_b.rotate((0, 0, 0), (1, 0, 0), 180)
    parts.append(("gear_b", coaxial_b, gear_od))

    # --- Input Spur Gears (friction-fit on axle, no dog teeth) ---
    input_gen = SpurGearGenerator(gear_id="a", include_dog_teeth=False)
    input_gear = input_gen.generate(spec, placement)
    parts.append(("input_gear_a", input_gear, gear_od))
    parts.append(("input_gear_b", input_gear, gear_od))

    # --- Dog Clutch (two separate pieces: inner core + outer sleeve) ---
    clutch_gen = DogClutchGenerator()
    clutch_od = gear_od * 0.4

    inner_core = clutch_gen.generate_inner_core(spec)
    core_od = spec.primary_shaft_diameter + DogClutchGenerator.CORE_OD_OFFSET
    parts.append(("clutch_inner_core", inner_core, core_od + 2))

    outer_sleeve = clutch_gen.generate_outer_sleeve(spec)
    parts.append(("clutch_outer_sleeve", outer_sleeve, clutch_od + 2))

    # --- Bevel Gears (driving + driven) ---
    bevel_gen = BevelGearGenerator(gear_id="driving")
    driving_bevel = bevel_gen.generate(spec, placement)
    bevel_size = 25.0  # Approximate bevel gear size
    parts.append(("driving_bevel", driving_bevel, bevel_size))

    driven_bevel_gen = BevelGearGenerator(gear_id="driven")
    driven_bevel = driven_bevel_gen.generate(spec, placement)
    parts.append(("driven_bevel", driven_bevel, bevel_size))

    # --- Shift Lever ---
    lever_gen = ShiftLeverGenerator()
    lever = lever_gen.generate(spec, placement)
    parts.append(("shift_lever", lever, 35.0))

    # --- Lower Housing (split into left and right halves) ---
    housing_gen = LowerHousingGenerator(spec=spec)
    lower_params = LowerHousingParams.from_spec(spec)

    lower_left, lower_right = housing_gen.generate_split()

    for name, half in [("lower_housing_left", lower_left), ("lower_housing_right", lower_right)]:
        bb = half.val().BoundingBox()
        half_origin = half.translate((-bb.xmin, -bb.ymin, -bb.zmin))
        parts.append((name, half_origin,
                       max(bb.xmax - bb.xmin, bb.ymax - bb.ymin,
                           bb.zmax - bb.zmin)))

    # --- Upper Housing (split into left and right halves) ---
    selector_layout = LayoutCalculator.calculate_selector_layout(spec)
    origin = (selector_layout.clutch_center, 0, 0)

    upper_gen = BevelLeverWithUpperHousingGenerator(
        include_axles=False,
        include_flexure=True,
        extend_to_lower_housing=True,
        lower_housing_y_max=lower_params.plate_y_max,
        l_shaped_front_back=False,
    )
    upper_left, upper_right = upper_gen.generate_split_upper_housing(spec, origin)

    for name, half in [("upper_housing_left", upper_left), ("upper_housing_right", upper_right)]:
        bb = half.val().BoundingBox()
        half_origin = half.translate((-bb.xmin, -bb.ymin, -bb.zmin))
        parts.append((name, half_origin,
                       max(bb.xmax - bb.xmin, bb.ymax - bb.ymin,
                           bb.zmax - bb.zmin)))

    # --- Serpentine Flexure ---
    try:
        flexure_shape = upper_gen._flexure_gen.generate()
        fl_bb = flexure_shape.val().BoundingBox()
        flexure_origin = flexure_shape.translate((
            -fl_bb.xmin, -fl_bb.ymin, -fl_bb.zmin
        ))
        parts.append(("serpentine_flexure", flexure_origin,
                       max(fl_bb.xmax - fl_bb.xmin, fl_bb.ymax - fl_bb.ymin)))
    except Exception as e:
        print(f"  Warning: could not generate flexure: {e}")

    # --- Printable D-flat Axles ---
    shaft_dia = spec.primary_shaft_diameter
    d_flat_depth = spec.tolerances.d_flat_depth
    housing_layout = LayoutCalculator.calculate_housing_layout(spec)

    # Selector axle (through-hole both sides) with retention grooves
    sel_axle_length = housing_layout.axle_length
    sel_axle_start = housing_layout.axle_start_x
    sel_axle = make_d_flat_axle(shaft_dia, sel_axle_length, d_flat_depth)

    # Grooves outboard of gear A and gear B (positions relative to axle start at X=0)
    face_width = spec.geometry.gear_face_width
    groove_offset = 1.0
    # Selector gear positions are absolute; convert to axle-local coordinates
    sel_groove_left = selector_layout.gear_a_center - groove_offset - sel_axle_start
    sel_groove_right = selector_layout.gear_b_center + face_width + groove_offset - sel_axle_start
    sel_axle = add_groove_to_axle(sel_axle, sel_groove_left, shaft_dia)
    sel_axle = add_groove_to_axle(sel_axle, sel_groove_right, shaft_dia)
    # Inner core retention grooves (axle-local coordinates)
    clutch_width = spec.geometry.clutch_width
    engagement_travel = selector_layout.engagement_travel
    core_length = clutch_width + 2 * engagement_travel + 2.0
    sel_core_groove_left = selector_layout.clutch_center - core_length / 2 - 1.0 - sel_axle_start
    sel_core_groove_right = selector_layout.clutch_center + core_length / 2 + 1.0 - sel_axle_start
    sel_axle = add_groove_to_axle(sel_axle, sel_core_groove_left, shaft_dia)
    sel_axle = add_groove_to_axle(sel_axle, sel_core_groove_right, shaft_dia)
    # Rotate so D-flat face (was +Y) lies on print bed (-Z)
    sel_axle = sel_axle.rotate((0, 0, 0), (1, 0, 0), -90)
    parts.append(("selector_axle", sel_axle, sel_axle_length))

    # Input axles with retention grooves
    input_axle_length = housing_layout.axle_length
    axle_start_x = housing_layout.axle_start_x
    for name, gear_x in [
        ("input_a_axle", layout.input_a_x),
        ("input_b_axle", layout.input_b_x),
    ]:
        axle = make_d_flat_axle(shaft_dia, input_axle_length, d_flat_depth)
        # Convert gear X to axle-local coordinate
        local_gear_x = gear_x - axle_start_x
        axle = add_groove_to_axle(axle, local_gear_x - groove_offset, shaft_dia)
        axle = add_groove_to_axle(axle, local_gear_x + face_width + groove_offset, shaft_dia)
        # Rotate so D-flat face lies on print bed
        axle = axle.rotate((0, 0, 0), (1, 0, 0), -90)
        parts.append((name, axle, input_axle_length))

    # Driving bevel axle with retention grooves
    bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
    bevel_face_width = BevelGearGenerator(gear_id="driving").get_face_width(spec)
    bevel_groove_offset = bevel_face_width + 1.0
    # Recompute driving axle length (mirrors bevel_lever_with_upper_housing._add_axles)
    wall_thickness = max(spec.geometry.housing_thickness, 6.0)
    left_wall_x = housing_layout.left_plate_x
    driving_axle_start = left_wall_x - wall_thickness / 2 - housing_layout.axle_overhang
    driving_gear_x = selector_layout.clutch_center - bevel_layout.mesh_distance
    lever_left_edge = selector_layout.clutch_center - 6.0
    driving_axle_end = min(driving_gear_x + 8, lever_left_edge - 2.0)
    driving_axle_length = driving_axle_end - driving_axle_start
    driving_axle = make_d_flat_axle(shaft_dia, driving_axle_length, d_flat_depth)
    # Grooves flanking driving bevel gear (axle-local coordinates)
    local_driving_gear_x = driving_gear_x - driving_axle_start
    driving_axle = add_groove_to_axle(driving_axle, local_driving_gear_x - bevel_groove_offset, shaft_dia)
    driving_axle = add_groove_to_axle(driving_axle, local_driving_gear_x + bevel_groove_offset, shaft_dia)
    # Rotate so D-flat face lies on print bed
    driving_axle = driving_axle.rotate((0, 0, 0), (1, 0, 0), -90)
    parts.append(("driving_bevel_axle", driving_axle, driving_axle_length))

    # Driven bevel axle with retention grooves
    # Use actual upper housing bounding box to ensure axle extends past flanges
    full_upper_housing = upper_gen._generate_upper_housing(spec, origin)
    upper_bb = full_upper_housing.val().BoundingBox()
    driven_axle_start = upper_bb.zmin - housing_layout.axle_overhang
    driven_axle_end = upper_bb.zmax + housing_layout.axle_overhang
    driven_axle_length = driven_axle_end - driven_axle_start
    driven_axle = make_d_flat_axle(shaft_dia, driven_axle_length, d_flat_depth)
    # Grooves flanking driven bevel gear (axle-local coordinates)
    # Driven gear Z = -bevel_layout.mesh_distance; axle starts at driven_axle_start
    local_driven_gear_z = -bevel_layout.mesh_distance - driven_axle_start
    driven_axle = add_groove_to_axle(driven_axle, local_driven_gear_z - bevel_groove_offset, shaft_dia)
    driven_axle = add_groove_to_axle(driven_axle, local_driven_gear_z + bevel_groove_offset, shaft_dia)
    # Rotate so D-flat face lies on print bed
    driven_axle = driven_axle.rotate((0, 0, 0), (1, 0, 0), -90)
    parts.append(("driven_bevel_axle", driven_axle, driven_axle_length))

    # --- C-Clips (14: 2 per axle × 5 + 2 inner core + 2 spares) ---
    # Export as separate STL to avoid mesh issues in the combined layout compound
    groove_dia = shaft_dia - 2 * 0.75  # 4.5mm for 6mm shaft
    clip = make_c_clip(groove_diameter=groove_dia, clip_od=10.0, thickness=1.5, gap_angle=120.0)
    clip_size = 10.0
    for i in range(14):
        parts.append((f"c_clip_{i+1:02d}", clip, clip_size))

    return parts


def layout_parts(parts: list, spacing: float = 10.0) -> cq.Assembly:
    """Arrange parts in rows on the XY plane.

    Each part is placed flat on Z=0, spaced out in X and Y.
    """
    assy = cq.Assembly()

    x_cursor = 0.0
    y_cursor = 0.0
    row_height = 0.0
    max_row_width = 256.0  # Printer plate size

    for name, shape, approx_size in parts:
        # Get actual bounding box
        bb = shape.val().BoundingBox()
        part_w = bb.xmax - bb.xmin
        part_d = bb.ymax - bb.ymin
        part_h = bb.zmax - bb.zmin

        # Start new row if needed
        if x_cursor > 0 and x_cursor + part_w > max_row_width:
            x_cursor = 0.0
            y_cursor += row_height + spacing
            row_height = 0.0

        # Place part at (x_cursor, y_cursor, 0), shifted so min corner is there
        offset = cq.Vector(
            x_cursor - bb.xmin,
            y_cursor - bb.ymin,
            -bb.zmin,  # Sit flat on Z=0
        )

        assy.add(shape, name=name, loc=cq.Location(offset),
                 color=cq.Color(0.6, 0.6, 0.6))

        x_cursor += part_w + spacing
        row_height = max(row_height, part_d)

    return assy


def main():
    parser = argparse.ArgumentParser(description="Generate flat print layout of mux parts")
    parser.add_argument("-s", "--spec", type=Path,
                        default=Path("examples/mux_2to1.yaml"))
    parser.add_argument("-o", "--output", type=Path,
                        default=Path("mux_print_layout.stl"))
    args = parser.parse_args()

    print(f"Loading spec from {args.spec}...")
    spec = load_spec(args.spec)

    print("Generating individual parts...")
    parts = generate_parts(spec)

    print(f"Laying out {len(parts)} parts on print bed...")
    for name, shape, size in parts:
        bb = shape.val().BoundingBox()
        print(f"  {name}: {bb.xmax-bb.xmin:.1f} x {bb.ymax-bb.ymin:.1f} x {bb.zmax-bb.zmin:.1f} mm")

    assy = layout_parts(parts)

    # Report total layout footprint
    total_bb = assy.toCompound().BoundingBox()
    plate_x = total_bb.xmax - total_bb.xmin
    plate_y = total_bb.ymax - total_bb.ymin
    print(f"Layout footprint: {plate_x:.1f} x {plate_y:.1f} mm")
    if plate_x > 256 or plate_y > 256:
        print(f"  WARNING: exceeds 256x256 mm plate!")

    # Split parts into main parts and c-clips for separate export
    main_parts = [(n, s, sz) for n, s, sz in parts if not n.startswith("c_clip")]
    clip_parts = [(n, s, sz) for n, s, sz in parts if n.startswith("c_clip")]

    print(f"Exporting to {args.output}...")
    output = args.output

    # Export main layout
    main_assy = layout_parts(main_parts)
    if output.suffix == '.stl':
        compound = main_assy.toCompound()
        cq.exporters.export(compound, str(output), tolerance=0.01, angularTolerance=0.1)
    else:
        main_assy.save(str(output))

    # Export c-clips as a separate file (avoids mesh issues in combined compound)
    if clip_parts:
        clip_assy = layout_parts(clip_parts)
        clip_output = output.with_stem(output.stem + "_c_clips")
        if clip_output.suffix == '.stl':
            clip_compound = clip_assy.toCompound()
            cq.exporters.export(clip_compound, str(clip_output), tolerance=0.005, angularTolerance=0.05)
        else:
            clip_assy.save(str(clip_output))
        print(f"  C-clips exported separately to {clip_output}")

    print(f"Done! {len(main_parts)} main parts + {len(clip_parts)} c-clips.")


if __name__ == "__main__":
    main()
