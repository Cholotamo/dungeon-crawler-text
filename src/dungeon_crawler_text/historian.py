"""Historian Agent module.

Chronicles the passage of epochs in a fantasy realm and mutates world map snapshots
using feature CRUD tools via Gemini Automatic Function Calling (AFC).
"""

import argparse
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
import heapq
import json
import logging
from pathlib import Path
import re
import sys
from typing import Any, Optional, Union

from dotenv import load_dotenv
from google import genai
from google.genai import types

from dungeon_crawler_text.region_history import update_regions_history
from dungeon_crawler_text.retry import retry_with_backoff
from dungeon_crawler_text.world_state import FEATURE_PRIORITY, format_world_for_llm

# Suppress the redundant SDK warning for stateless automatic function calling
try:
    from google.genai import models as _genai_models

    _genai_models.Models._logged_afc_warning = True
except Exception:
    pass

logger = logging.getLogger(__name__)

DEFAULT_ARTIFACTS_DIR = Path("artifacts")
DEFAULT_BASE_NAME = "worldmap"
DEFAULT_INPUT_MD_PATH = DEFAULT_ARTIFACTS_DIR / "worldmap.md"

DEFAULT_EPOCH_1_QUERY = (
    "The dawn of mortal civilization has arrived. Chronicle the arrival of the realm's first peoples, "
    "the founding of initial settlements and outposts, the paving of early trade trails, and "
    "the discovery or awakening of ancient primordial ruins or perilous dens."
)

DEFAULT_SUBSEQUENT_EPOCH_QUERY = (
    "Generations have passed. Chronicle the unfolding history of the realm across civilization, geography, and ecology:\n"
    "- Settlements & Fortresses: Thriving towns prospering into metropolises or citadels, fallen bastions sacked or ruined, ancient dungeons reclaimed and cleansed into civilized havens, or new frontier outposts founded.\n"
    "- Infrastructure & Routes: Paving trade or military highways and constructing bridges spanning rivers, shallows, or chasms.\n"
    "- Terraforming & Domains: Cultivating expanding agrarian farmlands, clearing dense timberlands or bogs, spreading blighted wastelands from awakened evils, or dissolving abandoned domains back to wilderness.\n"
    "- Mega-Engineering & Waterworks: Reshaping waterways by damming river gorges to create downstream shallows, draining wetlands, or cutting canals.\n"
    "- Regional Biome Evolution: Chronicling how wars, blights, and migrations reshape the ecology, atmosphere, dangers, and canonical lore of the realm's regional biomes."
)


class ToolRejectionError(ValueError):
    """Raised when a world map mutation tool validation check or parameter constraint fails."""
    pass



def _load_prompt(filename: str = "historian.md") -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


def _normalize_tiles(tiles: Any) -> list[list[int]]:
    """Defensively normalizes diverse coordinate representations into a list of [x, y] pairs."""
    if not tiles:
        return []

    # Case 1: Flat [x, y] coordinate pair, e.g. [14, 11]
    if (
        isinstance(tiles, (list, tuple))
        and len(tiles) == 2
        and isinstance(tiles[0], (int, float))
        and isinstance(tiles[1], (int, float))
    ):
        return [[int(tiles[0]), int(tiles[1])]]

    normalized: list[list[int]] = []
    if isinstance(tiles, (list, tuple)):
        for item in tiles:
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and isinstance(item[0], (int, float))
                and isinstance(item[1], (int, float))
            ):
                normalized.append([int(item[0]), int(item[1])])
            elif isinstance(item, dict) and "x" in item and "y" in item:
                normalized.append([int(item["x"]), int(item["y"])])
    elif isinstance(tiles, dict) and "x" in tiles and "y" in tiles:
        normalized.append([int(tiles["x"]), int(tiles["y"])])

    # Deduplicate consecutive identical coordinates to prevent zero-distance loops
    deduped: list[list[int]] = []
    for pt in normalized:
        if not deduped or pt != deduped[-1]:
            deduped.append(pt)

    return deduped


def resolve_epoch_paths(
    input_path: Optional[Union[str, Path]] = None,
    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR,
    base_name: str = DEFAULT_BASE_NAME,
) -> tuple[int, Path, Path, Path, Path]:
    """Resolves input markdown, source json, active snapshot json, and rendered markdown paths.

    Returns:
        tuple of (epoch_number, input_md_path, source_json_path, active_json_path, rendered_md_path)
    """
    artifacts_dir = Path(artifacts_dir)

    if input_path is not None:
        in_md = Path(input_path)
        if not in_md.exists():
            raise FileNotFoundError(f"Specified input markdown file not found: {in_md}")

        stem = in_md.stem
        # Check if input already ends with _epoch_N
        epoch_match = re.search(r"^(.*?)(?:_epoch_(\d+))?$", stem)
        if epoch_match and epoch_match.group(2):
            b_name = epoch_match.group(1)
            prev_epoch = int(epoch_match.group(2))
            next_epoch = prev_epoch + 1
            source_json = in_md.with_suffix(".json")
            if not source_json.exists():
                # Fallback to base json
                source_json = in_md.parent / f"{b_name}.json"
        else:
            b_name = stem
            next_epoch = 1
            source_json = in_md.with_suffix(".json")
            if not source_json.exists():
                source_json = in_md.parent / f"{b_name}.json"

        target_dir = in_md.parent
        active_json = target_dir / f"{b_name}_epoch_{next_epoch}.json"
        rendered_md = target_dir / f"{b_name}_epoch_{next_epoch}.md"
        return next_epoch, in_md, source_json, active_json, rendered_md

    # If input_path is not specified, auto-detect latest existing epoch in artifacts_dir
    epoch_files: list[tuple[int, Path]] = []
    if artifacts_dir.exists():
        for f in artifacts_dir.glob(f"{base_name}_epoch_*.md"):
            m = re.search(rf"^{re.escape(base_name)}_epoch_(\d+)\.md$", f.name)
            if m:
                epoch_files.append((int(m.group(1)), f))

    if epoch_files:
        epoch_files.sort(key=lambda x: x[0])
        latest_epoch, latest_md = epoch_files[-1]
        next_epoch = latest_epoch + 1
        source_json = latest_md.with_suffix(".json")
        if not source_json.exists():
            source_json = artifacts_dir / f"{base_name}.json"
        active_json = artifacts_dir / f"{base_name}_epoch_{next_epoch}.json"
        rendered_md = artifacts_dir / f"{base_name}_epoch_{next_epoch}.md"
        return next_epoch, latest_md, source_json, active_json, rendered_md

    # Default to Epoch 1 starting from base worldmap.md
    default_md = artifacts_dir / f"{base_name}.md"
    default_json = artifacts_dir / f"{base_name}.json"
    if not default_md.exists():
        raise FileNotFoundError(
            f"Initial world map markdown not found at {default_md}. "
            "Run the Architect first to generate the primordial map."
        )

    return (
        1,
        default_md,
        default_json,
        artifacts_dir / f"{base_name}_epoch_1.json",
        artifacts_dir / f"{base_name}_epoch_1.md",
    )


class WorldStateSnapshot:
    """Encapsulates the active world state snapshot JSON and provides bound CRUD tools for the LLM."""

    def __init__(self, json_path: Path, data: dict[str, Any], epoch: int = 1) -> None:
        self.json_path = Path(json_path)
        self.data = data
        self.epoch = epoch
        self.data["epoch"] = epoch
        self.data.setdefault("features", {})
        if "timeline" not in self.data:
            if "current_events" in self.data:
                self.data["timeline"] = [self.data.pop("current_events")]
            else:
                self.data["timeline"] = []
        elif isinstance(self.data["timeline"], str):
            self.data["timeline"] = [self.data["timeline"]]
        self.mutations_log: list[str] = []
        self.save()

    @classmethod
    def from_source_file(
        cls, source_json_path: Path, active_json_path: Path, epoch: int = 1
    ) -> "WorldStateSnapshot":
        """Loads data from source JSON and initializes active JSON copy on disk."""
        source_path = Path(source_json_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source world map JSON file not found at: {source_path}")

        data = json.loads(source_path.read_text(encoding="utf-8"))
        if "timeline" not in data and "current_events" in data:
            data["timeline"] = [data.pop("current_events")]
        elif "timeline" not in data:
            data["timeline"] = []
        active_path = Path(active_json_path)
        active_path.parent.mkdir(parents=True, exist_ok=True)
        return cls(json_path=active_path, data=data, epoch=epoch)

    def advance_epoch(self, next_epoch: int, next_json_path: Path) -> None:
        """Transitions this snapshot to a new epoch, persisting state to the next snapshot JSON."""
        self.epoch = next_epoch
        self.json_path = Path(next_json_path)
        self.data["epoch"] = next_epoch
        self.mutations_log = []
        self.save()

    def save(self) -> None:
        """Persists current state to the active JSON snapshot file."""
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def synthesize_fallback_timeline_entry(self, epoch: int) -> str:
        """Synthesizes an authoritative ## Epoch <N> timeline entry from mutations_log and active features."""
        lines = [f"## Epoch {epoch}: The Unfolding Age\n"]
        features = self.data.get("features", {})
        created_lines = []

        for log in self.mutations_log:
            if "[SUCCESS] Created feature" in log:
                m = re.search(r"Created feature '([^']+)'", log)
                if m:
                    fkey = m.group(1)
                    feat = features.get(fkey, {})
                    fname = feat.get("name", fkey)
                    fchar = feat.get("char", "?")
                    tiles = feat.get("tiles", [])
                    pos_str = f"at {tiles[0]}" if len(tiles) == 1 else (f"{tiles[0]} <---> {tiles[-1]}" if len(tiles) > 1 else "")
                    desc = feat.get("description", f"Established during Epoch {epoch}.")
                    created_lines.append(f"- **{fname} ({fchar}) {pos_str}:** {desc}")
            elif "[SUCCESS] Updated feature" in log:
                m = re.search(r"Updated feature '([^']+)'", log)
                if m:
                    fkey = m.group(1)
                    feat = features.get(fkey, {})
                    fname = feat.get("name", fkey)
                    fchar = feat.get("char", "?")
                    desc = feat.get("description", f"Upgraded or transformed during Epoch {epoch}.")
                    created_lines.append(f"- **{fname} ({fchar}):** {desc}")
            elif any(sub in log for sub in ("[SUCCESS] Expanded domain", "[SUCCESS] Cleared", "[SUCCESS] Engineered waterworks", "[SUCCESS] Abandoned")):
                clean_log = re.sub(r"^\[SUCCESS\]\s*", "", log).strip()
                created_lines.append(f"- **Territorial Evolution:** {clean_log}")
            elif "[SUCCESS] Updated Region" in log:
                clean_log = re.sub(r"^\[SUCCESS\]\s*", "", log).strip()
                created_lines.append(f"- **Region Lore Mutation:** {clean_log}")

        if not created_lines:
            lines.append("- *(Peaceful era with no territorial or landmark mutations)*")
        else:
            lines.extend(created_lines)

        return "\n".join(lines)

    def append_timeline_entry(self, epoch: int, content: str) -> None:
        """Appends an epoch entry to the growing chronological # Timeline, deduplicating and sorting."""
        clean_content = content.strip()
        if not clean_content:
            return
        # Strip any redundant top-level '# Timeline' header
        clean_content = re.sub(r"^#\s+Timeline\s*\n*", "", clean_content).strip()

        # Ensure the entry starts with ## Epoch header if missing
        if not re.match(r"^##\s+Epoch\b", clean_content, re.IGNORECASE):
            clean_content = f"## Epoch {epoch}\n{clean_content}"

        timeline_list = self.data.setdefault("timeline", [])
        if not isinstance(timeline_list, list):
            timeline_list = [str(timeline_list)]
            self.data["timeline"] = timeline_list

        # Deduplicate or replace if an entry for this epoch already exists
        epoch_pat = rf"^##\s+Epoch\s+{epoch}\b"
        replaced = False
        for idx, item in enumerate(timeline_list):
            if isinstance(item, str) and re.search(epoch_pat, item, re.MULTILINE | re.IGNORECASE):
                timeline_list[idx] = clean_content
                replaced = True
                break

        if not replaced:
            timeline_list.append(clean_content)

        # Keep timeline entries sorted by epoch number
        def _get_epoch_key(entry: Any) -> int:
            if isinstance(entry, dict):
                return int(entry.get("epoch", 999999))
            m = re.search(r"##\s+Epoch\s+(\d+)", str(entry), re.IGNORECASE)
            return int(m.group(1)) if m else 999999

        timeline_list.sort(key=_get_epoch_key)
        self.save()

    def has_timeline_entry(self, epoch: int) -> bool:
        """Checks if a timeline entry for the given epoch already exists in this snapshot."""
        timeline_list = self.data.get("timeline", [])
        if not isinstance(timeline_list, list):
            return False
        epoch_pat = rf"^##\s+Epoch\s+{epoch}\b"
        for item in timeline_list:
            if isinstance(item, str) and re.search(epoch_pat, item, re.MULTILINE | re.IGNORECASE):
                return True
            elif isinstance(item, dict) and item.get("epoch") == epoch:
                return True
        return False

    def render_and_save_md(self, md_path: Path, timeline_entry: Optional[str] = None) -> Path:
        """Renders the snapshot to LLM-readable Markdown companion with growing # Timeline and writes to disk."""
        entry_text = str(timeline_entry).strip() if timeline_entry is not None else ""
        if not entry_text and self.mutations_log and not self.has_timeline_entry(self.epoch):
            entry_text = self.synthesize_fallback_timeline_entry(epoch=self.epoch)

        if entry_text:
            self.append_timeline_entry(epoch=self.epoch, content=entry_text)

        md_file = Path(md_path)
        md_content = format_world_for_llm(self.data)
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text(md_content, encoding="utf-8")
        return md_file

    def _get_tile_info(self, x: int, y: int) -> tuple[str, str, str]:
        """Returns (terrain_char, region_id, region_name) for a coordinate."""
        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        regions = self.data.get("regions", {})

        t_char = terrain[y][x] if 0 <= y < len(terrain) and 0 <= x < len(terrain[y]) else "?"
        r_id = region[y][x] if 0 <= y < len(region) and 0 <= x < len(region[y]) else "?"
        r_name = regions.get(r_id, {}).get("name", f"Region {r_id}")
        return t_char, r_id, r_name

    def _validate_feature_terrain(
        self,
        fid: str,
        fchar: str,
        ftype: str,
        tiles: list[list[int]],
    ) -> Optional[str]:
        """Validates feature placement against natural terrain and existing landmarks.

        Returns an actionable prescriptive rejection message if invalid, or None if valid.
        """
        terrain = self.data.get("terrain_grid", [])
        features = self.data.get("features", {})
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        # Character validation
        VALID_FEATURE_CHARS = {"o", "O", "!", "+", "=", "*"}
        fchar_clean = str(fchar).strip()[0] if fchar and str(fchar).strip() else ""
        if not fchar_clean or fchar_clean not in VALID_FEATURE_CHARS:
            return (
                f"[REJECTION] Feature '{fid}' has invalid or missing char='{fchar}'. "
                f"char is required and must be one of 'o' (outpost/village/fort), 'O' (city/citadel/fortress), "
                f"'!' (hostile lair/dungeon/ruin), '+' (road), '=' (bridge), or '*' (masonry dam/barrier)."
            )

        # 1. Road Validation ('+')
        if fchar_clean == "+":
            water_coords: list[list[int]] = []
            chasm_coords: list[list[int]] = []
            peak_coords: list[list[int]] = []
            bridge_overlaps: list[tuple[list[int], str]] = []

            for pt in tiles:
                x, y = pt[0], pt[1]
                t_char = terrain[y][x] if 0 <= y < height and 0 <= x < width else "?"
                if t_char == "~":
                    water_coords.append(pt)
                elif t_char == "/":
                    chasm_coords.append(pt)
                elif t_char == "^":
                    peak_coords.append(pt)

                # Check for collision with existing bridge
                for existing_id, feat in features.items():
                    if existing_id == fid:
                        continue
                    if feat.get("char") == "=" or feat.get("type", "").lower() in ("bridge", "viaduct"):
                        ex_tiles = feat.get("tiles", [])
                        if pt in ex_tiles:
                            bridge_overlaps.append((pt, feat.get("name", existing_id)))

            if bridge_overlaps:
                pt, bname = bridge_overlaps[0]
                return (
                    f"[REJECTION] Road '{fid}' includes coordinate {pt} which is already assigned to bridge '{bname}'. "
                    f"Roads must terminate at the bridge approach rather than overlapping bridge coordinates."
                )

            if water_coords:
                first_water = water_coords[0]
                last_water = water_coords[-1]
                bridge_str = (
                    f"spanning all water tiles {water_coords}"
                    if len(water_coords) > 1
                    else f"across water tile {first_water}"
                )
                return (
                    f"[REJECTION] Road '{fid}' attempts to cross water tile(s) '~' without a bridge at {water_coords}.\n"
                    f"Actionable 3-Step Remedy:\n"
                    f"1. Terminate this road at the near bank (before coordinate {first_water}).\n"
                    f"2. Call create_feature to anchor an explicit bridge ('=') {bridge_str}.\n"
                    f"3. Call create_feature to continue the road from the opposite bank (starting after coordinate {last_water})."
                )

            if chasm_coords:
                first_chasm = chasm_coords[0]
                last_chasm = chasm_coords[-1]
                bridge_str = (
                    f"spanning all chasm tiles {chasm_coords}"
                    if len(chasm_coords) > 1
                    else f"across chasm tile {first_chasm}"
                )
                return (
                    f"[REJECTION] Road '{fid}' attempts to cross sheer chasm/cliff tile(s) '/' without a bridge at {chasm_coords}.\n"
                    f"Actionable 3-Step Remedy:\n"
                    f"1. Terminate this road at the near cliff edge (before coordinate {first_chasm}).\n"
                    f"2. Call create_feature to anchor a stone bridge/viaduct ('=') {bridge_str}.\n"
                    f"3. Call create_feature to continue the road from the opposite edge (starting after coordinate {last_chasm})."
                )

            if peak_coords:
                return (
                    f"[REJECTION] Road '{fid}' attempts to traverse impassable alpine mountain peak(s) '^' at {peak_coords}.\n"
                    f"Roads cannot scale sheer mountain peaks. Route through mountain passes, foothills (','), or valleys ('.')."
                )

        # 2. Settlement Validation ('o', 'O')
        elif fchar_clean in ("o", "O"):
            existing_feat = features.get(fid, {})
            existing_tiles = existing_feat.get("tiles", [])
            is_reclaimed_or_existing = (
                fid in features and all(pt in existing_tiles for pt in tiles)
            )

            for pt in tiles:
                x, y = pt[0], pt[1]
                t_char = terrain[y][x] if 0 <= y < height and 0 <= x < width else "?"
                if t_char == "~":
                    return (
                        f"[REJECTION] Settlement '{fid}' cannot be placed on water tile '~' at [{x}, {y}]. "
                        f"Settlements must be founded on dry land: fertile plains ('.'), sheltered coasts (';'), hills (','), or farmlands (':'). "
                        f"For coastal ports, place the settlement on an adjacent coast tile (';') or riverbank ('.')."
                    )
                elif t_char == "/" and not is_reclaimed_or_existing:
                    return (
                        f"[REJECTION] Settlement '{fid}' cannot be placed in a sheer chasm/cliff '/' at [{x}, {y}]. "
                        f"Found settlements on stable, habitable terrain."
                    )
                elif t_char == "^" and not is_reclaimed_or_existing:
                    return (
                        f"[REJECTION] Settlement '{fid}' cannot be placed atop an impassable mountain peak '^' at [{x}, {y}]. "
                        f"Place mountain outposts and mining camps in surrounding foothills (',') or valleys ('.')."
                    )

        # 3. Bridge Validation ('=')
        elif fchar_clean == "=":
            # Check contiguity for multi-tile bridges
            for i in range(1, len(tiles)):
                if max(abs(tiles[i][0] - tiles[i - 1][0]), abs(tiles[i][1] - tiles[i - 1][1])) > 1:
                    return (
                        f"[REJECTION] Bridge '{fid}' coordinates are not contiguous: tile {tiles[i - 1]} and "
                        f"tile {tiles[i]} have a gap. Bridges must form an unbroken sequence of adjacent coordinates."
                    )

            invalid_tiles = []
            barrier_tiles = []
            for pt in tiles:
                x, y = pt[0], pt[1]
                t_char = terrain[y][x] if 0 <= y < height and 0 <= x < width else "?"
                if t_char in ("~", "/", ";"):
                    barrier_tiles.append(pt)
                else:
                    invalid_tiles.append((pt, t_char))

            if invalid_tiles:
                pts = [lt[0] for lt in invalid_tiles]
                chars = [lt[1] for lt in invalid_tiles]
                if barrier_tiles:
                    return (
                        f"[REJECTION] Bridge '{fid}' at {tiles} extends past the barrier onto terrestrial land tile(s): {pts} ({chars}). "
                        f"Bridge tiles ('=') must strictly span the natural barrier ('~', ';', or '/'). "
                        f"Constrain the bridge strictly to barrier tiles: tiles={barrier_tiles}. "
                        f"For terrestrial approach paths between the bridgehead and inland settlements, use an overland road ('+')."
                    )
                else:
                    return (
                        f"[REJECTION] Bridge '{fid}' at {tiles} is situated entirely on dry land ({chars}). "
                        f"Bridges must span a natural water barrier ('~', ';') or chasm ('/'). "
                        f"Use a road ('+') for terrestrial overland routes."
                    )

            # Bank-to-bank reach validation for water, shallows, and chasm barriers
            def _is_water(pt: list[int] | tuple[int, int]) -> bool:
                px, py = pt[0], pt[1]
                return 0 <= py < height and 0 <= px < width and terrain[py][px] in ("~", ";")

            def _is_non_water(pt: list[int] | tuple[int, int]) -> bool:
                px, py = pt[0], pt[1]
                return 0 <= py < height and 0 <= px < width and terrain[py][px] not in ("~", ";")

            def _is_chasm(pt: list[int] | tuple[int, int]) -> bool:
                px, py = pt[0], pt[1]
                return 0 <= py < height and 0 <= px < width and terrain[py][px] == "/"

            def _is_non_chasm(pt: list[int] | tuple[int, int]) -> bool:
                px, py = pt[0], pt[1]
                return 0 <= py < height and 0 <= px < width and terrain[py][px] not in ("/", "~", ";")

            water_pts = [pt for pt in tiles if _is_water(pt)]
            if water_pts:
                tile_set = {(p[0], p[1]) for p in tiles}
                if len(tiles) == 1:
                    bx, by = tiles[0][0], tiles[0][1]
                    if _is_water((bx, by)):
                        w_land, e_land = _is_non_water((bx - 1, by)), _is_non_water((bx + 1, by))
                        n_land, s_land = _is_non_water((bx, by - 1)), _is_non_water((bx, by + 1))
                        # Single-tile bridge must connect two opposing non-water banks
                        if not ((w_land and e_land) or (n_land and s_land)):
                            cardinals = [
                                ((-1, 0), (1, 0), "East", "West"),
                                ((1, 0), (-1, 0), "West", "East"),
                                ((0, -1), (0, 1), "South", "North"),
                                ((0, 1), (0, -1), "North", "South"),
                            ]
                            for (dbx, dby), (dcx, dcy), fwd_name, back_name in cardinals:
                                if _is_non_water((bx + dbx, by + dby)) and _is_water((bx + dcx, by + dcy)):
                                    needed = [[bx, by]]
                                    cx, cy = bx + dcx, by + dcy
                                    while _is_water((cx, cy)):
                                        needed.append([cx, cy])
                                        cx += dcx
                                        cy += dcy
                                    return (
                                        f"[REJECTION] Bridge '{fid}' at {tiles} does not reach the opposite bank! "
                                        f"Anchored on the {back_name} bank at [{bx + dbx}, {by + dby}], but terminates in open water or shallows to the {fwd_name} at [{bx + dcx}, {by + dcy}]. "
                                        f"To span this waterway, define the bridge across all water/shallows tiles: tiles={needed} reaching the {fwd_name} bank at [{cx}, {cy}]."
                                    )
                            return (
                                f"[REJECTION] Bridge '{fid}' at {tiles} is situated on water/shallows but does not span between two opposing land banks. "
                                f"Bridges must reach from bank to bank across the water or shallows."
                            )
                else:
                    p_start = tiles[0]
                    p_end = tiles[-1]
                    v_start = (tiles[0][0] - tiles[1][0], tiles[0][1] - tiles[1][1])
                    v_end = (tiles[-1][0] - tiles[-2][0], tiles[-1][1] - tiles[-2][1])

                    # Check forward endpoint
                    if _is_water(p_end) and v_end != (0, 0):
                        next_pt = (p_end[0] + v_end[0], p_end[1] + v_end[1])
                        if _is_water(next_pt) and next_pt not in tile_set:
                            needed = list(tiles)
                            cx, cy = next_pt
                            while _is_water((cx, cy)):
                                needed.append([cx, cy])
                                cx += v_end[0]
                                cy += v_end[1]
                            return (
                                f"[REJECTION] Bridge '{fid}' endpoint {p_end} terminates in open water or shallows! "
                                f"The waterway continues to [{p_end[0] + v_end[0]}, {p_end[1] + v_end[1]}]. "
                                f"Extend the bridge to tiles={needed} to reach the opposite bank at [{cx}, {cy}]."
                            )

                    # Check backward start endpoint
                    if _is_water(p_start) and v_start != (0, 0):
                        prev_pt = (p_start[0] + v_start[0], p_start[1] + v_start[1])
                        if _is_water(prev_pt) and prev_pt not in tile_set:
                            needed_rev = []
                            cx, cy = prev_pt
                            while _is_water((cx, cy)):
                                needed_rev.append([cx, cy])
                                cx += v_start[0]
                                cy += v_start[1]
                            needed = list(reversed(needed_rev)) + list(tiles)
                            return (
                                f"[REJECTION] Bridge '{fid}' start {p_start} terminates in open water or shallows! "
                                f"The waterway continues to [{p_start[0] + v_start[0]}, {p_start[1] + v_start[1]}]. "
                                f"Extend the bridge to tiles={needed} to reach the near bank at [{cx}, {cy}]."
                            )

            chasm_pts = [pt for pt in tiles if _is_chasm(pt)]
            if chasm_pts and not water_pts:
                tile_set = {(p[0], p[1]) for p in tiles}
                if len(tiles) == 1:
                    bx, by = tiles[0][0], tiles[0][1]
                    if _is_chasm((bx, by)):
                        w_land, e_land = _is_non_chasm((bx - 1, by)), _is_non_chasm((bx + 1, by))
                        n_land, s_land = _is_non_chasm((bx, by - 1)), _is_non_chasm((bx, by + 1))
                        if not ((w_land and e_land) or (n_land and s_land)):
                            cardinals = [
                                ((-1, 0), (1, 0), "East", "West"),
                                ((1, 0), (-1, 0), "West", "East"),
                                ((0, -1), (0, 1), "South", "North"),
                                ((0, 1), (0, -1), "North", "South"),
                            ]
                            for (dbx, dby), (dcx, dcy), fwd_name, back_name in cardinals:
                                if _is_non_chasm((bx + dbx, by + dby)) and _is_chasm((bx + dcx, by + dcy)):
                                    needed = [[bx, by]]
                                    cx, cy = bx + dcx, by + dcy
                                    while _is_chasm((cx, cy)):
                                        needed.append([cx, cy])
                                        cx += dcx
                                        cy += dcy
                                    return (
                                        f"[REJECTION] Viaduct '{fid}' at {tiles} does not reach the opposite cliff edge! "
                                        f"Anchored on the {back_name} cliff at [{bx + dbx}, {by + dby}], but terminates in a sheer chasm to the {fwd_name} at [{bx + dcx}, {by + dcy}]. "
                                        f"To span this chasm, define the viaduct across all chasm tiles: tiles={needed} reaching the {fwd_name} edge at [{cx}, {cy}]."
                                    )
                else:
                    p_start = tiles[0]
                    p_end = tiles[-1]
                    v_start = (tiles[0][0] - tiles[1][0], tiles[0][1] - tiles[1][1])
                    v_end = (tiles[-1][0] - tiles[-2][0], tiles[-1][1] - tiles[-2][1])

                    # Check forward endpoint
                    if _is_chasm(p_end) and v_end != (0, 0):
                        next_pt = (p_end[0] + v_end[0], p_end[1] + v_end[1])
                        if _is_chasm(next_pt) and next_pt not in tile_set:
                            needed = list(tiles)
                            cx, cy = next_pt
                            while _is_chasm((cx, cy)):
                                needed.append([cx, cy])
                                cx += v_end[0]
                                cy += v_end[1]
                            return (
                                f"[REJECTION] Viaduct '{fid}' endpoint {p_end} terminates in a sheer chasm! "
                                f"The chasm continues to [{p_end[0] + v_end[0]}, {p_end[1] + v_end[1]}]. "
                                f"Extend the viaduct to tiles={needed} to reach the opposite edge at [{cx}, {cy}]."
                            )

                    # Check backward start endpoint
                    if _is_chasm(p_start) and v_start != (0, 0):
                        prev_pt = (p_start[0] + v_start[0], p_start[1] + v_start[1])
                        if _is_chasm(prev_pt) and prev_pt not in tile_set:
                            needed_rev = []
                            cx, cy = prev_pt
                            while _is_chasm((cx, cy)):
                                needed_rev.append([cx, cy])
                                cx += v_start[0]
                                cy += v_start[1]
                            needed = list(reversed(needed_rev)) + list(tiles)
                            return (
                                f"[REJECTION] Viaduct '{fid}' start {p_start} terminates in a sheer chasm! "
                                f"The chasm continues to [{p_start[0] + v_start[0]}, {p_start[1] + v_start[1]}]. "
                                f"Extend the viaduct to tiles={needed} to reach the near edge at [{cx}, {cy}]."
                            )

        # 4. Dungeon / Landmark Validation ('!')
        elif fchar_clean == "!":
            for pt in tiles:
                x, y = pt[0], pt[1]
                t_char = terrain[y][x] if 0 <= y < height and 0 <= x < width else "?"
                if t_char == "~" and not any(
                    sub in ftype.lower() or sub in fid.lower()
                    for sub in ("sunken", "submerged", "drowned", "water", "sea")
                ):
                    return (
                        f"[REJECTION] Landmark '{fid}' is placed on water tile '~' at [{x}, {y}]. "
                        f"Unless explicitly a sunken ruin or submerged shrine (with 'sunken' or 'submerged' in feature_type), "
                        f"place dungeons on land: deep forests ('&', '#'), peaks ('^'), bogs ('%'), wastelands ('*'), or cliffs ('/')."
                    )

        # 5. Dam / Barrier Validation ('*')
        elif fchar_clean == "*":
            for pt in tiles:
                x, y = pt[0], pt[1]
                t_char = terrain[y][x] if 0 <= y < height and 0 <= x < width else "?"
                if t_char not in ("*", "~", ";", "."):
                    return (
                        f"[REJECTION] Dam/barrier feature '{fid}' at [{x}, {y}] is placed on invalid terrain '{t_char}'. "
                        f"Dams and masonry barriers must be situated on masonry ('*') or waterways ('~', ';')."
                    )

        return None

    # =========================================================================
    # FEATURE CRUD TOOLS (BOUND TO THIS ACTIVE SNAPSHOT)
    # =========================================================================

    def create_feature(
        self,
        feature_id: str,
        name: str,
        char: str,
        feature_type: str,
        tiles: list[list[int]],
        description: str = "",
    ) -> str:
        """Creates a new landmark, road, bridge, or dam on the world map.

        Args:
            feature_id: Unique slug identifier (e.g. 'oakhaven', 'kings_road', 'high_dam').
            name: Display name (e.g. 'Oakhaven', "King's Road", 'High Dam').
            char: Symbol: 'o' (outpost/fort), 'O' (city/citadel), '!' (lair/dungeon), '+' (road), '=' (bridge), '*' (dam/barrier).
            feature_type: Semantic category (e.g. 'settlement', 'city', 'citadel', 'dungeon', 'road', 'bridge', 'dam').
            tiles: List of [x, y] coordinates (0..31). Single-tile features use [[x, y]], routes use [[x1, y1], [x2, y2], ...].
            description: Optional lore, founding history, or significance.

        Returns:
            Confirmation string detailing created feature and underlying terrain.
        """
        fid = str(feature_id).strip().lower().replace(" ", "_")
        if not fid:
            err = "Error: feature_id cannot be empty."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        features = self.data.setdefault("features", {})
        if fid in features:
            existing = features[fid]
            err = (
                f"Error: Feature '{fid}' already exists ('{existing.get('name')}'). "
                "Use update_feature to modify it, or choose a unique feature_id."
            )
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        norm_tiles = _normalize_tiles(tiles)
        if not norm_tiles:
            err = "Error: tiles must contain at least one valid [x, y] coordinate."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        # Validate coordinate boundaries (32x32)
        terrain = self.data.get("terrain_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32
        for pt in norm_tiles:
            x, y = pt[0], pt[1]
            if not (0 <= x < width and 0 <= y < height):
                err = (
                    f"Error: Coordinate [{x}, {y}] is out of bounds. "
                    f"Valid map coordinates are X: 0..{width-1}, Y: 0..{height-1}."
                )
                print(f"  -> {err}", flush=True)
                raise ToolRejectionError(err)

        fchar = str(char).strip()[0] if char and str(char).strip() else ""
        if fchar not in ("o", "O", "!", "+", "=", "*"):
            err = (
                f"Error: char is required and must be one of 'o', 'O', '!', '+', '=', '*' (got '{char}')."
            )
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)
        ftype = str(feature_type).strip() if feature_type and str(feature_type).strip() else "feature"
        fname = str(name).strip() or fid
        fdesc = str(description).strip()

        # Validate feature placement against terrain barriers and existing infrastructure
        rejection = self._validate_feature_terrain(
            fid=fid,
            fchar=fchar,
            ftype=ftype,
            tiles=norm_tiles,
        )
        if rejection:
            print(f"  -> {rejection}", flush=True)
            raise ToolRejectionError(rejection)

        features[fid] = {
            "name": fname,
            "char": fchar,
            "type": ftype,
            "tiles": norm_tiles,
            "description": fdesc,
        }
        self.save()

        # Build informative feedback with underlying biomes
        if len(norm_tiles) == 1:
            t_char, r_id, r_name = self._get_tile_info(norm_tiles[0][0], norm_tiles[0][1])
            info = f"Ground: '{t_char}', Biome: Region '{r_id}' ({r_name})"
        else:
            info = f"{len(norm_tiles)} tiles spanning from {norm_tiles[0]} to {norm_tiles[-1]}"

        msg = (
            f"[SUCCESS] Created feature '{fid}' (Name: '{fname}', Char: '{fchar}', "
            f"Type: '{ftype}') at coordinates {norm_tiles}. {info}"
        )
        self.mutations_log.append(msg)
        print(f"  -> {msg}", flush=True)
        return msg

    def read_feature(self, feature_id: str = "") -> str:
        """Reads details for a registered feature, or lists all registered features.

        Args:
            feature_id: Feature identifier to inspect, or ''/'all' to list all features.

        Returns:
            Feature details, coordinates, and geography, or feature listing.
        """
        features = self.data.get("features", {})
        fid = str(feature_id).strip().lower().replace(" ", "_") if feature_id else ""

        if not fid or fid in ("all", "*", "list"):
            if not features:
                return "No features currently registered in this world snapshot."
            lines = [f"Total registered features: {len(features)}"]
            for k, f in sorted(features.items()):
                tiles = f.get("tiles", [])
                pos_str = f"at {tiles}" if len(tiles) <= 3 else f"{len(tiles)} tiles ({tiles[0]}..{tiles[-1]})"
                lines.append(f"- ID '{k}': '{f.get('name')}' ['{f.get('char')}'] ({f.get('type')}) {pos_str}")
            return "\n".join(lines)

        match_key = None
        for k in features:
            if k.lower() == fid:
                match_key = k
                break

        if not match_key:
            return (
                f"Feature '{feature_id}' not found in current snapshot. "
                f"Registered features: {list(features.keys())}"
            )

        feat = deepcopy(features[match_key])
        # Enrich with coordinate biome inspections
        geo_info = []
        for pt in feat.get("tiles", []):
            t_char, r_id, r_name = self._get_tile_info(pt[0], pt[1])
            geo_info.append({"coord": pt, "terrain": t_char, "region_id": r_id, "region_name": r_name})
        feat["geography"] = geo_info
        return json.dumps({match_key: feat}, indent=2)

    def update_feature(
        self,
        feature_id: str,
        char: str,
        name: str = "",
        feature_type: str = "",
        tiles: list[list[int]] | None = None,
        description: str = "",
    ) -> str:
        """Updates an existing feature on the world map.

        Args:
            feature_id: Unique identifier of the feature to update.
            char: Target symbol ('o', 'O', '!', '+', '=', '*'). Pass new symbol to alter state (e.g. ruin or promote), or current symbol to keep unchanged.
            name: New display name (leave empty to keep current).
            feature_type: Optional updated category (e.g. 'city', 'outpost', 'ruin', 'road', 'dam').
            tiles: New list of [x, y] coordinates if position changed or road extended (leave empty to keep current).
            description: Updated chronicle note or description (leave empty to keep current).

        Returns:
            Confirmation string detailing changes made.
        """
        features = self.data.setdefault("features", {})
        fid = str(feature_id).strip().lower().replace(" ", "_")

        match_key = None
        for k in features:
            if k.lower() == fid:
                match_key = k
                break

        if not match_key:
            err = (
                f"Error: Feature '{feature_id}' not found. Cannot update non-existent feature. "
                f"Registered features: {list(features.keys())}"
            )
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        feat = features[match_key]
        old_char = str(feat.get("char", "o"))
        old_name = str(feat.get("name", match_key))
        old_type = str(feat.get("type", "")).lower()
        changes: list[str] = []

        proposed_char = str(char).strip()[:1] if char and str(char).strip() else ""
        if proposed_char not in ("o", "O", "!", "+", "=", "*"):
            err = (
                f"Error: char is required when updating feature '{feature_id}'. "
                f"Must be one of 'o', 'O', '!', '+', '=', '*' (got '{char}')."
            )
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        proposed_type = str(feature_type).strip() if feature_type and str(feature_type).strip() else feat.get("type", "feature")
        proposed_tiles = feat.get("tiles") or ([feat["pos"]] if "pos" in feat else [])

        if tiles is not None and len(tiles) > 0:
            norm_tiles = _normalize_tiles(tiles)
            terrain = self.data.get("terrain_grid", [])
            height = len(terrain)
            width = len(terrain[0]) if height > 0 else 32
            for pt in norm_tiles:
                if not (0 <= pt[0] < width and 0 <= pt[1] < height):
                    err = (
                        f"Error: Coordinate [{pt[0]}, {pt[1]}] is out of bounds "
                        f"(X: 0..{width-1}, Y: 0..{height-1})."
                    )
                    print(f"  -> {err}", flush=True)
                    raise ToolRejectionError(err)
            proposed_tiles = norm_tiles

        # Validate updated feature placement against terrain
        rejection = self._validate_feature_terrain(
            fid=match_key,
            fchar=proposed_char,
            ftype=proposed_type,
            tiles=proposed_tiles,
        )
        if rejection:
            print(f"  -> {rejection}", flush=True)
            raise ToolRejectionError(rejection)

        if name and str(name).strip():
            feat["name"] = str(name).strip()
            changes.append(f"name='{feat['name']}'")

        if proposed_char != old_char:
            feat["char"] = proposed_char
            changes.append(f"char='{old_char}' -> '{proposed_char}'")

        if feature_type and proposed_type.lower() != old_type:
            feat["type"] = proposed_type
            changes.append(f"type='{old_type}' -> '{proposed_type}'")

        if tiles is not None and len(tiles) > 0:
            feat["tiles"] = proposed_tiles
            changes.append(f"tiles={proposed_tiles}")

        if description and str(description).strip():
            feat["description"] = str(description).strip()
            changes.append("description updated")

        self.save()
        change_summary = ", ".join(changes) if changes else "no fields modified"
        msg = f"[SUCCESS] Updated feature '{match_key}': {change_summary}."

        # Proactive Road Lore Synchronization Note
        # If a landmark underwent a status transition (dungeon <-> settlement/city),
        # detect connected roads/bridges whose descriptions still reflect previous lore.
        status_transition = (
            (old_char == "!" and proposed_char in ("o", "O"))
            or (old_char in ("o", "O") and proposed_char == "!")
        )
        if status_transition:
            target_tiles = feat.get("tiles", proposed_tiles)
            target_coords = [(t[0], t[1]) for t in target_tiles if isinstance(t, (list, tuple))]

            unupdated_roads = []
            for r_id, r_feat in features.items():
                if r_id == match_key or not isinstance(r_feat, dict):
                    continue
                r_char = str(r_feat.get("char", ""))
                r_type = str(r_feat.get("type", "")).lower()
                if r_char not in ("+", "=") and r_type not in (
                    "road", "bridge", "highway", "trail", "path", "viaduct"
                ):
                    continue
                r_tiles = [(t[0], t[1]) for t in r_feat.get("tiles", []) if isinstance(t, (list, tuple))]
                if not r_tiles:
                    continue
                endpoints = [r_tiles[0], r_tiles[-1]]
                if any(
                    any(max(abs(ep[0] - tc[0]), abs(ep[1] - tc[1])) <= 1 for tc in target_coords)
                    for ep in endpoints
                ):
                    r_desc = str(r_feat.get("description", ""))
                    r_name = str(r_feat.get("name", r_id))
                    if (feat["name"].lower() not in r_desc.lower()) or (old_name.lower() in r_desc.lower()):
                        unupdated_roads.append((r_id, r_name))

            if unupdated_roads:
                road_hints = ", ".join(f"'{rid}' ({rname})" for rid, rname in unupdated_roads)
                if proposed_char in ("o", "O"):
                    action_desc = f"reconsecrated/settled (from dungeon '{old_name}' to settlement '{feat['name']}')"
                    tone_desc = "safe trade, pilgrim, or travel highway to the new settlement"
                else:
                    action_desc = f"fallen into ruin/dungeon (from settlement '{old_name}' to ruin '{feat['name']}')"
                    tone_desc = "perilous, abandoned, or ominous trail leading to the ruins"

                msg += (
                    f"\n[NOTE] Landmark was {action_desc}. "
                    f"Connected road/bridge infrastructure [{road_hints}] still reflects previous lore. "
                    f"Please call update_feature on connected road(s) to update their description ({tone_desc})!"
                )

        self.mutations_log.append(msg)
        print(f"  -> {msg}", flush=True)
        return msg

    def delete_feature(self, feature_id: str) -> str:
        """Deletes/removes an existing feature from the world map.

        Args:
            feature_id: Unique identifier of the feature to delete.

        Returns:
            A confirmation string confirming removal.
        """
        features = self.data.setdefault("features", {})
        fid = str(feature_id).strip().lower().replace(" ", "_")

        match_key = None
        for k in features:
            if k.lower() == fid:
                match_key = k
                break

        if not match_key:
            err = (
                f"Error: Feature '{feature_id}' not found. Cannot delete non-existent feature. "
                f"Registered features: {list(features.keys())}"
            )
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        deleted = features.pop(match_key)
        self.save()
        msg = (
            f"[SUCCESS] Deleted feature '{match_key}' ('{deleted.get('name')}'). "
            f"Remaining registered features: {len(features)}."
        )
        self.mutations_log.append(msg)
        print(f"  -> {msg}", flush=True)
        return msg

    # =========================================================================
    # SEMANTIC TERRAFORMING & DUAL-GRID MUTATION TOOLS
    # =========================================================================

    def expand_domain(
        self,
        center: list[int],
        radius: int,
        domain_type: str,
        region_name: str,
        region_id: str,
        lore: str = "",
    ) -> str:
        """Expands a territorial domain (farmland, wasteland, forest) around a center point.

        Waterways ('~', ';') and chasms ('/') are automatically shielded and preserved.

        Args:
            center: [x, y] epicenter coordinate (e.g. settlement or ruin).
            radius: Expansion radius in tiles (1 to 5).
            domain_type: Domain type ('farmland' -> ':', 'wasteland' -> '*', 'forest' -> '#').
            region_name: Display name of the domain (e.g. 'Oakhaven Farmlands').
            region_id: Single-character ID for region_grid (e.g. 'h', 'w').
            lore: Optional narrative lore describing this domain.

        Returns:
            Confirmation message detailing modified tiles and preserved terrain.
        """
        if not center or len(center) < 2:
            err = "Error: center must be an [x, y] coordinate pair."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)
        cx, cy = int(center[0]), int(center[1])
        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        if not (0 <= cx < width and 0 <= cy < height):
            err = f"Error: Center coordinate [{cx}, {cy}] is out of bounds."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        reg_key = str(region_id).strip()[:1]
        if not reg_key:
            err = "Error: region_id must be a non-empty single character."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        dtype = str(domain_type).strip().lower()
        if any(sub in dtype for sub in ("farm", "agrarian", "crop", "polder")):
            target_char = ":"
            reg_type = "farmland"
        elif any(sub in dtype for sub in ("waste", "blight", "ash", "corrupt", "cursed")):
            target_char = "*"
            reg_type = "wasteland"
        elif any(sub in dtype for sub in ("forest", "wood", "jungle", "sylvan", "grove")):
            target_char = "#"
            reg_type = "forest"
        else:
            target_char = ":"
            reg_type = dtype or "domain"

        # Register or update region in regions dict
        r_name = str(region_name).strip()
        regions_dict = self.data.setdefault("regions", {})
        existing_reg = regions_dict.get(reg_key, {}) if isinstance(regions_dict.get(reg_key), dict) else {}
        is_existing_biome = (
            bool(existing_reg)
            and any(
                region[y][x] == reg_key
                for y in range(height)
                for x in range(width)
            )
        )

        if is_existing_biome:
            existing_name = existing_reg.get("name", f"Region {reg_key}")
            existing_type = existing_reg.get("type", "wilderness").lower()
            # Valid expansion if:
            # - region_name matches existing_name (case-insensitive) or region_name is omitted
            # - OR existing_type is already a domain type compatible with this expansion
            # - OR existing_type matches reg_type
            is_valid_expansion = (
                (not r_name or r_name.lower() == existing_name.lower())
                or (existing_type in ("farmland", "wasteland", "forest", "domain") and reg_type in ("farmland", "wasteland", "forest", "domain"))
                or (existing_type == reg_type)
            )
            if not is_valid_expansion:
                err = (
                    f"[REJECTION] Region ID '{reg_key}' is already occupied by established biome '{existing_name}' ({existing_type}). "
                    f"To register '{r_name or f'Domain {reg_key}'}' as a new distinct domain, provide an UNUSED single-character region ID. "
                    f"To expand an existing domain, pass its matching name or omit region_name."
                )
                print(f"  -> {err}", flush=True)
                raise ToolRejectionError(err)

            if not r_name:
                r_name = existing_name
            if existing_type in ("farmland", "wasteland", "forest", "domain"):
                reg_type = existing_type
        else:
            if not r_name:
                r_name = f"Domain {reg_key}"

        reg_entry = {
            "name": r_name,
            "type": reg_type,
        }
        if lore and str(lore).strip():
            reg_entry["lore"] = str(lore).strip()
        elif "lore" in existing_reg:
            reg_entry["lore"] = existing_reg["lore"]
        regions_dict[reg_key] = reg_entry

        r = max(1, min(int(radius), 8))
        tg = [list(row) for row in terrain]
        rg = [list(row) for row in region]

        features = self.data.get("features", {})
        bridge_coords = {
            tuple(pt)
            for feat in features.values()
            if isinstance(feat, dict) and (feat.get("char") == "=" or feat.get("type") in ("bridge", "viaduct"))
            for pt in feat.get("tiles", [])
            if isinstance(pt, (list, tuple)) and len(pt) >= 2
        }

        modified_coords = []
        preserved_water = []

        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy > r * r + r:
                    continue
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue

                curr_t = tg[ny][nx]
                # River Shield: Never overwrite natural water tiles or coastal shallows
                if curr_t in ("~", ";"):
                    preserved_water.append([nx, ny])
                    continue
                # Shield bridges
                if (nx, ny) in bridge_coords:
                    continue
                # Shield alpine peaks and sheer chasms/cliffs from farming
                if target_char == ":" and curr_t in ("^", "/"):
                    continue

                tg[ny][nx] = target_char
                rg[ny][nx] = reg_key
                modified_coords.append([nx, ny])

        self.data["terrain_grid"] = ["".join(row) for row in tg]
        self.data["region_grid"] = ["".join(row) for row in rg]
        self.save()

        msg = (
            f"[SUCCESS] Expanded domain '{reg_key}' ('{r_name}', type: '{reg_type}', char: '{target_char}') "
            f"around [{cx}, {cy}] (radius {r}): modified {len(modified_coords)} land tiles. "
            f"Preserved {len(preserved_water)} water tiles."
        )
        self.mutations_log.append(msg)
        print(f"  -> {msg}", flush=True)
        return msg

    def clear_land(
        self,
        coords: list[list[int]],
        target_terrain: str = ".",
        domain_region_id: str = "",
        new_domain_name: str = "",
        new_domain_id: str = "",
        new_domain_lore: str = "",
    ) -> str:
        """Clears vegetation or obstacles into usable plains ('.') or farmlands (':').

        Converts woods ('#', '&'), bogs ('%'), or scrub (',') to plains or farms. Plains ('.') may be cleared to farmland (':'). Water ('~', ';') and peaks ('^', '/') are rejected.

        Args:
            coords: List of [x, y] coordinates to clear.
            target_terrain: Ground type after clearing: '.' for open plains, ':' for farmland.
            domain_region_id: Optional existing region ID (e.g. 'h') to assign cleared tiles to.
            new_domain_name: Optional name if establishing a new domain.
            new_domain_id: Single-character ID if establishing a new domain.
            new_domain_lore: Optional narrative lore for the cleared territory.

        Returns:
            Confirmation message detailing cleared tiles and assigned region.
        """
        norm_coords = _normalize_tiles(coords)
        if not norm_coords:
            err = "Error: coords must contain at least one valid [x, y] coordinate."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        t_target = str(target_terrain).strip()[:1] if target_terrain and str(target_terrain).strip() in (".", ":", "*", ",") else "."

        # Check bounds and terrain validity
        water_tiles = []
        impassable_tiles = []
        redundant_tiles = []
        for pt in norm_coords:
            x, y = pt[0], pt[1]
            if not (0 <= x < width and 0 <= y < height):
                err = f"Error: Coordinate [{x}, {y}] is out of bounds."
                print(f"  -> {err}", flush=True)
                raise ToolRejectionError(err)
            curr_t = terrain[y][x]
            if curr_t in ("~", ";"):
                water_tiles.append(pt)
            elif curr_t in ("^", "/"):
                impassable_tiles.append((pt, curr_t))
            elif curr_t == "." and t_target != ":":
                redundant_tiles.append(pt)

        if water_tiles:
            rejection = (
                f"[REJECTION] clear_land cannot be used on natural water tiles ('~' or ';') at {water_tiles}.\n"
                f"To dam, drain, or reclaim waterways into dry land, use engineer_waterworks(action='dam' or 'drain')."
            )
            print(f"  -> {rejection}", flush=True)
            raise ToolRejectionError(rejection)

        if impassable_tiles:
            rejection = (
                f"[REJECTION] clear_land cannot be used on impassable mountain peaks ('^') or sheer chasms/cliffs ('/') at "
                f"{[pt for pt, _ in impassable_tiles]}. Clearable terrain includes forests ('#'), dense forests ('&'), "
                f"wetlands ('%'), and scrublands (',') (or open plains ('.') when converting to farmland (':'))."
            )
            print(f"  -> {rejection}", flush=True)
            raise ToolRejectionError(rejection)

        if redundant_tiles:
            rejection = (
                f"[REJECTION] clear_land called on open plains ('.') at {redundant_tiles} with target_terrain='{t_target}'. "
                f"Clearing open plains to open plains is redundant. Open plains ('.') may only be cleared when target_terrain=':' (farmland)."
            )
            print(f"  -> {rejection}", flush=True)
            raise ToolRejectionError(rejection)

        # Determine target region
        reg_key = "0"
        if new_domain_name and new_domain_id:
            reg_key = str(new_domain_id).strip()[:1]
            regions_dict = self.data.setdefault("regions", {})
            existing_reg = regions_dict.get(reg_key, {}) if isinstance(regions_dict.get(reg_key), dict) else {}
            is_existing_biome = (
                bool(existing_reg)
                and any(
                    region[y][x] == reg_key
                    for y in range(height)
                    for x in range(width)
                )
            )
            r_name = str(new_domain_name).strip()
            reg_type = "farmland" if t_target == ":" else "cleared_land"

            if is_existing_biome:
                existing_name = existing_reg.get("name", f"Region {reg_key}")
                existing_type = existing_reg.get("type", "wilderness").lower()
                is_valid_expansion = (
                    (not r_name or r_name.lower() == existing_name.lower())
                    or (existing_type in ("farmland", "wasteland", "forest", "domain", "cleared_land") and reg_type in ("farmland", "wasteland", "forest", "domain", "cleared_land"))
                    or (existing_type == reg_type)
                )
                if not is_valid_expansion:
                    err = (
                        f"[REJECTION] Region ID '{reg_key}' is already occupied by established biome '{existing_name}' ({existing_type}). "
                        f"To clear land for '{r_name or f'Domain {reg_key}'}' as a new distinct domain, provide an UNUSED single-character region ID. "
                        f"To expand an existing domain, pass its matching name or use domain_region_id."
                    )
                    print(f"  -> {err}", flush=True)
                    raise ToolRejectionError(err)

                if not r_name:
                    r_name = existing_name
                if existing_type in ("farmland", "wasteland", "forest", "domain", "cleared_land"):
                    reg_type = existing_type

            reg_entry = {
                "name": r_name,
                "type": reg_type,
            }
            if new_domain_lore and str(new_domain_lore).strip():
                reg_entry["lore"] = str(new_domain_lore).strip()
            elif "lore" in existing_reg:
                reg_entry["lore"] = existing_reg["lore"]
            regions_dict[reg_key] = reg_entry
        elif domain_region_id and domain_region_id.strip()[:1] in self.data.get("regions", {}):
            reg_key = domain_region_id.strip()[:1]
        elif t_target == ":":
            reg_key = domain_region_id.strip()[:1] if domain_region_id else "0"

        tg = [list(row) for row in terrain]
        rg = [list(row) for row in region]

        for pt in norm_coords:
            x, y = pt[0], pt[1]
            tg[y][x] = t_target
            rg[y][x] = reg_key

        self.data["terrain_grid"] = ["".join(row) for row in tg]
        self.data["region_grid"] = ["".join(row) for row in rg]
        self.save()

        reg_name = self.data.get("regions", {}).get(reg_key, {}).get("name", f"Region {reg_key}")
        msg = (
            f"[SUCCESS] Cleared {len(norm_coords)} tile(s) to '{t_target}' "
            f"assigned to region '{reg_key}' ({reg_name})."
        )
        self.mutations_log.append(msg)
        print(f"  -> {msg}", flush=True)
        return msg

    def _detect_downstream_tiles(
        self,
        dam_coords: list[list[int]],
        river_reg_id: str,
        explicit_downstream: Optional[list[list[int]]] = None,
    ) -> list[list[int]]:
        """Detects and returns downstream river tiles from a dam.

        Traces connected river tiles belonging to river_reg_id outward from dam_coords.
        Identifies the downstream branch flowing toward the ocean, bay, coast, swamp,
        or lowlands, and returns the tiles ordered sequentially from dam to mouth.
        """
        if explicit_downstream:
            return _normalize_tiles(explicit_downstream)

        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        regions = self.data.get("regions", {})
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        dam_set = {(p[0], p[1]) for p in dam_coords}

        # 1. Collect all river/waterway tiles matching this region
        river_tiles = set()
        for y in range(height):
            for x in range(width):
                if region[y][x] == river_reg_id and terrain[y][x] in ("~", ";"):
                    river_tiles.add((x, y))

        remaining = river_tiles - dam_set
        if not remaining:
            return []

        # 2. Find adjacent river neighbors of the dam
        neighbors: list[tuple[int, int]] = []
        for bx, by in dam_set:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = bx + dx, by + dy
                if (nx, ny) in remaining and (nx, ny) not in neighbors:
                    neighbors.append((nx, ny))

        if not neighbors:
            return []

        # 3. Explore connected components for each neighbor
        def score_component(comp: set[tuple[int, int]]) -> float:
            score = 0.0
            for cx, cy in comp:
                for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ax, ay = cx + ddx, cy + ddy
                    if 0 <= ax < width and 0 <= ay < height:
                        adj_t = terrain[ay][ax]
                        adj_r = region[ay][ax]
                        adj_rtype = regions.get(adj_r, {}).get("type", "").lower()
                        if adj_rtype in ("ocean", "bay") or (adj_t == "~" and adj_r != river_reg_id):
                            score += 50.0
                        elif adj_rtype == "swamp" or adj_t == "%":
                            score += 25.0
                        elif adj_t == ";":
                            score += 15.0
                        elif adj_rtype == "mountains" or adj_t == "^":
                            score -= 30.0
                        elif adj_t == "/":
                            score -= 15.0
                        elif adj_t == ".":
                            score += 5.0
                if cx == 0 or cx == width - 1 or cy == 0 or cy == height - 1:
                    score += 20.0
                # In typical fantasy maps, rivers flow south/downward toward lower basin
                score += cy * 0.5
            return score

        components: list[tuple[tuple[int, int], set[tuple[int, int]], float]] = []
        visited_global: set[tuple[int, int]] = set()

        for start_node in neighbors:
            if start_node in visited_global:
                continue
            comp: set[tuple[int, int]] = set()
            queue = [start_node]
            comp.add(start_node)
            visited_global.add(start_node)

            while queue:
                curr = queue.pop(0)
                cx, cy = curr
                for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + ddx, cy + ddy
                    if (nx, ny) in remaining and (nx, ny) not in comp:
                        comp.add((nx, ny))
                        visited_global.add((nx, ny))
                        queue.append((nx, ny))

            s = score_component(comp)
            components.append((start_node, comp, s))

        if not components:
            return []

        # Highest score indicates downstream towards ocean/lowlands
        components.sort(key=lambda x: x[2], reverse=True)
        best_start, best_comp, _ = components[0]

        # 4. BFS from best_start to order tiles from near-dam to far-mouth
        ordered_downstream: list[list[int]] = []
        bfs_visited = {best_start}
        bfs_queue = [best_start]

        while bfs_queue:
            curr = bfs_queue.pop(0)
            ordered_downstream.append([curr[0], curr[1]])
            cx, cy = curr
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + ddx, cy + ddy
                if (nx, ny) in best_comp and (nx, ny) not in bfs_visited:
                    bfs_visited.add((nx, ny))
                    bfs_queue.append((nx, ny))

        return ordered_downstream

    def _find_canal_path(
        self,
        destination: list[int],
        source: list[int],
        max_length: int = 50,
    ) -> list[list[int]]:
        """Finds an optimal 4-cardinal path carving from destination to a source waterbody using A* pathfinding.

        Curves around settlements ('o', 'O'), dungeons ('!'), dams ('*'), bridges ('='), and mountain peaks ('^').
        Penalizes difficult terrain (cliffs have high cost, plains have low cost).
        Terminates upon reaching the source coordinate or any contiguous tile of the source's water region.
        """
        dest_x, dest_y = int(destination[0]), int(destination[1])
        src_x, src_y = int(source[0]), int(source[1])

        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        if not (0 <= dest_x < width and 0 <= dest_y < height):
            raise ToolRejectionError(f"[REJECTION] Destination coordinate [{dest_x}, {dest_y}] is out of bounds.")
        if not (0 <= src_x < width and 0 <= src_y < height):
            raise ToolRejectionError(f"[REJECTION] Source coordinate [{src_x}, {src_y}] is out of bounds.")

        # Identify source water region. If source tile itself isn't water, check if adjacent to water.
        src_reg_id = region[src_y][src_x]
        if terrain[src_y][src_x] not in ("~", ";"):
            found_water = None
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = src_x + ddx, src_y + ddy
                if 0 <= nx < width and 0 <= ny < height and terrain[ny][nx] in ("~", ";"):
                    found_water = (nx, ny)
                    src_reg_id = region[ny][nx]
                    break
            if not found_water:
                raise ToolRejectionError(
                    f"[REJECTION] Source coordinate [{src_x}, {src_y}] is situated on dry land ('{terrain[src_y][src_x]}'). "
                    f"Source must be an existing waterbody tile ('~' or ';') or directly adjacent to one."
                )
            src_x, src_y = found_water

        # 1. Collect protected landmark tiles (cannot be excavated/flooded)
        protected_tiles = set()
        features = self.data.get("features", {})
        for feat in features.values():
            if not isinstance(feat, dict):
                continue
            fchar = feat.get("char", "")
            ftype = feat.get("type", "")
            if fchar in ("+",) or ftype in ("road", "highway", "trail"):
                continue  # Roads can be crossed/dredged
            tiles = feat.get("tiles") or ([feat["pos"]] if "pos" in feat else [])
            for pt in tiles:
                protected_tiles.add((pt[0], pt[1]))

        dest_is_landmark = (dest_x, dest_y) in protected_tiles

        # 2. A* Priority Queue: (f_score, cost_so_far, (cx, cy), path)
        open_set: list[tuple[float, float, tuple[int, int], list[tuple[int, int]]]] = []
        h_start = float(abs(dest_x - src_x) + abs(dest_y - src_y))
        heapq.heappush(open_set, (h_start, 0.0, (dest_x, dest_y), [(dest_x, dest_y)]))
        visited: dict[tuple[int, int], float] = {}

        while open_set:
            f, cost, (cx, cy), path = heapq.heappop(open_set)

            # Check if current tile connects to source waterbody
            is_goal = False
            if (cx, cy) == (src_x, src_y):
                is_goal = True
            elif (cx, cy) != (dest_x, dest_y) and terrain[cy][cx] in ("~", ";") and region[cy][cx] == src_reg_id:
                is_goal = True

            if is_goal:
                # Extract path tiles that need excavation
                excavated: list[list[int]] = []
                for px, py in path:
                    if (px, py) == (dest_x, dest_y) and dest_is_landmark:
                        continue
                    if terrain[py][px] in ("~", ";") and region[py][px] == src_reg_id:
                        continue
                    excavated.append([px, py])
                return excavated

            if (cx, cy) in visited and visited[(cx, cy)] <= cost:
                continue
            visited[(cx, cy)] = cost

            if len(path) > max_length:
                continue

            # Expand 4-cardinal neighbors strictly (prevents diagonal water pinches)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                # Cannot dig through protected landmarks
                if (nx, ny) in protected_tiles and (nx, ny) != (dest_x, dest_y):
                    continue

                t = terrain[ny][nx]
                if t == "^":  # Mountain peaks are strictly impassable
                    continue

                # Excavation terrain weights
                if t in ("~", ";") and region[ny][nx] == src_reg_id:
                    step_cost = 0.5  # Docking into target water is encouraged
                elif t in (".", "%"):
                    step_cost = 1.0  # Soft ground / wetlands
                elif t in (",", "#", "&", ":"):
                    step_cost = 2.0  # Hills, timberlands, farmlands
                elif t == "/":
                    step_cost = 4.0  # Cliffs require rock-sapping / blasting powder
                else:
                    step_cost = 2.5

                new_cost = cost + step_cost
                h = float(abs(nx - src_x) + abs(ny - src_y))
                heapq.heappush(open_set, (new_cost + h, new_cost, (nx, ny), path + [(nx, ny)]))

        raise ToolRejectionError(
            f"[REJECTION] Could not find a viable canal route from destination [{dest_x}, {dest_y}] "
            f"to source waterbody [{src_x}, {src_y}]. Path is blocked by impassable mountain peaks ('^') "
            f"or landmarks, or exceeds maximum length of {max_length} tiles."
        )

    def _find_bridge_for_severed_road(
        self,
        road_tiles_original: list[list[int]],
        cut_coords: list[list[int]],
    ) -> Optional[list[list[int]]]:
        """Finds a validated bridge span ('=') to reconnect a severed road across the canal.

        Evaluates multiple strategies:
        1. Direct span using the exact cut tiles (in original or reversed order).
        2. Single-tile bridge at any cut tile, prioritized by proximity to the road banks.
        3. Straight-line bank-to-bank span originating from the remaining road bank endpoints.
        4. Perpendicular canal crossings centered at the cut tiles.
        5. BFS shortest water path between adjacent banks of bank_a and bank_b.
        All candidates are verified against _validate_feature_terrain to guarantee compliance.
        """
        terrain = self.data.get("terrain_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        def _is_water(pt: list[int] | tuple[int, int]) -> bool:
            px, py = pt[0], pt[1]
            return 0 <= py < height and 0 <= px < width and terrain[py][px] in ("~", ";")

        def _is_land(pt: list[int] | tuple[int, int]) -> bool:
            px, py = pt[0], pt[1]
            return 0 <= py < height and 0 <= px < width and terrain[py][px] not in ("~", ";", "/")

        cut_set = {(p[0], p[1]) for p in cut_coords}

        # Identify contiguous runs of cut tiles in original road sequence
        runs: list[list[list[int]]] = []
        current_run: list[list[int]] = []
        for pt in road_tiles_original:
            if (pt[0], pt[1]) in cut_set:
                current_run.append(pt)
            else:
                if current_run:
                    runs.append(current_run)
                    current_run = []
        if current_run:
            runs.append(current_run)

        for run in runs:
            # 1. Try exact cut run (original or reversed order)
            for candidate in [run, list(reversed(run))]:
                if self._validate_feature_terrain("test_bridge", "=", "bridge", candidate) is None:
                    return candidate

            # Locate road banks right before and after the cut
            first_idx = road_tiles_original.index(run[0])
            last_idx = road_tiles_original.index(run[-1])
            bank_a = road_tiles_original[first_idx - 1] if first_idx > 0 else None
            bank_b = road_tiles_original[last_idx + 1] if last_idx + 1 < len(road_tiles_original) else None

            # 2. Try single-tile bridge at cut tiles, prioritized by proximity to road banks
            run_sorted = sorted(
                run,
                key=lambda pt: min(
                    abs(pt[0] - (bank_a[0] if bank_a else pt[0])) + abs(pt[1] - (bank_a[1] if bank_a else pt[1])),
                    abs(pt[0] - (bank_b[0] if bank_b else pt[0])) + abs(pt[1] - (bank_b[1] if bank_b else pt[1])),
                ),
            )
            for pt in run_sorted:
                candidate = [pt]
                if self._validate_feature_terrain("test_bridge", "=", "bridge", candidate) is None:
                    return candidate

            # 3. Try straight-line bank-to-bank crossings from bank_a or bank_b
            banks_to_try = [b for b in (bank_a, bank_b) if b and _is_land(b)]
            for b in banks_to_try:
                bx, by = b[0], b[1]
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = bx + dx, by + dy
                    if _is_water((nx, ny)):
                        span = []
                        cx, cy = nx, ny
                        while _is_water((cx, cy)):
                            span.append([cx, cy])
                            cx += dx
                            cy += dy
                        if span and _is_land((cx, cy)):
                            if self._validate_feature_terrain("test_bridge", "=", "bridge", span) is None:
                                return span
                            rev_span = list(reversed(span))
                            if self._validate_feature_terrain("test_bridge", "=", "bridge", rev_span) is None:
                                return rev_span

            # 4. Perpendicular crossing across the canal from cut tiles
            for pt in run:
                px, py = pt[0], pt[1]
                for (dx1, dy1), (dx2, dy2) in [((0, -1), (0, 1)), ((-1, 0), (1, 0))]:
                    span = [pt]
                    cx, cy = px + dx1, py + dy1
                    while _is_water((cx, cy)):
                        span.insert(0, [cx, cy])
                        cx += dx1
                        cy += dy1
                    cx, cy = px + dx2, py + dy2
                    while _is_water((cx, cy)):
                        span.append([cx, cy])
                        cx += dx2
                        cy += dy2
                    if self._validate_feature_terrain("test_bridge", "=", "bridge", span) is None:
                        return span

            # 5. BFS shortest water path between adjacent banks of bank_a and bank_b
            if bank_a and bank_b and _is_land(bank_a) and _is_land(bank_b):
                target_set = {
                    (bank_b[0] + dx, bank_b[1] + dy)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
                    if _is_water((bank_b[0] + dx, bank_b[1] + dy))
                }
                start_points = [
                    (bank_a[0] + dx, bank_a[1] + dy)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
                    if _is_water((bank_a[0] + dx, bank_a[1] + dy))
                ]
                for sp in start_points:
                    queue = deque([(sp, [[sp[0], sp[1]]])])
                    visited = {sp}
                    while queue:
                        curr, path = queue.popleft()
                        if curr in target_set:
                            for cand in [path, list(reversed(path))]:
                                if self._validate_feature_terrain("test_bridge", "=", "bridge", cand) is None:
                                    return cand
                        if len(path) >= 8:
                            continue
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                            nxt = (curr[0] + dx, curr[1] + dy)
                            if nxt not in visited and _is_water(nxt):
                                visited.add(nxt)
                                queue.append((nxt, path + [[nxt[0], nxt[1]]]))

        return None

    def engineer_waterworks(
        self,
        coords: Optional[list[list[int]]] = None,
        action: str = "canal",
        destination: Optional[list[int]] = None,
        source: Optional[list[int]] = None,
        waterway_name: str = "",
        waterway_region_id: str = "",
        waterway_lore: str = "",
        dam_name: str = "",
        dam_lore: str = "",
        river_lore: str = "",
        target_terrain: str = "",
        target_region_id: str = "",
        downstream_coords: Optional[list[list[int]]] = None,
    ) -> str:
        """Alters waterways: carves canals, builds river dams, drains wetlands, or floods reservoirs.

        Actions:
        - 'canal': Carves water channel ('~') connecting inland 'destination' to waterbody 'source'.
        - 'dam': Erects masonry barrage ('*') across river 'coords' and reduces downstream flow.
        - 'drain': Reclaims water/wetland at 'coords' into dry ground ('.' plains, ':' farmlands).
        - 'flood': Expands water body or reservoir across 'coords'.

        Args:
            action: One of 'canal', 'dam', 'drain', or 'flood'.
            destination: [x, y] inland start coordinate for 'canal'.
            source: [x, y] target waterbody coordinate for 'canal'.
            coords: List of [x, y] tiles for 'dam', 'drain', or 'flood'. Dams must cross water.
            waterway_name: Display name for new canal/waterway (leave empty to extend source biome).
            waterway_region_id: Unused 1-char ID for named canal, or existing source ID if extending.
            waterway_lore: Narrative lore for the canal or reservoir.
            dam_name: Display name of the dam (e.g. 'Highwall Barrage').
            dam_lore: Narrative lore describing the dam barrier.
            river_lore: Optional updated lore for the dammed river.
            target_terrain: Ground type for drain or dam ('.' plains, ':' farmland, '*' masonry).
            target_region_id: Land region ID for reclaimed tiles (defaults to '0' wilderness).
            downstream_coords: Optional explicit downstream tiles to mutate to ';' (auto-detected if omitted).

        Returns:
            Confirmation message detailing modified tiles, features, and updated regions.
        """
        act = str(action).strip().lower()
        if act not in ("dam", "drain", "canal", "flood"):
            err = "Error: action must be one of 'dam', 'drain', 'canal', or 'flood'."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        regions = self.data.get("regions", {})
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        # Coordinate resolution: A* pathfinding for 'canal' when destination and source are supplied
        norm_dest = _normalize_tiles(destination) if destination else []
        norm_src = _normalize_tiles(source) if source else []

        if act == "canal" and norm_dest and norm_src:
            norm_coords = self._find_canal_path(norm_dest[0], norm_src[0])
            if not norm_coords:
                return f"[SUCCESS] Destination [{norm_dest[0][0]}, {norm_dest[0][1]}] is already adjacent to water body [{norm_src[0][0]}, {norm_src[0][1]}]."
        else:
            norm_coords = _normalize_tiles(coords)
            if not norm_coords:
                if act == "canal":
                    err = "Error: For action='canal', must provide 'destination' and 'source' coordinates (or explicit 'coords')."
                else:
                    err = f"Error: coords must contain at least one valid [x, y] coordinate for action='{act}'."
                print(f"  -> {err}", flush=True)
                raise ToolRejectionError(err)

        for pt in norm_coords:
            x, y = pt[0], pt[1]
            if not (0 <= x < width and 0 <= y < height):
                err = f"Error: Coordinate [{x}, {y}] is out of bounds."
                print(f"  -> {err}", flush=True)
                raise ToolRejectionError(err)

        tg = [list(row) for row in terrain]
        rg = [list(row) for row in region]

        if act == "dam":
            water_coords = [pt for pt in norm_coords if tg[pt[1]][pt[0]] in ("~", ";")]
            if not water_coords:
                err = (
                    f"[REJECTION] engineer_waterworks(action='dam') must cross at least one waterway tile ('~' or ';'). "
                    f"Coordinates {norm_coords} contain only dry land terrain."
                )
                print(f"  -> {err}", flush=True)
                raise ToolRejectionError(err)

            # 1. Identify primary river region from the water coordinates (not dry land banks)
            water_reg_candidates = [rg[pt[1]][pt[0]] for pt in water_coords]
            river_reg_id = water_reg_candidates[0]
            for r_id in water_reg_candidates:
                r_type = regions.get(r_id, {}).get("type", "").lower()
                if r_type in ("river", "water", "lake", "bay", "ocean") or r_id != "0":
                    river_reg_id = r_id
                    break

            river_info = regions.get(river_reg_id, {})
            river_name = river_info.get("name", f"Region {river_reg_id}")

            t_ground = target_terrain.strip()[:1] if target_terrain and target_terrain.strip() in (".", ":", "*", ",") else "*"

            water_coords_set = {(pt[0], pt[1]) for pt in water_coords}
            for pt in norm_coords:
                x, y = pt[0], pt[1]
                tg[y][x] = t_ground
                if target_region_id and target_region_id.strip():
                    rg[y][x] = target_region_id.strip()[:1]
                else:
                    if (x, y) in water_coords_set:
                        rg[y][x] = river_reg_id
                    # Dry land banks retain their existing region rg[y][x]

            # 2. Register Feature of type 'dam' with char '*'
            d_name = dam_name.strip() if dam_name and dam_name.strip() else f"{river_name} Dam"
            d_lore = dam_lore.strip() if dam_lore and dam_lore.strip() else f"An engineered heavy stone masonry dam impounding the {river_name}."

            first_x, first_y = norm_coords[0][0], norm_coords[0][1]
            fid = re.sub(r'[^a-z0-9_]', '', d_name.lower().replace(" ", "_").replace("'", "").replace("-", "_"))
            if not fid:
                fid = f"dam_{first_x}_{first_y}"

            features_dict = self.data.setdefault("features", {})
            if fid in features_dict and features_dict[fid].get("tiles") != norm_coords:
                fid = f"{fid}_{first_x}_{first_y}"

            features_dict[fid] = {
                "name": d_name,
                "char": "*",
                "type": "dam",
                "tiles": norm_coords,
                "description": d_lore,
            }

            # 3. Update the lore of the river being dammed
            dam_notice = f"Dammed by {d_name} at coordinates {norm_coords}, significantly reducing downstream flow into shallow flats and sandbanks."
            if river_reg_id in regions:
                curr_lore = regions[river_reg_id].get("lore", "").strip()
                if river_lore and river_lore.strip():
                    regions[river_reg_id]["lore"] = river_lore.strip()
                else:
                    if dam_notice not in curr_lore:
                        regions[river_reg_id]["lore"] = f"{curr_lore} {dam_notice}".strip() if curr_lore else dam_notice

            # 4. Mutate 50% of the tiles downstream into ';'
            downstream_tiles = self._detect_downstream_tiles(
                dam_coords=norm_coords,
                river_reg_id=river_reg_id,
                explicit_downstream=downstream_coords,
            )
            mutated_downstream = []
            for i, pt in enumerate(downstream_tiles):
                if i % 2 == 0:  # 50% alternating along flow
                    dx, dy = pt[0], pt[1]
                    if tg[dy][dx] == "~":
                        tg[dy][dx] = ";"
                        mutated_downstream.append(pt)

            self.data["terrain_grid"] = ["".join(row) for row in tg]
            self.data["region_grid"] = ["".join(row) for row in rg]
            self.save()

            assigned_reg = target_region_id.strip()[:1] if target_region_id and target_region_id.strip() else river_reg_id
            msg = (
                f"[SUCCESS] Engineered waterworks (dam): erected '{d_name}' ['*'] across {len(norm_coords)} tile(s) "
                f"at {norm_coords} in region '{assigned_reg}' ({river_name}). "
                f"Registered dam feature and updated river lore. "
                f"Downstream flow reduced: mutated {len(mutated_downstream)}/{len(downstream_tiles)} "
                f"downstream water tile(s) into shallow sandbanks (';')."
            )
            self.mutations_log.append(msg)
            print(f"  -> {msg}", flush=True)
            return msg

        elif act == "drain":
            # Validate that target coordinates are actually water or wetland
            invalid_drain = [pt for pt in norm_coords if tg[pt[1]][pt[0]] not in ("~", ";", "%")]
            if invalid_drain:
                err = (
                    f"[REJECTION] engineer_waterworks(action='drain') can only be applied to water ('~'), "
                    f"shallows (';'), or wetland ('%') tiles. Non-water tiles at {invalid_drain} cannot be drained. "
                    f"To clear overland vegetation, use clear_land."
                )
                print(f"  -> {err}", flush=True)
                raise ToolRejectionError(err)

            # Converting water -> dry land / reclaimed polders
            t_ground = target_terrain.strip()[:1] if target_terrain and target_terrain.strip() in (".", ":", "*", ",") else "."
            land_reg = target_region_id.strip()[:1] if target_region_id and target_region_id.strip() else "0"

            # Guard against phantom river bug: verify land_reg is NOT a water-type region!
            existing_reg_type = regions.get(land_reg, {}).get("type", "").lower()
            if existing_reg_type in ("river", "ocean", "lake", "bay", "water"):
                land_reg = "0"

            for pt in norm_coords:
                x, y = pt[0], pt[1]
                tg[y][x] = t_ground
                rg[y][x] = land_reg

            self.data["terrain_grid"] = ["".join(row) for row in tg]
            self.data["region_grid"] = ["".join(row) for row in rg]
            self.save()

            reg_name = regions.get(land_reg, {}).get("name", "Unnamed Wilderness")
            msg = (
                f"[SUCCESS] Engineered waterworks (drain): converted {len(norm_coords)} water tile(s) to "
                f"dry ground '{t_ground}' assigned to land region '{land_reg}' ({reg_name})."
            )
            self.mutations_log.append(msg)
            print(f"  -> {msg}", flush=True)
            return msg

        else:  # canal or flood (land -> water)
            w_id = waterway_region_id.strip()[:1] if waterway_region_id and waterway_region_id.strip() else "F"
            w_name = str(waterway_name).strip()
            w_type = "river" if act == "canal" else "lake"

            regions_dict = self.data.setdefault("regions", {})
            norm_coord_set = {(p[0], p[1]) for p in norm_coords}
            existing_reg = regions_dict.get(w_id)

            # Check if w_id is already occupied by an established region painted on the map
            is_existing_biome = (
                isinstance(existing_reg, dict)
                and any(
                    rg[y][x] == w_id
                    for y in range(height)
                    for x in range(width)
                    if (x, y) not in norm_coord_set
                )
            )

            if is_existing_biome:
                existing_name = existing_reg.get("name", f"Region {w_id}")
                # Case A: Extending existing water body (waterway_name omitted or matching)
                if not w_name or w_name.lower() == existing_name.lower():
                    if waterway_lore and str(waterway_lore).strip():
                        curr_l = str(existing_reg.get("lore", "")).strip()
                        new_l = str(waterway_lore).strip()
                        if new_l not in curr_l:
                            existing_reg["lore"] = f"{curr_l} {new_l}".strip() if curr_l else new_l
                    w_name = existing_name
                    w_type = existing_reg.get("type", w_type)
                else:
                    # Case B: Rejection - attempting to overwrite an established region with a new distinct waterway
                    err = (
                        f"[REJECTION] Region ID '{w_id}' is already occupied by established biome '{existing_name}' ({existing_reg.get('type')}). "
                        f"To register '{w_name}' as a new distinct waterway, provide an UNUSED single-character region ID. "
                        f"To extend '{existing_name}', omit waterway_name."
                    )
                    print(f"  -> {err}", flush=True)
                    raise ToolRejectionError(err)
            else:
                reg_name = w_name or ("Constructed Canal" if act == "canal" else "Flooded Basin")
                regions_dict[w_id] = {
                    "name": reg_name,
                    "type": w_type,
                    "lore": str(waterway_lore).strip() if waterway_lore and str(waterway_lore).strip() else f"Constructed {act} waterway.",
                }
                w_name = reg_name

            for pt in norm_coords:
                x, y = pt[0], pt[1]
                tg[y][x] = "~"
                rg[y][x] = w_id

            self.data["terrain_grid"] = ["".join(row) for row in tg]
            self.data["region_grid"] = ["".join(row) for row in rg]

            # Detect and handle road features severed by the excavated water
            severed_road_notes = []
            features_dict = self.data.setdefault("features", {})
            norm_coord_set = {(p[0], p[1]) for p in norm_coords}

            for r_id, r_feat in list(features_dict.items()):
                if not isinstance(r_feat, dict):
                    continue
                r_char = str(r_feat.get("char", ""))
                r_type = str(r_feat.get("type", "")).lower()
                if r_char != "+" and r_type not in ("road", "highway", "trail", "path"):
                    continue

                r_tiles = r_feat.get("tiles", [])
                cut_tiles = [pt for pt in r_tiles if (pt[0], pt[1]) in norm_coord_set]
                if not cut_tiles:
                    continue

                r_name = str(r_feat.get("name", r_id))
                orig_tiles = [list(pt) for pt in r_tiles]

                # Prune cut water tiles from road feature so it halts cleanly at the banks
                remaining_tiles = [pt for pt in r_tiles if (pt[0], pt[1]) not in norm_coord_set]
                r_feat["tiles"] = remaining_tiles

                bridge_tiles = self._find_bridge_for_severed_road(
                    road_tiles_original=orig_tiles,
                    cut_coords=cut_tiles,
                )

                bridge_id = re.sub(r'[^a-z0-9_]', '', f"{r_id}_canal_bridge")
                if not bridge_id:
                    bridge_id = f"bridge_{cut_tiles[0][0]}_{cut_tiles[0][1]}"
                if bridge_id in features_dict:
                    bridge_id = f"{bridge_id}_{cut_tiles[0][0]}_{cut_tiles[0][1]}"
                bridge_name = f"{r_name} Canal Bridge"

                if bridge_tiles:
                    bridge_tiles_str = str(bridge_tiles)
                    note = (
                        f"[NOTE] Water excavation severed road '{r_name}' ('{r_id}') at {cut_tiles}. "
                        f"The cut water tile(s) were removed from '{r_id}' so the road halts cleanly at the banks. "
                        f"To reconnect overland trade across the {w_name}, call create_feature with an engineered bridge ('='):\n"
                        f"  -> create_feature(\n"
                        f"         feature_id='{bridge_id}',\n"
                        f"         name='{bridge_name}',\n"
                        f"         char='=',\n"
                        f"         feature_type='bridge',\n"
                        f"         tiles={bridge_tiles_str},\n"
                        f"         description='A stone bridge spanning the {w_name} to reconnect the {r_name}.'\n"
                        f"     )"
                    )
                else:
                    note = (
                        f"[NOTE] Water excavation severed road '{r_name}' ('{r_id}') at {cut_tiles}. "
                        f"The cut water tile(s) were removed from '{r_id}' so the road halts cleanly at the banks. "
                        f"Please call create_feature with char='=' to construct a bridge across the water and restore connectivity."
                    )
                severed_road_notes.append(note)

            self.save()

            if act == "canal" and norm_dest and norm_src:
                msg = (
                    f"[SUCCESS] Engineered waterworks (canal): excavated navigable channel across {len(norm_coords)} tile(s) "
                    f"at {norm_coords} linking destination {norm_dest[0]} to source waterbody {norm_src[0]} "
                    f"under water region '{w_id}' ('{w_name}', type: '{w_type}')."
                )
            else:
                msg = (
                    f"[SUCCESS] Engineered waterworks ({act}): carved {len(norm_coords)} water tile(s) ('~') "
                    f"registered to water region '{w_id}' ('{w_name}', type: '{w_type}')."
                )
            if severed_road_notes:
                msg += "\n" + "\n".join(severed_road_notes)

            self.mutations_log.append(msg)
            print(f"  -> {msg}", flush=True)
            return msg

    def abandon_domain(
        self,
        center: list[int],
        radius: int,
        target_terrain: str = ".",
    ) -> str:
        """Simulates nature reclaiming fallen civilizations or cleansed blights.

        Reverts farmlands (':') or wastelands ('*') to plains ('.') or woods ('#') in Wilderness '0'. Registered features (dams, outposts) and water are preserved.

        Args:
            center: [x, y] coordinate of the abandoned site or epicenter.
            radius: Radius in tiles to dissolve (1 to 5).
            target_terrain: Ground type to revert to ('.' for plains, '#' for woods).

        Returns:
            Confirmation message detailing reclaimed tiles and dissolved regions.
        """
        if not center or len(center) < 2:
            err = "Error: center must be an [x, y] coordinate pair."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)
        cx, cy = int(center[0]), int(center[1])
        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        if not (0 <= cx < width and 0 <= cy < height):
            err = f"Error: Center coordinate [{cx}, {cy}] is out of bounds."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        r = max(1, min(int(radius), 8))
        t_revert = str(target_terrain).strip()[:1] if target_terrain and str(target_terrain).strip() in (".", "#", ",") else "."

        tg = [list(row) for row in terrain]
        rg = [list(row) for row in region]

        # Collect coordinates of registered features to protect them from being dissolved (e.g. dams, outposts, bridges)
        protected_feature_coords = set()
        for f in self.data.get("features", {}).values():
            if isinstance(f, dict):
                f_tiles = f.get("tiles") or ([f["pos"]] if "pos" in f else [])
                for pt in f_tiles:
                    protected_feature_coords.add((pt[0], pt[1]))

        reclaimed_coords = []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy > r * r + r:
                    continue
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue

                if (nx, ny) in protected_feature_coords:
                    continue

                curr_t = tg[ny][nx]
                # Only dissolve farmlands (:) or unfeatured wastelands (*)
                if curr_t in (":", "*"):
                    tg[ny][nx] = t_revert
                    rg[ny][nx] = "0"
                    reclaimed_coords.append([nx, ny])

        self.data["terrain_grid"] = ["".join(row) for row in tg]
        self.data["region_grid"] = ["".join(row) for row in rg]
        self.save()

        msg = (
            f"[SUCCESS] Abandoned domain around [{cx}, {cy}] (radius {r}): "
            f"nature reclaimed {len(reclaimed_coords)} tile(s) to '{t_revert}' (Wilderness Region '0')."
        )
        self.mutations_log.append(msg)
        print(f"  -> {msg}", flush=True)
        return msg

    def update_region(
        self,
        region_id: str,
        lore: str = "",
        name: str = "",
        region_type: str = "",
        description: str = "",
    ) -> str:
        """Updates an existing regional biome's lore, name, or classification.

        Args:
            region_id: Single-character alphanumeric ID of the region to update (e.g. 'I', 'D', '0', 'K').
            lore: Updated narrative lore describing the region's current state, threats, or ecology.
            name: Optional new display name if renamed.
            region_type: Optional updated category (e.g. 'forest', 'wasteland', 'mountains', 'wilderness', 'farmland').
            description: Optional alias for 'lore'.

        Returns:
            Confirmation string detailing the region updates.
        """
        reg_key = str(region_id).strip()[:1]
        if not reg_key:
            err = "Error: region_id cannot be empty."
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        regions = self.data.setdefault("regions", {})
        if reg_key not in regions or not isinstance(regions[reg_key], dict):
            err = (
                f"Error: Region ID '{reg_key}' not found in registered regions. "
                f"Available region IDs: {list(regions.keys())}"
            )
            print(f"  -> {err}", flush=True)
            raise ToolRejectionError(err)

        reg = regions[reg_key]
        changes: list[str] = []

        if name and str(name).strip():
            reg["name"] = str(name).strip()
            changes.append(f"name='{reg['name']}'")

        if region_type and str(region_type).strip():
            reg["type"] = str(region_type).strip().lower()
            changes.append(f"type='{reg['type']}'")

        effective_lore = str(lore).strip() if lore and str(lore).strip() else str(description).strip()
        if effective_lore:
            reg["lore"] = effective_lore
            changes.append("lore updated")

        if not changes:
            return f"Region '{reg_key}' ('{reg.get('name')}') unchanged. Provide lore, name, or region_type to update."

        self.save()
        msg = f"[SUCCESS] Updated Region '{reg_key}' ('{reg.get('name')}'): {', '.join(changes)}."
        self.mutations_log.append(msg)
        print(f"  -> {msg}", flush=True)
        return msg


@dataclass
class HistorianEpochResult:
    """Container for the output of a single Historian epoch turn."""

    epoch: int
    narrative: str
    timeline_entry: str
    input_md_path: Path
    active_json_path: Path
    rendered_md_path: Path
    mutations: list[str] = field(default_factory=list)
    features_count: int = 0
    token_usage: dict[str, int] = field(default_factory=dict)
    regions_history_path: Optional[Path] = None
    api_calls: int = 0
    estimated_cost_usd: float = 0.0
    cumulative_token_usage: dict[str, int] = field(default_factory=dict)
    cumulative_cost_usd: float = 0.0


def calculate_cost(
    model_name: str,
    prompt_tokens: int,
    candidates_tokens: int,
) -> float:
    """Estimates USD cost based on token counts and Gemini model pricing tiers.

    Pricing reference:
    - gemini-3.7-* / gemini-3.8-*:
        $0.75 per 1M prompt tokens ($0.75 / 1_000_000)
        $3.75 per 1M candidate tokens (including thoughts) ($3.75 / 1_000_000)
    - gemini-*-pro (e.g., gemini-2.5-pro, gemini-3.5-pro):
        $1.25 per 1M prompt tokens ($1.25 / 1_000_000)
        $5.00 per 1M candidate tokens ($5.00 / 1_000_000)
    - gemini-*-flash (default e.g., gemini-3.8-flash, gemini-3.6-flash, gemini-2.5-flash):
        $0.50 per 1M prompt tokens ($0.50 / 1_000_000)
        $3.00 per 1M candidate tokens ($3.00 / 1_000_000)
    """
    model = (model_name or "").lower()
    if any(m in model for m in ("3.7", "3.8")):
        input_rate = 0.75 / 1_000_000
        output_rate = 3.75 / 1_000_000
    elif "pro" in model:
        input_rate = 1.25 / 1_000_000
        output_rate = 5.00 / 1_000_000
    else:
        input_rate = 0.50 / 1_000_000
        output_rate = 3.00 / 1_000_000

    return (prompt_tokens * input_rate) + (candidates_tokens * output_rate)


class _UsageTracker:
    """Context manager that intercepts remote Gemini API calls to capture token usage across all AFC hops."""

    def __init__(self, client: Any, model_name: str = "gemini-3.8-flash") -> None:
        self.client = client
        self.model_name = model_name
        self.api_calls: int = 0
        self.prompt_tokens: int = 0
        self.candidates_tokens: int = 0
        self.thoughts_tokens: int = 0
        self.total_tokens: int = 0
        self._orig_method: Any = None
        self._target_attr: Optional[str] = None

    def __enter__(self) -> "_UsageTracker":
        models = getattr(self.client, "models", None)
        if models is not None:
            # Prefer intercepting `_generate_content` which executes for every AFC hop in the SDK
            if hasattr(models, "_generate_content") and callable(getattr(models, "_generate_content")):
                self._target_attr = "_generate_content"
            elif hasattr(models, "generate_content") and callable(getattr(models, "generate_content")):
                self._target_attr = "generate_content"

            if self._target_attr:
                self._orig_method = getattr(models, self._target_attr)

                def _hooked(*args: Any, **kwargs: Any) -> Any:
                    res = self._orig_method(*args, **kwargs)
                    self.record_response(res)
                    return res

                setattr(models, self._target_attr, _hooked)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        models = getattr(self.client, "models", None)
        if models is not None and self._target_attr and self._orig_method:
            setattr(models, self._target_attr, self._orig_method)

    def record_response(self, res: Any) -> None:
        """Records token metrics from a response object or candidate metadata."""
        self.api_calls += 1
        meta = getattr(res, "usage_metadata", None)
        if meta is not None:
            p = getattr(meta, "prompt_token_count", 0)
            c = getattr(meta, "candidates_token_count", 0)
            th = getattr(meta, "thoughts_token_count", 0)
            t = getattr(meta, "total_token_count", 0)

            p_val = p if isinstance(p, int) else 0
            c_val = c if isinstance(c, int) else 0
            th_val = th if isinstance(th, int) else 0
            t_val = t if isinstance(t, int) else (p_val + c_val)

            self.prompt_tokens += p_val
            self.candidates_tokens += c_val
            self.thoughts_tokens += th_val
            self.total_tokens += t_val

    @property
    def usage_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "candidates_tokens": self.candidates_tokens,
            "thoughts_tokens": self.thoughts_tokens,
            "total_tokens": self.total_tokens,
        }

    @property
    def cost_usd(self) -> float:
        return calculate_cost(
            model_name=self.model_name,
            prompt_tokens=self.prompt_tokens,
            candidates_tokens=self.candidates_tokens,
        )


def _extract_response_text(response: Any) -> str:
    """Extracts narrative prose text from response candidate parts."""
    texts: list[str] = []
    if hasattr(response, "candidates") and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        texts.append(text)
    if texts:
        return "\n".join(texts).strip()
    if hasattr(response, "text") and response.text:
        return response.text.strip()
    return ""


class Historian:
    """Stateless Historian agent that chronicles world epochs and mutates map snapshots via feature CRUD tools.

    Runs statelessly without conversational memory between epochs. All temporal context is passed
    via the input markdown file's growing '# Timeline' section, and each run appends the updated
    epoch entry to the output snapshot for subsequent iterations.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.8-flash",
        thinking_level: str = "HIGH",
        client: Optional[genai.Client] = None,
        max_afc_calls: int = 20,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("historian.md")
        self.max_afc_calls = max_afc_calls

        self.snapshot: Optional[WorldStateSnapshot] = None
        self.current_epoch: int = 0
        self.last_md_path: Optional[Path] = None
        self.last_json_path: Optional[Path] = None

        self.token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "total_tokens": 0,
            "thoughts_tokens": 0,
        }
        self.cumulative_usage: dict[str, int] = self.token_usage
        self.cumulative_api_calls: int = 0
        self.cumulative_cost_usd: float = 0.0
        self.last_epoch_usage: dict[str, int] = {}
        self.last_epoch_api_calls: int = 0
        self.last_epoch_cost_usd: float = 0.0

    def _track_usage(self, response: Any) -> None:
        """Records token usage from response metadata into cumulative counters."""
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            p = getattr(meta, "prompt_token_count", 0)
            c = getattr(meta, "candidates_token_count", 0)
            t = getattr(meta, "total_token_count", 0)
            th = getattr(meta, "thoughts_token_count", 0)
            p_val = p if isinstance(p, int) else 0
            c_val = c if isinstance(c, int) else 0
            th_val = th if isinstance(th, int) else 0
            t_val = t if isinstance(t, int) else (p_val + c_val)

            self.token_usage["prompt_tokens"] += p_val
            self.token_usage["candidates_tokens"] += c_val
            self.token_usage["total_tokens"] += t_val
            self.token_usage["thoughts_tokens"] += th_val
            self.cumulative_api_calls += 1
            self.cumulative_cost_usd += calculate_cost(self.model_name, p_val, c_val)

    @retry_with_backoff(max_retries=4, initial_delay=2.0)
    def _execute_turn(self, chat_session: Any, message: str) -> Any:
        """Executes a single turn within the provided chat session with retry backoff."""
        return chat_session.send_message(message)

    def run_epoch(
        self,
        input_md_path: Optional[Union[str, Path]] = None,
        query: str = "",
    ) -> HistorianEpochResult:
        """Runs a single epoch simulation turn statelessly without conversation memory.

        Args:
            input_md_path: Path to input worldmap.md (or previous epoch .md). If None,
                uses the previous turn's output .md or auto-detects from the artifacts directory.
            query: Custom historical prompt/directive for this epoch.

        Returns:
            HistorianEpochResult containing narrative, timeline_entry, mutated paths, and mutation log.
        """
        # 1. Determine input path: if subsequent run and not specified, use last rendered .md
        effective_input = input_md_path
        if effective_input is None and self.last_md_path is not None:
            effective_input = self.last_md_path

        epoch_num, in_md, source_json, active_json, rendered_md = resolve_epoch_paths(
            input_path=effective_input
        )

        print("=" * 80, flush=True)
        print(f" HISTORIAN: CHRONICLE & WORLD MUTATION (EPOCH {epoch_num}) [STATELESS]", flush=True)
        print("=" * 80, flush=True)
        print(f"Input Markdown:        {in_md}", flush=True)
        print(f"Active JSON Snapshot:  {active_json}", flush=True)
        print(f"Rendered Markdown:     {rendered_md}", flush=True)

        # 2. Setup or advance the WorldStateSnapshot active JSON copy
        if self.snapshot is None:
            self.snapshot = WorldStateSnapshot.from_source_file(
                source_json_path=source_json,
                active_json_path=active_json,
                epoch=epoch_num,
            )
        else:
            self.snapshot.advance_epoch(next_epoch=epoch_num, next_json_path=active_json)

        # 3. Create fresh, stateless single-turn chat session for this epoch
        print(
            f"\nInvoking stateless Historian agent ({self.model_name}, thinking={self.thinking_level}, tools=CRUD)...",
            flush=True,
        )
        historian_tools = [
            self.snapshot.create_feature,
            self.snapshot.read_feature,
            self.snapshot.update_feature,
            self.snapshot.delete_feature,
            self.snapshot.expand_domain,
            self.snapshot.clear_land,
            self.snapshot.engineer_waterworks,
            self.snapshot.abandon_domain,
            self.snapshot.update_region,
        ]
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            tools=historian_tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=self.max_afc_calls,
            ),
        )
        turn_chat = self.client.chats.create(model=self.model_name, config=config)

        # 4. Formulate the turn prompt incorporating the input .md and growing # Timeline
        input_md_content = in_md.read_text(encoding="utf-8")
        epoch_directive = query if query.strip() else (
            DEFAULT_EPOCH_1_QUERY if epoch_num == 1 else DEFAULT_SUBSEQUENT_EPOCH_QUERY
        )

        user_prompt = (
            f"{input_md_content}\n\n"
            f"---\n"
            f"### Epoch {epoch_num} Directive\n"
            f"{epoch_directive}"
        )

        with _UsageTracker(self.client, model_name=self.model_name) as tracker:
            response = self._execute_turn(turn_chat, user_prompt)
            if tracker.api_calls == 0:
                tracker.record_response(response)

            narrative = _extract_response_text(response)

            # If LLM executed mutations but omitted narrative text, prompt once for the mandatory entry
            if not narrative.strip() and self.snapshot.mutations_log:
                followup = (
                    f"You executed {len(self.snapshot.mutations_log)} map mutation(s), but did not output "
                    f"the mandatory '## Epoch {epoch_num}' timeline entry. "
                    f"Please output the concise '## Epoch {epoch_num}' Markdown timeline entry explaining the historical "
                    f"rationale for these mutations now."
                )
                try:
                    calls_before = tracker.api_calls
                    followup_resp = self._execute_turn(turn_chat, followup)
                    if tracker.api_calls == calls_before:
                        tracker.record_response(followup_resp)
                    followup_text = _extract_response_text(followup_resp)
                    if followup_text.strip():
                        narrative = followup_text.strip()
                except Exception as e:
                    logger.warning(f"Follow-up prompt for epoch narrative failed: {e}")

        # Authoritative fallback: guarantee an epoch entry is always recorded when mutations occurred
        if not narrative.strip() and self.snapshot.mutations_log:
            narrative = self.snapshot.synthesize_fallback_timeline_entry(epoch=epoch_num)

        # Record and accumulate epoch token metrics and dollar cost
        epoch_usage = tracker.usage_dict
        epoch_api_calls = tracker.api_calls
        epoch_cost_usd = tracker.cost_usd

        self.last_epoch_usage = epoch_usage
        self.last_epoch_api_calls = epoch_api_calls
        self.last_epoch_cost_usd = epoch_cost_usd

        self.token_usage["prompt_tokens"] += epoch_usage["prompt_tokens"]
        self.token_usage["candidates_tokens"] += epoch_usage["candidates_tokens"]
        self.token_usage["thoughts_tokens"] += epoch_usage["thoughts_tokens"]
        self.token_usage["total_tokens"] += epoch_usage["total_tokens"]
        self.cumulative_api_calls += epoch_api_calls
        self.cumulative_cost_usd += epoch_cost_usd

        # 5. Render and save the companion .md copy with growing # Timeline
        self.snapshot.render_and_save_md(rendered_md, timeline_entry=narrative)

        # 6. Incrementally update continuous regional biome history tracking
        reg_history_json = update_regions_history(
            epoch_num=epoch_num,
            world_data=self.snapshot.data,
            timeline_entry=narrative,
            artifacts_dir=active_json.parent,
        )

        # 7. Update file tracking (stateless: no chat session or message history retained)
        self.current_epoch = epoch_num
        self.last_md_path = rendered_md
        self.last_json_path = active_json

        features_count = len(self.snapshot.data.get("features", {}))
        mutations_count = len(self.snapshot.mutations_log)
        timeline_count = len(self.snapshot.data.get("timeline", []))

        print("\n" + "-" * 80, flush=True)
        print(f"--- EPOCH {epoch_num} TIMELINE ENTRY (SUPPORTING MAP MUTATIONS) ---", flush=True)
        print(narrative if narrative else "*(Timeline recorded in tools)*", flush=True)
        print("-" * 80, flush=True)
        print(f"\nMutations executed this epoch: {mutations_count}")
        print(f"Total registered features:     {features_count}")
        print(f"Total epochs in timeline:      {timeline_count}")
        print(f"Active JSON snapshot saved:    {active_json}")
        print(f"Rendered Markdown saved:       {rendered_md}")
        print(f"Regions History updated:       {reg_history_json}")

        print("\n" + "-" * 80, flush=True)
        print(f" EPOCH {epoch_num} TOKEN USAGE & COST BREAKDOWN", flush=True)
        print("-" * 80, flush=True)
        print(f"API Hops / Remote Calls: {epoch_api_calls}", flush=True)
        print(f"Prompt Tokens:           {epoch_usage['prompt_tokens']:,}", flush=True)
        print(f"Candidate Tokens:        {epoch_usage['candidates_tokens']:,}", flush=True)
        if epoch_usage.get("thoughts_tokens"):
            print(f"Thoughts Tokens:         {epoch_usage['thoughts_tokens']:,}", flush=True)
        print(f"Total Epoch Tokens:      {epoch_usage['total_tokens']:,}", flush=True)
        print(f"Estimated Epoch Cost:    ${epoch_cost_usd:.4f} USD", flush=True)
        if epoch_num > 1 or self.cumulative_api_calls > epoch_api_calls:
            print("-" * 80, flush=True)
            print(f"Cumulative Usage (Epochs 1 - {epoch_num}):", flush=True)
            print(f"  Total API Calls:       {self.cumulative_api_calls}", flush=True)
            print(f"  Total Tokens:          {self.cumulative_usage['total_tokens']:,}", flush=True)
            print(f"  Total Estimated Cost:  ${self.cumulative_cost_usd:.4f} USD", flush=True)
        print("-" * 80, flush=True)

        return HistorianEpochResult(
            epoch=epoch_num,
            narrative=narrative,
            timeline_entry=narrative,
            input_md_path=in_md,
            active_json_path=active_json,
            rendered_md_path=rendered_md,
            mutations=list(self.snapshot.mutations_log),
            features_count=features_count,
            token_usage=dict(epoch_usage),
            regions_history_path=reg_history_json,
            api_calls=epoch_api_calls,
            estimated_cost_usd=epoch_cost_usd,
            cumulative_token_usage=dict(self.cumulative_usage),
            cumulative_cost_usd=self.cumulative_cost_usd,
        )


def main() -> None:
    """CLI entry point for running the Historian agent."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Run the Historian agent to mutate world map snapshots across epochs using feature CRUD tools."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Path to input worldmap.md (default: auto-detect latest epoch or artifacts/worldmap.md)",
    )
    parser.add_argument(
        "--epochs",
        "-n",
        type=int,
        default=1,
        help="Number of sequential epochs to run within the same conversation (default: 1)",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="",
        help="Custom historical query or directive for the epoch",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.8-flash",
        help="Gemini model to use (default: gemini-3.8-flash)",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        default="HIGH",
        help="Thinking level for Gemini models (default: HIGH)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode, prompting for epoch directives in the same conversation",
    )
    parser.add_argument(
        "--max-afc-calls",
        type=int,
        default=20,
        help="Maximum number of remote calls for automatic function calling (default: 20)",
    )

    args = parser.parse_args()
    load_dotenv()

    historian = Historian(
        model_name=args.model,
        thinking_level=args.thinking,
        max_afc_calls=args.max_afc_calls,
    )

    if args.interactive:
        print("=" * 80)
        print(" HISTORIAN AGENT: INTERACTIVE MULTI-EPOCH SIMULATION")
        print(" Type your epoch directive at each prompt, or press Enter for default.")
        print(" Type 'exit' or 'quit' to terminate the session.")
        print("=" * 80)

        in_path = args.input
        while True:
            epoch_preview = historian.current_epoch + 1 if historian.current_epoch else "Next"
            try:
                user_input = input(f"\n[Epoch {epoch_preview} Directive] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting interactive simulation.")
                break

            if user_input.lower() in ("exit", "quit"):
                print("Ending simulation session.")
                break

            try:
                historian.run_epoch(input_md_path=in_path, query=user_input)
                in_path = None  # Subsequent turns use the agent's internal last_md_path
            except Exception as e:
                print(f"[ERROR] Epoch run failed: {e}", file=sys.stderr)
                break

    else:
        in_path = args.input
        for step in range(args.epochs):
            try:
                query = args.query if (step == 0 or args.query) else ""
                historian.run_epoch(input_md_path=in_path, query=query)
                in_path = None  # Subsequent runs within this loop use previous .md automatically
            except Exception as e:
                print(f"\n[ERROR] Historian simulation failed at epoch step {step + 1}: {e}", file=sys.stderr)
                sys.exit(1)

    print("\n" + "=" * 80)
    print(" HISTORIAN TOTAL TOKEN & COST SUMMARY")
    print("=" * 80)
    usage = historian.cumulative_usage
    print(f"Total API Calls:      {historian.cumulative_api_calls}")
    print(f"Prompt Tokens:        {usage['prompt_tokens']:,}")
    print(f"Candidate Tokens:     {usage['candidates_tokens']:,}")
    if usage.get("thoughts_tokens"):
        print(f"Thoughts Tokens:      {usage['thoughts_tokens']:,}")
    print(f"Total Tokens:         {usage['total_tokens']:,}")
    print(f"Total Estimated Cost: ${historian.cumulative_cost_usd:.4f} USD")
    print("=" * 80)


if __name__ == "__main__":
    main()
