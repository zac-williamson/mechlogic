"""Export functionality for STL/STEP files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Dict, List

import cadquery as cq

from ..models.geometry import PartMetadata


class Exporter:
    """Exports assembly and parts to various formats."""

    def __init__(self, output_dir: Path, formats: Optional[List[str]] = None):
        """Initialize exporter.

        Args:
            output_dir: Directory to write output files
            formats: List of export formats (stl, step). Defaults to both.
        """
        self.output_dir = Path(output_dir)
        self.formats = formats or ["stl", "step"]

        # Create output directories
        self.parts_dir = self.output_dir / "parts"
        self.assembly_dir = self.output_dir / "assembly"
        self.parts_dir.mkdir(parents=True, exist_ok=True)
        self.assembly_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        assembly: cq.Assembly,
        parts: dict[str, cq.Workplane],
        metadata: Optional[Dict[str, PartMetadata]] = None,
    ) -> Dict[str, Path]:
        """Export assembly and individual parts.

        Args:
            assembly: CadQuery Assembly to export
            parts: Dict of part_id -> CadQuery Workplane
            metadata: Optional metadata for BOM generation

        Returns:
            Dict mapping output type to file paths
        """
        outputs: dict[str, Path] = {}

        # Export individual parts
        for part_id, part in parts.items():
            for fmt in self.formats:
                path = self._export_part(part_id, part, fmt)
                outputs[f"{part_id}.{fmt}"] = path

        # Export full assembly
        for fmt in self.formats:
            path = self._export_assembly(assembly, fmt)
            outputs[f"assembly.{fmt}"] = path

        # Export GLB for visualization
        glb_path = self._export_assembly_glb(assembly)
        if glb_path:
            outputs["assembly.glb"] = glb_path

        # Export BOM
        if metadata:
            bom_path = self._export_bom(metadata)
            outputs["bom.json"] = bom_path

        # Export assembly manifest
        manifest_path = self._export_manifest(assembly, metadata)
        outputs["assembly_manifest.json"] = manifest_path

        return outputs

    def _export_part(self, part_id: str, part: cq.Workplane, fmt: str) -> Path:
        """Export a single part."""
        filename = f"{part_id}.{fmt}"
        path = self.parts_dir / filename

        if fmt == "stl":
            cq.exporters.export(part, str(path), exportType="STL")
        elif fmt == "step":
            cq.exporters.export(part, str(path), exportType="STEP")
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return path

    def _export_assembly(self, assembly: cq.Assembly, fmt: str) -> Path:
        """Export the full assembly."""
        filename = f"full_assembly.{fmt}"
        path = self.assembly_dir / filename

        if fmt == "stl":
            # For STL, we need to export the compound
            compound = assembly.toCompound()
            cq.exporters.export(compound, str(path), exportType="STL")
        elif fmt == "step":
            assembly.save(str(path))
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return path

    def _export_assembly_glb(self, assembly: cq.Assembly) -> Optional[Path]:
        """Export assembly to GLB format for web visualization."""
        path = self.assembly_dir / "full_assembly.glb"

        try:
            assembly.save(str(path), exportType="GLTF")
            return path
        except Exception as e:
            print(f"Warning: GLB export failed: {e}")
            return None

    def _export_bom(self, metadata: dict[str, PartMetadata]) -> Path:
        """Export bill of materials to JSON."""
        path = self.output_dir / "bom.json"

        bom_data = {
            "parts": [
                {
                    "part_id": meta.part_id,
                    "name": meta.name,
                    "material": meta.material,
                    "count": meta.count,
                    "dimensions": meta.dimensions,
                    "notes": meta.notes,
                }
                for meta in metadata.values()
            ]
        }

        with open(path, "w") as f:
            json.dump(bom_data, f, indent=2)

        return path

    def _export_manifest(
        self,
        assembly: cq.Assembly,
        metadata: Optional[Dict[str, PartMetadata]],
    ) -> Path:
        """Export assembly manifest with coordinate frames and constraints."""
        path = self.output_dir / "assembly_manifest.json"

        manifest: dict[str, Any] = {
            "name": assembly.name,
            "parts": {},
            "coordinate_frame": {
                "origin": [0, 0, 0],
                "x_axis": [1, 0, 0],
                "y_axis": [0, 1, 0],
                "z_axis": [0, 0, 1],
                "units": "mm",
            },
        }

        # Add part information from assembly children
        for name in assembly.objects:
            if name == assembly.name:
                continue  # Skip root

            manifest["parts"][name] = {
                "file": {
                    "stl": f"parts/{name}.stl",
                    "step": f"parts/{name}.step",
                },
            }

        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)

        return path
