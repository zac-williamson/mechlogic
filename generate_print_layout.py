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


def load_spec(spec_file: Path) -> LogicElementSpec:
    with open(spec_file) as f:
        data = yaml.safe_load(f)
    return LogicElementSpec.model_validate(data)


def generate_parts(spec: LogicElementSpec) -> list:
    """Generate all individual parts and return (name, shape, approx_size) tuples."""
    layout = LayoutCalculator.calculate_mux_layout(spec)
    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="print")

    parts = []

    # --- Spur Gears (4 identical gears: gear_a, gear_b, input_a, input_b) ---
    gear_gen = SpurGearGenerator(gear_id="a")
    gear = gear_gen.generate(spec, placement)
    gear_od = spec.gears.module * spec.gears.coaxial_teeth + 2 * spec.gears.module

    parts.append(("gear_a", gear, gear_od))
    parts.append(("gear_b", gear, gear_od))
    parts.append(("input_gear_a", gear, gear_od))
    parts.append(("input_gear_b", gear, gear_od))

    # --- Dog Clutch ---
    clutch_gen = DogClutchGenerator()
    clutch = clutch_gen.generate(spec, placement)
    clutch_od = gear_od * 0.4
    parts.append(("dog_clutch", clutch, clutch_od + 5))

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

    # --- Lower Housing (left plate, right plate, front wall, back wall) ---
    housing_gen = LowerHousingGenerator(spec=spec)
    lower_params = LowerHousingParams.from_spec(spec)
    housing_layout = LayoutCalculator.calculate_housing_layout(spec)

    left_plate = housing_gen.generate_plate(
        housing_layout.left_plate_x, is_left_plate=True
    )
    right_plate = housing_gen.generate_plate(
        housing_layout.right_plate_x, is_left_plate=False
    )

    # Calculate plate size for spacing
    z_min, z_max = housing_gen._calculate_plate_z_extent()
    plate_z_size = z_max - z_min
    plate_y_size = lower_params.plate_y_max - lower_params.plate_y_min

    # Move plates to origin (they're generated at their assembly position)
    left_bb = left_plate.val().BoundingBox()
    left_plate_origin = left_plate.translate((
        -left_bb.xmin, -left_bb.ymin, -left_bb.zmin
    ))
    parts.append(("housing_left_plate", left_plate_origin, max(plate_z_size, plate_y_size)))

    right_bb = right_plate.val().BoundingBox()
    right_plate_origin = right_plate.translate((
        -right_bb.xmin, -right_bb.ymin, -right_bb.zmin
    ))
    parts.append(("housing_right_plate", right_plate_origin, max(plate_z_size, plate_y_size)))

    # Front and back walls
    side_plates, front_back_walls = housing_gen.generate()
    # Extract the front/back walls compound - move to origin
    fb_bb = front_back_walls.val().BoundingBox()
    front_back_origin = front_back_walls.translate((
        -fb_bb.xmin, -fb_bb.ymin, -fb_bb.zmin
    ))
    parts.append(("housing_front_back_walls", front_back_origin,
                   max(fb_bb.xmax - fb_bb.xmin, fb_bb.ymax - fb_bb.ymin)))

    # --- Upper Housing ---
    selector_layout = LayoutCalculator.calculate_selector_layout(spec)
    origin = (selector_layout.clutch_center, 0, 0)

    upper_gen = BevelLeverWithUpperHousingGenerator(
        include_axles=False,
        include_flexure=True,
        extend_to_lower_housing=True,
        lower_housing_y_max=lower_params.plate_y_max,
        l_shaped_front_back=False,
    )
    upper_housing = upper_gen._generate_upper_housing(spec, origin)
    uh_bb = upper_housing.val().BoundingBox()
    upper_housing_origin = upper_housing.translate((
        -uh_bb.xmin, -uh_bb.ymin, -uh_bb.zmin
    ))
    parts.append(("upper_housing", upper_housing_origin,
                   max(uh_bb.xmax - uh_bb.xmin, uh_bb.ymax - uh_bb.ymin,
                       uh_bb.zmax - uh_bb.zmin)))

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

    return parts


def layout_parts(parts: list, spacing: float = 10.0) -> cq.Assembly:
    """Arrange parts in rows on the XY plane.

    Each part is placed flat on Z=0, spaced out in X and Y.
    """
    assy = cq.Assembly()

    x_cursor = 0.0
    y_cursor = 0.0
    row_height = 0.0
    max_row_width = 400.0  # Start new row after this X extent

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
                        default=Path("mux_print_layout.step"))
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

    print(f"Exporting to {args.output}...")
    assy.save(str(args.output))
    print(f"Done! {len(parts)} parts laid out for printing.")


if __name__ == "__main__":
    main()
