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
from dungeon_crawler_text.world_state import WorldStateMutator

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

    # Extract current biome and region ID from world_state
    regions = world_state.get("regions", {})
    rx, ry = int(pos[0]), int(pos[1])
    r_grid = world_state.get("region_grid", [])
    rid = r_grid[ry][rx] if 0 <= ry < len(r_grid) and 0 <= rx < len(r_grid[ry]) else "0"
    b_name = regions.get(rid, {}).get("name", "Wilderness")

    if not file_path.exists():
        # Turn of founding: Write complete header
        header = (
            f"# Location: {name}\n"
            f"- **Coordinates:** [X: {pos[0]:02d}, Y: {pos[1]:02d}]\n"
            f"- **Current Status:** {status_val}\n"
            f"- **Founding Era:** Epoch {epoch}\n"
            f"- **Biome & Geography:** {b_name} (Region ID: '{rid}')\n"
            f"- **Active Factions:** {factions_val}\n\n"
            f"---\n\n"
        )
        full_content = header + chronicle_chunk.strip() + "\n"
        file_path.write_text(full_content, encoding="utf-8")
    else:
        # Existing file: Update status, active factions & biome in header, then append chronicle
        existing_text = file_path.read_text(encoding="utf-8")

        # Update Current Status line if present
        if "- **Current Status:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Current Status:\*\*.*",
                f"- **Current Status:** {status_val}",
                existing_text,
                count=1,
            )
        # Update Biome & Geography line to reflect region mutations/wastelands
        if "- **Biome & Geography:**" in existing_text:
            existing_text = re.sub(
                r"- \*\*Biome & Geography:\*\*.*",
                f"- **Biome & Geography:** {b_name} (Region ID: '{rid}')",
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


COMMON_DESCRIPTOR_TOKENS = {
    "outpost", "camp", "ruin", "ruins", "fort", "keep", "tower",
    "dungeon", "metropolis", "city", "settlement", "site", "den",
    "the", "of", "and", "hold", "gate", "port", "crossing", "basin",
    "road", "bridge", "river", "peaks", "mountains", "woods", "forest",
    "swamp", "marsh", "plain", "plains", "hollow", "haven", "deep",
    "domain", "reach", "pass", "spire", "vale", "hall", "halls",
}


def is_landmark_mentioned(text: str, landmark_key: str, landmark_data: dict[str, Any]) -> bool:
    """Checks if a landmark is referenced in text using exact, slug, and distinctive token matching."""
    if not text:
        return False

    text_lower = text.lower()

    # 1. Exact key match (with underscores replaced by spaces)
    k_clean = landmark_key.lower().replace("_", " ").strip()
    if k_clean and re.search(rf"\b{re.escape(k_clean)}\b", text_lower):
        return True

    # 2. Display name match
    name = str(landmark_data.get("name", "")).lower().replace("_", " ").strip()
    if name and re.search(rf"\b{re.escape(name)}\b", text_lower):
        return True

    # 3. Normalized slug match
    slug = slugify(landmark_key)
    if slug and len(slug) >= 5 and re.search(rf"\b{re.escape(slug)}\b", text_lower):
        return True

    # 4. Distinctive tokens from key and display name (>= 4 letters, excluding common descriptors)
    combined_name = f"{landmark_key} {landmark_data.get('name', '')}".lower()
    combined_name = re.sub(r"['’]s\b", "", combined_name)
    tokens = re.findall(r"[a-z0-9]{4,}", combined_name)
    for token in tokens:
        if token not in COMMON_DESCRIPTOR_TOKENS:
            if re.search(rf"\b{re.escape(token)}\b", text_lower):
                return True

    return False


def detect_active_locations(
    previous_state: dict[str, Any],
    current_state: dict[str, Any],
    historian_narrative: str,
    cartographer_log: Optional[str] = None,
    rumors_and_dispatches: Optional[str] = None,
) -> list[str]:
    """Identifies landmarks that experienced state mutations, road connections, or were mentioned in text."""
    active: set[str] = set()
    prev_landmarks = previous_state.get("landmarks", {})
    curr_landmarks = current_state.get("landmarks", {})

    # 1. Any newly founded or mutated landmark in current_state
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

    # 2. Check road infrastructure mutations:
    # If roads were newly created or altered, activate landmarks on or adjacent to them
    prev_roads = previous_state.get("roads", {})
    curr_roads = current_state.get("roads", {})
    new_or_altered_road_tiles: set[tuple[int, int]] = set()

    for r_name, r_data in curr_roads.items():
        if not isinstance(r_data, dict):
            continue
        p_data = prev_roads.get(r_name)
        curr_tiles = [
            tuple(pt)
            for pt in r_data.get("tiles", [])
            if isinstance(pt, (list, tuple)) and len(pt) >= 2
        ]
        if not p_data:
            new_or_altered_road_tiles.update(curr_tiles)
        else:
            prev_tiles = [
                tuple(pt)
                for pt in p_data.get("tiles", [])
                if isinstance(pt, (list, tuple)) and len(pt) >= 2
            ]
            if curr_tiles != prev_tiles:
                new_or_altered_road_tiles.update(curr_tiles)

    # If roads were removed, activate landmarks along the lost route
    for r_name, p_data in prev_roads.items():
        if r_name not in curr_roads and isinstance(p_data, dict):
            prev_tiles = [
                tuple(pt)
                for pt in p_data.get("tiles", [])
                if isinstance(pt, (list, tuple)) and len(pt) >= 2
            ]
            new_or_altered_road_tiles.update(prev_tiles)

    if new_or_altered_road_tiles:
        for key, data in curr_landmarks.items():
            pos = data.get("pos")
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                px, py = int(pos[0]), int(pos[1])
                if (px, py) in new_or_altered_road_tiles:
                    active.add(key)
                else:
                    for rx, ry in new_or_altered_road_tiles:
                        if abs(px - rx) + abs(py - ry) <= 1:
                            active.add(key)
                            break

    # 3. Check text mentions across Historian prose, Cartographer log, and Rumors/Dispatches
    combined_text = f"{historian_narrative}\n{cartographer_log or ''}\n{rumors_and_dispatches or ''}"
    for key, data in curr_landmarks.items():
        if is_landmark_mentioned(combined_text, key, data):
            active.add(key)

    # 4. Deduplicate active locations by slug and coordinate position
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
        existing_history: Optional[str] = None,
        chronology: Optional[dict[str, str]] = None,
        referencing_context: Optional[str] = None,
    ) -> tuple[str, str, dict[str, str]]:
        """Generates the local chronicle and dispatch for a single location.

        Returns:
            (frontier_dispatch, chronicle_markdown, metadata_updates)
        """
        dossier = build_location_dossier(landmark_key, landmark_data, world_state)
        history_context = existing_history or "None (This location was just founded this epoch)."

        chrono_lines = ""
        if chronology:
            reck = chronology.get("reckoning", "")
            passed = chronology.get("years_passed", "")
            if reck:
                chrono_lines += f"- Canonical Calendar Reckoning: {reck}\n"
            if passed:
                chrono_lines += f"- Time Elapsed Since Prior Epoch: {passed}\n"

        ref_lines = ""
        if referencing_context:
            ref_lines = f"## Cross-Location Reports & Mentions Involving This Site:\n{referencing_context}\n\n"

        user_prompt = (
            f"## Location Dossier:\n"
            f"{dossier}\n\n"
            f"## Current Simulation Context:\n"
            f"- Current Epoch: {epoch}\n"
            f"{chrono_lines}\n"
            f"## Grand Historian's Chronicle for Epoch {epoch}:\n"
            f"{historian_narrative}\n\n"
            f"## Cartographer's Physical Alteration Log:\n"
            f"{cartographer_log}\n\n"
            f"{ref_lines}"
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


def generate_scribe_drafts(
    scribe: Scribe,
    active_landmarks: list[str],
    world_state: dict[str, Any],
    historian_narrative: str,
    cartographer_log: str,
    epoch: int,
    artifacts_dir: Path,
    chronology: Optional[dict[str, str]] = None,
    max_workers: int = 3,
    cascade_transitive: bool = True,
) -> dict[str, dict[str, Any]]:
    """Runs Scribe agents concurrently to generate uncommitted drafts for active landmarks,
    with an automatic secondary pass for transitively referenced landmarks."""
    drafts: dict[str, dict[str, Any]] = {}
    if not active_landmarks:
        return drafts

    landmarks = world_state.get("landmarks", {})

    def _draft_landmark(
        l_key: str, referencing_context: Optional[str] = None
    ) -> Optional[tuple[str, dict[str, Any]]]:
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
                existing_history=existing_hist,
                chronology=chronology,
                referencing_context=referencing_context,
            )
            draft_item = {
                "landmark_data": l_data,
                "dispatch": disp,
                "chronicle": chron,
                "metadata": meta,
                "existing_history": existing_hist,
            }
            return l_key, draft_item
        except Exception as e:
            print(f"  [WARNING] Scribe failed for '{l_key}': {e}", flush=True)
            return None

    # --- Round 1: Primary active landmarks ---
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_draft_landmark, key): key for key in active_landmarks}
        for future in as_completed(futures):
            key = futures[future]
            try:
                res = future.result()
                if res:
                    l_key, d_info = res
                    drafts[l_key] = d_info
            except Exception as e:
                print(f"  [ERROR] Scribe execution error for '{key}': {e}", flush=True)

    # --- Round 2: Transitive references in Round 1 drafts ---
    if cascade_transitive and drafts:
        already_drafted_slugs = {slugify(k) for k in drafts}
        already_drafted_positions = {
            tuple(d["landmark_data"]["pos"])
            for d in drafts.values()
            if isinstance(d.get("landmark_data", {}).get("pos"), list)
        }

        transitive_mentions: dict[str, list[str]] = {}
        for d_key, d_info in drafts.items():
            disp = d_info.get("dispatch", "")
            chron = d_info.get("chronicle", "")
            combined_draft_text = f"{disp}\n{chron}"

            for l_key, l_data in landmarks.items():
                slug = slugify(l_key)
                l_pos = (
                    tuple(l_data.get("pos", []))
                    if isinstance(l_data.get("pos"), list)
                    else None
                )

                if slug in already_drafted_slugs:
                    continue
                if l_pos and l_pos in already_drafted_positions:
                    continue

                if is_landmark_mentioned(combined_draft_text, l_key, l_data):
                    if l_key not in transitive_mentions:
                        transitive_mentions[l_key] = []
                    ref_snippet = disp if disp else f"Referenced by {d_key} in Epoch {epoch} chronicle."
                    transitive_mentions[l_key].append(f"- From {d_key}: {ref_snippet}")

        # Deduplicate transitive targets
        deduped_transitive: list[str] = []
        seen_trans_slugs = set(already_drafted_slugs)
        seen_trans_positions = set(already_drafted_positions)

        for l_key in sorted(transitive_mentions.keys(), key=lambda k: ("_" in k, k)):
            slug = slugify(l_key)
            l_pos = (
                tuple(landmarks[l_key].get("pos", []))
                if isinstance(landmarks[l_key].get("pos"), list)
                else None
            )
            if slug in seen_trans_slugs:
                continue
            if l_pos and l_pos in seen_trans_positions:
                continue
            seen_trans_slugs.add(slug)
            if l_pos:
                seen_trans_positions.add(l_pos)
            deduped_transitive.append(l_key)

        if deduped_transitive:
            print(
                f"\n  [TRANSITIVE ACTIVATION] Dispatching secondary Scribes for {len(deduped_transitive)} referenced location(s): "
                f"{', '.join(deduped_transitive)}...",
                flush=True,
            )
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                t_futures = {
                    executor.submit(
                        _draft_landmark,
                        t_key,
                        "\n".join(transitive_mentions.get(t_key, [])),
                    ): t_key
                    for t_key in deduped_transitive
                }
                for future in as_completed(t_futures):
                    t_key = t_futures[future]
                    try:
                        res = future.result()
                        if res:
                            l_key, d_info = res
                            drafts[l_key] = d_info
                    except Exception as e:
                        print(f"  [ERROR] Transitive Scribe execution error for '{t_key}': {e}", flush=True)

    return drafts


def sync_all_location_headers(
    artifacts_dir: Path,
    world_state: dict[str, Any],
) -> None:
    """Synchronizes header metadata (Biome & Geography) across all existing
    location history files with the current world state.
    """
    # Harmonize landmarks with surrounding domains, farmlands, or wastelands
    WorldStateMutator(world_state).harmonize_landmark_biomes()

    landmarks = world_state.get("landmarks", {})
    regions = world_state.get("regions", {})
    r_grid = world_state.get("region_grid", [])

    for l_key, l_data in landmarks.items():
        if not isinstance(l_data, dict):
            continue
        pos = l_data.get("pos", [0, 0])
        file_path = get_location_history_path(artifacts_dir, l_key, pos=pos)
        if not file_path.exists():
            continue

        rx, ry = int(pos[0]), int(pos[1])
        rid = r_grid[ry][rx] if 0 <= ry < len(r_grid) and 0 <= rx < len(r_grid[ry]) else "0"
        b_name = regions.get(rid, {}).get("name", "Wilderness")

        try:
            existing_text = file_path.read_text(encoding="utf-8")
            if "- **Biome & Geography:**" in existing_text:
                new_text = re.sub(
                    r"- \*\*Biome & Geography:\*\*.*",
                    f"- **Biome & Geography:** {b_name} (Region ID: '{rid}')",
                    existing_text,
                    count=1,
                )
                if new_text != existing_text:
                    file_path.write_text(new_text, encoding="utf-8")
        except Exception as e:
            print(f"  [WARN] Failed to sync header for '{l_key}': {e}", flush=True)


def commit_location_chronicles(
    drafts: dict[str, dict[str, Any]],
    artifacts_dir: Path,
    world_state: dict[str, Any],
    epoch: int,
) -> list[str]:
    """Persists finalized/reconciled drafts to disk and returns consolidated dispatches."""
    dispatches: list[str] = []
    for l_key, d_info in drafts.items():
        disp = d_info.get("dispatch", "")
        chron = d_info.get("chronicle", "")
        meta = d_info.get("metadata", {})
        l_data = d_info.get("landmark_data", {})

        save_location_chronicle(
            artifacts_dir=artifacts_dir,
            landmark_key=l_key,
            landmark_data=l_data,
            world_state=world_state,
            metadata_update=meta,
            chronicle_chunk=chron,
            epoch=epoch,
        )
        if disp:
            dispatches.append(disp)

    # Keep all existing location history headers in sync with current world state biomes
    sync_all_location_headers(artifacts_dir=artifacts_dir, world_state=world_state)

    return dispatches


def run_scribes_parallel(
    scribe: Scribe,
    active_landmarks: list[str],
    world_state: dict[str, Any],
    historian_narrative: str,
    cartographer_log: str,
    epoch: int,
    artifacts_dir: Path,
    chronology: Optional[dict[str, str]] = None,
    max_workers: int = 3,
    cascade_transitive: bool = True,
) -> list[str]:
    """Runs Scribe agents concurrently across active landmarks.

    Saves each location's chronicle and returns a list of frontier dispatches.
    """
    drafts = generate_scribe_drafts(
        scribe=scribe,
        active_landmarks=active_landmarks,
        world_state=world_state,
        historian_narrative=historian_narrative,
        cartographer_log=cartographer_log,
        epoch=epoch,
        artifacts_dir=artifacts_dir,
        chronology=chronology,
        max_workers=max_workers,
        cascade_transitive=cascade_transitive,
    )
    return commit_location_chronicles(
        drafts=drafts,
        artifacts_dir=artifacts_dir,
        world_state=world_state,
        epoch=epoch,
    )
