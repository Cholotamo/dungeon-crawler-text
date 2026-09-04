"""World State Manager module.

Handles parsing, saving, rendering, and formatting world state snapshots
consisting of terrain_grid, region_grid, regions, landmarks, and roads.
"""

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


class WorldStateMutator:
    """Manages programmatic state mutations and provides tool functions for the Cartographer agent."""

    def __init__(self, state: dict[str, Any], snapshot_path: Optional[Path] = None) -> None:
        self.state = state
        self.snapshot_path = snapshot_path
        self.mutation_log: list[str] = []

        # Ensure essential structure exists
        if "terrain_grid" not in self.state or not isinstance(self.state["terrain_grid"], list):
            self.state["terrain_grid"] = ["." * 32 for _ in range(32)]
        if "region_grid" not in self.state or not isinstance(self.state["region_grid"], list):
            self.state["region_grid"] = ["0" * 32 for _ in range(32)]
        if "regions" not in self.state or not isinstance(self.state["regions"], dict):
            self.state["regions"] = {"0": {"name": "Wilderness", "type": "wilderness"}}
        if "landmarks" not in self.state or not isinstance(self.state["landmarks"], dict):
            self.state["landmarks"] = {}
        if "roads" not in self.state or not isinstance(self.state["roads"], dict):
            self.state["roads"] = {}

    def _sync_to_disk(self) -> None:
        """Flushes the current state to the snapshot file if snapshot_path is configured."""
        if self.snapshot_path:
            self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            self.snapshot_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def set_tiles(
        self,
        coords: list[list[int]],
        terrain_char: Optional[str] = None,
        region_id: Optional[str] = None,
    ) -> str:
        """Updates terrain character and/or regional biome ID at one or more [x, y] coordinates.

        Use this tool whenever natural ground is altered (e.g. deforestation, canals, blight,
        draining wetlands, or terraforming).

        Args:
            coords: List of coordinate pairs [x, y] to update (0 <= x < 32, 0 <= y < 32).
                    Can be a single pair like [[14, 22]] or a list of pairs like [[14, 22], [14, 23]].
            terrain_char: Optional single character representing natural ground
                          (e.g., '.' for plains, '#' for forest, '~' for water, '*' for wasteland, etc.).
            region_id: Optional single alphanumeric character ID corresponding to the region
                       in the regions dictionary (e.g., '0', '1', '2').
        """
        # Defensive check for single coordinate pair passed directly as [x, y]
        if isinstance(coords, list) and len(coords) == 2 and isinstance(coords[0], int) and isinstance(coords[1], int):
            coords = [coords]

        if not isinstance(coords, list):
            return "Error: coords must be a list of [x, y] coordinate pairs."

        updated_count = 0
        terrain_grid = self.state["terrain_grid"]
        region_grid = self.state["region_grid"]

        t_char = str(terrain_char)[0] if terrain_char else None
        r_id = str(region_id)[0] if region_id else None

        for pt in coords:
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                continue
            x, y = int(pt[0]), int(pt[1])
            if not (0 <= x < 32 and 0 <= y < 32):
                continue

            if t_char is not None:
                row = list(terrain_grid[y])
                if len(row) < 32:
                    row.extend(["."] * (32 - len(row)))
                row[x] = t_char
                terrain_grid[y] = "".join(row[:32])

            if r_id is not None:
                row = list(region_grid[y])
                if len(row) < 32:
                    row.extend(["0"] * (32 - len(row)))
                row[x] = r_id
                region_grid[y] = "".join(row[:32])

            updated_count += 1

        self._sync_to_disk()
        msg = f"Updated {updated_count} tile(s) (terrain='{t_char}', region_id='{r_id}')."
        self.mutation_log.append(msg)
        return msg

    def fill_area(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        terrain_char: Optional[str] = None,
        region_id: Optional[str] = None,
    ) -> str:
        """Fills a rectangular bounding box with terrain_char and/or region_id for large geographical changes.

        Args:
            x1: First corner column X (0-31).
            y1: First corner row Y (0-31).
            x2: Opposite corner column X (0-31).
            y2: Opposite corner row Y (0-31).
            terrain_char: Optional single character terrain symbol (e.g., '*', '.', '#').
            region_id: Optional single character region ID (e.g., '0', '5').
        """
        min_x = max(0, min(int(x1), int(x2)))
        max_x = min(31, max(int(x1), int(x2)))
        min_y = max(0, min(int(y1), int(y2)))
        max_y = min(31, max(int(y1), int(y2)))

        coords = [[x, y] for y in range(min_y, max_y + 1) for x in range(min_x, max_x + 1)]
        res = self.set_tiles(coords, terrain_char=terrain_char, region_id=region_id)
        msg = f"Filled box [{min_x}, {min_y}] to [{max_x}, {max_y}]: {res}"
        self.mutation_log.append(msg)
        return msg

    def upsert_landmark(
        self,
        landmark_id: str,
        name: str,
        char: str,
        type: str,
        pos: list[int],
    ) -> str:
        """Adds a new landmark or updates an existing one (founding, upgrading, ruining, or moving).

        Args:
            landmark_id: Unique identifier key in the landmarks dictionary (e.g., 'Highwatch', 'Oakhaven').
            name: Full display name (e.g., 'Highwatch Metropolis', 'Ruins of Highwatch').
            char: Map marker overlay ('o' for outpost, 'O' for major city, '!' for ruin/dungeon).
            type: Category type (e.g., 'major_city', 'outpost', 'dungeon', 'ruin', 'beast_den', 'stronghold').
            pos: [x, y] coordinates (column X, row Y, 0-31).
        """
        if not isinstance(pos, (list, tuple)) or len(pos) < 2:
            return "Error: pos must be [x, y] with 0 <= x < 32 and 0 <= y < 32."

        x, y = int(pos[0]), int(pos[1])
        if not (0 <= x < 32 and 0 <= y < 32):
            return f"Error: Coordinates [{x}, {y}] are out of map bounds (0-31)."

        clean_id = str(landmark_id).strip()
        marker = str(char).strip()[:1] or "o"

        self.state["landmarks"][clean_id] = {
            "name": str(name).strip(),
            "char": marker,
            "type": str(type).strip(),
            "pos": [x, y],
        }
        self._sync_to_disk()
        msg = f"Landmark '{clean_id}' set to '{name}' ['{marker}'] at [X: {x}, Y: {y}] ({type})."
        self.mutation_log.append(msg)
        return msg

    def remove_landmark(self, landmark_id: str) -> str:
        """Removes a landmark from the landmarks registry.

        Args:
            landmark_id: Key of the landmark to remove.
        """
        clean_id = str(landmark_id).strip()
        removed = self.state["landmarks"].pop(clean_id, None)
        self._sync_to_disk()
        if removed:
            msg = f"Landmark '{clean_id}' removed from landmarks registry."
        else:
            msg = f"Landmark '{clean_id}' not found in landmarks registry."
        self.mutation_log.append(msg)
        return msg

    def upsert_road(
        self,
        road_name: str,
        road_type: str,
        tiles: list[list[int]],
        extend: bool = False,
    ) -> str:
        """Adds, updates, or extends a road or bridge route in the roads registry.

        Args:
            road_name: Name of the route (e.g., "King's Highway", "Silver Bridge").
            road_type: Type of road ('paved', 'dirt', 'bridge').
            tiles: List of [x, y] coordinate pairs making up the route.
            extend: If True, appends new unique coordinates to existing tiles instead of replacing.
        """
        clean_name = str(road_name).strip()
        valid_tiles: list[list[int]] = []

        if isinstance(tiles, list):
            for pt in tiles:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    x, y = int(pt[0]), int(pt[1])
                    if 0 <= x < 32 and 0 <= y < 32:
                        valid_tiles.append([x, y])

        if extend and clean_name in self.state["roads"]:
            existing = self.state["roads"][clean_name].get("tiles", [])
            seen = {tuple(t) for t in existing}
            for t in valid_tiles:
                if tuple(t) not in seen:
                    existing.append(t)
                    seen.add(tuple(t))
            self.state["roads"][clean_name]["tiles"] = existing
            self.state["roads"][clean_name]["type"] = str(road_type)
            msg = f"Extended road '{clean_name}' to {len(existing)} tiles."
        else:
            self.state["roads"][clean_name] = {
                "type": str(road_type),
                "tiles": valid_tiles,
            }
            msg = f"Road '{clean_name}' set with {len(valid_tiles)} tiles ({road_type})."

        self._sync_to_disk()
        self.mutation_log.append(msg)
        return msg

    def decay_road(
        self,
        road_name: str,
        decay_percentage: float = 0.5,
    ) -> str:
        """Simulates road decay by removing a percentage of coordinates from an abandoned road.

        Args:
            road_name: Name of the road to decay.
            decay_percentage: Fraction of tiles to remove (between 0.1 and 0.9, default 0.5 for 50%).
        """
        clean_name = str(road_name).strip()
        if clean_name not in self.state["roads"]:
            return f"Road '{clean_name}' not found."

        tiles = self.state["roads"][clean_name].get("tiles", [])
        if not tiles:
            return f"Road '{clean_name}' has no tiles to decay."

        pct = max(0.1, min(0.9, float(decay_percentage)))
        remove_count = int(len(tiles) * pct)
        if remove_count == 0 and len(tiles) > 1:
            remove_count = 1

        step = max(2, int(round(1.0 / pct)))
        remaining = [t for i, t in enumerate(tiles) if (i % step) != 0]
        self.state["roads"][clean_name]["tiles"] = remaining
        self._sync_to_disk()
        msg = f"Road '{clean_name}' decayed by {int(pct * 100)}%: {len(tiles)} -> {len(remaining)} tiles remaining."
        self.mutation_log.append(msg)
        return msg

    def remove_road(self, road_name: str) -> str:
        """Removes a road entirely from the roads registry.

        Args:
            road_name: Name of the road to remove.
        """
        clean_name = str(road_name).strip()
        removed = self.state["roads"].pop(clean_name, None)
        self._sync_to_disk()
        if removed:
            msg = f"Road '{clean_name}' removed from roads registry."
        else:
            msg = f"Road '{clean_name}' not found in roads registry."
        self.mutation_log.append(msg)
        return msg

    def upsert_region(
        self,
        region_id: str,
        name: str,
        region_type: str,
    ) -> str:
        """Adds or updates a regional biome in the regions registry.

        Args:
            region_id: Single alphanumeric character key matching region_grid (e.g., '0', '1', 'a').
            name: Full name of the region (e.g., 'Whispering Woods', 'The Ashen Scars').
            region_type: Biome category (e.g., 'forest', 'wilderness', 'swamp', 'wasteland', 'mountain').
        """
        reg_key = str(region_id).strip()[:1]
        if not reg_key:
            return "Error: region_id must be a non-empty single character."

        self.state["regions"][reg_key] = {
            "name": str(name).strip(),
            "type": str(region_type).strip(),
        }
        self._sync_to_disk()
        msg = f"Region '{reg_key}' registered as '{name}' ({region_type})."
        self.mutation_log.append(msg)
        return msg

    def get_tools(self) -> list[Any]:
        """Returns the list of callable mutation tools for LLM function calling."""
        return [
            self.set_tiles,
            self.fill_area,
            self.upsert_landmark,
            self.remove_landmark,
            self.upsert_road,
            self.decay_road,
            self.remove_road,
            self.upsert_region,
        ]

