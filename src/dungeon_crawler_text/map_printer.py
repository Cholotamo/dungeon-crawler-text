"""CLI Composite Map Printer for Dungeon Crawler Text.

Renders world maps and 16x16 localemaps directly to the terminal with
clean character spacing, coordinate rulers, ANSI color highlights, and legends.
"""

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Optional, Union

# Enable VT100 / ANSI escape processing on Windows console
if sys.platform == "win32":
    try:
        os.system("")
    except Exception:
        pass

# Layering priority: lower draws first, higher overlays on top
FEATURE_PRIORITY: dict[str, int] = {
    "~": 5,   # Canal / Water Channel
    "+": 10,  # Active Road / Trade Route
    "=": 20,  # Bridge / River Crossing
    "*": 25,  # Masonry Dam / Civil Barrier
    "o": 30,  # Civilized Outpost / Village / Fort
    "O": 40,  # Civilized City / Metropolis / Citadel
    "!": 50,  # Hostile Lair / Dungeon / Ruin
}

TERRAIN_DESCRIPTIONS: dict[str, str] = {
    ".": "Open Plains / Grassland",
    ",": "Hills / Rolling Slopes",
    "#": "Forest / Woods",
    "&": "Dense Forest / Deep Jungle",
    "%": "Swamp / Bog / Wetland",
    "~": "Water / River / Ocean",
    ";": "Coast / Beach / Shallows",
    "^": "Mountain Peak / Ridge",
    "/": "Cliffs / Edges / Chasms",
    "*": "Wastelands / Ash / Barrier",
    ":": "Farmland / Cultivated Polders",
}

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "O": "Major City / Metropolis / Citadel",
    "o": "Settlement / Village / Outpost / Fort",
    "!": "Hostile Lair / Ruin / Perilous Den",
    "+": "Road / Trade Highway",
    "=": "Bridge / River Crossing",
    "*": "Masonry Dam / Civil Impoundment",
    "~": "Excavated Canal / Irrigation Channel",
}

# ANSI Color codes
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"

# Terrain color palette
COLOR_TERRAIN: dict[str, str] = {
    "~": "\033[36m",         # Cyan (Water)
    ";": "\033[33;1m",       # Bold Yellow / Sand (Coast)
    ".": "\033[32m",         # Green (Plains)
    ",": "\033[33m",         # Yellow/Brown (Hills)
    "#": "\033[32;1m",       # Bold Green (Forest)
    "&": "\033[32m",         # Dark Green (Dense Forest)
    "%": "\033[35m",         # Magenta (Swamp)
    "^": "\033[37;1m",       # Bold White (Mountains)
    "/": "\033[90;1m",       # Bright Black / Gray (Cliffs)
    "*": "\033[31m",         # Red (Wasteland)
    ":": "\033[93m",         # Bright Yellow (Farmland)
}

# Feature color palette (bold / high visibility)
COLOR_FEATURES: dict[str, str] = {
    "O": "\033[93;1m",       # Bold Bright Yellow (City)
    "o": "\033[33;1m",       # Bold Yellow (Village/Outpost)
    "!": "\033[91;1m",       # Bold Bright Red (Dungeon)
    "+": "\033[97;1m",       # Bold Bright White (Road)
    "=": "\033[96;1m",       # Bold Bright Cyan (Bridge)
    "*": "\033[95;1m",       # Bold Bright Magenta (Dam)
    "~": "\033[94;1m",       # Bold Bright Blue (Canal)
}


def colorize_char(char: str, is_feature: bool = False, use_color: bool = True) -> str:
    """Wraps a character with ANSI colors if color output is enabled."""
    if not use_color:
        return char
    if is_feature:
        color = COLOR_FEATURES.get(char, "\033[97;1m")
        return f"{color}{char}{ANSI_RESET}"
    color = COLOR_TERRAIN.get(char, "")
    if color:
        return f"{color}{char}{ANSI_RESET}"
    return char


def load_map_data(source: Union[dict[str, Any], str, Path]) -> tuple[dict[str, Any], Path | None]:
    """Loads map data from a dictionary, JSON file, or Path."""
    if isinstance(source, dict):
        return source, None

    file_path = Path(source)
    if not file_path.exists():
        raise FileNotFoundError(f"Map file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {file_path}, got {type(data).__name__}")

    return data, file_path


def build_composite_cells(map_data: dict[str, Any]) -> tuple[list[list[tuple[str, bool]]], int, int]:
    """Overlays features onto terrain_grid, returning a grid of (char, is_feature) tuples."""
    terrain_grid = map_data.get("terrain_grid", [])
    height = len(terrain_grid)
    width = len(terrain_grid[0]) if height > 0 else 0

    # Initialize cells: (char, is_feature)
    cells: list[list[tuple[str, bool]]] = [
        [(char, False) for char in row] for row in terrain_grid
    ]

    features = map_data.get("features", {})
    if isinstance(features, dict):
        sorted_features = sorted(
            features.items(),
            key=lambda item: FEATURE_PRIORITY.get(
                item[1].get("char", ""), 25
            ) if isinstance(item[1], dict) else 0,
        )

        for _, feat in sorted_features:
            if not isinstance(feat, dict):
                continue
            char = str(feat.get("char", "o"))[0]
            tiles = feat.get("tiles", [])
            if not tiles and "pos" in feat:
                tiles = [feat["pos"]]
            elif tiles and isinstance(tiles[0], int):
                tiles = [tiles]

            for pt in tiles:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    x, y = pt[0], pt[1]
                    if 0 <= y < height and 0 <= x < width:
                        cells[y][x] = (char, True)

    return cells, width, height


def render_map_grid(
    cells: list[list[tuple[str, bool]]],
    width: int,
    height: int,
    spaced: bool = True,
    use_color: bool = True,
) -> list[str]:
    """Renders coordinate-aligned ASCII grid with rulers, borders, and optional spacing."""
    lines: list[str] = []

    if spaced:
        # Spaced out mode: 1 space between each cell column
        header_tens = "     " + " ".join(str(x // 10) for x in range(width))
        header_ones = "     " + " ".join(str(x % 10) for x in range(width))
        border = "   +-" + "-" * (width * 2 - 1) + "-+"

        if width >= 10:
            lines.append(header_tens)
        lines.append(header_ones)
        lines.append(border)

        for y in range(height):
            row_cells = cells[y] if y < len(cells) else [(" ", False)] * width
            colored_chars = [
                colorize_char(ch, is_feat, use_color) for ch, is_feat in row_cells
            ]
            row_content = " ".join(colored_chars)
            lines.append(f"{y:02d} | {row_content} | {y:02d}")

        lines.append(border)
        lines.append(header_ones)
        if width >= 10:
            lines.append(header_tens)

    else:
        # Compact mode: 1 character per tile
        header_tens = "    " + "".join(str(x // 10) for x in range(width))
        header_ones = "    " + "".join(str(x % 10) for x in range(width))
        border = "   +" + "-" * width + "+"

        if width >= 10:
            lines.append(header_tens)
        lines.append(header_ones)
        lines.append(border)

        for y in range(height):
            row_cells = cells[y] if y < len(cells) else [(" ", False)] * width
            row_content = "".join(
                colorize_char(ch, is_feat, use_color) for ch, is_feat in row_cells
            )
            lines.append(f"{y:02d} |{row_content}| {y:02d}")

        lines.append(border)
        lines.append(header_ones)
        if width >= 10:
            lines.append(header_tens)

    return lines


def render_region_grid(
    region_grid: list[str],
    width: int,
    height: int,
    spaced: bool = True,
    use_color: bool = True,
) -> list[str]:
    """Renders region/district grid with coordinate rulers."""
    cells = [[(ch, False) for ch in row] for row in region_grid]
    return render_map_grid(cells, width, height, spaced=spaced, use_color=False)


def render_side_by_side(
    comp_cells: list[list[tuple[str, bool]]],
    reg_grid: list[str],
    width: int,
    height: int,
    spaced: bool = False,
    use_color: bool = True,
) -> list[str]:
    """Renders composite map and region grid side-by-side."""
    comp_lines = render_map_grid(comp_cells, width, height, spaced=spaced, use_color=use_color)
    reg_cells = [[(ch, False) for ch in row] for row in reg_grid]
    reg_lines = render_map_grid(reg_cells, width, height, spaced=spaced, use_color=False)

    sep = "    |    "
    sep_pad = " " * len(sep)

    header_left = "    [--- COMPOSITE MAP (Terrain + Features) ---]"
    header_right = "[--- REGION GRID (Biome IDs) ---]"
    title_line = f"{header_left}{sep_pad}{header_right}"

    combined: list[str] = [title_line]
    max_rows = max(len(comp_lines), len(reg_lines))
    for i in range(max_rows):
        left = comp_lines[i] if i < len(comp_lines) else ""
        right = reg_lines[i] if i < len(reg_lines) else ""
        combined.append(f"{left}{sep}{right}")

    return combined


def print_composite_map(
    source: Union[dict[str, Any], str, Path] = Path("artifacts/worldmap.json"),
    spaced: bool = True,
    map_only: bool = False,
    show_regions: bool = False,
    side_by_side: bool = False,
    show_legend: bool = True,
    use_color: Optional[bool] = None,
) -> None:
    """Prints formatted composite map to standard output."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Determine color support
    if use_color is None:
        no_color_env = os.environ.get("NO_COLOR") is not None
        use_color = sys.stdout.isatty() and not no_color_env

    map_data, file_path = load_map_data(source)
    name = map_data.get("name", "Unknown Realm")
    epoch = map_data.get("epoch")
    kf_idx = map_data.get("keyframe_index")
    features = map_data.get("features", {})
    regions = map_data.get("regions", {})
    districts = map_data.get("districts", {})
    region_grid = map_data.get("region_grid") or map_data.get("district_grid") or []

    cells, width, height = build_composite_cells(map_data)

    # Title Banner
    if not map_only:
        epoch_str = f"Epoch {epoch}" if epoch is not None else "Primordial Era"
        if kf_idx is not None:
            epoch_str += f" | Keyframe {kf_idx}"
        file_str = f" ({file_path})" if file_path else ""

        term_width = min(os.get_terminal_size().columns if sys.stdout.isatty() else 80, 80)
        banner_len = max(term_width, (width * 2 + 10) if spaced else (width + 10))

        print("=" * banner_len)
        print(f" REALM: {name} [{epoch_str}] ({width}x{height}){file_str}")
        print("=" * banner_len)
        print(f"\n[COMPOSITE MAP: TERRAIN + FEATURES]")

    # Grid Display
    if side_by_side and region_grid:
        lines = render_side_by_side(
            cells, region_grid, width, height, spaced=spaced, use_color=use_color
        )
        print("\n".join(lines))
    else:
        lines = render_map_grid(cells, width, height, spaced=spaced, use_color=use_color)
        print("\n".join(lines))

        if show_regions and region_grid:
            grid_name = "DISTRICT GRID" if districts else "REGION GRID (Biome IDs)"
            print(f"\n[{grid_name}]")
            reg_lines = render_region_grid(
                region_grid, width, height, spaced=spaced, use_color=use_color
            )
            print("\n".join(reg_lines))

    if map_only:
        return

    # Terrain & Feature Legend
    if show_legend:
        # Collect present terrain glyphs
        present_chars = {ch for row in cells for ch, _ in row}
        present_features = {ch for row in cells for ch, is_feat in row if is_feat}

        print("\n" + "-" * 40)
        print(" GLYPH LEGEND")
        print("-" * 40)

        # Features present
        if present_features:
            print("Features:")
            for ch in sorted(present_features):
                desc = FEATURE_DESCRIPTIONS.get(ch, "Constructed Landmark / Feature")
                colored_ch = colorize_char(ch, is_feature=True, use_color=use_color)
                print(f"  [{colored_ch}]  {desc}")

        # Terrain present
        terrain_present = present_chars - present_features
        if terrain_present:
            print("Natural Terrain:")
            for ch in sorted(terrain_present):
                desc = TERRAIN_DESCRIPTIONS.get(ch, "Natural Terrain")
                colored_ch = colorize_char(ch, is_feature=False, use_color=use_color)
                print(f"  [{colored_ch}]  {desc}")

    # Features Registry
    if features:
        print("\n" + "-" * 40)
        print(f" REGISTERED FEATURES ({len(features)})")
        print("-" * 40)
        for fid, feat in sorted(features.items()):
            if not isinstance(feat, dict):
                continue
            fname = feat.get("name", fid)
            fchar = str(feat.get("char", "?"))[0]
            ftype = feat.get("type", "feature")
            tiles = feat.get("tiles", [])
            if not tiles and "pos" in feat:
                tiles = [feat["pos"]]
            elif tiles and isinstance(tiles[0], int):
                tiles = [tiles]

            colored_ch = colorize_char(fchar, is_feature=True, use_color=use_color)
            desc = feat.get("lore", "") or feat.get("description", "")
            desc_str = f" - \"{desc}\"" if desc else ""

            if len(tiles) == 1:
                pt = tiles[0]
                print(f"  [{colored_ch}] {fname} ({ftype}) at [X: {pt[0]:02d}, Y: {pt[1]:02d}]{desc_str}")
            elif len(tiles) > 1:
                p_start = f"[{tiles[0][0]:02d}, {tiles[0][1]:02d}]"
                p_end = f"[{tiles[-1][0]:02d}, {tiles[-1][1]:02d}]"
                print(f"  [{colored_ch}] {fname} ({ftype}, {len(tiles)} tiles) Span: {p_start} -> {p_end}{desc_str}")
            else:
                print(f"  [{colored_ch}] {fname} ({ftype}){desc_str}")

    # Regional Biomes or Districts Registry
    active_regions = regions or districts
    if active_regions:
        reg_title = "DISTRICT ZONING" if districts else "REGIONAL BIOMES"
        print("\n" + "-" * 40)
        print(f" {reg_title} ({len(active_regions)})")
        print("-" * 40)
        for rid, rdata in sorted(active_regions.items()):
            if not isinstance(rdata, dict):
                continue
            rname = rdata.get("name", f"Region {rid}")
            rtype = rdata.get("type", "wilderness")
            rlore = rdata.get("lore", "") or rdata.get("description", "")
            lore_snippet = f": \"{rlore[:70]}...\"" if len(rlore) > 70 else (f": \"{rlore}\"" if rlore else "")
            print(f"  [{rid}] {rname} ({rtype}){lore_snippet}")

    print("\n" + "=" * 80)


def main() -> None:
    """CLI entry point for dungeon-crawler-map."""
    default_worldmap = Path("artifacts/worldmap.json")

    parser = argparse.ArgumentParser(
        prog="dungeon-crawler-map",
        description="Prints the Dungeon Crawler Text composite map to the CLI, spaced out and formatted.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(default_worldmap),
        help=f"Path to world map or locale map JSON file (default: {default_worldmap})",
    )
    parser.add_argument(
        "--compact",
        "-c",
        action="store_true",
        help="Print in compact 1-char-per-tile mode (omits horizontal spacing between columns)",
    )
    parser.add_argument(
        "--regions",
        "-r",
        action="store_true",
        help="Also print the Region Grid (or District Grid)",
    )
    parser.add_argument(
        "--side-by-side",
        "-s",
        action="store_true",
        help="Display composite map and region grid side-by-side",
    )
    parser.add_argument(
        "--map-only",
        "-m",
        action="store_true",
        help="Print only the map grid with rulers (suppress title, legend, and registries)",
    )
    parser.add_argument(
        "--no-legend",
        action="store_true",
        help="Suppress the terrain and feature glyph legend",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color highlights",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="Force ANSI color highlights even when output is piped or redirected",
    )

    args = parser.parse_args()

    # Determine color preference
    use_color = None
    if args.no_color:
        use_color = False
    elif args.color:
        use_color = True

    input_path = Path(args.input)
    if not input_path.exists():
        # Helpful fallback search in artifacts/
        artifacts_match = sorted(Path("artifacts").glob(f"*{args.input}*")) if Path("artifacts").exists() else []
        if artifacts_match:
            input_path = artifacts_match[0]
            print(f"[NOTE] Using matched artifact: {input_path}\n", file=sys.stderr)
        else:
            print(f"[ERROR] Map file not found at: {args.input}", file=sys.stderr)
            sys.exit(1)

    try:
        print_composite_map(
            source=input_path,
            spaced=not args.compact,
            map_only=args.map_only,
            show_regions=args.regions,
            side_by_side=args.side_by_side,
            show_legend=not args.no_legend,
            use_color=use_color,
        )
    except Exception as e:
        print(f"[ERROR] Failed to print composite map: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
