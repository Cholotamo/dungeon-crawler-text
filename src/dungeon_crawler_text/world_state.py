"""World state formatting and display utilities for LLM context."""

import json
from pathlib import Path
from typing import Any, Union

# Layering priority: lower draws first, higher overlays on top
FEATURE_PRIORITY: dict[str, int] = {
    "+": 10,  # Active Road / Trade Route
    "=": 20,  # Bridge / River Crossing
    "o": 30,  # Small Settlement / Outpost
    "O": 40,  # Major City / Metropolis
    "!": 50,  # Dungeon / Ruined City / Beast Den / Stronghold
}


def format_world_for_llm(world_data: Union[dict[str, Any], str, Path]) -> str:
    """Formats world map JSON into an optimal, coordinate-aligned format for LLM context.

    Draws the Composite Map (Terrain + Features) and Region Grid side-by-side.

    Args:
        world_data: World state dictionary, JSON string, or Path to world map JSON file.

    Returns:
        Formatted markdown string designed for LLM spatial reasoning and context injection.
    """
    if isinstance(world_data, Path):
        with open(world_data, "r", encoding="utf-8") as f:
            world_data = json.load(f)
    elif isinstance(world_data, str):
        path = Path(world_data)
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                world_data = json.load(f)
        else:
            world_data = json.loads(world_data)

    name = world_data.get("name", "Unknown Realm")
    terrain_grid = world_data.get("terrain_grid", [])
    region_grid = world_data.get("region_grid", [])
    regions = world_data.get("regions", {})
    features = world_data.get("features", {})

    height = len(terrain_grid)
    width = len(terrain_grid[0]) if height > 0 else 0

    # 1. Build Composite Map (Terrain + Overlaid Features)
    screen = [list(row) for row in terrain_grid]

    sorted_features = sorted(
        features.items(),
        key=lambda item: FEATURE_PRIORITY.get(item[1].get("char", ""), 25) if isinstance(item[1], dict) else 0,
    )

    for _, feat in sorted_features:
        if not isinstance(feat, dict):
            continue
        char = str(feat.get("char", "o"))[0]
        tiles = feat.get("tiles", [])
        if tiles and isinstance(tiles[0], int):
            tiles = [tiles]

        for pt in tiles:
            x, y = pt[0], pt[1]
            if 0 <= y < height and 0 <= x < width:
                screen[y][x] = char

    # 2. Render Composite and Region Grids Side-by-Side
    header_tens = "".join(f"{x // 10}" for x in range(width))
    header_ones = "".join(f"{x % 10}" for x in range(width))

    sep = "    |    "
    sep_pad = " " * len(sep)

    side_by_side = [
        f"    [--- COMPOSITE MAP (Terrain + Features) ---]{sep_pad}[--- REGION GRID (Biome IDs) ---]",
        f"    {header_tens}{sep_pad}    {header_tens}",
        f"    {header_ones}{sep_pad}    {header_ones}",
    ]
    for y in range(height):
        comp_row = "".join(screen[y]) if y < len(screen) else " " * width
        reg_row = region_grid[y] if y < len(region_grid) else " " * width
        side_by_side.append(f"{y:02d}: {comp_row}{sep}{y:02d}: {reg_row}")

    map_block = "\n".join(side_by_side)

    # 3. Features Registry
    feature_lines = []
    if not features:
        feature_lines.append("*(No features registered yet)*")
    else:
        for key, feat in sorted(features.items()):
            if not isinstance(feat, dict):
                continue
            fname = feat.get("name", key)
            fchar = feat.get("char", "?")
            ftype = feat.get("type", "feature")
            tiles = feat.get("tiles", [])
            if tiles and isinstance(tiles[0], int):
                tiles = [tiles]

            if len(tiles) == 1:
                x, y = tiles[0][0], tiles[0][1]
                t_char = terrain_grid[y][x] if 0 <= y < height and 0 <= x < width else "?"
                r_id = region_grid[y][x] if 0 <= y < len(region_grid) and 0 <= x < len(region_grid[y]) else "?"
                r_name = regions.get(r_id, {}).get("name", f"Region {r_id}")
                feature_lines.append(
                    f"- `[{key}]` **{fname}** ['{fchar}'] ({ftype})\n"
                    f"  - Position: [X: {x:02d}, Y: {y:02d}]\n"
                    f"  - Biome: Region '{r_id}' ({r_name}) | Natural Ground: '{t_char}'"
                )
            else:
                p_start = f"[X: {tiles[0][0]:02d}, Y: {tiles[0][1]:02d}]" if tiles else "[?]"
                p_end = f"[X: {tiles[-1][0]:02d}, Y: {tiles[-1][1]:02d}]" if tiles else "[?]"
                feature_lines.append(
                    f"- `[{key}]` **{fname}** ['{fchar}'] ({ftype}, {len(tiles)} tiles)\n"
                    f"  - Span: {p_start} <---> {p_end}\n"
                    f"  - Coordinates: {tiles}"
                )

    # 4. Regions Registry
    region_lines = [
        f"- ID '{r_id}': **{r_info.get('name', 'Unnamed')}** ({r_info.get('type', 'wilderness')})"
        for r_id, r_info in sorted(regions.items())
        if isinstance(r_info, dict)
    ]

    return (
        f"# World State: {name}\n"
        f"- Dimensions: {width}x{height} (X: 00..{width-1:02d}, Y: 00..{height-1:02d})\n"
        f"- Registered Features: {len(features)}\n\n"
        f"### Map Inspection (Side-by-Side)\n"
        f"```text\n{map_block}\n```\n\n"
        f"### Feature Legend\n"
        f"- `+` : Road / Route  |  `=` : Bridge  |  `o` : Outpost/Settlement  |  `O` : Major City  |  `!` : Dungeon/Stronghold\n\n"
        f"### Features Registry\n"
        f"{chr(10).join(feature_lines)}\n\n"
        f"### Regional Biomes\n"
        f"{chr(10).join(region_lines)}"
    )
