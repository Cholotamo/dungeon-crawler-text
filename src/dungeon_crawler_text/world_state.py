"""World State Manager module.

Handles parsing, saving, rendering, and formatting world state snapshots
consisting of terrain_grid, region_grid, regions, landmarks, and roads.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Optional

SNAPSHOT_START_DELIMITER = "___WORLD_STATE_SNAPSHOT_START___"
SNAPSHOT_END_DELIMITER = "___WORLD_STATE_SNAPSHOT_END___"


def extract_snapshot_from_text(text: str) -> Optional[dict[str, Any]]:
    """Extracts and parses a JSON world state snapshot from text.

    Looks first for the designated delimiters ___WORLD_STATE_SNAPSHOT_START___
    and ___WORLD_STATE_SNAPSHOT_END___. If not found, attempts to locate
    a JSON object containing 'terrain_grid' and 'region_grid'.
    """
    if not text:
        return None

    # 1. Search using explicit delimiters
    if SNAPSHOT_START_DELIMITER in text and SNAPSHOT_END_DELIMITER in text:
        start_idx = text.index(SNAPSHOT_START_DELIMITER) + len(SNAPSHOT_START_DELIMITER)
        end_idx = text.index(SNAPSHOT_END_DELIMITER, start_idx)
        raw_json = text[start_idx:end_idx].strip()
        # Clean markdown code blocks if present inside delimiters
        if raw_json.startswith("```"):
            raw_json = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", raw_json)
            raw_json = re.sub(r"\n```$", "", raw_json).strip()
        try:
            data = json.loads(raw_json)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 2. Fallback: Search for JSON blocks containing key schema fields
    json_block_matches = re.findall(r"\{[\s\S]*\}", text)
    for match in reversed(json_block_matches):
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "terrain_grid" in data and "region_grid" in data:
                return data
        except json.JSONDecodeError:
            continue

    return None


def extract_cartographic_log(text: str) -> str:
    """Extracts narrative text and cartographic log outside the snapshot delimiters."""
    if not text:
        return ""

    cleaned = text
    # Remove snapshot blocks wrapped in delimiters
    if SNAPSHOT_START_DELIMITER in cleaned and SNAPSHOT_END_DELIMITER in cleaned:
        pattern = re.escape(SNAPSHOT_START_DELIMITER) + r"[\s\S]*?" + re.escape(SNAPSHOT_END_DELIMITER)
        cleaned = re.sub(pattern, "", cleaned)

    # Remove any markdown code blocks (python, json, or generic)
    cleaned = re.sub(r"```[a-zA-Z0-9_-]*[\s\S]*?```", "", cleaned)

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines)


def render_composite_map(state: dict[str, Any]) -> str:
    """Renders the composite ASCII map from the state snapshot.

    Layer order:
    1. Base terrain_grid
    2. Roads ('=' for bridges, '+' for normal road tiles)
    3. Landmarks ('O', 'o', '!', etc.)
    """
    terrain_grid = state.get("terrain_grid", [])
    if not terrain_grid:
        return "Empty map"

    # Base terrain layer
    screen = [list(row) for row in terrain_grid]
    height = len(screen)
    width = len(screen[0]) if height > 0 else 0

    # Overlay roads
    roads = state.get("roads", {})
    if isinstance(roads, dict):
        for road in roads.values():
            if not isinstance(road, dict):
                continue
            road_type = road.get("type", "paved")
            tiles = road.get("tiles", [])
            for pt in tiles:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    x, y = pt[0], pt[1]
                    if 0 <= y < height and 0 <= x < width:
                        is_water = screen[y][x] == "~"
                        screen[y][x] = "=" if (is_water or road_type == "bridge") else "+"

    # Overlay landmarks
    landmarks = state.get("landmarks", {})
    if isinstance(landmarks, dict):
        for landmark in landmarks.values():
            if not isinstance(landmark, dict):
                continue
            pos = landmark.get("pos")
            char = landmark.get("char", "o")
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                x, y = pos[0], pos[1]
                if 0 <= y < height and 0 <= x < width:
                    screen[y][x] = char

    # Format with stacked column headers and row numbers
    header_tens = "   " + " ".join(f"{x // 10}" for x in range(width))
    header_ones = "   " + " ".join(f"{x % 10}" for x in range(width))
    rendered_rows = [header_tens, header_ones]

    for y, row in enumerate(screen):
        rendered_rows.append(f"{y:02d} " + " ".join(row))

    return "\n".join(rendered_rows)


def format_side_by_side(terrain_grid: list[str], region_grid: list[str]) -> str:
    """Formats terrain_grid and region_grid side-by-side with coordinate rulers."""
    if not terrain_grid or not region_grid:
        return ""

    width = len(terrain_grid[0]) if terrain_grid else 32
    header_tens = "".join(f"{x // 10}" for x in range(width))
    header_ones = "".join(f"{x % 10}" for x in range(width))

    title_line = "    [--- TERRAIN_GRID (Natural) ---]            [--- REGION_GRID (Biome IDs) ---]"
    tens_line = f"    {header_tens}            {header_tens}"
    ones_line = f"    {header_ones}            {header_ones}"

    rows = [title_line, tens_line, ones_line]

    max_y = max(len(terrain_grid), len(region_grid))
    for y in range(max_y):
        t_row = terrain_grid[y] if y < len(terrain_grid) else " " * width
        r_row = region_grid[y] if y < len(region_grid) else " " * width
        rows.append(f"{y:02d}: {t_row}    |    {y:02d}: {r_row}")

    return "\n".join(rows)


def format_snapshot_injection(state: dict[str, Any]) -> str:
    """Builds the textual injection of world state for Historian and Cartographer.

    Includes:
    1. Side-by-side matrices (terrain_grid and region_grid)
    2. Regions dictionary
    3. Landmarks dictionary
    4. Roads dictionary
    """
    terrain_grid = state.get("terrain_grid", [])
    region_grid = state.get("region_grid", [])
    side_by_side = format_side_by_side(terrain_grid, region_grid)

    lines = [
        "### Dual-Grid Inspection Matrices",
        side_by_side,
        "",
        "### Regions Registry (Biome IDs in region_grid):",
    ]

    regions = state.get("regions", {})
    if isinstance(regions, dict) and regions:
        for reg_id, reg_data in sorted(regions.items()):
            name = reg_data.get("name", "Unnamed") if isinstance(reg_data, dict) else str(reg_data)
            reg_type = reg_data.get("type", "unknown") if isinstance(reg_data, dict) else ""
            lines.append(f"- ID '{reg_id}': **{name}** ({reg_type})")
    else:
        lines.append("(No regional biomes registered yet)")

    lines.append("")
    lines.append("### Established Landmarks:")
    landmarks = state.get("landmarks", {})
    if isinstance(landmarks, dict) and landmarks:
        for key, lm in landmarks.items():
            if not isinstance(lm, dict):
                continue
            name = lm.get("name", key)
            char = lm.get("char", "o")
            lm_type = lm.get("type", "site")
            pos = lm.get("pos", ["?", "?"])
            lines.append(f"- **{name}** ['{char}'] at [X: {pos[0]}, Y: {pos[1]}] ({lm_type})")
    else:
        lines.append("(No landmarks founded yet)")

    lines.append("")
    lines.append("### Established Roads & Crossings:")
    roads = state.get("roads", {})
    if isinstance(roads, dict) and roads:
        for road_name, road_info in roads.items():
            if not isinstance(road_info, dict):
                continue
            road_type = road_info.get("type", "paved")
            tiles = road_info.get("tiles", [])
            lines.append(f"- **{road_name}** ({road_type}, {len(tiles)} tiles)")
    else:
        lines.append("(No roads built yet)")

    return "\n".join(lines)


def save_snapshot_file(state: dict[str, Any], output_dir: Path, epoch: int) -> Path:
    """Saves the state snapshot as JSON in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"world_state_epoch_{epoch:02d}.json"
    filepath = output_dir / filename
    filepath.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # Also update latest_snapshot.json
    latest_path = output_dir / "latest_snapshot.json"
    latest_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return filepath
