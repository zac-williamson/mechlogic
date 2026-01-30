"""Tests for bevel gear meshing and axle geometry."""

import pytest
import cadquery as cq

from mechlogic.models.spec import LogicElementSpec
from mechlogic.models.geometry import PartPlacement, PartType
from mechlogic.generators.gear_bevel import BevelGearGenerator


# Constants for axle geometry (must match generate_bevel_submodel.py)
AXLE_LENGTH = 50.0
AXLE_CLEARANCE = 0.5


@pytest.fixture
def spec():
    """Return a valid specification for testing."""
    spec_data = {
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
    return LogicElementSpec.model_validate(spec_data)


def shapes_intersect(shape1, shape2, tolerance=0.01):
    """Check if two CadQuery shapes intersect.

    Returns True if the intersection has volume greater than tolerance.
    """
    try:
        intersection = shape1.intersect(shape2)
        vol = intersection.Volume()
        return vol > tolerance
    except Exception:
        return False


def create_meshed_gear_pair(spec, driven_rotation_offset=0.0):
    """Create a pair of bevel gears positioned for meshing.

    Args:
        spec: LogicElementSpec with gear parameters
        driven_rotation_offset: Additional rotation (degrees) to apply to driven gear

    Returns:
        Tuple of (driving_gear_solid, driven_gear_solid) positioned for meshing
    """
    gen = BevelGearGenerator(gear_id="driving")
    placement = PartPlacement(part_type=PartType.BEVEL_DRIVE, part_id="bevel_driving")

    driving_gear = gen.generate(spec, placement)
    driven_gear = gen.generate(spec, placement)

    cone_distance = gen.get_cone_distance(spec)
    tooth_angle = 360.0 / spec.gears.bevel_teeth

    # Mesh distance empirically determined for proper tooth engagement
    mesh_distance = cone_distance * 0.79

    # Position driving gear on Z-axis
    driving_positioned = driving_gear.translate((0, 0, -mesh_distance))

    # Prepare driven gear: flip and rotate for mesh alignment
    mesh_offset_angle = tooth_angle / 2 + driven_rotation_offset
    driven_flipped = (
        driven_gear
        .rotate((0, 0, 0), (1, 0, 0), 180)
        .rotate((0, 0, 0), (0, 0, 1), mesh_offset_angle)
    )

    # Position driven gear: rotate 90° around Y, translate along -X
    driven_positioned = (
        driven_flipped
        .rotate((0, 0, 0), (0, 1, 0), -90)
        .translate((-mesh_distance, 0, 0))
    )

    return driving_positioned.val(), driven_positioned.val()


class TestBevelGearMeshing:
    """Tests for bevel gear mesh geometry."""

    def test_gears_do_not_intersect_at_rest(self, spec):
        """Verify that properly meshed gears do not intersect.

        When teeth are aligned to interleave (one gear's teeth in the other's gaps),
        the gears should not have any overlapping volume.
        """
        driving, driven = create_meshed_gear_pair(spec, driven_rotation_offset=0.0)

        assert not shapes_intersect(driving, driven), (
            "Gears should not intersect when properly meshed with teeth interleaved"
        )

    def test_gears_intersect_when_misaligned(self, spec):
        """Verify that gears intersect when rotated by half a tooth.

        If the driven gear is rotated by half a tooth pitch, the teeth
        should collide with each other instead of interleaving.
        """
        tooth_angle = 360.0 / spec.gears.bevel_teeth
        half_tooth = tooth_angle / 2

        driving, driven = create_meshed_gear_pair(spec, driven_rotation_offset=half_tooth)

        assert shapes_intersect(driving, driven), (
            "Gears should intersect when driven gear is rotated by half a tooth "
            "(teeth collide instead of interleaving)"
        )

    def test_gears_intersect_when_rotated_quarter_tooth(self, spec):
        """Verify that gears intersect when rotated by a quarter tooth.

        Even a quarter tooth rotation should cause intersection as the
        tooth flanks will overlap.
        """
        tooth_angle = 360.0 / spec.gears.bevel_teeth
        quarter_tooth = tooth_angle / 4

        driving, driven = create_meshed_gear_pair(spec, driven_rotation_offset=quarter_tooth)

        assert shapes_intersect(driving, driven), (
            "Gears should intersect when driven gear is rotated by a quarter tooth"
        )


def create_axle_pair(spec, driving_axle_extension=0.0):
    """Create the two axles for the bevel gear assembly.

    Args:
        spec: LogicElementSpec with gear parameters
        driving_axle_extension: Additional length (mm) to add to driving axle top

    Returns:
        Tuple of (driving_axle_solid, driven_axle_solid)
    """
    gen = BevelGearGenerator(gear_id="driving")
    cone_distance = gen.get_cone_distance(spec)
    mesh_distance = cone_distance * 0.79

    shaft_diameter = spec.primary_shaft_diameter
    shaft_radius = shaft_diameter / 2

    # Driving axle: along Z-axis, truncated to not hit driven axle
    driving_axle_top = -(shaft_radius + AXLE_CLEARANCE) + driving_axle_extension
    driving_axle_bottom = -mesh_distance - 30
    driving_axle_length = driving_axle_top - driving_axle_bottom

    driving_axle = (
        cq.Workplane('XY')
        .workplane(offset=driving_axle_bottom)
        .circle(shaft_radius)
        .extrude(driving_axle_length)
    )

    # Driven axle: along X-axis
    driven_axle = (
        cq.Workplane('YZ')
        .circle(shaft_radius)
        .extrude(AXLE_LENGTH)
        .translate((-mesh_distance - AXLE_LENGTH / 2, 0, 0))
    )

    return driving_axle.val(), driven_axle.val()


class TestAxleGeometry:
    """Tests for axle positioning to avoid interference."""

    def test_axles_do_not_intersect(self, spec):
        """Verify that the two axles do not intersect at their normal lengths."""
        driving_axle, driven_axle = create_axle_pair(spec, driving_axle_extension=0.0)

        assert not shapes_intersect(driving_axle, driven_axle), (
            "Axles should not intersect - driving axle should be truncated "
            "to clear the driven axle"
        )

    def test_axles_intersect_when_driving_extended(self, spec):
        """Verify that axles intersect if driving axle is extended by 5mm."""
        driving_axle, driven_axle = create_axle_pair(spec, driving_axle_extension=5.0)

        assert shapes_intersect(driving_axle, driven_axle), (
            "Axles should intersect when driving axle is extended by 5mm"
        )
