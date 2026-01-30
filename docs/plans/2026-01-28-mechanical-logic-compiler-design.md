# Mechanical Logic Compiler Design

## Overview

Software that takes a logic element specification and generates 3D-printable CAD files for a mechanical assembly implementing digital logic using rotational direction encoding.

**Logic encoding:** Rotational direction on an axle (clockwise = 0, counterclockwise = 1)

**Fundamental primitive:** A 2:1 multiplexer using a sliding dog clutch that selects between two coaxial gears based on a selector input (S).

## Architecture

```
Input Spec (YAML) → Parser → Internal Model → CAD Generator → Validator
                                    ↓                            ↓
                              Visualization ←────────────────────┘
                                    ↓
                                Exporter
```

### Four-Layer Architecture

1. **Specification Layer** - YAML input parsed into validated Pydantic models
2. **Model Layer** - Kinematic model (functional relationships, truth table) + Geometric model (dimensions, positions, coordinate frames)
3. **Generation Layer** - CadQuery generators producing part solids and assembly
4. **Visualization Layer** - HTML-based preview with embedded three.js viewer

## Mechanical Design

### Logic Element I/O
- Inputs A, B, S enter along the same axis (coaxial shafts)
- Output O exits along the same axis
- MVP implements simple MUX: O = (S==0) ? A : B

### Switching Mechanism
- Two coaxial gears on a common axle (freely rotating)
- Sliding dog clutch moves axially to engage one gear's face teeth
- Clutch position controlled by pivoting lever driven by input S

### S-Axis Conversion
- S rotation converted to perpendicular axis via bevel gear pair
- Flexure compliance mechanism allows S to rotate when lever at end-of-travel
- Flexure deflection partially disengages bevel gear under overload

## Input Specification Format

```yaml
element:
  name: "mux_2to1"
  type: "mux"

inputs:
  a: { shaft_diameter: 6.0 }
  b: { shaft_diameter: 6.0 }
  s: { shaft_diameter: 6.0 }

output:
  o: { shaft_diameter: 6.0 }

gears:
  module: 1.5
  pressure_angle: 20
  coaxial_teeth: 24
  bevel_teeth: 16
  dog_clutch:
    teeth: 6
    tooth_height: 2.0
    engagement_depth: 1.5

geometry:
  axle_length: 60.0
  housing_thickness: 4.0
  lever_throw: 8.0
  clutch_width: 10.0
  gear_face_width: 8.0
  gear_spacing: 3.0

flexure:
  thickness: 1.2
  length: 15.0
  max_deflection: 2.0

tolerances:
  shaft_clearance: 0.2
  gear_backlash: 0.15
  press_fit_interference: -0.1
```

## Data Models

### Pydantic Spec Models
- `LogicElementSpec` - Top-level container
- `GearSpec` - Module, pressure angle, teeth counts
- `DogClutchSpec` - Teeth, height, engagement depth
- `GeometrySpec` - Dimensions for all parts
- `FlexureSpec` - Compliant beam parameters
- `ToleranceSpec` - FDM printing tolerances

### Internal Geometric Model
- `PartPlacement` - Part ID, origin, rotation in assembly frame
- `AssemblyModel` - Parts dict, shaft axes, mate pairs

### Kinematic Model
- `KinematicModel` - Truth table mapping (A,B,S) → O, gear ratios per path

## CAD Generation

### Technology Choice
**CadQuery** - Selected for:
- Native STEP + STL export
- Mature assembly support via `cq.Assembly`
- Good parametric patterns
- Active community

### Part Generators
Each part type implements `PartGenerator` protocol:
- `gear_spur.py` - Spur gear with involute profile
- `gear_bevel.py` - Bevel gear pair
- `dog_clutch.py` - Sliding clutch with dog teeth
- `lever.py` - Pivoting lever
- `housing.py` - Front/back plates with bearing bores
- `flexure_block.py` - Compliant bearing mount
- `axle.py` - Shafts with shoulders
- `spacer.py` - Spacing collars

### Layout Solver
Computes part placements ensuring:
- Coaxial alignment of A, B, S, O shafts
- Proper gear mesh distances
- Lever pivot placement
- Clearances for clutch travel

## Validation

### Gear Compatibility
- Module/pitch matching between meshing pairs
- Pressure angle matching
- Bevel gear shaft angle (90°)
- Dog clutch tooth count for reliable engagement

### Clearance Checks (Bounding-Box MVP)
- No part intersections at rest
- No intersections at clutch travel extremes
- Minimum wall thickness on housing
- Flexure deflection clearance

### Travel Checks
- Clutch travel ≥ engagement_depth + clearance
- Lever throw achieves full travel
- No lever/housing collision at extremes

### Kinematic Verification
- Truth table verification by tracing gear paths
- Gear ratio confirmation (1:1 for MVP)

## Export

### Output Structure
```
output/
├── parts/           # Individual .step and .stl files
├── assembly/
│   ├── full_assembly.step
│   └── full_assembly.glb
├── preview.html     # Self-contained 3D viewer
├── bom.json
├── assembly_manifest.json
└── validation_report.json
```

### HTML Preview
- Self-contained HTML with three.js
- Orbit/zoom/pan controls
- Part highlighting on click
- Per-part visibility toggle
- Validation status badge

## Repository Structure

```
cadproject/
├── pyproject.toml
├── src/mechlogic/
│   ├── cli.py
│   ├── models/
│   ├── generators/
│   ├── assembly/
│   ├── validation/
│   └── export/
├── templates/
├── examples/
├── tests/
└── docs/
```

## Milestone Plan

### MVP
- Project scaffolding
- Pydantic spec models with YAML parsing
- Basic LayoutSolver
- Placeholder generators (housing, lever, axle)
- Assembly builder
- STL/STEP export
- Example YAML spec

### v0.2 (Real Geometry)
- Parametric spur gear generator
- Dog clutch with face teeth
- Bevel gear pair
- Flexure block
- Updated LayoutSolver

### v0.3 (Visualization + Validation)
- GLB export
- HTML preview
- All validation checks
- JSON validation report

### v1.0 (Production-Ready)
- Kinematic verification
- BOM generation
- Assembly manifest
- Comprehensive tests
- Documentation

### Future (v2+)
- Multi-element composition
- Alternative logic types
- Different printing technologies

## Design Constraints

- FDM printing assumed
- Parametric, configurable parts
- Typical FDM tolerances (shaft clearance, backlash)
- Minimize supports
- Simple, iterable geometry
