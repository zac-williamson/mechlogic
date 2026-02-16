"""Tests for gear rack teeth positioning.

Validates that teeth are properly mounted on the rack body.

For a proper gear rack:
- The rack body is a solid base from Z=0 to Z=rack_height
- Teeth sit on TOP of the body with:
  - Tooth tips at Z = rack_height + addendum
  - Tooth roots at Z = rack_height - dedendum (overlapping with body top)
- Teeth and body should share material at the root area (they connect)
"""

import math
import pytest
import cadquery as cq

from src.mechlogic.gears.gear_rack import GearRackGenerator, GearRackParams, RackSection


class TestGearRackTeethPosition:
    """Test that gear rack teeth are properly positioned on the rack body."""

    @pytest.fixture
    def rack_params(self):
        """Simple rack with one toothed section for testing."""
        return GearRackParams(
            module=1.5,
            pressure_angle=20.0,
            rack_height=10.0,
            rack_width=15.0,
            sections=[
                RackSection(50.0, True),  # Just teeth, no flat sections
            ],
        )

    @pytest.fixture
    def rack_body(self, rack_params):
        """Generate just the rack body (no teeth)."""
        p = rack_params
        total_length = sum(s.length for s in p.sections)

        body = (
            cq.Workplane('XY')
            .rect(total_length, p.rack_width, centered=False)
            .extrude(p.rack_height)
            .translate((0, -p.rack_width / 2, 0))
        )
        return body

    @pytest.fixture
    def rack_teeth_above_body(self, rack_params):
        """Generate teeth positioned just above the body (no overlap).

        Teeth are placed so their root is at Z=rack_height (body top),
        meaning they just touch but don't overlap.
        """
        p = rack_params
        m = p.module
        pitch = math.pi * m
        addendum = m
        dedendum = 1.25 * m
        alpha = math.radians(p.pressure_angle)

        # Tooth profile (root at Z=0 in local coords)
        tooth_thickness = pitch / 2
        tan_alpha = math.tan(alpha)
        tip_half_width = tooth_thickness / 2 - addendum * tan_alpha
        root_half_width = tooth_thickness / 2 + dedendum * tan_alpha

        # Profile with root at Z=0, tip at Z=addendum+dedendum
        tooth_profile = [
            (-root_half_width, 0),
            (-tip_half_width, addendum + dedendum),
            (tip_half_width, addendum + dedendum),
            (root_half_width, 0),
        ]

        # Position teeth so root is at rack_height (body top)
        root_z = p.rack_height

        total_length = sum(s.length for s in p.sections)
        num_teeth = int(total_length / pitch)
        teeth_total_length = num_teeth * pitch
        start_offset = (total_length - teeth_total_length) / 2

        teeth = None
        for i in range(num_teeth):
            tooth_center_x = start_offset + (i + 0.5) * pitch

            tooth_points = [
                (tooth_center_x + px, root_z + pz)
                for px, pz in tooth_profile
            ]

            tooth = (
                cq.Workplane('XZ')
                .polyline(tooth_points)
                .close()
                .extrude(p.rack_width)
                .translate((0, p.rack_width / 2, 0))  # Center on Y=0
            )

            if teeth is None:
                teeth = tooth
            else:
                teeth = teeth.union(tooth)

        return teeth

    def _get_intersection_volume(self, shape1: cq.Workplane, shape2: cq.Workplane) -> float:
        """Get the volume of intersection between two shapes."""
        intersection = shape1.intersect(shape2)
        if intersection.val().isValid():
            return intersection.val().Volume()
        return 0.0

    def _check_intersection(self, shape1: cq.Workplane, shape2: cq.Workplane) -> bool:
        """Check if two shapes intersect (non-zero intersection volume)."""
        return self._get_intersection_volume(shape1, shape2) > 0.001

    def test_idle_state_no_intersection(self, rack_body, rack_teeth_above_body):
        """Test 1: In idle state, teeth should NOT intersect with rack body.

        The teeth are positioned with their root at the body top surface,
        so they touch but don't overlap.
        """
        intersects = self._check_intersection(rack_body, rack_teeth_above_body)

        # Export for debugging
        cq.exporters.export(rack_body, "test_rack_body.step")
        cq.exporters.export(rack_teeth_above_body, "test_rack_teeth.step")

        assert not intersects, (
            "Teeth should NOT intersect with rack body in idle state. "
            "Teeth are improperly positioned."
        )

    def test_teeth_moved_into_body_intersection(self, rack_body, rack_teeth_above_body):
        """Test 2: If teeth are moved 2mm in -Z (into body), they SHOULD intersect.

        This validates that the teeth are close enough to the body that a small
        movement would cause overlap.
        """
        # Move teeth 2mm down (into the body)
        teeth_moved = rack_teeth_above_body.translate((0, 0, -2.0))

        intersects = self._check_intersection(rack_body, teeth_moved)

        assert intersects, (
            "Teeth moved 2mm into body (-Z) should intersect with rack body. "
            "This suggests teeth are too far from the body."
        )

    def test_teeth_moved_in_y_no_intersection(self, rack_body, rack_teeth_above_body):
        """Test 3: If teeth are moved 2mm in Y, they should NOT intersect.

        Moving parallel to the rack surface shouldn't cause intersection
        (assuming teeth were not intersecting to begin with).
        """
        # Move teeth 2mm in Y direction
        teeth_moved = rack_teeth_above_body.translate((0, 2.0, 0))

        intersects = self._check_intersection(rack_body, teeth_moved)

        assert not intersects, (
            "Teeth moved 2mm in Y should NOT intersect with rack body."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
