"""Internal geometric models for assembly layout."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple

import cadquery as cq


class PartType(Enum):
    """Types of parts in the assembly."""

    HOUSING_FRONT = "housing_front"
    HOUSING_BACK = "housing_back"
    GEAR_A = "gear_a"
    GEAR_B = "gear_b"
    DOG_CLUTCH = "dog_clutch"
    LEVER = "lever"
    LEVER_PIVOT = "lever_pivot"
    BEVEL_DRIVE = "bevel_drive"
    BEVEL_DRIVEN = "bevel_driven"
    FLEXURE_BLOCK = "flexure_block"
    AXLE_MAIN = "axle_main"
    AXLE_S = "axle_s"
    SPACER = "spacer"


@dataclass
class PartPlacement:
    """Placement of a part in the assembly coordinate frame."""

    part_type: PartType
    part_id: str
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Euler angles (degrees)
    metadata: Optional[Dict[str, float]] = None  # Part-specific parameters (e.g., length)

    def to_location(self) -> cq.Location:
        """Convert to CadQuery Location for assembly positioning."""
        return cq.Location(
            cq.Vector(*self.origin),
            cq.Vector(1, 0, 0),
            self.rotation[0],
        ) * cq.Location(
            cq.Vector(0, 0, 0),
            cq.Vector(0, 1, 0),
            self.rotation[1],
        ) * cq.Location(
            cq.Vector(0, 0, 0),
            cq.Vector(0, 0, 1),
            self.rotation[2],
        )


@dataclass
class ShaftAxis:
    """Defines a shaft axis for coaxial alignment constraints."""

    axis_id: str
    direction: tuple[float, float, float]  # Unit vector
    origin: tuple[float, float, float]
    parts: list[str] = field(default_factory=list)  # Part IDs on this axis


@dataclass
class MatePair:
    """Mating constraint between two parts (e.g., shaft in hole)."""

    part_a: str
    part_b: str
    mate_type: str  # "shaft_hole", "face_contact", "dog_clutch"
    clearance: float = 0.0


@dataclass
class PartMetadata:
    """Metadata for BOM generation."""

    part_id: str
    part_type: PartType
    name: str
    material: str = "PLA"
    count: int = 1
    dimensions: dict[str, float] = field(default_factory=dict)
    notes: Optional[str] = None


@dataclass
class AssemblyModel:
    """Complete assembly model with all parts and constraints."""

    parts: dict[str, PartPlacement] = field(default_factory=dict)
    shafts: list[ShaftAxis] = field(default_factory=list)
    mate_pairs: list[MatePair] = field(default_factory=list)
    metadata: dict[str, PartMetadata] = field(default_factory=dict)

    def add_part(
        self,
        part_type: PartType,
        part_id: str,
        origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        metadata: Optional[Dict[str, float]] = None,
    ) -> PartPlacement:
        """Add a part to the assembly."""
        placement = PartPlacement(
            part_type=part_type,
            part_id=part_id,
            origin=origin,
            rotation=rotation,
            metadata=metadata,
        )
        self.parts[part_id] = placement
        return placement

    def add_shaft_axis(
        self,
        axis_id: str,
        direction: tuple[float, float, float],
        origin: tuple[float, float, float],
        parts: Optional[list[str]] = None,
    ) -> ShaftAxis:
        """Define a shaft axis for coaxial parts."""
        shaft = ShaftAxis(
            axis_id=axis_id,
            direction=direction,
            origin=origin,
            parts=parts or [],
        )
        self.shafts.append(shaft)
        return shaft

    def add_mate(
        self,
        part_a: str,
        part_b: str,
        mate_type: str,
        clearance: float = 0.0,
    ) -> MatePair:
        """Add a mating constraint between parts."""
        mate = MatePair(
            part_a=part_a,
            part_b=part_b,
            mate_type=mate_type,
            clearance=clearance,
        )
        self.mate_pairs.append(mate)
        return mate
