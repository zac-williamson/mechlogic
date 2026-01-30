"""Axle/shaft generator."""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class AxleGenerator:
    """Generator for axles/shafts."""

    def __init__(self, axle_type: str = "main"):
        """Initialize generator.

        Args:
            axle_type: "main" for A/B/O axis, "s" for selector axis, "lever" for lever pivot
        """
        self.axle_type = axle_type

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate an axle."""
        shaft_dia = spec.primary_shaft_diameter

        # Use length from placement metadata if provided, else fallback to spec
        if placement.metadata and "length" in placement.metadata:
            length = placement.metadata["length"]
        else:
            length = spec.geometry.axle_length

            # Default scaling for different axle types
            if self.axle_type == "s":
                length = length * 0.6
            elif self.axle_type == "lever":
                length = 20.0

        # Create cylinder along Z axis
        axle = (
            cq.Workplane("XY")
            .cylinder(length, shaft_dia / 2)
        )

        return axle

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        length = spec.geometry.axle_length
        if self.axle_type == "s":
            length = length * 0.6
        elif self.axle_type == "lever":
            length = 20.0

        if self.axle_type == "main":
            part_type = PartType.AXLE_MAIN
        elif self.axle_type == "s":
            part_type = PartType.AXLE_S
        else:
            part_type = PartType.LEVER_PIVOT

        return PartMetadata(
            part_id=part_type.value,
            part_type=part_type,
            name=f"Axle ({self.axle_type.upper()})",
            material="Steel rod" if self.axle_type == "main" else "PLA",
            count=1,
            dimensions={
                "diameter": spec.primary_shaft_diameter,
                "length": length,
            },
            notes="Consider using metal rod for main axle" if self.axle_type == "main" else None,
        )
