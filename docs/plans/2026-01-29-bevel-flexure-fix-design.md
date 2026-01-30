# Bevel Gear & Flexure Fix Design

## Overview

Fix the bevel gear geometry, positioning, and flexure integration issues identified in v0.2 visual inspection.

## Issues Being Fixed

1. **Bevel gears are flat discs** - Need true conical geometry with converging teeth
2. **Bevel gears don't mesh** - Need 90° arrangement with apexes meeting at common point
3. **Driven bevel not on lever axle** - Need to mount on lever pivot shaft
4. **Lever pivot floats** - Need bore through front housing for support
5. **Flexure not integrated** - Need bolt-on flexure with housing cutout for S-axis

## Bevel Gear Geometry

### Approach: Simplified Straight Bevel

**Driving bevel (on S-shaft):**
- Conical body with 45° pitch cone angle
- Teeth cut into cone surface as triangular profiles
- Teeth converge toward cone apex (at mesh intersection point)
- Central bore fits S-shaft with clearance
- Cone apex points toward driven bevel

**Driven bevel (on lever pivot):**
- Identical cone geometry (1:1 ratio)
- Mounted on lever pivot axle, inside front housing
- Cone apex points toward driving bevel
- Both apexes meet at same intersection point

**Mesh geometry:**
- Pitch cones touch along a line at 90°
- Back cone (larger end) of each gear faces outward
- Teeth interleave at contact line
- Backlash applied by reducing tooth thickness

## Lever Pivot & Housing

### Lever Pivot Axle

- Short shaft through front housing only
- Inner end: driven bevel gear (press-fit or keyed)
- Outer end: lever arm (fork engages dog clutch)
- Supported by bore in front housing plate

### Front Housing Modifications

- Main axle bore at center (unchanged)
- Lever pivot bore - positioned so driven bevel meshes with driving bevel
- Square cutout for S-axis - NOT a bore, open window
- 4x M3 mounting holes around square cutout for flexure block

### Positioning Math

- Bevel pitch radius = `(module * bevel_teeth) / 2`
- Mesh point where both pitch cones meet at 90°
- Lever pivot bore offset from S-axis by pitch radius
- Both bevel apexes converge at mesh intersection

## Flexure Block

### Structure

- Mounting plate with 4x M3 bolt holes (matches housing cutout pattern)
- Thin beam extending inward (living hinge section)
- Bearing boss at free end - holds S-shaft with clearance
- Beam oriented for radial bending (perpendicular to S-shaft)

### Dimensions

- Beam thickness: `spec.flexure.thickness` (1.2mm default)
- Beam length: `spec.flexure.length` (15mm default)
- Beam width: matches bevel gear face width
- Mounting plate: ~4mm thick for M3 threads

### Deflection Behavior

- Normal: beam rigid, driving bevel fully engaged
- Overload: beam bends radially, driving bevel moves away from mesh
- Partial disengagement allows S to slip without breaking teeth
- Deflection direction: perpendicular to S-shaft axis

### Mounting

- Bolts to front housing from outside
- S-shaft bearing boss sits inside square cutout
- Driving bevel on S-shaft just inside the bearing boss

## File Changes

| File | Change |
|------|--------|
| `generators/gear_bevel.py` | Rewrite for true conical bevel with converging teeth |
| `generators/flexure_block.py` | Add mounting plate, reorient for radial deflection |
| `generators/housing.py` | Add lever pivot bore, square cutout, flexure mount holes |
| `assembly/layout.py` | Fix bevel positions (apexes meet), lever pivot through housing |
| `assembly/builder.py` | Ensure flexure positioned correctly |

## Testing

- Visual inspection: apexes should meet at mesh point
- Flexure mounts flush against housing
- Lever pivot passes through housing bore
- Export STEP and verify in CAD viewer
