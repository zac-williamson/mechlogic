"""Pydantic models for input specification parsing and validation."""

from __future__ import annotations

from typing import Literal, Dict, Optional

from pydantic import BaseModel, Field, model_validator


class ShaftSpec(BaseModel):
    """Specification for a shaft/axle."""

    # Individual shaft_diameter is optional - uses top-level if not specified
    shaft_diameter: Optional[float] = Field(default=None, gt=0, description="Shaft diameter in mm (optional override)")


class ElementInfo(BaseModel):
    """Basic information about the logic element."""

    name: str = Field(min_length=1, description="Element identifier")
    type: Literal["mux"] = Field(default="mux", description="Element type (mux for MVP)")


class DogClutchSpec(BaseModel):
    """Specification for dog clutch teeth."""

    teeth: int = Field(ge=3, le=12, description="Number of dog teeth")
    tooth_height: float = Field(gt=0, description="Height of dog teeth in mm")
    engagement_depth: float = Field(gt=0, description="Depth of tooth engagement in mm")

    @model_validator(mode="after")
    def validate_engagement(self) -> "DogClutchSpec":
        if self.engagement_depth > self.tooth_height:
            raise ValueError("engagement_depth cannot exceed tooth_height")
        return self


class GearSpec(BaseModel):
    """Specification for gear parameters."""

    module: float = Field(gt=0, le=5, description="Gear module in mm")
    pressure_angle: float = Field(
        default=20, ge=14.5, le=25, description="Pressure angle in degrees"
    )
    coaxial_teeth: int = Field(ge=12, le=100, description="Teeth on A/B coaxial gears")
    bevel_teeth: int = Field(ge=10, le=50, description="Teeth on S-axis bevel pair")
    dog_clutch: DogClutchSpec


class GeometrySpec(BaseModel):
    """Specification for assembly geometry."""

    axle_length: float = Field(gt=0, description="Total axle length in mm")
    housing_thickness: float = Field(gt=0, description="Housing plate thickness in mm")
    lever_throw: float = Field(gt=0, description="Total lever travel distance in mm")
    clutch_width: float = Field(gt=0, description="Width of sliding clutch in mm")
    gear_face_width: float = Field(gt=0, description="Face width of gears in mm")
    gear_spacing: float = Field(ge=0, description="Gap between coaxial gears in mm")
    device_length_x: float = Field(gt=0, description="Total device length along X axis in mm")
    axle_overhang: float = Field(ge=0, description="How far axles extend past housing plates in mm")


class FlexureSpec(BaseModel):
    """Specification for compliant flexure mechanism."""

    thickness: float = Field(gt=0, description="Flexure beam thickness in mm")
    length: float = Field(gt=0, description="Flexure beam length in mm")
    max_deflection: float = Field(gt=0, description="Maximum deflection target in mm")

    @model_validator(mode="after")
    def validate_deflection_feasible(self) -> "FlexureSpec":
        # Basic sanity check: deflection shouldn't exceed length/4
        if self.max_deflection > self.length / 4:
            raise ValueError("max_deflection too large relative to length")
        return self


class ToleranceSpec(BaseModel):
    """Specification for manufacturing tolerances (FDM defaults)."""

    shaft_clearance: float = Field(
        default=0.2, ge=0, description="Clearance added to holes for shaft fit in mm"
    )
    gear_backlash: float = Field(
        default=0.15, ge=0, description="Backlash allowance for gear meshing in mm"
    )
    press_fit_interference: float = Field(
        default=-0.1, le=0, description="Interference for press fits in mm (negative)"
    )


class LogicElementSpec(BaseModel):
    """Top-level specification for a mechanical logic element."""

    element: ElementInfo
    shaft_diameter: float = Field(gt=0, description="Primary shaft/axle diameter in mm (used for all shafts)")
    inputs: dict[str, ShaftSpec] = Field(description="Input shaft specifications")
    output: dict[str, ShaftSpec] = Field(description="Output shaft specifications")
    gears: GearSpec
    geometry: GeometrySpec
    flexure: FlexureSpec
    tolerances: ToleranceSpec = Field(default_factory=ToleranceSpec)

    @model_validator(mode="after")
    def validate_mux_inputs(self) -> "LogicElementSpec":
        if self.element.type == "mux":
            required_inputs = {"a", "b", "s"}
            actual_inputs = set(self.inputs.keys())
            if not required_inputs.issubset(actual_inputs):
                missing = required_inputs - actual_inputs
                raise ValueError(f"MUX element requires inputs: {missing}")
            if "o" not in self.output:
                raise ValueError("MUX element requires output 'o'")
        return self

    @model_validator(mode="after")
    def validate_lever_travel(self) -> "LogicElementSpec":
        min_travel = (
            self.gears.dog_clutch.engagement_depth + self.geometry.gear_spacing + 1.0
        )
        if self.geometry.lever_throw < min_travel:
            raise ValueError(
                f"lever_throw ({self.geometry.lever_throw}) must be >= "
                f"engagement_depth + gear_spacing + clearance ({min_travel})"
            )
        return self

    @property
    def primary_shaft_diameter(self) -> float:
        """Get the primary shaft diameter."""
        return self.shaft_diameter
