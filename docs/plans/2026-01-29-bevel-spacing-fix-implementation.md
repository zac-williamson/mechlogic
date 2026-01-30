# Bevel Spacing & Flexure Mounting Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix bevel gear Z positioning to prevent intersection, increase assembly length, and correctly mount flexure to housing.

**Architecture:** Update LayoutSolver to add bevel zone length, offset bevel gear Z positions, separate driven bevel from lever, and fix flexure mounting position/rotation. Update axle generator to compute lengths from layout.

**Tech Stack:** CadQuery, Pydantic, pytest

---

## Task 1: Add Tests for Bevel Gear Non-Intersection

**Files:**
- Modify: `tests/test_layout_bevel.py`

**Step 1: Add test for bevel Z separation**

```python
    def test_bevel_gears_z_separated(self, spec):
        """Verify bevel gears have Z separation to prevent intersection."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driving = model.parts["bevel_driving"]
        driven = model.parts["bevel_driven"]

        # Bevels should have different Z positions
        dz = abs(driving.origin[2] - driven.origin[2])

        # Minimum separation should be at least bevel_pitch_radius
        bevel_pitch_radius = (spec.gears.module * spec.gears.bevel_teeth) / 2
        assert dz >= bevel_pitch_radius * 0.5, \
            f"Bevel Z separation {dz} too small, need at least {bevel_pitch_radius * 0.5}"

    def test_driven_bevel_lever_z_separated(self, spec):
        """Verify driven bevel and lever have Z separation."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driven = model.parts["bevel_driven"]
        lever = model.parts["lever"]

        # Driven bevel and lever should have different Z positions
        dz = abs(driven.origin[2] - lever.origin[2])

        # Minimum separation should be at least bevel face width
        bevel_face_width = 2.5 * spec.gears.module
        assert dz >= bevel_face_width * 0.5, \
            f"Driven bevel/lever Z separation {dz} too small"
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_layout_bevel.py -v`
Expected: New tests FAIL (bevels currently at same Z)

**Step 3: Commit test updates**

```bash
git add tests/test_layout_bevel.py
git commit -m "test: add bevel gear Z separation tests"
```

---

## Task 2: Update Layout Solver - Add Bevel Zone Length

**Files:**
- Modify: `src/mechlogic/assembly/layout.py`

**Step 1: Calculate bevel zone dimensions early**

Add after the key dimensions section (around line 31):

```python
        # Bevel gear dimensions (needed for layout calculation)
        bevel_face_width = 2.5 * spec.gears.module
        bevel_pitch_radius = (spec.gears.module * spec.gears.bevel_teeth) / 2

        # Extra length needed for bevel gear zone
        # Space for: driving bevel offset + driven bevel + clearance
        bevel_zone_length = bevel_pitch_radius + bevel_face_width + 5.0
```

**Step 2: Update inner_length calculation**

Replace line 37:
```python
        inner_length = gear_a_length + gear_spacing + clutch_width + gear_spacing + gear_b_length + bevel_zone_length
```

**Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_layout_bevel.py -v`
Expected: Some tests may still fail (positions not yet updated)

**Step 4: Commit**

```bash
git add src/mechlogic/assembly/layout.py
git commit -m "feat: add bevel zone length to assembly layout"
```

---

## Task 3: Update Bevel Gear Z Positions

**Files:**
- Modify: `src/mechlogic/assembly/layout.py`

**Step 1: Calculate new bevel Z positions**

Replace the bevel positioning section (around lines 89-138) with:

```python
        # Bevel gear pair - positioned with Z separation to prevent intersection
        # bevel_face_width and bevel_pitch_radius already calculated above

        # For 45-degree cones meeting at 90 degrees:
        # Cone distance (apex to pitch circle) = pitch_radius / tan(45) = pitch_radius
        cone_distance = bevel_pitch_radius

        # Lever pivot Y position (driven bevel mounts here)
        lever_pivot_y = s_offset_y - bevel_pitch_radius

        # Z positions for bevel gears - offset from clutch to prevent intersection
        # Driving bevel: offset in +Z direction from clutch
        z_bevel_driving = z_clutch + bevel_pitch_radius

        # Driven bevel: between driving bevel and lever, toward back of assembly
        z_bevel_driven = z_clutch + bevel_face_width + 2.0  # 2mm clearance from lever

        # Lever stays at z_clutch so fork can engage clutch groove
        lever_z = z_clutch

        # Lever (attached to lever pivot, fork reaches clutch)
        model.add_part(
            PartType.LEVER,
            "lever",
            origin=(0, lever_pivot_y, lever_z),
            rotation=(0, 0, 90),  # Rotate so fork faces clutch
        )

        # S-axis components (perpendicular axis)
        model.add_part(
            PartType.AXLE_S,
            "axle_s",
            origin=(0, s_offset_y, z_clutch),
            rotation=(90, 0, 0),  # Rotate to align with Y axis
        )

        # Driving bevel on S-axis - offset in Z
        driving_y = s_offset_y - bevel_face_width / 2
        model.add_part(
            PartType.BEVEL_DRIVE,
            "bevel_driving",
            origin=(0, driving_y, z_bevel_driving),
            rotation=(90, 0, 0),  # Rotate so axis is along Y
        )

        # Driven bevel on lever pivot axis - offset in Z from lever
        model.add_part(
            PartType.BEVEL_DRIVEN,
            "bevel_driven",
            origin=(0, lever_pivot_y, z_bevel_driven),
            rotation=(0, 0, 0),  # Axis along Z
        )

        # Lever pivot axle (through front housing)
        model.add_part(
            PartType.LEVER_PIVOT,
            "lever_pivot",
            origin=(0, lever_pivot_y, z_clutch),
            rotation=(0, 0, 0),
        )
```

**Step 2: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_layout_bevel.py -v`
Expected: Z separation tests PASS

**Step 3: Commit**

```bash
git add src/mechlogic/assembly/layout.py
git commit -m "fix: offset bevel gear Z positions to prevent intersection"
```

---

## Task 4: Fix Flexure Block Position and Orientation

**Files:**
- Modify: `tests/test_layout_bevel.py`
- Modify: `src/mechlogic/assembly/layout.py`

**Step 1: Add test for flexure mounting position**

```python
    def test_flexure_mounted_to_housing(self, spec):
        """Verify flexure is positioned at front housing outer face."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        flexure = model.parts["flexure_block"]
        housing_front = model.parts["housing_front"]

        # Flexure should be at or near the front housing Z position
        # (mounted to outer face, so slightly in front)
        housing_z = housing_front.origin[2]
        housing_t = spec.geometry.housing_thickness

        # Flexure origin should be near the outer face of housing
        expected_z = housing_z - housing_t / 2
        assert abs(flexure.origin[2] - expected_z) < 5.0, \
            f"Flexure Z {flexure.origin[2]} not near housing outer face {expected_z}"
```

**Step 2: Update flexure position in layout.py**

Replace the flexure block section:

```python
        # Flexure block (bolted to front housing outer face, supports S-shaft)
        # Mounting plate against housing, beam extends inward (-Y direction toward bevels)
        flexure_z = z_front_housing - housing_t / 2  # Outer face of housing
        model.add_part(
            PartType.FLEXURE_BLOCK,
            "flexure_block",
            origin=(0, s_offset_y, flexure_z),
            rotation=(0, 180, 0),  # Flip so beam points toward assembly center
        )
```

**Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_layout_bevel.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_layout_bevel.py src/mechlogic/assembly/layout.py
git commit -m "fix: position flexure block at housing outer face"
```

---

## Task 5: Update Axle Lengths for New Assembly Size

**Files:**
- Modify: `src/mechlogic/generators/axle.py`
- Modify: `src/mechlogic/assembly/layout.py`

**Step 1: Pass total_length via placement metadata**

In layout.py, update axle placements to include length info. First, store total_length:

```python
        # Store for axle length calculations
        self._total_length = total_length
```

Update each axle add_part to include metadata:

```python
        # Main axle - spans full assembly
        model.add_part(
            PartType.AXLE_MAIN,
            "axle_main",
            origin=(0, 0, 0),
            metadata={"length": total_length + 10}  # Extra for protrusion
        )
```

**Step 2: Update axle generator to use placement metadata**

In axle.py, update generate method:

```python
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
```

**Step 3: Update S-axis and lever pivot lengths in layout.py**

```python
        # S-axis components
        s_axis_length = s_offset_y + 20  # From origin to beyond S-axis position
        model.add_part(
            PartType.AXLE_S,
            "axle_s",
            origin=(0, s_offset_y, z_clutch),
            rotation=(90, 0, 0),
            metadata={"length": s_axis_length}
        )

        # Lever pivot axle
        lever_pivot_length = total_length * 0.4  # Spans from housing inward
        model.add_part(
            PartType.LEVER_PIVOT,
            "lever_pivot",
            origin=(0, lever_pivot_y, z_clutch),
            rotation=(0, 0, 0),
            metadata={"length": lever_pivot_length}
        )
```

**Step 4: Run tests**

Run: `source .venv/bin/activate && pytest -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/mechlogic/generators/axle.py src/mechlogic/assembly/layout.py
git commit -m "feat: compute axle lengths from assembly layout"
```

---

## Task 6: Integration Test and Visual Verification

**Files:**
- None (verification only)

**Step 1: Run full test suite**

Run: `source .venv/bin/activate && pytest -v --tb=short`
Expected: All PASS

**Step 2: Generate and export assembly**

Run:
```bash
source .venv/bin/activate && python -c "
from mechlogic.models.spec import LogicElementSpec
from mechlogic.assembly.builder import AssemblyBuilder
import yaml

spec_data = yaml.safe_load(open('examples/mux_2to1.yaml'))
spec = LogicElementSpec.model_validate(spec_data)
builder = AssemblyBuilder(spec)
assembly = builder.build()
assembly.save('output/v02_spacing_fixed.step')
print('Assembly saved to output/v02_spacing_fixed.step')
print(f'Parts: {[c.name for c in assembly.children]}')
"
```

**Step 3: Visual inspection checklist**

Open `output/v02_spacing_fixed.step` in CAD viewer and verify:
- [ ] Bevel gears do NOT intersect (separated in Z)
- [ ] Driven bevel and lever do NOT intersect
- [ ] Bevel gears positioned to mesh at edges
- [ ] Flexure block mounted against front housing outer face
- [ ] Flexure beam/boss extends inward toward assembly
- [ ] All axles span appropriately

**Step 4: Commit verification**

```bash
git add -A
git commit -m "feat: complete bevel spacing and flexure mounting fix"
```

---

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| Driving bevel Z | `z_clutch` | `z_clutch + bevel_pitch_radius` |
| Driven bevel Z | `z_clutch` | `z_clutch + bevel_face_width + 2` |
| Lever Z | `z_clutch` | `z_clutch` (unchanged) |
| Assembly length | `inner_length` | `inner_length + bevel_zone_length` |
| Flexure Z | `z_front_housing` | `z_front_housing - housing_t/2` |
| Flexure rotation | `(0,0,0)` | `(0,180,0)` |
| Axle lengths | Fixed from spec | Computed from layout |
