"""Simple linkage bar with rounded ends and axle holes."""

import cadquery as cq


def generate_linkage_bar(
    length: float = 100.0,
    width: float = 10.0,
    thickness: float = 3.0,
    hole_diameter: float = 2.6,
) -> cq.Workplane:
    """Generate a rectangular bar with rounded ends and axle holes.

    Args:
        length: Total length (center-to-center of holes + width for rounded ends)
        width: Width of the bar
        thickness: Thickness of the bar
        hole_diameter: Diameter of the axle holes at each end

    Returns:
        CadQuery Workplane with the linkage bar.
    """
    # Stadium shape: rectangle with semicircle ends
    # Hole centers at each end, inset by width/2 (at semicircle centers)
    half_len = length / 2
    half_w = width / 2
    hole_x = half_len - half_w  # Hole at center of each rounded end

    bar = (
        cq.Workplane('XY')
        .slot2D(length, width)
        .extrude(thickness)
    )

    # Cut axle holes at each end
    for x_sign in [-1, 1]:
        hole = (
            cq.Workplane('XY')
            .center(x_sign * hole_x, 0)
            .circle(hole_diameter / 2)
            .extrude(thickness + 1)
            .translate((0, 0, -0.5))
        )
        bar = bar.cut(hole)

    return bar


def main():
    bar = generate_linkage_bar(
        length=100.0,
        width=10.0,
        thickness=3.0,
        hole_diameter=2.6,
    )

    print("Linkage Bar:")
    print("  Length: 100.0 mm")
    print("  Width: 10.0 mm")
    print("  Thickness: 3.0 mm")
    print("  Hole diameter: 2.6 mm")

    cq.exporters.export(bar, "linkage_bar.step")
    print("\nExported: linkage_bar.step")


if __name__ == "__main__":
    main()
