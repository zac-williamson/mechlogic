"""Bevel lever with upper housing plates for axle mounting.

Creates a bevel lever assembly (bevel gear pair + shift lever) with
upper housing plates that provide mounting points for the axles.

The housing consists of:
- YZ plates for the driving bevel axle (runs along X-axis)
- XY plates for the driven bevel axle (runs along Z-axis)
- Optional serpentine flexure mounted to left wall for compliant axle support
"""

import cadquery as cq

from ..models.spec import LogicElementSpec
from ..models.geometry import PartPlacement, PartMetadata, PartType
from .bevel_lever import BevelLeverGenerator
from .layout import LayoutCalculator
from .serpentine_flexure import SerpentineFlexureGenerator, SerpentineFlexureParams


class BevelLeverWithUpperHousingGenerator:
    """Generator for bevel lever with upper housing plates.

    Combines BevelLeverGenerator with housing plates for axle support.
    """

    def __init__(
        self,
        include_axles: bool = True,
        cantilevered: bool = True,
        include_flexure: bool = False,
        extend_to_lower_housing: bool = False,
        lower_housing_y_max: float = 10.0,
        l_shaped_front_back: bool = False,
    ):
        """Initialize the generator.

        Args:
            include_axles: Whether to include axles in the assembly.
            cantilevered: If True, only generate outer plates to avoid
                         axle intersection at the lever pivot.
            include_flexure: Whether to mount serpentine flexure on left wall.
            extend_to_lower_housing: Whether to extend walls down to meet lower housing.
            lower_housing_y_max: Top Y position of lower housing (for wall extension).
            l_shaped_front_back: If True, front/back walls get L-shaped extensions.
                                If False (Option A), only left/right walls extend.
        """
        self.include_axles = include_axles
        self.cantilevered = cantilevered
        self.include_flexure = include_flexure
        self.extend_to_lower_housing = extend_to_lower_housing
        self.lower_housing_y_max = lower_housing_y_max
        self.l_shaped_front_back = l_shaped_front_back

        # Flexure params/gen are initialized lazily when spec is available
        self._flexure_params = None
        self._flexure_gen = None

    def _init_flexure(self, spec: LogicElementSpec) -> None:
        """Initialize flexure parameters from spec."""
        if self._flexure_params is None:
            self._flexure_params = SerpentineFlexureParams(
                axle_diameter=spec.shaft_diameter,
                mounting_hole_diameter=2.2,  # M2 clearance hole
            )
            self._flexure_gen = SerpentineFlexureGenerator(self._flexure_params)

    def generate(self, spec: LogicElementSpec, placement: PartPlacement) -> cq.Assembly:
        """Generate bevel lever with upper housing assembly.

        Args:
            spec: The logic element specification.
            placement: The placement of this assembly.

        Returns:
            CadQuery Assembly containing the mechanism and housing.
        """
        assy = cq.Assembly()
        self.add_to_assembly(assy, spec, origin=(0, 0, 0))
        return assy

    def add_to_assembly(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        origin: tuple[float, float, float] = (0, 0, 0),
        name_prefix: str = "",
    ) -> None:
        """Add bevel lever and upper housing to an existing assembly.

        Args:
            assy: The assembly to add components to.
            spec: The logic element specification.
            origin: The (x, y, z) origin point (at clutch axis).
            name_prefix: Optional prefix for component names.
        """
        # Add bevel lever mechanism (without axles - we create our own)
        bevel_lever_gen = BevelLeverGenerator(include_axles=False)
        bevel_lever_gen.add_to_assembly(assy, spec, origin=origin, name_prefix=name_prefix)

        # Add upper housing plates
        upper_housing = self._generate_upper_housing(spec, origin)
        assy.add(
            upper_housing,
            name=f"{name_prefix}upper_housing" if name_prefix else "upper_housing",
            color=cq.Color(0.7, 0.7, 0.7),  # Light gray
        )

        # Add extended axles that pass through housing plates
        if self.include_axles:
            self._add_axles(assy, spec, origin, name_prefix)

        # Add serpentine flexure to left wall
        if self.include_flexure:
            self._add_flexure(assy, spec, origin, name_prefix)

    def _generate_upper_housing(
        self,
        spec: LogicElementSpec,
        origin: tuple[float, float, float],
    ) -> cq.Workplane:
        """Generate the upper housing walls.

        Creates 4 connected walls forming an open box:
        - Left wall (YZ plane): holds driving bevel axle
        - Right wall (YZ plane): structural, aligned with lower housing
        - Front wall (XY plane): holds driven bevel axle (front)
        - Back wall (XY plane): holds driven bevel axle (back)

        The left and right walls are aligned with the lower housing plates
        (same X-coordinates) so all faces are flush.

        Args:
            spec: The logic element specification.
            origin: The origin point (at clutch axis).

        Returns:
            CadQuery Workplane containing the housing walls.
        """
        # Initialize flexure params if needed (requires spec)
        self._init_flexure(spec)

        ox, oy, oz = origin
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)
        spur_gear_radius = LayoutCalculator.calculate_spur_gear_radius(spec)

        # Dimensions from spec
        shaft_diameter = spec.primary_shaft_diameter
        axle_clearance = 0.2  # Clearance for rotation
        hole_diameter = shaft_diameter + axle_clearance * 2

        wall_thickness = spec.geometry.housing_thickness

        # Bevel gear clearance (still needed for Z calculations)
        bevel_gear_radius = 10.0  # Approximate gear body radius
        gear_clearance = 2.0

        # Calculate flexure dimensions if needed
        if self.include_flexure:
            fp = self._flexure_params
            fold_pitch = fp.beam_width + fp.beam_spacing
            serpentine_width = (fp.num_folds - 1) * fold_pitch + fp.beam_width
            inner_width = fp.platform_width + 2 * serpentine_width + 2 * fp.beam_spacing
            inner_height = fp.segment_length + 2 * fp.beam_width
            flexure_outer_width = inner_width + 2 * fp.frame_thickness  # ~50mm
            flexure_outer_height = inner_height + 2 * fp.frame_thickness  # ~27mm

            # When flexure is rotated 90° onto YZ plane:
            # - Flexure X (outer_width ~50mm) → Wall Z extent
            # - Flexure Y (outer_height ~27mm) → Wall Y height
            # Flexure mounting hole positions (relative to flexure center)
            self._flexure_hole_offset_y = flexure_outer_height / 2 - fp.frame_thickness / 2  # Y on wall
            self._flexure_hole_offset_z = flexure_outer_width / 2 - fp.frame_thickness / 2   # Z on wall
            self._flexure_outer_width = flexure_outer_width
            self._flexure_outer_height = flexure_outer_height
            # Store inner cavity dimensions for rectangular opening in wall
            # When rotated: inner_width → Z dimension, inner_height → Y dimension
            self._flexure_inner_width = inner_width    # ~40mm → opening Z size
            self._flexure_inner_height = inner_height  # ~17mm → opening Y size

            # Wall Z extent must be large enough so mounting holes don't intersect front/back walls
            # Mounting holes are at Z = ±(flexure_outer_width/2 - frame_thickness/2) from center
            # Add clearance between mounting holes and wall inner faces
            mounting_hole_clearance = 5.0  # Clearance between mounting holes and walls
            wall_z_extent = flexure_outer_width + 2 * wall_thickness + 2 * mounting_hole_clearance

            # Wall Y extent: bottom accommodates flexure, top at pivot_y + spur_gear_radius
            wall_bottom_y = oy + pivot_y - flexure_outer_height / 2
        else:
            wall_z_extent = None  # Use default calculation
            wall_bottom_y = oy + pivot_y - 10.0  # Default bottom

        # Top of upper housing at pivot_y + spur_gear_radius for stackability
        # This allows stacked mux units to connect via spur gears
        wall_top_y = oy + pivot_y + spur_gear_radius

        # Calculate wall X positions
        # When origin is at clutch_center (mux assembly), align with lower housing plates
        # When origin is at 0 (standalone), use bevel-relative positions
        selector_layout = LayoutCalculator.calculate_selector_layout(spec)
        is_mux_assembly = abs(ox - selector_layout.clutch_center) < 0.1

        if is_mux_assembly:
            # Align with lower housing plates for flush faces
            left_wall_x = housing_layout.left_plate_x
            right_wall_x = housing_layout.right_plate_x
        else:
            # Standalone: position walls relative to bevel mechanism
            driving_gear_x = ox - bevel_layout.mesh_distance
            left_wall_x = driving_gear_x - bevel_gear_radius - gear_clearance - 5
            # Right wall: clear driven bevel gear at ox
            driven_gear_clearance = bevel_gear_radius + gear_clearance + 5
            right_wall_x = ox + driven_gear_clearance

        # Right edge of front/back walls (X dimension) - extend to meet right wall
        right_edge_x = right_wall_x + wall_thickness / 2  # Flush with right face of right wall

        # Driven bevel gear is at Z = -bevel_layout.mesh_distance from origin
        driven_gear_z = oz - bevel_layout.mesh_distance
        front_wall_z_gear = driven_gear_z - bevel_gear_radius - gear_clearance - 5

        # Back wall must clear both lever AND driving bevel gear
        # Driving bevel is at Z=0, extends roughly ±face_width in Z when rotated
        # Use generous clearance to avoid intersection
        driving_bevel_clearance = 20.0  # Clear the driving bevel gear body
        back_wall_z_gear = oz + driving_bevel_clearance

        # If flexure is included, walls are sized to match flexure + sit flush
        if self.include_flexure:
            # Center the Z extent on the driving axle (oz)
            front_wall_z = oz - wall_z_extent / 2 + wall_thickness  # Inner edge of front wall
            back_wall_z = oz + wall_z_extent / 2 - wall_thickness   # Inner edge of back wall
        else:
            front_wall_z = front_wall_z_gear
            back_wall_z = back_wall_z_gear

        # Calculate extension Y if extending to lower housing
        if self.extend_to_lower_housing:
            extension_y_min = self.lower_housing_y_max
        else:
            extension_y_min = wall_bottom_y

        # Store positions for axle generation
        self._wall_positions = {
            'left_wall_x': left_wall_x,
            'front_wall_z': front_wall_z,
            'back_wall_z': back_wall_z,
            'right_wall_x': right_wall_x,
            'right_edge_x': right_edge_x,
            'wall_bottom_y': wall_bottom_y,
            'wall_top_y': wall_top_y,
            'wall_thickness': wall_thickness,
            'pivot_y': oy + pivot_y,
            'driving_axle_z': oz,
            'driven_axle_x': ox,
            'extension_y_min': extension_y_min,
            'extend_to_lower_housing': self.extend_to_lower_housing,
        }

        # Calculate flexure mounting hole positions if needed
        if self.include_flexure:
            flexure_mount_holes = [
                (oy + pivot_y + self._flexure_hole_offset_y, oz + self._flexure_hole_offset_z),
                (oy + pivot_y - self._flexure_hole_offset_y, oz + self._flexure_hole_offset_z),
                (oy + pivot_y + self._flexure_hole_offset_y, oz - self._flexure_hole_offset_z),
                (oy + pivot_y - self._flexure_hole_offset_y, oz - self._flexure_hole_offset_z),
            ]
        else:
            flexure_mount_holes = None

        # Create left wall (YZ plane) with hole for driving bevel axle
        # Left wall Z extent should match outer faces of front/back walls for flush fit
        # Front wall is centered on front_wall_z, so its front face is at front_wall_z - thickness/2
        # Back wall is centered on back_wall_z, so its back face is at back_wall_z + thickness/2
        # When flexure is used, pass inner cavity size for large rectangular opening
        inner_cavity_size = None
        if self.include_flexure:
            # inner_width → Z, inner_height → Y (after 90° rotation)
            inner_cavity_size = (self._flexure_inner_height, self._flexure_inner_width)

        # Left/right walls extend down to lower housing when enabled
        left_right_y_min = extension_y_min if self.extend_to_lower_housing else wall_bottom_y

        left_wall = self._make_left_wall(
            wall_x=left_wall_x,
            y_min=left_right_y_min,
            y_max=wall_top_y,
            z_min=front_wall_z - wall_thickness / 2,  # Flush with front face of front wall
            z_max=back_wall_z + wall_thickness / 2,   # Flush with back face of back wall
            thickness=wall_thickness,
            hole_y=oy + pivot_y,
            hole_z=oz,
            hole_diameter=hole_diameter,
            mounting_holes=flexure_mount_holes,
            inner_cavity_size=inner_cavity_size,
        )

        # Create front wall (XY plane) with hole for driven bevel axle
        # Front/back walls X extent should start at left wall's left face for flush fit
        # Left wall is centered on left_wall_x, so its left face is at left_wall_x - thickness/2
        if self.extend_to_lower_housing and self.l_shaped_front_back:
            # Option B: L-shaped front/back walls with outer sections extending down
            outer_section_width = 10.0  # Width of outer sections that extend down
            front_wall = self._make_front_back_wall_l_shaped(
                wall_z=front_wall_z,
                x_min=left_wall_x - wall_thickness / 2,
                x_max=right_edge_x,
                y_upper=wall_top_y,
                y_mid=wall_bottom_y,
                y_lower=extension_y_min,
                thickness=wall_thickness,
                outer_section_width=outer_section_width,
                hole_x=ox,
                hole_y=oy + pivot_y,
                hole_diameter=hole_diameter,
            )
            back_wall = self._make_front_back_wall_l_shaped(
                wall_z=back_wall_z,
                x_min=left_wall_x - wall_thickness / 2,
                x_max=right_edge_x,
                y_upper=wall_top_y,
                y_mid=wall_bottom_y,
                y_lower=extension_y_min,
                thickness=wall_thickness,
                outer_section_width=outer_section_width,
                hole_x=ox,
                hole_y=oy + pivot_y,
                hole_diameter=hole_diameter,
            )
        else:
            front_wall = self._make_front_back_wall(
                wall_z=front_wall_z,
                x_min=left_wall_x - wall_thickness / 2,  # Flush with left face of left wall
                x_max=right_edge_x,
                y_min=wall_bottom_y,
                y_max=wall_top_y,
                thickness=wall_thickness,
                hole_x=ox,
                hole_y=oy + pivot_y,
                hole_diameter=hole_diameter,
            )
            back_wall = self._make_front_back_wall(
                wall_z=back_wall_z,
                x_min=left_wall_x - wall_thickness / 2,  # Flush with left face of left wall
                x_max=right_edge_x,
                y_min=wall_bottom_y,
                y_max=wall_top_y,
                thickness=wall_thickness,
                hole_x=ox,
                hole_y=oy + pivot_y,
                hole_diameter=hole_diameter,
            )

        # Create right wall (YZ plane) - no hole needed, just structural
        right_wall = self._make_right_wall(
            wall_x=right_wall_x,
            y_min=left_right_y_min,
            y_max=wall_top_y,
            z_min=front_wall_z - wall_thickness / 2,  # Flush with front face of front wall
            z_max=back_wall_z + wall_thickness / 2,   # Flush with back face of back wall
            thickness=wall_thickness,
        )

        result = left_wall.union(front_wall).union(back_wall).union(right_wall)

        return result

    def _make_left_wall(
        self,
        wall_x: float,
        y_min: float,
        y_max: float,
        z_min: float,
        z_max: float,
        thickness: float,
        hole_y: float,
        hole_z: float,
        hole_diameter: float,
        mounting_holes: list[tuple[float, float]] = None,
        inner_cavity_size: tuple[float, float] = None,
    ) -> cq.Workplane:
        """Create the left wall (YZ plane) with axle opening and optional mounting holes.

        When inner_cavity_size is provided (flexure mode), cuts a large rectangular
        opening matching the flexure's inner cavity since the flexure provides axle support.

        Args:
            inner_cavity_size: (height, width) of rectangular opening in Y, Z dimensions
        """
        height = y_max - y_min
        depth = z_max - z_min
        center_y = (y_min + y_max) / 2
        center_z = (z_min + z_max) / 2

        wall = (
            cq.Workplane('YZ')
            .center(center_y, center_z)
            .rect(height, depth)
            .extrude(thickness)
            .translate((wall_x - thickness / 2, 0, 0))
        )

        # Cut opening for driving bevel axle
        if inner_cavity_size:
            # Flexure provides axle support - cut large rectangular opening
            # matching flexure's inner cavity size
            rect_height, rect_width = inner_cavity_size  # Y, Z dimensions
            opening = (
                cq.Workplane('YZ')
                .center(hole_y, hole_z)
                .rect(rect_height, rect_width)
                .extrude(thickness + 2)
                .translate((wall_x - thickness / 2 - 1, 0, 0))
            )
        else:
            # No flexure - cut circular hole for axle mounting
            opening = (
                cq.Workplane('YZ')
                .center(hole_y, hole_z)
                .circle(hole_diameter / 2)
                .extrude(thickness + 2)
                .translate((wall_x - thickness / 2 - 1, 0, 0))
            )
        wall = wall.cut(opening)

        # Cut mounting holes for flexure (M2 clearance holes)
        if mounting_holes:
            mounting_hole_dia = 2.2  # M2 clearance
            for mount_y, mount_z in mounting_holes:
                mount_hole = (
                    cq.Workplane('YZ')
                    .center(mount_y, mount_z)
                    .circle(mounting_hole_dia / 2)
                    .extrude(thickness + 2)
                    .translate((wall_x - thickness / 2 - 1, 0, 0))
                )
                wall = wall.cut(mount_hole)

        return wall

    def _make_front_back_wall(
        self,
        wall_z: float,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        thickness: float,
        hole_x: float,
        hole_y: float,
        hole_diameter: float,
    ) -> cq.Workplane:
        """Create a front or back wall (XY plane) with axle hole."""
        width = x_max - x_min
        height = y_max - y_min
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2

        wall = (
            cq.Workplane('XY')
            .center(center_x, center_y)
            .rect(width, height)
            .extrude(thickness)
            .translate((0, 0, wall_z - thickness / 2))
        )

        # Cut hole for driven bevel axle
        hole = (
            cq.Workplane('XY')
            .center(hole_x, hole_y)
            .circle(hole_diameter / 2)
            .extrude(thickness + 2)
            .translate((0, 0, wall_z - thickness / 2 - 1))
        )
        wall = wall.cut(hole)

        return wall

    def _make_front_back_wall_l_shaped(
        self,
        wall_z: float,
        x_min: float,
        x_max: float,
        y_upper: float,
        y_mid: float,
        y_lower: float,
        thickness: float,
        outer_section_width: float,
        hole_x: float,
        hole_y: float,
        hole_diameter: float,
    ) -> cq.Workplane:
        """Create an L-shaped front or back wall (XY plane) with axle hole.

        The wall has an inverted-U shape when viewed from the Z direction:
        - Full width at the top (y_mid to y_upper)
        - Only outer sections extend down (y_lower to y_mid) on left and right edges
        - Central section is cut out to avoid gears

        Args:
            wall_z: Z position of wall center
            x_min: Left edge X
            x_max: Right edge X
            y_upper: Top Y of wall
            y_mid: Y where the central cutout starts (bottom of upper section)
            y_lower: Bottom Y of outer sections
            thickness: Wall thickness
            outer_section_width: Width of each outer section that extends down
            hole_x: X position of axle hole
            hole_y: Y position of axle hole
            hole_diameter: Diameter of axle hole
        """
        width = x_max - x_min

        # Create the L-shape by combining three rectangles:
        # 1. Top section: full width, from y_mid to y_upper
        top_height = y_upper - y_mid
        top_center_y = (y_mid + y_upper) / 2
        top_center_x = (x_min + x_max) / 2

        top_section = (
            cq.Workplane('XY')
            .center(top_center_x, top_center_y)
            .rect(width, top_height)
            .extrude(thickness)
            .translate((0, 0, wall_z - thickness / 2))
        )

        # 2. Left outer section: from y_lower to y_mid
        left_height = y_mid - y_lower
        left_center_y = (y_lower + y_mid) / 2
        left_center_x = x_min + outer_section_width / 2

        left_section = (
            cq.Workplane('XY')
            .center(left_center_x, left_center_y)
            .rect(outer_section_width, left_height)
            .extrude(thickness)
            .translate((0, 0, wall_z - thickness / 2))
        )

        # 3. Right outer section: from y_lower to y_mid
        right_center_x = x_max - outer_section_width / 2

        right_section = (
            cq.Workplane('XY')
            .center(right_center_x, left_center_y)
            .rect(outer_section_width, left_height)
            .extrude(thickness)
            .translate((0, 0, wall_z - thickness / 2))
        )

        # Combine all sections
        wall = top_section.union(left_section).union(right_section)

        # Cut hole for driven bevel axle (in the top section)
        hole = (
            cq.Workplane('XY')
            .center(hole_x, hole_y)
            .circle(hole_diameter / 2)
            .extrude(thickness + 2)
            .translate((0, 0, wall_z - thickness / 2 - 1))
        )
        wall = wall.cut(hole)

        return wall

    def _make_right_wall(
        self,
        wall_x: float,
        y_min: float,
        y_max: float,
        z_min: float,
        z_max: float,
        thickness: float,
    ) -> cq.Workplane:
        """Create the right wall (YZ plane) - structural only, no holes."""
        height = y_max - y_min
        depth = z_max - z_min
        center_y = (y_min + y_max) / 2
        center_z = (z_min + z_max) / 2

        wall = (
            cq.Workplane('YZ')
            .center(center_y, center_z)
            .rect(height, depth)
            .extrude(thickness)
            .translate((wall_x - thickness / 2, 0, 0))
        )

        return wall

    def _add_axles(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add bevel gear axles that extend through housing walls.

        Axles extend past the outer housing walls by axle_overhang.
        """
        ox, oy, oz = origin
        housing_layout = LayoutCalculator.calculate_housing_layout(spec)

        shaft_diameter = spec.primary_shaft_diameter
        axle_overhang = housing_layout.axle_overhang

        # Get wall positions from housing generation
        wp = self._wall_positions
        wall_thickness = wp['wall_thickness']

        # Driving bevel axle: runs along X at (Y=pivot_y, Z=0)
        driving_y = wp['pivot_y']
        driving_z = wp['driving_axle_z']
        left_wall_x = wp['left_wall_x']

        # Axle starts at left wall outer edge minus overhang
        # Axle must end BEFORE the lever pivot block (which extends from X=-6 to X=+6)
        # The driving bevel gear is at X = -bevel_mesh_distance, axle should end just past the gear
        driving_axle_start = left_wall_x - wall_thickness / 2 - axle_overhang
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        driving_gear_x = ox - bevel_layout.mesh_distance
        lever_clearance = 2.0  # Clearance from lever pivot block
        lever_left_edge = ox - 6.0  # Lever pivot block extends from X=-6 to X=+6
        driving_axle_end = min(driving_gear_x + 8, lever_left_edge - lever_clearance)
        driving_axle_length = driving_axle_end - driving_axle_start

        driving_axle = (
            cq.Workplane('YZ')
            .center(driving_y, driving_z)
            .circle(shaft_diameter / 2)
            .extrude(driving_axle_length)
            .translate((driving_axle_start, 0, 0))
        )
        assy.add(
            driving_axle,
            name=f"{name_prefix}driving_bevel_axle" if name_prefix else "driving_bevel_axle",
            color=cq.Color("slategray"),
        )

        # Driven bevel axle: runs along Z at (X=0, Y=pivot_y)
        driven_x = wp['driven_axle_x']
        driven_y = wp['pivot_y']
        front_wall_z = wp['front_wall_z']
        back_wall_z = wp['back_wall_z']

        # Axle extends from front wall (minus overhang) to back wall (plus overhang)
        driven_axle_start = front_wall_z - wall_thickness / 2 - axle_overhang
        driven_axle_end = back_wall_z + wall_thickness / 2 + axle_overhang
        driven_axle_length = driven_axle_end - driven_axle_start

        driven_axle = (
            cq.Workplane('XY')
            .center(driven_x, driven_y)
            .circle(shaft_diameter / 2)
            .extrude(driven_axle_length)
            .translate((0, 0, driven_axle_start))
        )
        assy.add(
            driven_axle,
            name=f"{name_prefix}driven_bevel_axle" if name_prefix else "driven_bevel_axle",
            color=cq.Color("slategray"),
        )

    def _add_flexure(
        self,
        assy: cq.Assembly,
        spec: LogicElementSpec,
        origin: tuple[float, float, float],
        name_prefix: str,
    ) -> None:
        """Add serpentine flexure to the left wall.

        The flexure is mounted on the inside of the left wall (toward the mechanism),
        with its platform hole aligned with the driving bevel axle.
        """
        # Initialize flexure params if needed (requires spec)
        self._init_flexure(spec)

        ox, oy, oz = origin
        wp = self._wall_positions

        # Generate the flexure
        flexure = self._flexure_gen.generate()

        # Position the flexure:
        # - Flexure is generated in XY plane (X=width, Y=height, Z=thickness)
        # - Need to rotate so it's in YZ plane (aligned with left wall)
        # - Rotate 90° around Y axis: X→-Z, Y→Y, Z→X
        # - Then position on inside of left wall

        # Flexure center should align with axle position (pivot_y, driving_axle_z)
        left_wall_x = wp['left_wall_x']
        wall_thickness = wp['wall_thickness']
        flexure_thickness = self._flexure_params.thickness

        # Position: inside of left wall (in +X direction, toward mechanism)
        # After rotating 90° around Y, the flexure's original Z (thickness) becomes +X
        # So flexure spans X from flexure_x to flexure_x + flexure_thickness
        # Wall inner face is at left_wall_x + wall_thickness/2
        flexure_wall_gap = 0.5  # Small gap to prevent intersection
        flexure_x = left_wall_x + wall_thickness / 2 + flexure_wall_gap

        flexure_positioned = (
            flexure
            .rotate((0, 0, 0), (0, 1, 0), 90)  # Align with YZ plane
            .translate((flexure_x, wp['pivot_y'], wp['driving_axle_z']))
        )

        assy.add(
            flexure_positioned,
            name=f"{name_prefix}serpentine_flexure" if name_prefix else "serpentine_flexure",
            color=cq.Color(0.2, 0.6, 0.2),  # Green
        )

    def get_metadata(self, spec: LogicElementSpec) -> PartMetadata:
        """Get metadata for this assembly."""
        bevel_layout = LayoutCalculator.calculate_bevel_layout(spec)
        pivot_y = LayoutCalculator.calculate_pivot_y(spec)

        return PartMetadata(
            part_id="bevel_lever_with_upper_housing",
            part_type=PartType.BEVEL_DRIVE,
            name="Bevel Lever with Upper Housing",
            material="PLA",
            count=1,
            dimensions={
                "bevel_mesh_distance": bevel_layout.mesh_distance,
                "pivot_y": pivot_y,
                "cantilevered": 1.0 if self.cantilevered else 0.0,
            },
            notes="Assembly: bevel gear pair + shift lever + upper housing plates",
        )
