#!/usr/bin/env python3
"""Generate mechanical logic assemblies.

Usage:
    python generate_assembly.py <assembly-type> [--spec SPEC] [--output OUTPUT]

Assembly types:
    bevel-pair        Meshing bevel gear pair (90° axis conversion)
    selector          Gear selector mechanism (2 spur gears + dog clutch + lever)
    combined-selector Selector mechanism with bevel gear control
    mux-selector      Full 2-to-1 mux with input gears and bevel control
    mux-assembly      Complete mux assembly with housing

Examples:
    python generate_assembly.py bevel-pair
    python generate_assembly.py mux-selector --output my_mux.step
    python generate_assembly.py mux-assembly --spec examples/mux_2to1.yaml
"""

import argparse
import sys
from pathlib import Path

import yaml

from src.mechlogic.models.spec import LogicElementSpec
from src.mechlogic.models.geometry import PartPlacement, PartType
from src.mechlogic.generators import (
    BevelPairGenerator,
    SelectorMechanismGenerator,
    CombinedSelectorGenerator,
    MuxSelectorGenerator,
    MuxAssemblyGenerator,
)


ASSEMBLY_TYPES = {
    "bevel-pair": {
        "generator": BevelPairGenerator,
        "kwargs": {"include_axles": True},
        "default_output": "bevel_gear_pair.step",
        "description": "Meshing bevel gear pair (90° axis conversion)",
    },
    "selector": {
        "generator": SelectorMechanismGenerator,
        "kwargs": {"include_axle": True, "include_lever": True},
        "default_output": "selector_mechanism.step",
        "description": "Gear selector mechanism (2 spur gears + dog clutch + lever)",
    },
    "combined-selector": {
        "generator": CombinedSelectorGenerator,
        "kwargs": {"include_axles": True},
        "default_output": "combined_selector.step",
        "description": "Selector mechanism with bevel gear control",
    },
    "mux-selector": {
        "generator": MuxSelectorGenerator,
        "kwargs": {"include_axles": True},
        "default_output": "mux_selector.step",
        "description": "Full 2-to-1 mux with input gears and bevel control",
    },
    "mux-assembly": {
        "generator": MuxAssemblyGenerator,
        "kwargs": {"include_housing": True, "housing_transparent": False},
        "default_output": "mux_complete_assembly.step",
        "description": "Complete mux assembly with housing",
    },
}


def list_assemblies():
    """Print available assembly types."""
    print("\nAvailable assembly types:\n")
    for name, info in ASSEMBLY_TYPES.items():
        print(f"  {name:<20} {info['description']}")
    print()


def generate(assembly_type: str, spec_file: Path, output_file: Path, no_axles: bool = False):
    """Generate the specified assembly."""
    if assembly_type not in ASSEMBLY_TYPES:
        print(f"Error: Unknown assembly type '{assembly_type}'")
        list_assemblies()
        sys.exit(1)

    config = ASSEMBLY_TYPES[assembly_type]

    # Load spec
    print(f"Loading specification from {spec_file}...")
    with open(spec_file) as f:
        spec_data = yaml.safe_load(f)
    spec = LogicElementSpec.model_validate(spec_data)

    # Create generator with config
    kwargs = config["kwargs"].copy()
    if no_axles:
        if "include_axles" in kwargs:
            kwargs["include_axles"] = False
        if "include_axle" in kwargs:
            kwargs["include_axle"] = False

    generator = config["generator"](**kwargs)

    # Generate assembly
    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="assembly")

    print(f"Generating {assembly_type}...")
    assembly = generator.generate(spec, placement)

    # Export
    print(f"Exporting to {output_file}...")
    assembly.save(str(output_file))

    # Print metadata
    metadata = generator.get_metadata(spec)
    print(f"\nGenerated: {metadata.name}")
    print(f"  Output: {output_file}")
    if metadata.dimensions:
        print("  Dimensions:")
        for key, value in metadata.dimensions.items():
            print(f"    {key}: {value:.2f}")
    if metadata.notes:
        print(f"  Notes: {metadata.notes}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate mechanical logic assemblies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "assembly_type",
        nargs="?",
        choices=list(ASSEMBLY_TYPES.keys()) + ["list"],
        help="Type of assembly to generate (or 'list' to show all types)",
    )
    parser.add_argument(
        "-s", "--spec",
        type=Path,
        default=Path("examples/mux_2to1.yaml"),
        help="Path to YAML specification file (default: examples/mux_2to1.yaml)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: <assembly_type>.step)",
    )
    parser.add_argument(
        "--no-axles",
        action="store_true",
        help="Exclude axles from the assembly",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_types",
        help="List available assembly types",
    )

    args = parser.parse_args()

    if args.list_types or args.assembly_type == "list" or args.assembly_type is None:
        list_assemblies()
        return

    if not args.spec.exists():
        print(f"Error: Specification file not found: {args.spec}")
        sys.exit(1)

    output_file = args.output or Path(ASSEMBLY_TYPES[args.assembly_type]["default_output"])

    generate(args.assembly_type, args.spec, output_file, args.no_axles)


if __name__ == "__main__":
    main()
