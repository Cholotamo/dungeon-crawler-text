"""Scribe Agent module.

Chronicles the localized evolution, districts, notable figures, and micro-lore
of settlements and dungeons across epochs. Outputs feed downstream systems
(Architect, Socio, Quest Writer) and produce frontier dispatches for the Historian.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import math
from pathlib import Path
import re
from typing import Any, Optional

from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff

METADATA_UPDATE_START = "___METADATA_UPDATE_START___"
METADATA_UPDATE_END = "___METADATA_UPDATE_END___"
DISPATCH_START = "___DISPATCH_START___"
DISPATCH_END = "___DISPATCH_END___"
CHRONICLE_START = "___CHRONICLE_START___"
CHRONICLE_END = "___CHRONICLE_END___"


def _load_prompt(filename: str) -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


def slugify(text: str) -> str:
    """Converts a name into a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_") or "unnamed_location"


def extract_delimited_block(text: str, start_delim: str, end_delim: str) -> str:
    """Extracts content between delimiters."""
    if start_delim in text and end_delim in text:
        start_idx = text.index(start_delim) + len(start_delim)
        end_idx = text.index(end_delim, start_idx)
        return text[start_idx:end_idx].strip()
    return ""


def parse_metadata_update(text: str) -> dict[str, str]:
    """Parses key-value pairs from the METADATA_UPDATE block."""
    raw = extract_delimited_block(text, METADATA_UPDATE_START, METADATA_UPDATE_END)
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip().lower()] = v.strip()
    return data


def extract_dispatch(text: str) -> str:
    """Extracts the 1-line frontier dispatch from the Scribe's output."""
    raw = extract_delimited_block(text, DISPATCH_START, DISPATCH_END)
    if raw:
        # Return first non-empty line
        for line in raw.splitlines():
            line = line.strip()
            if line:
                return line
    return ""


def extract_chronicle(text: str) -> str:
    """Extracts the full markdown chronicle block."""
    raw = extract_delimited_block(text, CHRONICLE_START, CHRONICLE_END)
    if raw:
        return raw.strip()

    # Fallback: strip delimiters if partially present, or return text
    cleaned = text
    for delim in (METADATA_UPDATE_START, METADATA_UPDATE_END, DISPATCH_START, DISPATCH_END):
        cleaned = cleaned.replace(delim, "")
    return cleaned.strip()


def build_location_dossier(
    landmark_key: str,
    landmark_data: dict[str, Any],
    world_state: dict[str, Any],
) -> str:
    """Constructs a geographic and contextual dossier for a specific landmark."""
    name = landmark_data.get("name", landmark_key)
    pos = landmark_data.get("pos", [0, 0])
    x, y = pos[0], pos[1]
    char = landmark_data.get("char", "o")
    l_type = landmark_data.get("type", "settlement")

    # Resolve terrain and biome
    terrain_grid = world_state.get("terrain_grid", [])
    region_grid = world_state.get("region_grid", [])
    regions = world_state.get("regions", {})

    terrain_char = "."
    if 0 <= y < len(terrain_grid) and 0 <= x < len(terrain_grid[y]):
        terrain_char = terrain_grid[y][x]

    region_id = "0"
    if 0 <= y < len(region_grid) and 0 <= x < len(region_grid[y]):
        region_id = region_grid[y][x]

    region_info = regions.get(region_id, {})
    biome_name = region_info.get("name", "Wilderness")
    biome_type = region_info.get("type", "wilderness")

    # Detect connected routes
    connected_roads: list[str] = []
    roads = world_state.get("roads", {})
    for road_name, road_info in roads.items():
        tiles = road_info.get("tiles", [])
        # Check if any road tile is within Chebyshev distance of 1 (adjacent or on landmark)
        for rx, ry in tiles:
            if max(abs(rx - x), abs(ry - y)) <= 1:
                r_type = road_info.get("type", "road")
                connected_roads.append(f"{road_name} ({r_type})")
                break

    # Detect nearby landmarks (within 8 tiles Euclidean distance)
    nearby_landmarks: list[str] = []
    all_landmarks = world_state.get("landmarks", {})
    for other_key, other_data in all_landmarks.items():
        if other_key == landmark_key:
            continue
        ox, oy = other_data.get("pos", [0, 0])
        dist = math.hypot(ox - x, oy - y)
        if dist <= 8.0:
            nearby_landmarks.append(
                f"{other_data.get('name', other_key)} at [{ox}, {oy}] (~{round(dist)} tiles away)"
            )

    dossier_lines = [
        f"- Name: {name}",
        f"- Key / ID: {landmark_key}",
        f"- Coordinates: [X: {x}, Y: {y}]",
        f"- Map Symbol: '{char}' (Type: {l_type})",
        f"- Natural Ground: '{terrain_char}'",
        f"- Biome / Territory: {biome_name} ({biome_type}, ID: '{region_id}')",
        f"- Connected Routes: {', '.join(connected_roads) if connected_roads else 'None (Isolated)'}",
        f"- Nearby Landmarks: {', '.join(nearby_landmarks) if nearby_landmarks else 'None within 8 tiles'}",
    ]
    return "\n".join(dossier_lines)


def find_existing_location_history(
    artifacts_dir: Path,
    pos: Optional[list[int]] = None,
    location_key: Optional[str] = None,
) -> Optional[Path]:
    """Finds an existing history.md file by matching [X, Y] coordinates or fallback slug."""
    locations_dir = artifacts_dir / "locations"
    if not locations_dir.exists():
        return None

    # 1. Coordinate check: match against coordinates in the header of existing history.md files
    if pos and isinstance(pos, (list, tuple)) and len(pos) >= 2:
        px, py = int(pos[0]), int(pos[1])
        coord_patterns = [
            f"[X: {px:02d}, Y: {py:02d}]",
            f"[X: {px}, Y: {py}]",
        ]
        for hist_file in locations_dir.glob("*/history.md"):
            try:
                # Read top 15 lines where header lives
                lines = hist_file.read_text(encoding="utf-8").splitlines()[:15]
                header_text = "\n".join(lines)
                for pat in coord_patterns:
                    if pat in header_text:
                        return hist_file
            except Exception:
                continue

    # 2. Slug check fallback
    if location_key:
        slug_path = locations_dir / slugify(location_key) / "history.md"
        if slug_path.exists():
            return slug_path

    return None


def get_location_history_path(
    artifacts_dir: Path,
    location_key: str,
    pos: Optional[list[int]] = None,
) -> Path:
    """Returns the path to artifacts/locations/<slug>/history.md, reusing any existing file at the same coordinates."""
    existing = find_existing_location_history(artifacts_dir, pos=pos, location_key=location_key)
    if existing:
        return existing
    slug = slugify(location_key)
    return artifacts_dir / "locations" / slug / "history.md"


def read_location_history(
    artifacts_dir: Path,
    location_key: str,
    pos: Optional[list[int]] = None,
) -> Optional[str]:
    """Reads existing location history markdown if it exists."""
    path = get_location_history_path(artifacts_dir, location_key, pos=pos)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def save_location_chronicle(
    artifacts_dir: Path,
    landmark_key: str,
    landmark_data: dict[str, Any],
    world_state: dict[str, Any],
    metadata_update: dict[str, str],
    chronicle_chunk: str,
    epoch: int,
    year: int,
) -> Path:
    """Writes or appends to artifacts/locations/<slug>/history.md with updated header."""
    pos = landmark_data.get("pos", [0, 0])
    file_path = get_location_history_path(artifacts_dir, landmark_key, pos=pos)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    name = landmark_data.get("name", landmark_key)
    pos = landmark_data.get("pos", [0, 0])
    char = landmark_data.get("char", "o")
    l_type = landmark_data.get("type", "settlement")

    # Current status
    status_val = metadata_update.get(
        "current status", f"{l_type.replace('_', ' ').title()} (`{char}`)"
    )
    factions_val = metadata_update.get("active factions", "None recorded")

    if not file_path.exists():
        # Turn of founding: Write complete header
        dossier_str = build_location_dossier(landmark_key, landmark_data, world_state)
        # Extract biome and connected routes for clean header
        regions = world_state.get("regions", {})
        rx, ry = pos[0], pos[1]
        r_grid = world_state.get("region_grid", [])
        rid = r_grid[ry][rx] if 0 <= ry < len(r_grid) and 0 <= rx < len(r_grid[ry]) else "0"
        b_name = regions.get(rid, {}).get("name", "Wilderness")

        header = (
            f"# Location: {name}\n"
            f"- **Coordinates:** [X: {pos[0]:02d}, Y: {pos[1]:02d}]\n"
            f"- **Current Status:** {status_val}\n"
            f"- **Founding Era:** Epoch {epoch} (Year {year})\n"
            f"- **Biome & Geography:** {b_name} (Region ID: '{rid}')\n"
            f"- **Active Factions:** {factions_val}\n\n"
            f"---\n\n"
        )
        full_content = header + chronicle_chunk.strip() + "\n"
        file_path.write_text(full_content, encoding="utf-8")
    else:
        # Existing file: Update status & active factions in header, then append chronicle
        existing_text = file_path.read_text(encoding="utf-8")

        # Update Current Status line if present
        if "- **Current Status:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Current Status:\*\*.*",
                f"- **Current Status:** {status_val}",
                existing_text,
                count=1,
            )
        # Update Active Factions line if present
        if "- **Active Factions:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Active Factions:\*\*.*",
                f"- **Active Factions:** {factions_val}",
                existing_text,
                count=1,
            )

        append_content = f"\n\n---\n\n{chronicle_chunk.strip()}\n"
        full_content = existing_text.rstrip() + append_content
        file_path.write_text(full_content, encoding="utf-8")

    return file_path


def detect_active_locations(
    previous_state: dict[str, Any],
    current_state: dict[str, Any],
    historian_narrative: str,
) -> list[str]:
    """Identifies landmarks that experienced state mutations or were mentioned in the narrative."""
    active: set[str] = set()
    prev_landmarks = previous_state.get("landmarks", {})
    curr_landmarks = current_state.get("landmarks", {})

    # 1. Any newly founded landmark in current_state
    for key in curr_landmarks:
        if key not in prev_landmarks:
            active.add(key)
        else:
            # Check for mutations (symbol, pos, type)
            p = prev_landmarks[key]
            c = curr_landmarks[key]
            if (
                p.get("char") != c.get("char")
                or p.get("type") != c.get("type")
                or p.get("pos") != c.get("pos")
            ):
                active.add(key)

    # 2. Check if any existing landmark was mentioned in Historian's prose
    narrative_lower = historian_narrative.lower()
    for key, data in curr_landmarks.items():
        if key.lower() in narrative_lower:
            active.add(key)
            continue
        name = data.get("name", "")
        if name and name.lower() in narrative_lower:
            active.add(key)

    # 3. Deduplicate active locations by slug and coordinate position
    # (prevents dispatching multiple Scribes for duplicate keys like "Kaelens_Ford" and "Kaelen's Ford")
    deduped_active: list[str] = []
    seen_slugs: set[str] = set()
    seen_positions: set[tuple[int, int]] = set()

    # Sort keys so cleaner keys without underscores are prioritized
    sorted_keys = sorted(list(active), key=lambda k: ("_" in k, k))

    for key in sorted_keys:
        data = curr_landmarks.get(key, {})
        slug = slugify(key)
        pos_list = data.get("pos", [])
        pos = tuple(pos_list) if isinstance(pos_list, list) and len(pos_list) >= 2 else None

        if slug in seen_slugs:
            continue
        if pos and pos in seen_positions:
            continue

        seen_slugs.add(slug)
        if pos:
            seen_positions.add(pos)
        deduped_active.append(key)

    return sorted(deduped_active)


class Scribe:
    """Scribe agent that chronicles local history for individual landmarks."""

    def __init__(
        self,
        model_name: str = "gemini-3.7-flash",
        thinking_level: str = "HIGH",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("Scribe.md")
        self.token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "total_tokens": 0,
            "thoughts_tokens": 0,
        }

    def _track_usage(self, response: Any) -> None:
        """Records token usage from response metadata."""
        meta = getattr(response, "usage_metadata", None)
        if meta:
            p = getattr(meta, "prompt_token_count", 0)
            c = getattr(meta, "candidates_token_count", 0)
            t = getattr(meta, "total_token_count", 0)
            th = getattr(meta, "thoughts_token_count", 0)
            p = p if isinstance(p, int) else 0
            c = c if isinstance(c, int) else 0
            t = t if isinstance(t, int) else (p + c)
            th = th if isinstance(th, int) else 0
            self.token_usage["prompt_tokens"] += p
            self.token_usage["candidates_tokens"] += c
            self.token_usage["total_tokens"] += t
            self.token_usage["thoughts_tokens"] += th

    @retry_with_backoff(max_retries=4, initial_delay=2.0)
    def chronicle_location(
        self,
        landmark_key: str,
        landmark_data: dict[str, Any],
        world_state: dict[str, Any],
        historian_narrative: str,
        cartographer_log: str,
        epoch: int,
        year: int,
        existing_history: Optional[str] = None,
    ) -> tuple[str, str, dict[str, str]]:
        """Generates the local chronicle and dispatch for a single location.

        Returns:
            (frontier_dispatch, chronicle_markdown, metadata_updates)
        """
        dossier = build_location_dossier(landmark_key, landmark_data, world_state)
        history_context = existing_history or "None (This location was just founded this epoch)."

        user_prompt = (
            f"## Location Dossier:\n"
            f"{dossier}\n\n"
            f"## Current Simulation Context:\n"
            f"- Current Epoch: {epoch}\n"
            f"- Current Year: {year}\n\n"
            f"## Grand Historian's Chronicle for Epoch {epoch}:\n"
            f"{historian_narrative}\n\n"
            f"## Cartographer's Physical Alteration Log:\n"
            f"{cartographer_log}\n\n"
            f"## Existing Location History:\n"
            f"{history_context}\n\n"
            "Now, provide the three required delimited blocks:\n"
            "1. Living Metadata Update (___METADATA_UPDATE_START___ ... ___METADATA_UPDATE_END___)\n"
            "2. Frontier Dispatch (___DISPATCH_START___ ... ___DISPATCH_END___)\n"
            "3. Epoch Chronicle (___CHRONICLE_START___ ... ___CHRONICLE_END___)"
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.75,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        )
        self._track_usage(response)

        raw_text = getattr(response, "text", "") or ""
        metadata_update = parse_metadata_update(raw_text)
        dispatch = extract_dispatch(raw_text)
        chronicle = extract_chronicle(raw_text)

        return dispatch, chronicle, metadata_update


def run_scribes_parallel(
    scribe: Scribe,
    active_landmarks: list[str],
    world_state: dict[str, Any],
    historian_narrative: str,
    cartographer_log: str,
    epoch: int,
    year: int,
    artifacts_dir: Path,
    max_workers: int = 3,
) -> list[str]:
    """Runs Scribe agents concurrently across active landmarks.

    Saves each location's chronicle and returns a list of frontier dispatches.
    """
    dispatches: list[str] = []
    if not active_landmarks:
        return dispatches

    landmarks = world_state.get("landmarks", {})

    def _process_landmark(l_key: str) -> Optional[str]:
        l_data = landmarks.get(l_key, {})
        l_pos = l_data.get("pos", [])
        existing_hist = read_location_history(artifacts_dir, l_key, pos=l_pos)
        try:
            disp, chron, meta = scribe.chronicle_location(
                landmark_key=l_key,
                landmark_data=l_data,
                world_state=world_state,
                historian_narrative=historian_narrative,
                cartographer_log=cartographer_log,
                epoch=epoch,
                year=year,
                existing_history=existing_hist,
            )
            save_location_chronicle(
                artifacts_dir=artifacts_dir,
                landmark_key=l_key,
                landmark_data=l_data,
                world_state=world_state,
                metadata_update=meta,
                chronicle_chunk=chron,
                epoch=epoch,
                year=year,
            )
            return disp
        except Exception as e:
            print(f"  [WARNING] Scribe failed for '{l_key}': {e}", flush=True)
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_landmark, key): key for key in active_landmarks}
        for future in as_completed(futures):
            key = futures[future]
            try:
                res = future.result()
                if res:
                    dispatches.append(res)
            except Exception as e:
                print(f"  [ERROR] Scribe execution error for '{key}': {e}", flush=True)

    return dispatches
