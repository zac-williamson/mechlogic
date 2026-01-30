# Bevel Gear Spacing & Flexure Mounting Fix Design

## Overview

Fix the bevel gear positioning to prevent intersection, add space for proper mesh, and correctly mount the flexure block to the housing.

## Issues Being Fixed

1. **Bevel gears intersect each other** - Both at same Z position (`z_clutch`), bodies overlap
2. **Driven bevel and lever intersect** - Both at same Z on lever pivot axis
3. **Insufficient assembly length** - No room for bevel gear Z offsets
4. **Flexure block floating** - Not mounted against front housing
5. **Flexure orientation wrong** - Bearing boss should point inward

## Bevel Gear Mesh Geometry

### Current Problem

```
Top view (looking down Y axis):

     S-axis (Y)
        |
        v
   [driving bevel] ← at z_clutch
   [driven bevel]  ← also at z_clutch (INTERSECTING!)
        |
   [lever pivot]
```

Both gears occupy the same Z region, causing overlap.

### Correct Arrangement

For two 45° bevel gears to mesh at 90°:
- Driving bevel (axis along Y) needs Z offset from driven bevel (axis along Z)
- The gears mesh where their pitch cones touch, not where their bodies overlap

```
Top view (looking down Y axis):

     S-axis (Y)
        |
        v
   [driving bevel] ← at z_bevel_driving (offset in +Z)
        \
         \ mesh point
          \
   [driven bevel]  ← at z_bevel_driven
        |
   [lever pivot] ← at z_lever (separate from driven bevel)
```

### Offset Calculation

For 1:1 ratio 45° bevels:
- `bevel_pitch_radius = (module * bevel_teeth) / 2`
- Mesh point is where pitch cones intersect
- Z offset between gears ≈ `bevel_pitch_radius` (the cone projects this far in Z)

**Driving bevel Z position:** `z_clutch + bevel_pitch_radius`
**Driven bevel Z position:** `z_clutch` (or slightly offset toward front)

### Driven Bevel vs Lever Separation

The driven bevel and lever are both on the lever pivot axis but need Z separation:
- Driven bevel: positioned to mesh with driving bevel
- Lever: positioned so fork reaches the dog clutch groove

**Lever Z:** `z_clutch` (fork engages clutch)
**Driven bevel Z:** `z_clutch + bevel_face_width + clearance` (behind lever)

## Assembly Length Increase

### Current Layout

```
[front_housing] [gear_a] [gap] [clutch] [gap] [gear_b] [back_housing]
```

### New Layout

Need extra space for:
- Driving bevel Z offset: `+bevel_pitch_radius` behind clutch
- Driven bevel separation from lever: `+bevel_face_width`

Add `bevel_zone_length` to inner_length:
```python
bevel_zone_length = bevel_pitch_radius + bevel_face_width + 5  # 5mm clearance
inner_length = gear_a_length + gear_spacing + clutch_width + gear_spacing + gear_b_length + bevel_zone_length
```

### Axle Length Updates

All axles must span the new total length:
- **Main axle:** Use new `total_length` (derived from layout)
- **S-axis:** Proportionally longer
- **Lever pivot:** May need adjustment based on driven bevel position

The axle generator currently uses `spec.geometry.axle_length`. Options:
1. Update spec to have longer `axle_length`
2. Calculate axle length from layout in generator
3. Pass computed length via placement metadata

**Approach:** Calculate required lengths in LayoutSolver and pass via placement metadata or compute in generator based on total_length.

## Flexure Block Mounting

### Current Problem

Flexure at `origin=(0, s_offset_y, z_front_housing)` with no rotation places it:
- Centered at the housing Z position
- But the flexure geometry extends in +Y from its origin (mounting plate at origin, beam/boss extend +Y)

This puts the flexure floating in front of the housing rather than mounted to it.

### Correct Positioning

The flexure should:
1. Have mounting plate face against the outer face of front housing
2. Beam and bearing boss extend inward (toward assembly center, in +Z direction)

**Required changes:**
- Rotate flexure 90° around X axis so beam extends in +Z instead of +Y
- Position so mounting plate is at `z_front_housing - housing_thickness/2` (outer face)

**New flexure position:**
```python
origin=(0, s_offset_y, z_front_housing - housing_t/2)
rotation=(90, 0, 0)  # Rotate so boss points in +Z (inward)
```

Wait - actually the flexure geometry has:
- Mounting plate in XY plane at origin
- Beam extending in +Y
- Boss extending in +Y from beam end

After 90° rotation around X:
- Mounting plate in XZ plane
- Beam extending in +Z
- Boss extending in +Z

This would have the mounting plate vertical, not against housing.

**Better approach:** Rotate 90° around X to point beam in -Z (toward housing), OR redesign flexure orientation.

Actually, let's think about this differently:
- Front housing is at `z_front_housing` (an XY plane)
- Flexure mounts to the **outer face** of front housing (the -Z face)
- Beam should extend in -Y (downward toward the bevel mesh area)
- Boss at end of beam holds S-shaft

**Flexure orientation fix:**
- Keep mounting plate in XY plane
- Rotate 180° around Z so beam extends in -Y
- Position at outer face: `z = z_front_housing - housing_t/2 - plate_thickness/2`

Or simpler: flip the flexure generation so beam extends -Y by default.

**Simplest fix:** Position flexure at `z_front_housing - housing_t/2` with rotation `(0, 180, 0)` to flip it so boss faces inward.

## File Changes

| File | Change |
|------|--------|
| `assembly/layout.py` | Add bevel_zone_length, offset bevel Z positions, fix flexure position/rotation |
| `generators/axle.py` | Compute lengths based on actual assembly dimensions |

## Testing

- Bevel gears should not intersect (visual check)
- Driven bevel and lever should not intersect
- Flexure mounting plate flush with housing outer face
- All parts fit within housing span

## Dimensions Summary (for default spec)

With module=1.5, bevel_teeth=16:
- `bevel_pitch_radius = 12mm`
- `bevel_face_width = 3.75mm`
- `bevel_zone_length ≈ 20mm` additional length needed

New total assembly length will be ~20mm longer than current.
