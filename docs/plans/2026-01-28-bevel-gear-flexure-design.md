# Bevel Gear Pair & Flexure Block Design (v0.2)

## Overview

Add bevel gear pair for S-axis direction conversion and a compliant flexure block to absorb overload when the lever reaches end-of-travel.

## Bevel Gear Pair

### Purpose
Converts S-axis rotation (Y-direction) to perpendicular motion driving the lever that shifts the dog clutch. 1:1 ratio for direction conversion only.

### Driving Bevel (on S-shaft)
- Mounted on the S-input shaft via the flexure block
- Teeth count: `spec.gears.bevel_teeth` (default 16)
- Cone angle: 45° (for 90° shaft intersection)
- Face width: `2.5 * module`
- Central bore fits S-shaft with clearance

### Driven Bevel (on lever shaft)
- Identical teeth count (1:1 ratio)
- Meshes with driving bevel at 90°
- Keyed or press-fit to `axle_lever`
- That shaft connects to lever pivot

### Mesh Geometry
- Pitch cone distance calculated from teeth and module
- Back cone forms the mounting face
- Tooth profile: simplified straight bevel (not spiral) for FDM printability
- Backlash allowance per `spec.tolerances.gear_backlash`

## Flexure Block (Living Hinge)

### Purpose
Provides compliance when S input continues rotating after lever reaches end-of-travel. Deflection partially disengages bevel mesh to prevent tooth damage.

### Position in Power Path
Between S-input shaft and driving bevel gear.

### Geometry
- Thin rectangular beam section connecting housing wall to bearing boss
- Beam thickness: `spec.flexure.thickness` (default 1.2mm)
- Beam length: `spec.flexure.length` (default 15mm)
- Beam width: roughly equal to bevel gear face width
- Bearing boss at free end holds S-shaft with clearance fit

### Deflection Behavior
- Normal operation: flexure stays rigid, bevel gears mesh fully
- At lever end-of-travel: continued S rotation deflects flexure
- Deflection moves driving bevel axially away from driven bevel
- Partial disengagement allows S to "slip" without breaking teeth
- Design target: `spec.flexure.max_deflection` (default 2mm)

### Integration
- Printed integrally with `housing_front`
- Print orientation: beam aligned with layer lines for bend compliance
- No separate part - reduces assembly, leverages FDM anisotropic properties

## Layout Integration

### New Parts (PartType enum)
- `BEVEL_DRIVING` - gear on S-input side
- `BEVEL_DRIVEN` - gear on lever shaft side
- `AXLE_LEVER` - short shaft connecting driven bevel to lever pivot

### Positioning
- S-shaft enters along Y-axis at `s_offset_y` above main axis
- Driving bevel sits at end of S-shaft, near `z_clutch`
- Driven bevel meshes at 90°, its shaft parallel to Z-axis
- Lever pivot axis aligns with driven bevel shaft
- Flexure geometry added to housing (not separate part)

### Mates
- `axle_s` → `bevel_driving` (shaft-to-bore)
- `bevel_driving` → `bevel_driven` (gear mesh)
- `bevel_driven` → `axle_lever` (shaft-to-bore)
- `axle_lever` → `lever` (pivot connection)
- `lever` → `housing_front` (pivot bearing)

### Housing Modifications
- `housing_front` gains flexure beam and S-shaft bearing boss
- Pocket/cutout allows flexure to deflect without collision
- Lever pivot bore at appropriate location

## Implementation

### New Files
| File | Purpose |
|------|---------|
| `src/mechlogic/generators/gear_bevel.py` | `BevelGearGenerator` class producing matched pair |
| `src/mechlogic/generators/flexure_block.py` | `FlexureBlockGenerator` for living hinge geometry |

### BevelGearGenerator
- Constructor takes `gear_id` ("driving" or "driven")
- `generate()` builds cone geometry with straight bevel teeth
- Teeth cut radially along cone face using boolean operations
- Returns single gear; caller invokes twice for the pair

### FlexureBlockGenerator
- Produces flexure beam + bearing boss as a solid
- Designed to be unioned with housing during housing generation
- `generate()` takes spec and returns geometry positioned for integration

### Modified Files
- `src/mechlogic/models/geometry.py` - add new PartType values
- `src/mechlogic/generators/__init__.py` - export new generators
- `src/mechlogic/generators/housing.py` - integrate flexure, add lever pivot bore
- `src/mechlogic/generators/axle.py` - support generating `AXLE_LEVER`
- `src/mechlogic/assembly/layout.py` - place new parts, add mates
- `src/mechlogic/assembly/builder.py` - instantiate new generators

## Testing

- Unit tests for bevel gear geometry (diameter, tooth count)
- Unit tests for flexure dimensions
- Integration test generating full assembly with new parts
- Visual inspection of exported STL/STEP
