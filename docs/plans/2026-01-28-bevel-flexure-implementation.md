# Bevel Gear & Flexure Block Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add bevel gear pair and living-hinge flexure to convert S-axis rotation to lever motion with overload protection.

**Architecture:** Two new generators (BevelGearGenerator, FlexureBlockGenerator), updates to LayoutSolver for positioning, updates to AssemblyBuilder for instantiation, and housing modifications to integrate the flexure.

**Tech Stack:** CadQuery, Pydantic, pytest

---

## Task 1: Bevel Gear Generator - Test Setup

**Files:**
- Create: `tests/test_bevel_gear.py`

**Step 1: Write test file with imports and fixture**

```python
"""Tests for bevel gear generator."""

import pytest
import math

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType


@pytest.fixture
def spec_data():
    """Return valid specification data."""
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
            "dog_clutch": {
                "teeth": 6,
                "tooth_height": 2.0,
                "engagement_depth": 1.5,
            },
        },
        "geometry": {
            "axle_length": 60.0,
            "housing_thickness": 4.0,
            "lever_throw": 8.0,
            "clutch_width": 10.0,
            "gear_face_width": 8.0,
            "gear_spacing": 3.0,
        },
        "flexure": {
            "thickness": 1.2,
            "length": 15.0,
            "max_deflection": 2.0,
        },
    }


@pytest.fixture
def spec(spec_data):
    return LogicElementSpec.model_validate(spec_data)


class TestBevelGearGenerator:
    """Tests for BevelGearGenerator."""

    def test_import(self):
        from mechlogic.generators.gear_bevel import BevelGearGenerator
        assert BevelGearGenerator is not None
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/test_bevel_gear.py -v`
Expected: FAIL with "ModuleNotFoundError" or "cannot import"

**Step 3: Commit test file**

```bash
git add tests/test_bevel_gear.py
git commit -m "test: add bevel gear generator test scaffold"
```

---

## Task 2: Bevel Gear Generator - Minimal Implementation

**Files:**
- Create: `src/mechlogic/generators/gear_bevel.py`
- Modify: `src/mechlogic/generators/__init__.py`

**Step 1: Create minimal generator file**

```python
"""Bevel gear generator."""

import math

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class BevelGearGenerator:
    """Generator for bevel gears (90-degree axis conversion).

    Creates straight bevel gears for 1:1 ratio direction conversion.
    Cone angle is 45 degrees for perpendicular shaft intersection.
    """

    def __init__(self, gear_id: str = "driving"):
        """Initialize generator.

        Args:
            gear_id: "driving" (on S-shaft) or "driven" (on lever shaft)
        """
        if gear_id not in ("driving", "driven"):
            raise ValueError("gear_id must be 'driving' or 'driven'")
        self.gear_id = gear_id

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a bevel gear."""
        # Placeholder - returns simple cone
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pitch_dia = module * teeth

        cone_height = pitch_dia / 2  # 45-degree cone

        gear = (
            cq.Workplane("XY")
            .circle(pitch_dia / 2)
            .workplane(offset=cone_height)
            .circle(0.1)
            .loft()
        )

        return gear

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pitch_dia = module * teeth

        part_type = PartType.BEVEL_DRIVE if self.gear_id == "driving" else PartType.BEVEL_DRIVEN

        return PartMetadata(
            part_id=part_type.value,
            part_type=part_type,
            name=f"Bevel Gear ({self.gear_id})",
            material="PLA",
            count=1,
            dimensions={
                "module": module,
                "teeth": teeth,
                "pitch_diameter": pitch_dia,
                "cone_angle": 45.0,
            },
        )
```

**Step 2: Update generators __init__.py**

Add to `src/mechlogic/generators/__init__.py`:

```python
"""Part generators for mechanical logic compiler."""

from .housing import HousingGenerator
from .lever import LeverGenerator
from .axle import AxleGenerator
from .dog_clutch import DogClutchGenerator
from .gear_spur import SpurGearGenerator
from .gear_bevel import BevelGearGenerator

__all__ = [
    "HousingGenerator",
    "LeverGenerator",
    "AxleGenerator",
    "DogClutchGenerator",
    "SpurGearGenerator",
    "BevelGearGenerator",
]
```

**Step 3: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/test_bevel_gear.py::TestBevelGearGenerator::test_import -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/mechlogic/generators/gear_bevel.py src/mechlogic/generators/__init__.py
git commit -m "feat: add minimal bevel gear generator"
```

---

## Task 3: Bevel Gear Generator - Geometry Tests

**Files:**
- Modify: `tests/test_bevel_gear.py`

**Step 1: Add geometry tests**

Append to `TestBevelGearGenerator` class:

```python
    def test_driving_gear_dimensions(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driving")
        placement = PartPlacement(
            part_type=PartType.BEVEL_DRIVE,
            part_id="bevel_driving",
        )

        gear = gen.generate(spec, placement)
        bb = gear.val().BoundingBox()

        # Expected pitch diameter: module * teeth = 1.5 * 16 = 24mm
        expected_dia = 24.0
        actual_dia = max(bb.xlen, bb.ylen)

        assert abs(actual_dia - expected_dia) < 1.0, f"Diameter {actual_dia} not close to {expected_dia}"

    def test_driven_gear_dimensions(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driven")
        placement = PartPlacement(
            part_type=PartType.BEVEL_DRIVEN,
            part_id="bevel_driven",
        )

        gear = gen.generate(spec, placement)
        bb = gear.val().BoundingBox()

        # Same dimensions as driving (1:1 ratio)
        expected_dia = 24.0
        actual_dia = max(bb.xlen, bb.ylen)

        assert abs(actual_dia - expected_dia) < 1.0

    def test_metadata_driving(self, spec):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        gen = BevelGearGenerator(gear_id="driving")
        meta = gen.get_metadata(spec)

        assert meta.part_type == PartType.BEVEL_DRIVE
        assert meta.dimensions["teeth"] == 16
        assert meta.dimensions["module"] == 1.5
        assert meta.dimensions["cone_angle"] == 45.0

    def test_invalid_gear_id(self):
        from mechlogic.generators.gear_bevel import BevelGearGenerator

        with pytest.raises(ValueError, match="must be 'driving' or 'driven'"):
            BevelGearGenerator(gear_id="invalid")
```

**Step 2: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_bevel_gear.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_bevel_gear.py
git commit -m "test: add bevel gear geometry and metadata tests"
```

---

## Task 4: Bevel Gear Generator - Full Geometry with Teeth

**Files:**
- Modify: `src/mechlogic/generators/gear_bevel.py`

**Step 1: Replace generate() with full implementation**

Replace the `generate` method:

```python
    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate a bevel gear with straight teeth.

        The gear has:
        - Conical body (45-degree cone angle for 90-degree shaft intersection)
        - Straight bevel teeth cut into cone surface
        - Central bore for shaft
        """
        module = spec.gears.module
        teeth = spec.gears.bevel_teeth
        pressure_angle = spec.gears.pressure_angle
        shaft_dia = spec.primary_shaft_diameter
        clearance = spec.tolerances.shaft_clearance
        backlash = spec.tolerances.gear_backlash

        # Gear geometry
        pitch_dia = module * teeth
        addendum = module
        dedendum = module * 1.25
        face_width = 2.5 * module

        # Cone dimensions (45-degree for 1:1 ratio at 90 degrees)
        cone_angle = 45.0  # degrees
        pitch_cone_dist = pitch_dia / (2 * math.sin(math.radians(cone_angle)))

        # Outer and inner cone radii
        outer_radius = pitch_dia / 2 + addendum
        inner_radius = pitch_dia / 2 - dedendum

        # Face width along cone
        cone_length = face_width / math.cos(math.radians(cone_angle))

        # Create conical blank
        # Back face (larger)
        back_outer = outer_radius
        back_inner = inner_radius
        # Front face (smaller, toward cone apex)
        taper = face_width * math.tan(math.radians(cone_angle))
        front_outer = outer_radius - taper
        front_inner = inner_radius - taper

        bore_dia = shaft_dia + clearance

        # Build gear blank as conical shell
        gear = (
            cq.Workplane("XY")
            .circle(back_outer)
            .circle(bore_dia / 2)
            .extrude(face_width, taper=-taper)
        )

        # Cut teeth using radial slots
        # Simplified straight bevel: cut slots radially
        tooth_angle = 360.0 / teeth
        slot_angle = tooth_angle * 0.4  # Slot is 40% of pitch

        for i in range(teeth):
            angle = i * tooth_angle

            # Create a wedge-shaped cutter for the tooth gap
            slot_depth = addendum + dedendum + backlash

            # Slot at back (larger)
            slot_width_back = 2 * back_outer * math.sin(math.radians(slot_angle / 2))
            # Slot at front (smaller)
            slot_width_front = 2 * front_outer * math.sin(math.radians(slot_angle / 2))

            # Create tapered slot cutter
            cutter = (
                cq.Workplane("XY")
                .transformed(rotate=(0, 0, angle))
                .center(back_outer - slot_depth / 2, 0)
                .rect(slot_depth, slot_width_back)
                .extrude(face_width * 1.5)
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
git commit -m "feat: implement bevel gear teeth geometry"
```

---

## Task 5: Flexure Block Generator - Test Setup

**Files:**
- Create: `tests/test_flexure_block.py`

**Step 1: Write test file**

```python
"""Tests for flexure block generator."""

import pytest

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType


@pytest.fixture
def spec_data():
    """Return valid specification data."""
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
            "dog_clutch": {
                "teeth": 6,
                "tooth_height": 2.0,
                "engagement_depth": 1.5,
            },
        },
        "geometry": {
            "axle_length": 60.0,
            "housing_thickness": 4.0,
            "lever_throw": 8.0,
            "clutch_width": 10.0,
            "gear_face_width": 8.0,
            "gear_spacing": 3.0,
        },
        "flexure": {
            "thickness": 1.2,
            "length": 15.0,
            "max_deflection": 2.0,
        },
    }


@pytest.fixture
def spec(spec_data):
    return LogicElementSpec.model_validate(spec_data)


class TestFlexureBlockGenerator:
    """Tests for FlexureBlockGenerator."""

    def test_import(self):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator
        assert FlexureBlockGenerator is not None
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/test_flexure_block.py -v`
Expected: FAIL with import error

**Step 3: Commit**

```bash
git add tests/test_flexure_block.py
git commit -m "test: add flexure block generator test scaffold"
```

---

## Task 6: Flexure Block Generator - Implementation

**Files:**
- Create: `src/mechlogic/generators/flexure_block.py`
- Modify: `src/mechlogic/generators/__init__.py`

**Step 1: Create flexure generator**

```python
"""Flexure block generator (living hinge for overload protection)."""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType


class FlexureBlockGenerator:
    """Generator for flexure block with living hinge.

    Creates a compliant beam that mounts the driving bevel gear.
    When S-axis continues rotating after lever reaches end-of-travel,
    the flexure deflects to partially disengage the bevel mesh.

    Designed to be integrated (unioned) with the front housing plate.
    """

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Workplane:
        """Generate flexure block geometry.

        The flexure consists of:
        - A thin beam (living hinge) that bends under load
        - A bearing boss at the free end for the S-shaft
        - A mounting base that connects to housing wall
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
        boss_height = 8.0  # Depth for bearing support
        bore_dia = shaft_dia + clearance

        # Mounting base (thicker for rigidity at fixed end)
        base_thickness = beam_thickness * 3
        base_length = 10.0

        # Create mounting base
        base = (
            cq.Workplane("XY")
            .box(base_length, beam_width, base_thickness)
            .translate((base_length / 2, 0, base_thickness / 2))
        )

        # Create thin beam (living hinge section)
        beam = (
            cq.Workplane("XY")
            .box(beam_length, beam_width, beam_thickness)
            .translate((base_length + beam_length / 2, 0, beam_thickness / 2))
        )

        # Create bearing boss at free end
        boss_x = base_length + beam_length + boss_dia / 2
        boss = (
            cq.Workplane("XY")
            .cylinder(boss_height, boss_dia / 2)
            .translate((boss_x, 0, boss_height / 2))
        )

        # Union all parts
        flexure_block = base.union(beam).union(boss)

        # Cut bearing bore through boss
        bore = (
            cq.Workplane("XY")
            .cylinder(boss_height * 2, bore_dia / 2)
            .translate((boss_x, 0, 0))
        )
        flexure_block = flexure_block.cut(bore)

        return flexure_block

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for BOM."""
        flexure = spec.flexure

        return PartMetadata(
            part_id=PartType.FLEXURE_BLOCK.value,
            part_type=PartType.FLEXURE_BLOCK,
            name="Flexure Block (Living Hinge)",
            material="PLA",
            count=1,
            dimensions={
                "beam_thickness": flexure.thickness,
                "beam_length": flexure.length,
                "max_deflection": flexure.max_deflection,
            },
            notes="Print with beam aligned to layer lines for compliance",
        )
```

**Step 2: Update generators __init__.py**

```python
"""Part generators for mechanical logic compiler."""

from .housing import HousingGenerator
from .lever import LeverGenerator
from .axle import AxleGenerator
from .dog_clutch import DogClutchGenerator
from .gear_spur import SpurGearGenerator
from .gear_bevel import BevelGearGenerator
from .flexure_block import FlexureBlockGenerator

__all__ = [
    "HousingGenerator",
    "LeverGenerator",
    "AxleGenerator",
    "DogClutchGenerator",
    "SpurGearGenerator",
    "BevelGearGenerator",
    "FlexureBlockGenerator",
]
```

**Step 3: Run test**

Run: `source .venv/bin/activate && pytest tests/test_flexure_block.py::TestFlexureBlockGenerator::test_import -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/mechlogic/generators/flexure_block.py src/mechlogic/generators/__init__.py
git commit -m "feat: add flexure block generator"
```

---

## Task 7: Flexure Block Generator - Geometry Tests

**Files:**
- Modify: `tests/test_flexure_block.py`

**Step 1: Add geometry tests**

Append to `TestFlexureBlockGenerator` class:

```python
    def test_generates_solid(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)

        # Should produce valid geometry
        assert block is not None
        assert block.val().isValid()

    def test_beam_length_matches_spec(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)
        bb = block.val().BoundingBox()

        # Total length = base (10) + beam (15) + boss (~9)
        expected_min_length = spec.flexure.length + 15
        assert bb.xlen >= expected_min_length

    def test_has_bearing_bore(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        placement = PartPlacement(
            part_type=PartType.FLEXURE_BLOCK,
            part_id="flexure_block",
        )

        block = gen.generate(spec, placement)

        # Volume should be less than solid block (bore removed)
        bb = block.val().BoundingBox()
        bounding_volume = bb.xlen * bb.ylen * bb.zlen
        actual_volume = block.val().Volume()

        assert actual_volume < bounding_volume * 0.9  # At least 10% removed

    def test_metadata(self, spec):
        from mechlogic.generators.flexure_block import FlexureBlockGenerator

        gen = FlexureBlockGenerator()
        meta = gen.get_metadata(spec)

        assert meta.part_type == PartType.FLEXURE_BLOCK
        assert meta.dimensions["beam_thickness"] == 1.2
        assert meta.dimensions["beam_length"] == 15.0
        assert "layer lines" in meta.notes.lower()
```

**Step 2: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_flexure_block.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_flexure_block.py
git commit -m "test: add flexure block geometry and metadata tests"
```

---

## Task 8: Update LayoutSolver - Add Bevel and Lever Axle Positions

**Files:**
- Modify: `src/mechlogic/assembly/layout.py`
- Create: `tests/test_layout_bevel.py`

**Step 1: Write test for new layout parts**

```python
"""Tests for layout solver bevel gear positioning."""

import pytest

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartType
from mechlogic.assembly.layout import LayoutSolver


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
            "dog_clutch": {
                "teeth": 6,
                "tooth_height": 2.0,
                "engagement_depth": 1.5,
            },
        },
        "geometry": {
            "axle_length": 60.0,
            "housing_thickness": 4.0,
            "lever_throw": 8.0,
            "clutch_width": 10.0,
            "gear_face_width": 8.0,
            "gear_spacing": 3.0,
        },
        "flexure": {
            "thickness": 1.2,
            "length": 15.0,
            "max_deflection": 2.0,
        },
    }


@pytest.fixture
def spec(spec_data):
    return LogicElementSpec.model_validate(spec_data)


class TestLayoutBevelGears:
    """Tests for bevel gear layout."""

    def test_layout_includes_bevel_driving(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        assert "bevel_driving" in model.parts
        assert model.parts["bevel_driving"].part_type == PartType.BEVEL_DRIVE

    def test_layout_includes_bevel_driven(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        assert "bevel_driven" in model.parts
        assert model.parts["bevel_driven"].part_type == PartType.BEVEL_DRIVEN

    def test_layout_includes_lever_pivot(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        assert "lever_pivot" in model.parts
        assert model.parts["lever_pivot"].part_type == PartType.LEVER_PIVOT

    def test_bevel_gears_perpendicular(self, spec):
        solver = LayoutSolver(spec)
        model = solver.solve()

        driving = model.parts["bevel_driving"]
        driven = model.parts["bevel_driven"]

        # Driving gear on S-axis (rotated 90 deg around X)
        # Driven gear on lever axis (no rotation or different)
        # Their rotations should differ by 90 degrees on one axis
        assert driving.rotation != driven.rotation
```

**Step 2: Run test to verify failure**

Run: `source .venv/bin/activate && pytest tests/test_layout_bevel.py -v`
Expected: FAIL (parts not in layout)

**Step 3: Update LayoutSolver**

In `src/mechlogic/assembly/layout.py`, add after line 105 (after axle_s):

```python
        # Bevel gear pair
        # Driving bevel on S-axis, at end of S-shaft near clutch
        bevel_face_width = 2.5 * spec.gears.module
        bevel_pitch_dia = spec.gears.module * spec.gears.bevel_teeth

        model.add_part(
            PartType.BEVEL_DRIVE,
            "bevel_driving",
            origin=(0, s_offset_y - bevel_pitch_dia / 4, z_clutch),
            rotation=(90, 0, 0),  # Aligned with S-axis (Y direction)
        )

        # Driven bevel meshes at 90 degrees, shaft parallel to Z
        # Position so teeth mesh with driving bevel
        model.add_part(
            PartType.BEVEL_DRIVEN,
            "bevel_driven",
            origin=(0, s_offset_y - bevel_pitch_dia / 2, z_clutch),
            rotation=(0, 0, 0),  # Aligned with Z-axis
        )

        # Lever pivot axle (short shaft for driven bevel and lever)
        model.add_part(
            PartType.LEVER_PIVOT,
            "lever_pivot",
            origin=(0, lever_y, z_clutch),
            rotation=(0, 0, 0),
        )
```

Also add new mates after line 129:

```python
        model.add_mate("axle_s", "bevel_driving", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("bevel_driving", "bevel_driven", "gear_mesh", spec.tolerances.gear_backlash)
        model.add_mate("lever_pivot", "bevel_driven", "shaft_hole", spec.tolerances.shaft_clearance)
        model.add_mate("lever_pivot", "lever", "pivot", 0)
```

**Step 4: Run tests**

Run: `source .venv/bin/activate && pytest tests/test_layout_bevel.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/mechlogic/assembly/layout.py tests/test_layout_bevel.py
git commit -m "feat: add bevel gears and lever pivot to layout solver"
```

---

## Task 9: Update AssemblyBuilder - Register New Generators

**Files:**
- Modify: `src/mechlogic/assembly/builder.py`

**Step 1: Add imports and generator registrations**

Update imports at top:

```python
from ..generators import (
    HousingGenerator,
    LeverGenerator,
    AxleGenerator,
    DogClutchGenerator,
    SpurGearGenerator,
    BevelGearGenerator,
    FlexureBlockGenerator,
)
```

Update `_generators` dict in `__init__` (add after line 39):

```python
            PartType.BEVEL_DRIVE: BevelGearGenerator(gear_id="driving"),
            PartType.BEVEL_DRIVEN: BevelGearGenerator(gear_id="driven"),
            PartType.LEVER_PIVOT: AxleGenerator(axle_type="lever"),
```

Update `_get_color` method (add after line 91):

```python
            PartType.BEVEL_DRIVE: cq.Color(0.8, 0.5, 0.2, 1.0),  # Bronze
            PartType.BEVEL_DRIVEN: cq.Color(0.8, 0.5, 0.2, 1.0),  # Bronze
            PartType.LEVER_PIVOT: cq.Color(0.5, 0.5, 0.5, 1.0),  # Gray
```

**Step 2: Update AxleGenerator to support lever type**

In `src/mechlogic/generators/axle.py`, update `__init__`:

```python
    def __init__(self, axle_type: str = "main"):
        """Initialize generator.

        Args:
            axle_type: "main" for A/B/O axis, "s" for selector axis, "lever" for lever pivot
        """
        self.axle_type = axle_type
```

Update `generate` method, add after the S-axis case:

```python
        # For lever pivot, short axle
        if self.axle_type == "lever":
            length = 20.0  # Short pivot shaft
```

Update `get_metadata`:

```python
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
```

**Step 3: Run all tests**

Run: `source .venv/bin/activate && pytest -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/mechlogic/assembly/builder.py src/mechlogic/generators/axle.py
git commit -m "feat: register bevel and lever pivot generators in assembly builder"
```

---

## Task 10: Integration Test - Full Assembly with Bevel Gears

**Files:**
- Create: `tests/test_assembly_integration.py`

**Step 1: Write integration test**

```python
"""Integration tests for full assembly generation."""

import pytest
import tempfile
from pathlib import Path

from mechlogic.models.spec import LogicElementSpec
from mechlogic.assembly.builder import AssemblyBuilder


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
            "dog_clutch": {
                "teeth": 6,
                "tooth_height": 2.0,
                "engagement_depth": 1.5,
            },
        },
        "geometry": {
            "axle_length": 60.0,
            "housing_thickness": 4.0,
            "lever_throw": 8.0,
            "clutch_width": 10.0,
            "gear_face_width": 8.0,
            "gear_spacing": 3.0,
        },
        "flexure": {
            "thickness": 1.2,
            "length": 15.0,
            "max_deflection": 2.0,
        },
    }


@pytest.fixture
def spec(spec_data):
    return LogicElementSpec.model_validate(spec_data)


class TestFullAssembly:
    """Integration tests for complete assembly."""

    def test_build_assembly_succeeds(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        assert assembly is not None
        assert assembly.name == "test_mux"

    def test_assembly_contains_bevel_gears(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        part_names = [child.name for child in assembly.children]

        assert "bevel_driving" in part_names
        assert "bevel_driven" in part_names

    def test_assembly_contains_lever_pivot(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        part_names = [child.name for child in assembly.children]

        assert "lever_pivot" in part_names

    def test_bom_includes_new_parts(self, spec):
        builder = AssemblyBuilder(spec)
        builder.build()

        bom = builder.get_bom()
        part_ids = [item["part_id"] for item in bom]

        assert "bevel_driving" in part_ids
        assert "bevel_driven" in part_ids
        assert "lever_pivot" in part_ids

    def test_export_step(self, spec):
        builder = AssemblyBuilder(spec)
        assembly = builder.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "assembly.step"
            assembly.save(str(step_path))

            assert step_path.exists()
            assert step_path.stat().st_size > 0
```

**Step 2: Run integration tests**

Run: `source .venv/bin/activate && pytest tests/test_assembly_integration.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_assembly_integration.py
git commit -m "test: add integration tests for assembly with bevel gears"
```

---

## Task 11: Run Full Test Suite and Verify

**Step 1: Run all tests**

Run: `source .venv/bin/activate && pytest -v --tb=short`
Expected: All tests PASS

**Step 2: Generate test assembly and visually inspect**

Run: `source .venv/bin/activate && python -c "
from mechlogic.models.spec import LogicElementSpec
from mechlogic.assembly.builder import AssemblyBuilder
import yaml

spec_data = yaml.safe_load(open('examples/mux_2to1.yaml'))
spec = LogicElementSpec.model_validate(spec_data)
builder = AssemblyBuilder(spec)
assembly = builder.build()
assembly.save('output/v02_assembly.step')
print('Assembly saved to output/v02_assembly.step')
print(f'Parts: {[c.name for c in assembly.children]}')
"`

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete v0.2 bevel gear and flexure implementation"
```
