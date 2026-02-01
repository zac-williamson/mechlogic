"""CLI entry point for mechanical logic compiler."""

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
import yaml

app = typer.Typer(
    name="mechlogic",
    help="Mechanical logic compiler - converts logic element specs to 3D-printable CAD files",
)


class AssemblyType(str, Enum):
    """Available assembly types for generation."""
    bevel_pair = "bevel-pair"
    selector = "selector"
    combined_selector = "combined-selector"
    mux_selector = "mux-selector"
    mux_assembly = "mux-assembly"


@app.command()
def build(
    spec_file: Path = typer.Argument(..., help="Path to YAML specification file"),
    output_dir: Path = typer.Option(
        Path("output"), "-o", "--output", help="Output directory for generated files"
    ),
    preview: bool = typer.Option(
        False, "--preview", help="Open HTML preview in browser after build"
    ),
    formats: str = typer.Option(
        "stl,step", "--formats", help="Comma-separated export formats (stl,step)"
    ),
) -> None:
    """Build mechanical assembly from specification file."""
    from .models import LogicElementSpec
    from .assembly.builder import AssemblyBuilder
    from .export.exporter import Exporter

    if not spec_file.exists():
        typer.echo(f"Error: Specification file not found: {spec_file}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Loading specification from {spec_file}...")
    with open(spec_file) as f:
        spec_data = yaml.safe_load(f)

    spec = LogicElementSpec.model_validate(spec_data)
    typer.echo(f"Building assembly: {spec.element.name}")

    builder = AssemblyBuilder(spec)
    assembly = builder.build()

    output_dir.mkdir(parents=True, exist_ok=True)
    export_formats = [fmt.strip().lower() for fmt in formats.split(",")]

    exporter = Exporter(output_dir, export_formats)
    exporter.export(assembly, builder.parts)

    typer.echo(f"Assembly exported to {output_dir}")

    if preview:
        preview_path = output_dir / "preview.html"
        if preview_path.exists():
            typer.launch(str(preview_path))
        else:
            typer.echo("Preview not yet implemented", err=True)


@app.command()
def validate(
    spec_file: Path = typer.Argument(..., help="Path to YAML specification file"),
) -> None:
    """Validate specification file without building."""
    from .models import LogicElementSpec

    if not spec_file.exists():
        typer.echo(f"Error: Specification file not found: {spec_file}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Validating specification from {spec_file}...")
    with open(spec_file) as f:
        spec_data = yaml.safe_load(f)

    try:
        spec = LogicElementSpec.model_validate(spec_data)
        typer.echo(f"Specification valid: {spec.element.name}")
        typer.echo(f"  Type: {spec.element.type}")
        typer.echo(f"  Inputs: {', '.join(spec.inputs.keys())}")
        typer.echo(f"  Outputs: {', '.join(spec.output.keys())}")
    except Exception as e:
        typer.echo(f"Validation error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def generate(
    assembly_type: AssemblyType = typer.Argument(..., help="Type of assembly to generate"),
    spec_file: Path = typer.Option(
        Path("examples/mux_2to1.yaml"), "-s", "--spec", help="Path to YAML specification file"
    ),
    output: Path = typer.Option(
        None, "-o", "--output", help="Output file path (default: <assembly_type>.step)"
    ),
    no_axles: bool = typer.Option(
        False, "--no-axles", help="Exclude axles from assembly"
    ),
    no_housing: bool = typer.Option(
        False, "--no-housing", help="Exclude housing (mux-assembly only)"
    ),
) -> None:
    """Generate a specific assembly type as a STEP file.

    Available assembly types:

    - bevel-pair: Meshing bevel gear pair (90° axis conversion)

    - selector: Gear selector mechanism (2 spur gears + dog clutch + lever)

    - combined-selector: Selector with bevel gear control

    - mux-selector: Full 2-to-1 mux with input gears and bevel control

    - mux-assembly: Complete mux with housing
    """
    import cadquery as cq
    from .models.spec import LogicElementSpec
    from .models.geometry import PartPlacement, PartType
    from .generators import (
        BevelPairGenerator,
        SelectorMechanismGenerator,
        CombinedSelectorGenerator,
        MuxSelectorGenerator,
        MuxAssemblyGenerator,
    )

    if not spec_file.exists():
        typer.echo(f"Error: Specification file not found: {spec_file}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Loading specification from {spec_file}...")
    with open(spec_file) as f:
        spec_data = yaml.safe_load(f)

    spec = LogicElementSpec.model_validate(spec_data)

    # Create placement (generic, position handled by generator)
    placement = PartPlacement(part_type=PartType.GEAR_A, part_id="assembly")

    # Select and configure generator
    include_axles = not no_axles

    if assembly_type == AssemblyType.bevel_pair:
        generator = BevelPairGenerator(include_axles=include_axles)
        default_name = "bevel_gear_pair.step"
    elif assembly_type == AssemblyType.selector:
        generator = SelectorMechanismGenerator(include_axle=include_axles, include_lever=True)
        default_name = "selector_mechanism.step"
    elif assembly_type == AssemblyType.combined_selector:
        generator = CombinedSelectorGenerator(include_axles=include_axles)
        default_name = "combined_selector.step"
    elif assembly_type == AssemblyType.mux_selector:
        generator = MuxSelectorGenerator(include_axles=include_axles)
        default_name = "mux_selector.step"
    elif assembly_type == AssemblyType.mux_assembly:
        generator = MuxAssemblyGenerator(
            include_housing=not no_housing,
            housing_transparent=False,
        )
        default_name = "mux_complete_assembly.step"
    else:
        typer.echo(f"Error: Unknown assembly type: {assembly_type}", err=True)
        raise typer.Exit(1)

    output_path = output or Path(default_name)

    typer.echo(f"Generating {assembly_type.value}...")
    assembly = generator.generate(spec, placement)

    typer.echo(f"Exporting to {output_path}...")
    assembly.save(str(output_path))

    # Print metadata
    metadata = generator.get_metadata(spec)
    typer.echo(f"\nGenerated: {metadata.name}")
    typer.echo(f"  Output: {output_path}")
    if metadata.dimensions:
        typer.echo("  Dimensions:")
        for key, value in metadata.dimensions.items():
            typer.echo(f"    {key}: {value:.2f}")
    if metadata.notes:
        typer.echo(f"  Notes: {metadata.notes}")


@app.command()
def list_assemblies() -> None:
    """List all available assembly types."""
    typer.echo("Available assembly types:\n")

    assemblies = [
        ("bevel-pair", "Meshing bevel gear pair (90° axis conversion)"),
        ("selector", "Gear selector mechanism (2 spur gears + dog clutch + lever)"),
        ("combined-selector", "Selector mechanism with bevel gear control"),
        ("mux-selector", "Full 2-to-1 mux with input gears and bevel control"),
        ("mux-assembly", "Complete mux assembly with housing"),
    ]

    for name, description in assemblies:
        typer.echo(f"  {name:<20} {description}")

    typer.echo("\nUsage: mechlogic generate <assembly-type> [OPTIONS]")
    typer.echo("       mechlogic generate --help for more options")


if __name__ == "__main__":
    app()
