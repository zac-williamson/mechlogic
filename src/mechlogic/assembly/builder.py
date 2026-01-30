"""Assembly builder - constructs CadQuery assembly from specification."""

from __future__ import annotations

from typing import Any, Optional, Dict, List

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import AssemblyModel, PartType, PartMetadata
from ..generators import (
    HousingGenerator,
    LeverGenerator,
    AxleGenerator,
    DogClutchGenerator,
    SpurGearGenerator,
    BevelGearGenerator,
    FlexureBlockGenerator,
)
from .layout import LayoutSolver


class AssemblyBuilder:
    """Builds a CadQuery assembly from a logic element specification."""

    def __init__(self, spec: LogicElementSpec):
        self.spec = spec
        self.layout: Optional[AssemblyModel] = None
        self.parts: dict[str, cq.Workplane] = {}
        self.metadata: dict[str, PartMetadata] = {}

        # Initialize generators
        self._generators = {
            PartType.HOUSING_FRONT: HousingGenerator(is_front=True),
            PartType.HOUSING_BACK: HousingGenerator(is_front=False),
            PartType.GEAR_A: SpurGearGenerator(gear_id="a"),
            PartType.GEAR_B: SpurGearGenerator(gear_id="b"),
            PartType.DOG_CLUTCH: DogClutchGenerator(),
            PartType.LEVER: LeverGenerator(),
            PartType.AXLE_MAIN: AxleGenerator(axle_type="main"),
            PartType.AXLE_S: AxleGenerator(axle_type="s"),
            PartType.BEVEL_DRIVE: BevelGearGenerator(gear_id="driving"),
            PartType.BEVEL_DRIVEN: BevelGearGenerator(gear_id="driven"),
            PartType.LEVER_PIVOT: AxleGenerator(axle_type="lever"),
            PartType.FLEXURE_BLOCK: FlexureBlockGenerator(),
        }

    def build(self) -> cq.Assembly:
        """Build the complete assembly.

        Returns:
            CadQuery Assembly with all parts positioned
        """
        # Compute layout
        solver = LayoutSolver(self.spec)
        self.layout = solver.solve()

        # Create assembly
        assembly = cq.Assembly(name=self.spec.element.name)

        # Generate each part and add to assembly
        for part_id, placement in self.layout.parts.items():
            generator = self._generators.get(placement.part_type)
            if generator is None:
                print(f"Warning: No generator for part type {placement.part_type}")
                continue

            # Generate part geometry
            part = generator.generate(self.spec, placement)
            self.parts[part_id] = part

            # Get metadata
            meta = generator.get_metadata(self.spec)
            meta.part_id = part_id  # Override with actual part_id
            self.metadata[part_id] = meta

            # Add to assembly with placement
            assembly.add(
                part,
                name=part_id,
                loc=placement.to_location(),
                color=self._get_color(placement.part_type),
            )

        return assembly

    def _get_color(self, part_type: PartType) -> cq.Color:
        """Get color for part type (for visualization)."""
        colors = {
            PartType.HOUSING_FRONT: cq.Color(0.7, 0.7, 0.7, 0.8),  # Gray, semi-transparent
            PartType.HOUSING_BACK: cq.Color(0.7, 0.7, 0.7, 0.8),
            PartType.GEAR_A: cq.Color(0.2, 0.6, 0.9, 1.0),  # Blue
            PartType.GEAR_B: cq.Color(0.9, 0.6, 0.2, 1.0),  # Orange
            PartType.DOG_CLUTCH: cq.Color(0.9, 0.2, 0.2, 1.0),  # Red
            PartType.LEVER: cq.Color(0.2, 0.8, 0.2, 1.0),  # Green
            PartType.AXLE_MAIN: cq.Color(0.5, 0.5, 0.5, 1.0),  # Dark gray
            PartType.AXLE_S: cq.Color(0.5, 0.5, 0.5, 1.0),
            PartType.BEVEL_DRIVE: cq.Color(0.8, 0.5, 0.2, 1.0),  # Bronze
            PartType.BEVEL_DRIVEN: cq.Color(0.8, 0.5, 0.2, 1.0),  # Bronze
            PartType.LEVER_PIVOT: cq.Color(0.5, 0.5, 0.5, 1.0),  # Gray
            PartType.FLEXURE_BLOCK: cq.Color(0.2, 0.7, 0.3, 1.0),  # Green
        }
        return colors.get(part_type, cq.Color(0.8, 0.8, 0.8, 1.0))

    def get_bom(self) -> list[dict[str, Any]]:
        """Get bill of materials."""
        bom = []
        for part_id, meta in self.metadata.items():
            bom.append({
                "part_id": part_id,
                "name": meta.name,
                "material": meta.material,
                "count": meta.count,
                "dimensions": meta.dimensions,
                "notes": meta.notes,
            })
        return bom
