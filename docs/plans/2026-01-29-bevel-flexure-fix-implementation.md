# Bevel Gear & Flexure Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix bevel gear geometry to be true conical bevels, correct mesh positioning, and integrate flexure as bolt-on part with housing cutout.

**Architecture:** Rewrite BevelGearGenerator with conical teeth converging to apex, update FlexureBlockGenerator with mounting plate and radial deflection orientation, modify HousingGenerator with lever pivot bore and square S-axis cutout, fix LayoutSolver positioning.

**Tech Stack:** CadQuery, Pydantic, pytest

---

## Task 1: Update Bevel Gear Tests for Conical Geometry

**Files:**
- Modify: `tests/test_bevel_gear.py`

**Step 1: Update test for conical shape**

Replace `test_driving_gear_dimensions` with a test that verifies conical geometry:

```python
    def test_driving_gear_is_conical(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driving")
        placement = PartPlacement(
            part_type=PartType.BEVEL_DRIVE,
            part_id="bevel_driving",
        )

        gear = gen.generate(spec, placement)
        bb = gear.val().BoundingBox()

        # Gear should be conical - height (Z) should be significant
        # Face width = 2.5 * module = 2.5 * 1.5 = 3.75mm
        face_width = 2.5 * spec.gears.module
        assert bb.zlen >= face_width * 0.8, f"Z height {bb.zlen} too small for conical gear"

        # Pitch diameter at back = module * teeth = 1.5 * 16 = 24mm
        pitch_dia = spec.gears.module * spec.gears.bevel_teeth
        # With addendum, outer diameter slightly larger
        assert bb.xlen >= pitch_dia * 0.9, f"X diameter {bb.xlen} too small"
        assert bb.ylen >= pitch_dia * 0.9, f"Y diameter {bb.ylen} too small"
```

**Step 2: Add test for tooth count**

```python
    def test_gear_has_teeth(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driving")
        placement = PartPlacement(
            part_type=PartType.BEVEL_DRIVE,
            part_id="bevel_driving",
        )

        gear = gen.generate(spec, placement)

        # Volume should be less than solid cone (teeth cut out)
        bb = gear.val().BoundingBox()
        # Approximate cone volume = (1/3) * pi * r^2 * h
        import math
        r = max(bb.xlen, bb.ylen) / 2
        h = bb.zlen
        cone_volume = (1/3) * math.pi * r**2 * h
        actual_volume = gear.val().Volume()

        # Teeth remove material, so actual < theoretical cone
        assert actual_volume < cone_volume * 0.95, "Teeth should remove material from cone"
```

**Step 3: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_bevel_gear.py -v`
Expected: Some tests may fail with current implementation

**Step 4: Commit test updates**

```bash
git add tests/test_bevel_gear.py
git commit -m "test: update bevel gear tests for conical geometry"
```

---

## Task 2: Rewrite Bevel Gear Generator with True Conical Geometry

**Files:**
- Modify: `src/mechlogic/generators/gear_bevel.py`

**Step 1: Rewrite generate() for true conical bevel**

Replace the entire `generate` method:

```python
    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a bevel gear with straight teeth on conical surface.

        The gear has:
        - True conical body (45-degree pitch cone for 90-degree shaft intersection)
        - Teeth on cone surface converging toward apex
        - Central bore for shaft
        """
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        backlash = spec.tolerances.gear_backlash

        # Gear geometry
        pitch_dia = module * teeth
        addendum = module
        dedendum = module * 1.25
        face_width = 2.5 * module

        # Cone dimensions (45-degree pitch cone for 1:1 ratio at 90 degrees)
        pitch_cone_angle = 45.0  # degrees
        pitch_radius = pitch_dia / 2

        # Outer (addendum) and root (dedendum) cone angles
        # For straight bevel, addendum/dedendum are along the cone surface
        outer_radius = pitch_radius + addendum
        root_radius = pitch_radius - dedendum

        # Cone apex distance from pitch circle (along axis)
        cone_distance = pitch_radius / math.tan(math.radians(pitch_cone_angle))

        # Back face radii (larger end, at z=0)
        back_outer = outer_radius
        back_root = root_radius

        # Front face radii (smaller end, toward apex)
        # Taper based on face width along the cone
        taper_ratio = face_width / cone_distance
        front_outer = outer_radius * (1 - taper_ratio)
        front_root = root_radius * (1 - taper_ratio)

        bore_dia = shaft_dia + clearance

        # Create conical blank using revolution
        # Profile: trapezoid from root to outer radius, tapered along Z
        profile_pts = [
            (bore_dia / 2, 0),
            (back_outer, 0),
            (front_outer, face_width),
            (bore_dia / 2, face_width),
        ]

        gear = (
            cq.Workplane("XZ")
            .polyline(profile_pts)
            .close()
            .revolve(360, (0, 0, 0), (0, 0, 1))
        )

        # Cut teeth using radial wedge cutters that taper toward apex
        tooth_angle = 360.0 / teeth
        gap_angle = tooth_angle * 0.45  # Gap is 45% of pitch (leaves 55% for tooth)

        for i in range(teeth):
            angle = i * tooth_angle

            # Tooth gap depth (radial)
            gap_depth = addendum + dedendum + backlash

            # Create tapered wedge cutter for tooth gap
            # Back (larger) end dimensions
            back_inner_r = back_root - backlash
            back_outer_r = back_outer + 1  # Extend past outer surface

            # Front (smaller) end dimensions
            front_inner_r = front_root - backlash * (1 - taper_ratio)
            front_outer_r = front_outer + 1

            # Angular width of gap
            gap_half_angle = math.radians(gap_angle / 2)

            # Create cutter as a tapered wedge
            # Use loft between back and front profiles
            back_pts = [
                (back_inner_r * math.cos(-gap_half_angle), back_inner_r * math.sin(-gap_half_angle)),
                (back_outer_r * math.cos(-gap_half_angle), back_outer_r * math.sin(-gap_half_angle)),
                (back_outer_r * math.cos(gap_half_angle), back_outer_r * math.sin(gap_half_angle)),
                (back_inner_r * math.cos(gap_half_angle), back_inner_r * math.sin(gap_half_angle)),
            ]

            front_pts = [
                (front_inner_r * math.cos(-gap_half_angle), front_inner_r * math.sin(-gap_half_angle)),
                (front_outer_r * math.cos(-gap_half_angle), front_outer_r * math.sin(-gap_half_angle)),
                (front_outer_r * math.cos(gap_half_angle), front_outer_r * math.sin(gap_half_angle)),
                (front_inner_r * math.cos(gap_half_angle), front_inner_r * math.sin(gap_half_angle)),
            ]

            cutter = (
                cq.Workplane("XY")
                .polyline(back_pts)
                .close()
                .workplane(offset=face_width)
                .polyline(front_pts)
                .close()
                .loft()
                .rotate((0, 0, 0), (0, 0, 1), angle)
            )

            gear = gear.cut(cutter)

        return gear
```

**Step 2: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_bevel_gear.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/mechlogic/generators/gear_bevel.py
git commit -m "feat: rewrite bevel gear with true conical geometry"
```

---

## Task 3: Update Flexure Block with Mounting Plate and Radial Deflection

**Files:**
- Modify: `tests/test_flexure_block.py`
- Modify: `src/mechlogic/generators/flexure_block.py`

**Step 1: Add test for mounting holes**

Add to `TestFlexureBlockGenerator`:

```python
    def test_has_mounting_holes(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)

        # Check that volume is reduced by mounting holes
        # Mounting plate is approximately 20x20x4mm with 4 holes of 3.2mm dia
        # Each hole removes about 32mm^3, total ~128mm^3
        bb = block.val().BoundingBox()
        bounding_volume = bb.xlen * bb.ylen * bb.zlen
        actual_volume = block.val().Volume()

        # Should have significant material removed (bore + mounting holes)
        assert actual_volume < bounding_volume * 0.85
```

**Step 2: Rewrite FlexureBlockGenerator**

Replace the entire `generate` method:

```python
    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate flexure block geometry.

        The flexure consists of:
        - Mounting plate with 4x M3 bolt holes (bolts to housing)
        - Thin beam (living hinge) oriented for radial deflection
        - Bearing boss at free end for S-shaft
        """
        flexure = spec.flexure
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        module = spec.gears.module

        # Flexure beam dimensions
        beam_thickness = flexure.thickness
        beam_length = flexure.length
        beam_width = 2.5 * module + 4  # Match bevel face width plus margin

        # Bearing boss dimensions
        boss_dia = shaft_dia + 6  # Wall around bearing
        boss_length = 10.0  # Length along S-axis
        bore_dia = shaft_dia + clearance

        # Mounting plate dimensions
        plate_size = 20.0  # Square plate
        plate_thickness = 4.0  # Thick enough for M3 threads
        mount_hole_dia = 3.2  # M3 clearance
        mount_inset = 4.0  # From edge to hole center

        # Create mounting plate (XY plane, centered at origin)
        plate = (
            cq.Workplane("XY")
            .box(plate_size, plate_size, plate_thickness)
        )

        # Add 4 mounting holes
        mount_positions = [
            (plate_size/2 - mount_inset, plate_size/2 - mount_inset),
            (-plate_size/2 + mount_inset, plate_size/2 - mount_inset),
            (plate_size/2 - mount_inset, -plate_size/2 + mount_inset),
            (-plate_size/2 + mount_inset, -plate_size/2 + mount_inset),
        ]

        for x, y in mount_positions:
            plate = (
                plate.faces(">Z")
                .workplane()
                .center(x, y)
                .hole(mount_hole_dia)
            )

        # Create thin beam extending in +Y direction (for radial deflection in X)
        # Beam sits on top of plate (+Z face)
        beam = (
            cq.Workplane("XY")
            .box(beam_thickness, beam_length, beam_width)
            .translate((0, beam_length/2 + plate_size/2, plate_thickness/2 + beam_width/2))
        )

        # Create bearing boss at end of beam
        # Boss extends in +Y direction from beam end
        boss_y = plate_size/2 + beam_length + boss_length/2
        boss = (
            cq.Workplane("XZ")  # Boss axis along Y
            .circle(boss_dia / 2)
            .extrude(boss_length)
            .translate((0, plate_size/2 + beam_length, plate_thickness/2 + beam_width/2))
        )

        # Union all parts
        flexure_block = plate.union(beam).union(boss)

        # Cut bearing bore through boss (along Y axis)
        bore = (
            cq.Workplane("XZ")
            .circle(bore_dia / 2)
            .extrude(boss_length + 2)
            .translate((0, plate_size/2 + beam_length - 1, plate_thickness/2 + beam_width/2))
        )
        flexure_block = flexure_block.cut(bore)

        return flexure_block
```

**Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_flexure_block.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_flexure_block.py src/mechlogic/generators/flexure_block.py
git commit -m "feat: update flexure with mounting plate and radial deflection"
```

---

## Task 4: Update Housing Generator with Lever Pivot Bore and S-Axis Cutout

**Files:**
- Modify: `tests/test_bevel_gear.py` (add housing test)
- Modify: `src/mechlogic/generators/housing.py`

**Step 1: Create test for front housing features**

Add new test file section or add to existing:

```python
# In tests/test_housing.py (create new file)
"""Tests for housing generator."""

import pytest

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType


@pytest.fixture
def spec_data():
    return {
        "element": {"name": "test_mux", "type": "mux"},
        "inputs": {
            "a": {"shaft_diameter": 6.0},
            "b": {"shaft_diameter": 6.0},
            "s": {"shaft_diameter": 6.0},
        },
        "output": {"o": {"shaft_diameter": 6.0}},
        "gears": {
            "module": 1.5,
            "pressure_angle": 20,
            "coaxial_teeth": 24,
            "bevel_teeth": 16,
            "dog_clutch": {"teeth": 6, "tooth_height": 2.0, "engagement_depth": 1.5},
        },
        "geometry": {
            "axle_length": 60.0,
            "housing_thickness": 4.0,
            "lever_throw": 8.0,
            "clutch_width": 10.0,
            "gear_face_width": 8.0,
            "gear_spacing": 3.0,
        },
        "flexure": {"thickness": 1.2, "length": 15.0, "max_deflection": 2.0},
    }


@pytest.fixture
def spec(spec_data):
    return LogicElementSpec.model_validate(spec_data)


class TestHousingGenerator:
    """Tests for HousingGenerator."""

    def test_front_housing_has_lever_pivot_bore(self, spec):
        from mechlogic.generators.housing import HousingGenerator

        gen = HousingGenerator(is_front=True)
        placement = PartPlacement(
            part_type=PartType.HOUSING_FRONT,
            part_id="housing_front",
        )

        housing = gen.generate(spec, placement)

        # Front housing should have more material removed than back
        # (lever pivot bore + S-axis cutout + flexure mount holes)
        bb = housing.val().BoundingBox()
        bounding_volume = bb.xlen * bb.ylen * bb.zlen
        actual_volume = housing.val().Volume()

        # Should have significant material removed
        assert actual_volume < bounding_volume * 0.9

    def test_back_housing_simpler(self, spec):
        from mechlogic.generators.housing import HousingGenerator

        gen_front = HousingGenerator(is_front=True)
        gen_back = HousingGenerator(is_front=False)

        placement_f = PartPlacement(part_type=PartType.HOUSING_FRONT, part_id="f")
        placement_b = PartPlacement(part_type=PartType.HOUSING_BACK, part_id="b")

        front = gen_front.generate(spec, placement_f)
        back = gen_back.generate(spec, placement_b)

        # Back housing should have more material (fewer cutouts)
        front_vol = front.val().Volume()
        back_vol = back.val().Volume()

        assert back_vol > front_vol
```

**Step 2: Update HousingGenerator for front plate**

Modify the `generate` method in `housing.py`:

```python
    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a housing plate with bearing holes.

        Front plate has:
        - Central bore for main axle
        - Lever pivot bore (for driven bevel connection)
        - Square cutout for S-axis (flexure mounts here)
        - Flexure mounting holes (4x M3)
        - Corner mounting holes

        Back plate has:
        - Central bore for main axle
        - Corner mounting holes
        """
        thickness = spec.geometry.housing_thickness
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance

        # Calculate plate dimensions based on gear size
        gear_od = spec.gears.module * spec.gears.coaxial_teeth
        bevel_pitch_radius = (spec.gears.module * spec.gears.bevel_teeth) / 2
        plate_width = gear_od + 20
        plate_height = gear_od + 40  # Extra height for bevel/flexure area

        bore_dia = shaft_dia + clearance

        # S-axis Y offset (where flexure mounts)
        s_offset_y = gear_od / 2 + 15

        # Lever pivot Y position (offset from S-axis by bevel pitch radius)
        lever_pivot_y = s_offset_y - bevel_pitch_radius

        # Create base plate
        plate = (
            cq.Workplane("XY")
            .box(plate_width, plate_height, thickness)
            .faces(">Z")
            .workplane()
            .hole(bore_dia)  # Main axle bore at center
        )

        if self.is_front:
            # Add lever pivot bore
            plate = (
                plate.faces(">Z")
                .workplane()
                .center(0, lever_pivot_y)
                .hole(bore_dia)
            )

            # Add square cutout for S-axis (NOT a bore - flexure supports the shaft)
            cutout_size = 22.0  # Slightly larger than flexure mounting plate
            plate = (
                plate.faces(">Z")
                .workplane()
                .center(0, s_offset_y)
                .rect(cutout_size, cutout_size)
                .cutThruAll()
            )

            # Add flexure mounting holes (4x M3 around the cutout)
            mount_hole_dia = 3.2
            mount_offset = cutout_size / 2 + 3  # Just outside cutout
            flexure_mount_positions = [
                (mount_offset, s_offset_y + mount_offset),
                (-mount_offset, s_offset_y + mount_offset),
                (mount_offset, s_offset_y - mount_offset),
                (-mount_offset, s_offset_y - mount_offset),
            ]

            for x, y in flexure_mount_positions:
                plate = (
                    plate.faces(">Z")
                    .workplane()
                    .center(x, y)
                    .hole(mount_hole_dia)
                )
        else:
            # Back plate: just main axle bore (no S-axis features)
            pass

        # Add corner mounting holes (both plates)
        mount_inset = 8
        mount_hole_dia = 3.2
        corner_positions = [
            (plate_width / 2 - mount_inset, plate_height / 2 - mount_inset),
            (-plate_width / 2 + mount_inset, plate_height / 2 - mount_inset),
            (plate_width / 2 - mount_inset, -plate_height / 2 + mount_inset),
            (-plate_width / 2 + mount_inset, -plate_height / 2 + mount_inset),
        ]

        for x, y in corner_positions:
            plate = plate.faces(">Z").workplane().center(x, y).hole(mount_hole_dia)

        return plate
```

**Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_housing.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_housing.py src/mechlogic/generators/housing.py
git commit -m "feat: update front housing with lever pivot bore and S-axis cutout"
```

---

## Task 5: Fix Layout Solver Positioning

**Files:**
- Modify: `tests/test_layout_bevel.py`
- Modify: `src/mechlogic/assembly/layout.py`

**Step 1: Add test for correct bevel mesh positioning**

Add to `TestLayoutBevelGears`:

```python
    def test_bevel_apexes_meet(self, spec):
        """Verify bevel gear apexes converge at same point."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driving = model.parts["bevel_driving"]
        driven = model.parts["bevel_driven"]

        # Both gears should have their apex at the same point
        # The apex is offset from the gear origin by the cone distance
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pitch_radius = (module * teeth) / 2
        cone_distance = pitch_radius  # For 45-degree cone

        # Driving gear on S-axis (Y direction), apex points toward driven
        # Driven gear on lever pivot axis (Z direction), apex points toward driving
        # They should meet at a common point

        # Calculate expected apex positions
        # Driving: origin + cone_distance in direction toward driven
        # Driven: origin + cone_distance in direction toward driving

        # The gears should be positioned so their pitch cones intersect
        # This means the distance between origins should equal the sum of their
        # pitch radii projected onto the line connecting them

        # Simplified check: origins should be separated by approximately pitch_radius * sqrt(2)
        import math
        dx = driving.origin[0] - driven.origin[0]
        dy = driving.origin[1] - driven.origin[1]
        dz = driving.origin[2] - driven.origin[2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)

        expected_distance = pitch_radius * math.sqrt(2)
        assert abs(distance - expected_distance) < pitch_radius * 0.5, \
            f"Bevel origins distance {distance} not close to expected {expected_distance}"

    def test_driven_bevel_at_lever_pivot(self, spec):
        """Verify driven bevel is at the lever pivot location."""
        solver = LayoutSolver(spec)
        model = solver.solve()

        driven = model.parts["bevel_driven"]
        pivot = model.parts["lever_pivot"]

        # Driven bevel should share Y coordinate with lever pivot
        assert abs(driven.origin[1] - pivot.origin[1]) < 1.0, \
            "Driven bevel should be at lever pivot Y position"
```

**Step 2: Fix LayoutSolver positioning**

Update the bevel gear positioning section in `layout.py`:

```python
        # Bevel gear pair - positioned so pitch cone apexes meet
        bevel_face_width = 2.5 * spec.gears.module
        bevel_pitch_radius = (spec.gears.module * spec.gears.bevel_teeth) / 2

        # For 45-degree cones meeting at 90 degrees:
        # Cone distance (apex to pitch circle) = pitch_radius / tan(45) = pitch_radius
        cone_distance = bevel_pitch_radius

        # Lever pivot Y position (driven bevel mounts here)
        # Position so driven bevel can mesh with driving bevel
        lever_pivot_y = s_offset_y - bevel_pitch_radius

        # Driving bevel on S-axis
        # Positioned with back face toward S-shaft entry, apex pointing down toward driven
        # Origin at back face center, face_width extends toward apex
        driving_y = s_offset_y - bevel_face_width / 2  # Center of gear body

        model.add_part(
            PartType.BEVEL_DRIVE,
            "bevel_driving",
            origin=(0, driving_y, z_clutch),
            rotation=(90, 0, 0),  # Rotate so axis is along Y, teeth face down
        )

        # Driven bevel on lever pivot axis
        # Positioned with back face away from housing, apex pointing up toward driving
        # The driven bevel center is at lever_pivot_y
        model.add_part(
            PartType.BEVEL_DRIVEN,
            "bevel_driven",
            origin=(0, lever_pivot_y, z_clutch),
            rotation=(0, 0, 0),  # Axis along Z, teeth face up
        )

        # Lever pivot axle (through front housing)
        model.add_part(
            PartType.LEVER_PIVOT,
            "lever_pivot",
            origin=(0, lever_pivot_y, z_clutch),
            rotation=(0, 0, 0),
        )

        # Flexure block (bolted to front housing, supports S-shaft)
        model.add_part(
            PartType.FLEXURE_BLOCK,
            "flexure_block",
            origin=(0, s_offset_y, z_front_housing),
            rotation=(0, 0, 0),
        )

        # Update lever position to match lever pivot
        # (remove old lever positioning, use lever_pivot_y)
```

Also update the lever positioning earlier in the file to use `lever_pivot_y`:

```python
        # Lever (attached to lever pivot, fork reaches clutch)
        model.add_part(
            PartType.LEVER,
            "lever",
            origin=(0, lever_pivot_y, lever_z),
            rotation=(0, 0, 90),
        )
```

**Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_layout_bevel.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_layout_bevel.py src/mechlogic/assembly/layout.py
git commit -m "fix: correct bevel gear and lever pivot positioning in layout"
```

---

## Task 6: Update Assembly Builder

**Files:**
- Modify: `src/mechlogic/assembly/builder.py`

**Step 1: Ensure flexure block is in generators and has color**

Check that `_generators` dict includes `FLEXURE_BLOCK` and add if missing:

```python
            PartType.FLEXURE_BLOCK: FlexureBlockGenerator(),
```

Add color for flexure block in `_get_color`:

```python
            PartType.FLEXURE_BLOCK: cq.Color(0.2, 0.7, 0.3, 1.0),  # Green
```

**Step 2: Run all tests**

Run: `source .venv/bin/activate && pytest -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/mechlogic/assembly/builder.py
git commit -m "feat: add flexure block to assembly builder"
```

---

## Task 7: Integration Test and Visual Verification

**Files:**
- Modify: `tests/test_assembly_integration.py`

**Step 1: Add test for flexure block in assembly**

```python
    def test_assembly_contains_flexure_block(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        part_names = [child.name for child in assembly.children]

        assert "flexure_block" in part_names
```

**Step 2: Run full test suite**

Run: `source .venv/bin/activate && pytest -v --tb=short`
Expected: All PASS

**Step 3: Generate and visually inspect assembly**

Run: `source .venv/bin/activate && python -c "
from mechlogic.models.spec import LogicElementSpec
from mechlogic.assembly.builder import AssemblyBuilder
import yaml

spec_data = yaml.safe_load(open('examples/mux_2to1.yaml'))
spec = LogicElementSpec.model_validate(spec_data)
builder = AssemblyBuilder(spec)
assembly = builder.build()
assembly.save('output/v02_fixed_assembly.step')
print('Assembly saved to output/v02_fixed_assembly.step')
print(f'Parts: {[c.name for c in assembly.children]}')
"`

**Step 4: Commit**

```bash
git add tests/test_assembly_integration.py
git commit -m "test: add flexure block to integration tests"
```

---

## Task 8: Final Verification and Cleanup

**Step 1: Run full test suite**

Run: `source .venv/bin/activate && pytest -v`
Expected: All tests PASS

**Step 2: Visual inspection checklist**

Open `output/v02_fixed_assembly.step` in a CAD viewer and verify:
- [ ] Bevel gears are conical (not flat discs)
- [ ] Bevel gear teeth converge toward apex
- [ ] Both bevel apexes meet at the same point
- [ ] Driven bevel is on the lever pivot axis
- [ ] Lever pivot passes through front housing bore
- [ ] S-axis has square cutout in front housing (not round bore)
- [ ] Flexure block sits against front housing with mounting holes aligned
- [ ] Flexure bearing boss aligns with S-axis entry point

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete bevel gear and flexure fix implementation"
```
