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
        has_roads = False
        for road_name, road_info in roads.items():
            if not isinstance(road_info, dict):
                continue
            tiles = road_info.get("tiles", [])
            if not tiles:
                continue
            has_roads = True
            road_type = road_info.get("type", "paved")
            lines.append(f"- **{road_name}** ({road_type}, {len(tiles)} tiles)")
        if not has_roads:
            lines.append("(No roads built yet)")
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


def get_world_chronicle_path(artifacts_dir: Path) -> Path:
    """Returns the path to artifacts/world_state.md."""
    return artifacts_dir / "world_state.md"


def read_world_chronicle(artifacts_dir: Path) -> Optional[str]:
    """Reads existing world history markdown (world_state.md) if it exists."""
    path = get_world_chronicle_path(artifacts_dir)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def _format_world_metadata_fields(world_state: dict[str, Any], epoch: int) -> dict[str, str]:
    """Extracts summary strings for regions, landmarks, and roads from world_state."""
    # Regions
    regions = world_state.get("regions", {})
    if isinstance(regions, dict) and regions:
        reg_items = []
        for reg_id, rdata in sorted(regions.items()):
            if isinstance(rdata, dict):
                r_name = rdata.get("name", f"Region {reg_id}")
                r_type = rdata.get("type", "")
                reg_items.append(f"{r_name} ({r_type.title()})" if r_type else r_name)
            elif isinstance(rdata, str):
                reg_items.append(rdata)
        regions_str = ", ".join(reg_items)
    else:
        regions_str = "Wilderness"

    # Landmarks
    landmarks = world_state.get("landmarks", {})
    if isinstance(landmarks, dict) and landmarks:
        lm_items = []
        for lm_key, lm_data in sorted(landmarks.items()):
            if isinstance(lm_data, dict):
                l_name = lm_data.get("name", lm_key)
                l_char = lm_data.get("char", "o")
                lm_items.append(f"{l_name} (`{l_char}`)")
            else:
                lm_items.append(str(lm_key))
        landmarks_str = ", ".join(lm_items)
    else:
        landmarks_str = "None (Primordial wilderness)" if epoch == 1 else "None recorded"

    # Roads
    roads = world_state.get("roads", {})
    if isinstance(roads, dict) and roads:
        road_items = []
        for r_name, r_data in sorted(roads.items()):
            if isinstance(r_data, dict):
                tiles = r_data.get("tiles", [])
                if not tiles:
                    continue
                r_type = r_data.get("type", "paved").capitalize()
                road_items.append(f"{r_name} ({r_type})")
            else:
                road_items.append(str(r_name))
        roads_str = ", ".join(road_items) if road_items else "None recorded"
    else:
        roads_str = "None recorded"

    return {
        "regions": regions_str,
        "landmarks": landmarks_str,
        "roads": roads_str,
    }


def build_world_header(world_state: dict[str, Any], epoch: int) -> str:
    """Constructs the markdown header for world_state.md."""
    name = world_state.get("name", "The Known World")
    meta = _format_world_metadata_fields(world_state, epoch)

    epoch_str = f"Epoch {epoch}"
    chronology = world_state.get("chronology")
    if isinstance(chronology, dict) and chronology.get("reckoning"):
        epoch_str = f"Epoch {epoch} ({chronology['reckoning']})"

    return (
        f"# World: {name}\n"
        f"- **Current Epoch:** {epoch_str}\n"
        f"- **Dominant Biomes & Regions:** {meta['regions']}\n"
        f"- **Active Settlements & Landmarks:** {meta['landmarks']}\n"
        f"- **Active Roads & Crossings:** {meta['roads']}\n\n"
        f"---\n\n"
    )


def format_world_chronicle_chunk(narrative: str, epoch: int) -> str:
    """Formats the historian's narrative into an epoch chronicle block.

    Ensures a standardized '## Epoch {epoch}' markdown header is present at the start.
    """
    text = (narrative or "").strip()
    if not text:
        return f"## Epoch {epoch}\n\n*(No chronicle recorded for this epoch.)*"

    first_line = text.splitlines()[0].strip()
    rest_lines = text.splitlines()[1:]
    rest_text = "\n".join(rest_lines).strip()

    # Case 1: Already starts with '## Epoch X' or '# Epoch X'
    epoch_header_match = re.match(r"^#+\s*(Epoch\s*" + str(epoch) + r"\b.*)", first_line, re.IGNORECASE)
    if epoch_header_match:
        title_part = epoch_header_match.group(1).strip()
        if rest_text:
            return f"## {title_part}\n\n{rest_text}"
        return f"## {title_part}"

    # Case 2: Starts with a markdown header like '# Title' or '## Title'
    header_match = re.match(r"^#+\s*(.+)$", first_line)
    if header_match:
        title = header_match.group(1).strip()
        # Strip redundant leading 'Epoch X: ' or 'Epoch X - '
        title = re.sub(r"^Epoch\s*\d+\s*[:—–-]?\s*", "", title, flags=re.IGNORECASE).strip()
        header_line = f"## Epoch {epoch} — {title}" if title else f"## Epoch {epoch}"
        if rest_text:
            return f"{header_line}\n\n{rest_text}"
        return header_line

    # Case 3: Raw narrative without leading markdown heading
    default_title = "Primordial Geography" if epoch == 1 else ""
    header_line = f"## Epoch {epoch} — {default_title}" if default_title else f"## Epoch {epoch}"
    return f"{header_line}\n\n{text}"


def save_world_chronicle(
    artifacts_dir: Path,
    world_state: dict[str, Any],
    narrative: str,
    epoch: int,
) -> Path:
    """Writes or appends to artifacts/world_state.md with updated world-level header."""
    file_path = get_world_chronicle_path(artifacts_dir)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    name = world_state.get("name", "The Known World")
    chronicle_chunk = format_world_chronicle_chunk(narrative, epoch)
    meta = _format_world_metadata_fields(world_state, epoch)

    if not file_path.exists() or epoch == 1:
        header = build_world_header(world_state, epoch)
        full_content = header + chronicle_chunk.strip() + "\n"
        file_path.write_text(full_content, encoding="utf-8")
    else:
        existing_text = file_path.read_text(encoding="utf-8")

        # Update World Title line if present
        if "# World:" in existing_text:
            existing_text = re.sub(
                r"# World:.*",
                lambda _: f"# World: {name}",
                existing_text,
                count=1,
            )
        # Update Current Epoch line if present
        epoch_str = f"Epoch {epoch}"
        chronology = world_state.get("chronology")
        if isinstance(chronology, dict) and chronology.get("reckoning"):
            epoch_str = f"Epoch {epoch} ({chronology['reckoning']})"

        if "- **Current Epoch:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Current Epoch:\*\*.*",
                lambda _: f"- **Current Epoch:** {epoch_str}",
                existing_text,
                count=1,
            )
        # Update Dominant Biomes & Regions line if present
        if "- **Dominant Biomes & Regions:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Dominant Biomes & Regions:\*\*.*",
                lambda _: f"- **Dominant Biomes & Regions:** {meta['regions']}",
                existing_text,
                count=1,
            )
        # Update Active Settlements & Landmarks line if present
        if "- **Active Settlements & Landmarks:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Active Settlements & Landmarks:\*\*.*",
                lambda _: f"- **Active Settlements & Landmarks:** {meta['landmarks']}",
                existing_text,
                count=1,
            )
        # Update Active Roads & Crossings line if present
        if "- **Active Roads & Crossings:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Active Roads & Crossings:\*\*.*",
                lambda _: f"- **Active Roads & Crossings:** {meta['roads']}",
                existing_text,
                count=1,
            )

        # Check if this epoch is already recorded (idempotency check)
        epoch_pattern = re.compile(
            r"(## Epoch\s*" + str(epoch) + r"\b[\s\S]*?)(?=\n---\n\s*## Epoch|\Z)",
            re.IGNORECASE,
        )
        if epoch_pattern.search(existing_text):
            existing_text = epoch_pattern.sub(lambda _: chronicle_chunk.strip(), existing_text)
            full_content = existing_text.rstrip() + "\n"
        else:
            append_content = f"\n\n---\n\n{chronicle_chunk.strip()}\n"
            full_content = existing_text.rstrip() + append_content

        file_path.write_text(full_content, encoding="utf-8")

    return file_path


def _slugify_key(text: str) -> str:
    """Converts text into an alphanumeric lowercase key for collision checks."""
    return re.sub(r"[^a-zA-Z0-9]", "", str(text)).lower()


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

        # Deduplicate landmarks on initialization
        self._deduplicate_landmarks()

    def _deduplicate_landmarks(self) -> None:
        """Removes co-located or identically named duplicate landmarks, keeping the most evolved."""
        cleaned: dict[str, dict[str, Any]] = {}
        seen_positions: dict[tuple[int, int], str] = {}
        seen_slugs: dict[str, str] = {}

        for key, data in list(self.state.get("landmarks", {}).items()):
            if not isinstance(data, dict):
                continue
            pos = tuple(data.get("pos", [])) if isinstance(data.get("pos"), list) else ()
            slug = _slugify_key(key) or _slugify_key(data.get("name", ""))

            conflict_key = None
            if pos and pos in seen_positions:
                conflict_key = seen_positions[pos]
            elif slug and slug in seen_slugs:
                conflict_key = seen_slugs[slug]

            if conflict_key and conflict_key in cleaned:
                prev_data = cleaned[conflict_key]
                p_char = prev_data.get("char", "o")
                c_char = data.get("char", "o")
                # Keep the canonical key (conflict_key), but update attributes if new data is more evolved
                if c_char in ("O", "!") and p_char == "o":
                    cleaned[conflict_key]["char"] = c_char
                    cleaned[conflict_key]["type"] = data.get("type", prev_data.get("type", "settlement"))
                    if data.get("name"):
                        cleaned[conflict_key]["name"] = data["name"]
            else:
                cleaned[key] = data
                if pos:
                    seen_positions[pos] = key
                if slug:
                    seen_slugs[slug] = key

        self.state["landmarks"] = cleaned

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
        draining wetlands, or terraforming). When a location expands its influence (agricultural
        farmland ':' or dungeon wastelands '*'), pass BOTH terrain_char and region_id to ensure
        dual-grid synchronization.

        Args:
            coords: List of coordinate pairs [x, y] to update (0 <= x < 32, 0 <= y < 32).
                    Can be a single pair like [[14, 22]] or a list of pairs like [[14, 22], [14, 23]].
            terrain_char: Optional single character representing natural ground
                          (e.g., '.' for plains, '#' for forest, '~' for water, '*' for wasteland, ':' for farmland).
            region_id: Optional single alphanumeric character ID corresponding to the region
                       in the regions dictionary (e.g., '0', '1', 'a').
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

        When a location expands its influence (e.g. agricultural basin ':' or dungeon wasteland '*'),
        pass BOTH terrain_char and region_id to ensure dual-grid synchronization.

        Args:
            x1: First corner column X (0-31).
            y1: First corner row Y (0-31).
            x2: Opposite corner column X (0-31).
            y2: Opposite corner row Y (0-31).
            terrain_char: Optional single character terrain symbol (e.g., '*', '.', '#', ':').
            region_id: Optional single character region ID (e.g., '0', '5', 'a').
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
        target_slug = _slugify_key(clean_id) or _slugify_key(name)

        # Enforce key immutability: check if a landmark already exists at this coordinate or with matching slug/key
        canonical_key = clean_id
        is_update = False
        key_mutation_attempted = False

        if clean_id in self.state["landmarks"]:
            canonical_key = clean_id
            is_update = True
        else:
            for existing_k, existing_data in self.state["landmarks"].items():
                if not isinstance(existing_data, dict):
                    continue
                e_pos = existing_data.get("pos", [])
                e_slug = _slugify_key(existing_k) or _slugify_key(existing_data.get("name", ""))
                if e_pos == [x, y] or (target_slug and e_slug == target_slug):
                    canonical_key = existing_k
                    is_update = True
                    if existing_k != clean_id:
                        key_mutation_attempted = True
                    break

        self.state["landmarks"][canonical_key] = {
            "name": str(name).strip(),
            "char": marker,
            "type": str(type).strip(),
            "pos": [x, y],
        }
        self._sync_to_disk()

        if is_update and key_mutation_attempted:
            msg = (
                f"Landmark '{canonical_key}' updated to '{name}' ['{marker}'] at [X: {x}, Y: {y}] ({type}) "
                f"(retained immutable primary key '{canonical_key}', ignored key mutation attempt '{clean_id}')."
            )
        elif is_update:
            msg = f"Landmark '{canonical_key}' updated to '{name}' ['{marker}'] at [X: {x}, Y: {y}] ({type})."
        else:
            msg = f"Landmark '{canonical_key}' founded as '{name}' ['{marker}'] at [X: {x}, Y: {y}] ({type})."

        self.mutation_log.append(msg)
        return msg

    def remove_landmark(self, landmark_id: str) -> str:
        """Removes a landmark from the landmarks registry.

        Args:
            landmark_id: Key of the landmark to remove.
        """
        clean_id = str(landmark_id).strip()
        target_slug = _slugify_key(clean_id)

        # Direct key match
        if clean_id in self.state["landmarks"]:
            del self.state["landmarks"][clean_id]
            self._sync_to_disk()
            msg = f"Landmark '{clean_id}' removed from landmarks registry."
            self.mutation_log.append(msg)
            return msg

        # Fallback: match by slug or display name
        for k, data in list(self.state["landmarks"].items()):
            if not isinstance(data, dict):
                continue
            if target_slug and (
                _slugify_key(k) == target_slug or _slugify_key(data.get("name", "")) == target_slug
            ):
                del self.state["landmarks"][k]
                self._sync_to_disk()
                msg = f"Landmark '{k}' (matched via '{clean_id}') removed from landmarks registry."
                self.mutation_log.append(msg)
                return msg

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
        clean_type = str(road_type).strip().lower()
        valid_tiles: list[list[int]] = []

        if isinstance(tiles, list):
            for pt in tiles:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    x, y = int(pt[0]), int(pt[1])
                    if 0 <= x < 32 and 0 <= y < 32:
                        valid_tiles.append([x, y])

        if not valid_tiles:
            msg = f"Error: No valid within-bounds coordinates provided for road '{clean_name}'."
            self.mutation_log.append(msg)
            return msg

        # Barrier & Bridge Overlap Validation for non-bridge roads
        if clean_type != "bridge":
            terrain_grid = self.state.get("terrain_grid", [])

            # 1. Check for overlap with existing bridges
            existing_bridges: dict[tuple[int, int], str] = {}
            for r_name, r_data in self.state.get("roads", {}).items():
                if (
                    r_name != clean_name
                    and str(r_data.get("type", "")).strip().lower() == "bridge"
                ):
                    for b_pt in r_data.get("tiles", []):
                        if isinstance(b_pt, (list, tuple)) and len(b_pt) >= 2:
                            existing_bridges[(int(b_pt[0]), int(b_pt[1]))] = r_name

            bridge_overlaps = [
                (i, pt, existing_bridges[tuple(pt)])
                for i, pt in enumerate(valid_tiles)
                if tuple(pt) in existing_bridges
            ]
            if bridge_overlaps:
                idx, overlap_tile, bridge_name = bridge_overlaps[0]
                tiles_before = valid_tiles[:idx]
                tiles_after = valid_tiles[idx + 1 :]
                bx, by = tiles_before[-1] if tiles_before else (None, None)
                ax, ay = tiles_after[0] if tiles_after else (None, None)

                res_lines = [
                    f"REJECTED: Road '{clean_name}' (type: '{road_type}') overlaps with existing bridge '{bridge_name}' at coordinate(s) {[pt for _, pt, _ in bridge_overlaps]}.",
                    "",
                    "ACTIONABLE RESOLUTION:",
                    f"Do not include bridge coordinates in '{clean_name}', as this crossing is already served by '{bridge_name}'.",
                ]
                step_num = 1
                if tiles_before:
                    res_lines.append(f"{step_num}. Register '{clean_name}' up to the bridgehead [{bx}, {by}]:")
                    res_lines.append(f"   upsert_road(road_name='{clean_name}', road_type='{road_type}', tiles={tiles_before})")
                    step_num += 1
                if tiles_after:
                    res_lines.append(f"{step_num}. Continue '{clean_name}' from the opposite bank [{ax}, {ay}] (using extend=True):")
                    res_lines.append(f"   upsert_road(road_name='{clean_name}', road_type='{road_type}', tiles={tiles_after}, extend=True)")
                msg = "\n".join(res_lines)
                self.mutation_log.append(f"[REJECTED] {clean_name}: Overlaps existing bridge '{bridge_name}'")
                return msg

            # 2. Check for natural barriers ('~' water, '/' chasm)
            # Landmark tiles (e.g. cliffside ports or island forts) are exempt if they are terminal points
            landmark_positions = {
                tuple(lm["pos"])
                for lm in self.state.get("landmarks", {}).values()
                if isinstance(lm, dict) and "pos" in lm and isinstance(lm["pos"], (list, tuple)) and len(lm["pos"]) >= 2
            }

            barrier_indices = []
            for i, (x, y) in enumerate(valid_tiles):
                if 0 <= y < len(terrain_grid) and 0 <= x < len(terrain_grid[y]):
                    t_char = terrain_grid[y][x]
                    if t_char in ("~", "/"):
                        # If this is the road's start or end point and a landmark is located here,
                        # exempt it — the road is terminating at the settlement's harbor/gates.
                        is_terminal = (i == 0 or i == len(valid_tiles) - 1)
                        if is_terminal and (x, y) in landmark_positions:
                            continue
                        barrier_indices.append((i, [x, y], t_char))

            if barrier_indices:
                first_idx = barrier_indices[0][0]
                contiguous_span = [barrier_indices[0][1]]
                barrier_char = barrier_indices[0][2]
                curr_i = first_idx
                for bi, bpt, bch in barrier_indices[1:]:
                    if bi == curr_i + 1:
                        contiguous_span.append(bpt)
                        curr_i = bi
                    else:
                        break

                tiles_before = valid_tiles[:first_idx]
                tiles_after = valid_tiles[first_idx + len(contiguous_span) :]

                is_water = barrier_char == "~"
                barrier_type = "water / river" if is_water else "chasm / cliff"
                bank_label = "river bank" if is_water else "cliff edge"

                bx, by = tiles_before[-1] if tiles_before else (None, None)
                ax, ay = tiles_after[0] if tiles_after else (None, None)

                suggested_bridge = (
                    f"{clean_name} Crossing"
                    if "bridge" not in clean_name.lower() and "span" not in clean_name.lower() and "crossing" not in clean_name.lower()
                    else clean_name
                )

                res_lines = [
                    f"REJECTED: Road '{clean_name}' (type: '{road_type}') failed barrier validation.",
                    f"- Untamed {barrier_type} barrier detected at coordinate(s): {contiguous_span} (Terrain: '{barrier_char}'). Standard roads cannot directly cross {barrier_type} without a bridge.",
                    "",
                    "ACTIONABLE RESOLUTION:",
                ]
                step_num = 1
                if tiles_before:
                    res_lines.append(f"{step_num}. Terminate '{clean_name}' at the {bank_label} [{bx}, {by}]:")
                    res_lines.append(f"   upsert_road(road_name='{clean_name}', road_type='{road_type}', tiles={tiles_before})")
                    step_num += 1

                res_lines.append(f"{step_num}. Upsert a bridge across the {barrier_type} at {contiguous_span} using the chronicle's named bridge or a contextual name (e.g., '{suggested_bridge}'):")
                res_lines.append(f"   upsert_road(road_name='{suggested_bridge}', road_type='bridge', tiles={contiguous_span})")
                step_num += 1

                if tiles_after:
                    res_lines.append(f"{step_num}. Continue the road from the opposite {bank_label} [{ax}, {ay}] (using extend=True):")
                    res_lines.append(f"   upsert_road(road_name='{clean_name}', road_type='{road_type}', tiles={tiles_after}, extend=True)")

                msg = "\n".join(res_lines)
                self.mutation_log.append(f"[REJECTED] {clean_name}: Barrier '{barrier_char}' at {contiguous_span}")
                return msg

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
            self.state["roads"].pop(clean_name, None)
            self._sync_to_disk()
            msg = f"Road '{clean_name}' had 0 tiles and was removed from roads registry."
            self.mutation_log.append(msg)
            return msg

        pct = max(0.1, min(0.9, float(decay_percentage)))
        remove_count = int(len(tiles) * pct)
        if remove_count == 0 and len(tiles) > 1:
            remove_count = 1

        step = max(2, int(round(1.0 / pct)))
        remaining = [t for i, t in enumerate(tiles) if (i % step) != 0]

        if not remaining:
            self.state["roads"].pop(clean_name, None)
            self._sync_to_disk()
            msg = f"Road '{clean_name}' fully decayed and was removed from roads registry (0 tiles remaining)."
            self.mutation_log.append(msg)
            return msg

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

