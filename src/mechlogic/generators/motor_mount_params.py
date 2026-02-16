"""Parameters for motor mounts and 130-size DC motors."""

from dataclasses import dataclass, field


@dataclass
class Motor130Params:
    """Parameters for a 130-size DC motor.

    Standard 130-size DC motor dimensions (approximate).
    The 130-size motor has a cylindrical body with two flat sides
    and two mounting tabs extending from those flat sides.
    """
    body_diameter: float = 20.0  # Motor can body diameter (across round parts)
    body_length: float = 25.0    # Motor can length (excluding shaft)
    shaft_diameter: float = 2.0  # Output shaft diameter
    shaft_length: float = 8.0    # Output shaft length

    # Motor can flat sides (for anti-rotation)
    flat_width: float = 15.0     # Width across the two flat sides
    flat_depth: float = 2.5      # How much material is removed at flats (radius - flat_width/2)

    # Mounting tabs (extend from flat sides)
    tab_width: float = 5.0       # Width of each mounting tab
    tab_length: float = 3.0      # How far tab extends from motor body
    tab_thickness: float = 0.8   # Thickness of the metal tab
    tab_hole_diameter: float = 2.0  # Hole in the tab for M2 screw
    tab_hole_offset: float = 1.5    # Distance from tab edge to hole center


@dataclass
class MotorMountParams:
    """Parameters for motor mount plates."""

    motor: Motor130Params = field(default_factory=Motor130Params)

    # Plate dimensions
    plate_thickness: float = 6.0  # Increased for deeper motor pocket

    # Clearances
    motor_body_clearance: float = 0.3   # Clearance around motor body
    shaft_clearance: float = 0.3        # Clearance for shaft hole
    tab_clearance: float = 0.2          # Clearance around mounting tabs

    # Mounting holes (for attaching to housing)
    mounting_hole_diameter: float = 3.2  # M3 clearance
    mounting_hole_inset: float = 6.0     # Distance from edge to hole center

    # Motor pocket depth (how deep motor body sits into plate for anti-rotation)
    motor_pocket_depth: float = 5.0     # Deep enough to engage flats

    # Tab retention
    tab_screw_diameter: float = 2.2     # M2 clearance hole through tabs
    include_tab_slots: bool = True      # Whether to include slots for motor tabs

    # Gap between motor mount and housing (for shaft coupling)
    housing_gap: float = 20.0  # Space for coupling + clearance

    # Self-supporting structure (L-bracket design)
    self_supporting: bool = True        # Whether to add base plate and gussets
    base_thickness: float = 6.0         # Thickness of horizontal base plate
    base_depth: float = 40.0            # How far base extends (X direction)
    gusset_thickness: float = 4.0       # Thickness of triangular gussets
    gusset_count: int = 2               # Number of gussets per mount
    foot_height: float = 5.0            # Height of feet/standoffs under base
    foot_diameter: float = 10.0         # Diameter of feet


@dataclass
class ShaftCouplingParams:
    """Parameters for motor-to-mechanism shaft coupling."""

    motor_shaft_diameter: float = 2.0   # Motor side bore
    mechanism_shaft_diameter: float = 6.0  # Mechanism side bore

    outer_diameter: float = 12.0  # Coupling outer diameter
    length: float = 15.0          # Total coupling length

    # Set screw parameters
    set_screw_diameter: float = 3.0  # M3 set screw
    set_screw_depth: float = 4.0     # How deep set screw hole goes

    # Internal bore dimensions
    motor_bore_length: float = 6.0     # Length of motor shaft bore
    mechanism_bore_length: float = 9.0  # Length of mechanism shaft bore
