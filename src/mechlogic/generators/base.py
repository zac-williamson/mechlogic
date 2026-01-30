"""Base protocol for part generators."""

from typing import Protocol

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata


class PartGenerator(Protocol):
    """Protocol for part generators."""

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate the part geometry.

        Args:
            spec: The logic element specification
            placement: The placement of this part in the assembly

        Returns:
            CadQuery Workplane containing the part solid
        """
        ...

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM generation.

        Args:
            spec: The logic element specification

        Returns:
            Part metadata including name, dimensions, material
        """
        ...
