"""CLI entry point for mechanical logic compiler."""

from pathlib import Path
from typing import Optional

import typer
import yaml

app = typer.Typer(
    name="mechlogic",
    help="Mechanical logic compiler - converts logic element specs to 3D-printable CAD files",
)


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


if __name__ == "__main__":
    app()
