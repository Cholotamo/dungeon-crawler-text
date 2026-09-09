"""Historian Agent module.

Chronicles the passage of epochs in a fantasy realm and mutates world map snapshots
using feature CRUD tools via Gemini Automatic Function Calling (AFC).
"""

import argparse
from copy import deepcopy
from dataclasses import dataclass, field
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
    "Generations have passed. Chronicle the unfolding history of the realm: how established settlements "
    "prospered into major cities or succumbed to war, plague, or famine; how new frontiers were settled; "
    "how trade routes expanded; and what ancient horrors or dungeons were unearthed."
)


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

    return normalized


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

    def append_timeline_entry(self, epoch: int, content: str) -> None:
        """Appends an epoch entry to the growing chronological # Timeline."""
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

        timeline_list.append(clean_content)
        self.save()

    def render_and_save_md(self, md_path: Path, timeline_entry: Optional[str] = None) -> Path:
        """Renders the snapshot to LLM-readable Markdown companion with growing # Timeline and writes to disk."""
        if timeline_entry is not None and str(timeline_entry).strip():
            self.append_timeline_entry(epoch=self.epoch, content=str(timeline_entry))
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

        # 1. Road Validation ('+')
        if fchar == "+" or ftype.lower() in ("road", "highway", "trail", "path", "route"):
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
                return (
                    f"[REJECTION] Road '{fid}' attempts to cross water tile(s) '~' without a bridge at {water_coords}.\n"
                    f"Actionable 3-Step Remedy:\n"
                    f"1. Terminate this road at the near bank (before coordinate {first_water}).\n"
                    f"2. Call create_feature to anchor an explicit bridge ('=') across water tile {first_water}.\n"
                    f"3. Call create_feature to continue the road from the opposite bank."
                )

            if chasm_coords:
                first_chasm = chasm_coords[0]
                return (
                    f"[REJECTION] Road '{fid}' attempts to cross sheer chasm/cliff tile(s) '/' without a bridge at {chasm_coords}.\n"
                    f"Actionable 3-Step Remedy:\n"
                    f"1. Terminate this road at the near cliff edge (before coordinate {first_chasm}).\n"
                    f"2. Call create_feature to anchor a stone bridge/viaduct ('=') across chasm tile {first_chasm}.\n"
                    f"3. Call create_feature to continue the road from the opposite edge."
                )

            if peak_coords:
                return (
                    f"[REJECTION] Road '{fid}' attempts to traverse impassable alpine mountain peak(s) '^' at {peak_coords}.\n"
                    f"Roads cannot scale sheer mountain peaks. Route through mountain passes, foothills (','), or valleys ('.')."
                )

        # 2. Settlement Validation ('o', 'O')
        elif fchar in ("o", "O") or ftype.lower() in (
            "settlement", "outpost", "village", "major_city", "city", "metropolis", "town", "hamlet"
        ):
            for pt in tiles:
                x, y = pt[0], pt[1]
                t_char = terrain[y][x] if 0 <= y < height and 0 <= x < width else "?"
                if t_char == "~":
                    return (
                        f"[REJECTION] Settlement '{fid}' cannot be placed on water tile '~' at [{x}, {y}]. "
                        f"Settlements must be founded on dry land: fertile plains ('.'), sheltered coasts (';'), hills (','), or farmlands (':'). "
                        f"For coastal ports, place the settlement on an adjacent coast tile (';') or riverbank ('.')."
                    )
                elif t_char == "/":
                    return (
                        f"[REJECTION] Settlement '{fid}' cannot be placed in a sheer chasm/cliff '/' at [{x}, {y}]. "
                        f"Found settlements on stable, habitable terrain."
                    )
                elif t_char == "^":
                    return (
                        f"[REJECTION] Settlement '{fid}' cannot be placed atop an impassable mountain peak '^' at [{x}, {y}]. "
                        f"Place mountain outposts and mining camps in surrounding foothills (',') or valleys ('.')."
                    )

        # 3. Bridge Validation ('=')
        elif fchar == "=" or ftype.lower() in ("bridge", "viaduct"):
            barrier_tiles = []
            for pt in tiles:
                x, y = pt[0], pt[1]
                t_char = terrain[y][x] if 0 <= y < height and 0 <= x < width else "?"
                if t_char in ("~", "/", "%"):
                    barrier_tiles.append(pt)

            if not barrier_tiles:
                ground_chars = [terrain[pt[1]][pt[0]] for pt in tiles if 0 <= pt[1] < height and 0 <= pt[0] < width]
                return (
                    f"[REJECTION] Bridge '{fid}' at {tiles} is situated entirely on dry land ({ground_chars}). "
                    f"Bridges must span a natural water barrier ('~'), chasm ('/'), or wetland bottleneck ('%'). "
                    f"Use a road ('+') for terrestrial overland routes."
                )

        # 4. Dungeon / Landmark Validation ('!')
        elif fchar == "!":
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
        """Creates a new feature (settlement, dungeon, outpost, city, road, bridge) on the world map.

        Args:
            feature_id: Unique slug identifier for the feature (e.g. 'oakhaven', 'highwatch', 'kings_highway').
            name: Evocative human-readable display name (e.g. 'Oakhaven', 'Highwatch Citadel').
            char: Map character symbol representing the feature. 'o' for outpost/village, 'O' for major city,
                '!' for dungeon/ruin/stronghold, '+' for road, '=' for bridge.
            feature_type: Semantic category (e.g. 'outpost', 'settlement', 'major_city', 'dungeon', 'ruin',
                'stronghold', 'road', 'bridge').
            tiles: List of [x, y] coordinates. Single-tile features use [[x, y]]. Multi-tile routes or bridges
                use a sequence of coordinates [[x1, y1], [x2, y2], ...]. Coordinates must be in range 0..31.
            description: Optional lore, history, or context describing the founding and significance of this feature.

        Returns:
            A confirmation string detailing the created feature and underlying terrain.
        """
        fid = str(feature_id).strip().lower().replace(" ", "_")
        if not fid:
            return "Error: feature_id cannot be empty."

        features = self.data.setdefault("features", {})
        if fid in features:
            existing = features[fid]
            return (
                f"Error: Feature '{fid}' already exists ('{existing.get('name')}'). "
                "Use update_feature to modify it, or choose a unique feature_id."
            )

        norm_tiles = _normalize_tiles(tiles)
        if not norm_tiles:
            return "Error: tiles must contain at least one valid [x, y] coordinate."

        # Validate coordinate boundaries (32x32)
        terrain = self.data.get("terrain_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32
        for pt in norm_tiles:
            x, y = pt[0], pt[1]
            if not (0 <= x < width and 0 <= y < height):
                return (
                    f"Error: Coordinate [{x}, {y}] is out of bounds. "
                    f"Valid map coordinates are X: 0..{width-1}, Y: 0..{height-1}."
                )

        fchar = str(char).strip()[0] if char else "o"
        ftype = str(feature_type).strip() or "feature"
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
            return rejection

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
        """Reads information about a registered feature, or lists all registered features in the snapshot.

        Args:
            feature_id: Unique identifier of the feature to inspect. Pass '' or 'all' to list all features.

        Returns:
            JSON or formatted string with feature details, coordinates, and underlying geography.
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
        name: str = "",
        char: str = "",
        feature_type: str = "",
        tiles: list[list[int]] | None = None,
        description: str = "",
    ) -> str:
        """Updates an existing feature on the world map (e.g. upgrade village to city, ruin a site, reclaim a ruin, extend road).

        Args:
            feature_id: Unique identifier of the feature to update.
            name: New display name (leave empty to keep current name).
            char: New map character symbol, e.g. 'O' when upgraded to major city, '!' when ruined,
                or 'o' / 'O' when an ancient ruin is reclaimed and resettled.
            feature_type: New semantic category, e.g. 'major_city', 'ruin', 'outpost', 'settlement' (leave empty to keep current).
            tiles: New list of [x, y] coordinates if position changed or road extended (leave empty to keep current).
            description: Updated description or chronicle note (leave empty to keep current).

        Returns:
            A confirmation string detailing the changes made.
        """
        features = self.data.setdefault("features", {})
        fid = str(feature_id).strip().lower().replace(" ", "_")

        match_key = None
        for k in features:
            if k.lower() == fid:
                match_key = k
                break

        if not match_key:
            return (
                f"Error: Feature '{feature_id}' not found. Cannot update non-existent feature. "
                f"Registered features: {list(features.keys())}"
            )

        feat = features[match_key]
        changes: list[str] = []

        proposed_char = str(char).strip()[0] if char and str(char).strip() else feat.get("char", "o")
        proposed_type = str(feature_type).strip() if feature_type and str(feature_type).strip() else feat.get("type", "feature")
        proposed_tiles = feat.get("tiles", [])

        if tiles is not None and len(tiles) > 0:
            norm_tiles = _normalize_tiles(tiles)
            terrain = self.data.get("terrain_grid", [])
            height = len(terrain)
            width = len(terrain[0]) if height > 0 else 32
            for pt in norm_tiles:
                if not (0 <= pt[0] < width and 0 <= pt[1] < height):
                    return (
                        f"Error: Coordinate [{pt[0]}, {pt[1]}] is out of bounds "
                        f"(X: 0..{width-1}, Y: 0..{height-1})."
                    )
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
            return rejection

        if name and str(name).strip():
            feat["name"] = str(name).strip()
            changes.append(f"name='{feat['name']}'")

        if char and str(char).strip():
            feat["char"] = proposed_char
            changes.append(f"char='{proposed_char}'")

        if feature_type and str(feature_type).strip():
            feat["type"] = proposed_type
            changes.append(f"type='{proposed_type}'")

        if tiles is not None and len(tiles) > 0:
            feat["tiles"] = proposed_tiles
            changes.append(f"tiles={proposed_tiles}")

        if description and str(description).strip():
            feat["description"] = str(description).strip()
            changes.append("description updated")

        self.save()
        change_summary = ", ".join(changes) if changes else "no fields modified"
        msg = f"[SUCCESS] Updated feature '{match_key}': {change_summary}."
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
            return (
                f"Error: Feature '{feature_id}' not found. Cannot delete non-existent feature. "
                f"Registered features: {list(features.keys())}"
            )

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
        """Expands a territorial domain (farmlands, blighted wastelands, or forest canopy) around a center point.

        Automatically synchronizes terrain_grid and region_grid, registers the region, and shields natural waterways:
        existing water tiles ('~') and bridges ('=') within the radius are strictly preserved and never paved over.

        Args:
            center: [x, y] center coordinate (e.g. location of a settlement, city, or ruin).
            radius: Tile radius of expansion (1 to 5).
            domain_type: Category of domain ('farmland' -> ':' tiles, 'wasteland' -> '*' tiles, 'forest' -> '#' tiles).
            region_name: Display name of the domain (e.g. 'Oakhaven Farmlands', 'The Ashen Blight').
            region_id: Single alphanumeric character identifier for region_grid (e.g. 'h', 'w').
            lore: Optional narrative lore describing the atmosphere, history, or ecological nature of this domain.

        Returns:
            Confirmation message detailing modified tiles and preserved water/landmarks.
        """
        if not center or len(center) < 2:
            return "Error: center must be an [x, y] coordinate pair."
        cx, cy = int(center[0]), int(center[1])
        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        if not (0 <= cx < width and 0 <= cy < height):
            return f"Error: Center coordinate [{cx}, {cy}] is out of bounds."

        reg_key = str(region_id).strip()[:1]
        if not reg_key:
            return "Error: region_id must be a non-empty single character."

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
        r_name = str(region_name).strip() or f"Domain {reg_key}"
        regions_dict = self.data.setdefault("regions", {})
        existing_reg = regions_dict.get(reg_key, {}) if isinstance(regions_dict.get(reg_key), dict) else {}
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
                # River Shield: Never overwrite natural water tiles
                if curr_t == "~":
                    preserved_water.append([nx, ny])
                    continue
                # Shield bridges
                if (nx, ny) in bridge_coords:
                    continue
                # Shield alpine peaks from farming
                if curr_t == "^" and target_char == ":":
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
        """Clears natural obstacles (deforestation, fen drainage, stone quarrying) into usable plains or farmland.

        Converts woods ('#', '&') or bogs ('%') into open plains ('.') or farmlands (':').
        If converted to farmland, can extend an existing domain region or register a new one.
        Strictly rejects execution on water tiles ('~').

        Args:
            coords: List of [x, y] coordinates to clear.
            target_terrain: Ground type after clearing: '.' for open plains/pasture, ':' for farmland, '*' for quarry.
            domain_region_id: Optional existing region ID (e.g. 'h') to assign these cleared tiles to.
            new_domain_name: Optional name if founding a new agricultural domain (e.g. 'Greenwood Grange').
            new_domain_id: Single character ID if founding a new domain.
            new_domain_lore: Optional narrative lore describing the newly cleared and settled land.

        Returns:
            Confirmation message or actionable rejection if water tiles were targeted.
        """
        norm_coords = _normalize_tiles(coords)
        if not norm_coords:
            return "Error: coords must contain at least one valid [x, y] coordinate."

        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        # Check bounds and reject water tiles
        water_tiles = []
        for pt in norm_coords:
            x, y = pt[0], pt[1]
            if not (0 <= x < width and 0 <= y < height):
                return f"Error: Coordinate [{x}, {y}] is out of bounds."
            if terrain[y][x] == "~":
                water_tiles.append(pt)

        if water_tiles:
            return (
                f"[REJECTION] clear_land cannot be used on natural water tiles '~' at {water_tiles}.\n"
                f"To dam, drain, or reclaim waterways into dry land, use engineer_waterworks(action='dam' or 'drain')."
            )

        t_target = str(target_terrain).strip()[:1] if target_terrain and str(target_terrain).strip() in (".", ":", "*", ",") else "."

        # Determine target region
        reg_key = "0"
        if new_domain_name and new_domain_id:
            reg_key = str(new_domain_id).strip()[:1]
            regions_dict = self.data.setdefault("regions", {})
            existing_reg = regions_dict.get(reg_key, {}) if isinstance(regions_dict.get(reg_key), dict) else {}
            reg_entry = {
                "name": str(new_domain_name).strip(),
                "type": "farmland" if t_target == ":" else "cleared_land",
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

    def engineer_waterworks(
        self,
        coords: list[list[int]],
        action: str,
        target_terrain: str = "",
        target_region_id: str = "",
        waterway_name: str = "",
        waterway_region_id: str = "",
        waterway_lore: str = "",
    ) -> str:
        """Modifies waterways, dams, canals, and reclaimed polders while guaranteeing dual-grid synchronization.

        Actions:
        - 'dam' / 'drain': Converts water ('~') into ground ('.' plains, ':' farmlands, '*' masonry dam).
          Automatically reassigns region away from the water body to the target land region or ambient wilderness ('0').
        - 'canal' / 'flood': Converts land into water ('~') and registers/assigns a designated water region ('river'/'lake').

        Args:
            coords: List of [x, y] coordinates to modify.
            action: 'dam', 'drain', 'canal', or 'flood'.
            target_terrain: For dam/drain: ground type to convert into ('.' for plains, ':' for farmland, '*' for masonry dam).
            target_region_id: For dam/drain: land region ID to assign (defaults to ambient wilderness '0').
            waterway_name: For canal/flood: name of the canal or reservoir (e.g. 'King's Canal').
            waterway_region_id: For canal/flood: single-character region ID for the water body.
            waterway_lore: Optional narrative lore describing the constructed canal or flooded basin.

        Returns:
            Confirmation message detailing modified water/ground tiles and updated regional biomes.
        """
        norm_coords = _normalize_tiles(coords)
        if not norm_coords:
            return "Error: coords must contain at least one valid [x, y] coordinate."

        act = str(action).strip().lower()
        if act not in ("dam", "drain", "canal", "flood"):
            return "Error: action must be one of 'dam', 'drain', 'canal', or 'flood'."

        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        regions = self.data.get("regions", {})
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        for pt in norm_coords:
            x, y = pt[0], pt[1]
            if not (0 <= x < width and 0 <= y < height):
                return f"Error: Coordinate [{x}, {y}] is out of bounds."

        tg = [list(row) for row in terrain]
        rg = [list(row) for row in region]

        if act in ("dam", "drain"):
            # Converting water -> dry land / dam masonry
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
                f"[SUCCESS] Engineered waterworks ({act}): converted {len(norm_coords)} water tile(s) to "
                f"dry ground '{t_ground}' assigned to land region '{land_reg}' ({reg_name})."
            )
            self.mutations_log.append(msg)
            print(f"  -> {msg}", flush=True)
            return msg

        else:  # canal or flood (land -> water)
            w_id = waterway_region_id.strip()[:1] if waterway_region_id and waterway_region_id.strip() else "F"
            w_name = str(waterway_name).strip() or "Constructed Canal"
            w_type = "river" if act == "canal" else "lake"

            # Register water region
            regions_dict = self.data.setdefault("regions", {})
            existing_reg = regions_dict.get(w_id, {}) if isinstance(regions_dict.get(w_id), dict) else {}
            reg_entry = {
                "name": w_name,
                "type": w_type,
            }
            if waterway_lore and str(waterway_lore).strip():
                reg_entry["lore"] = str(waterway_lore).strip()
            elif "lore" in existing_reg:
                reg_entry["lore"] = existing_reg["lore"]
            regions_dict[w_id] = reg_entry

            for pt in norm_coords:
                x, y = pt[0], pt[1]
                tg[y][x] = "~"
                rg[y][x] = w_id

            self.data["terrain_grid"] = ["".join(row) for row in tg]
            self.data["region_grid"] = ["".join(row) for row in rg]
            self.save()

            msg = (
                f"[SUCCESS] Engineered waterworks ({act}): carved {len(norm_coords)} water tile(s) ('~') "
                f"registered to water region '{w_id}' ('{w_name}', type: '{w_type}')."
            )
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

        Reverts abandoned farmlands (':') or wastelands ('*') back to wild grasslands ('.') or light woods ('#'),
        and dissolves the domain by reassigning tiles to ambient wilderness ('0').
        Waterways ('~') and mountain peaks ('^') are preserved.

        Args:
            center: [x, y] coordinate of the abandoned settlement, ruin, or epicenter.
            radius: Tile radius to dissolve (1 to 5).
            target_terrain: Ground type to revert to ('.' for wild plains, '#' for overgrown woods).

        Returns:
            Confirmation message detailing reclaimed tiles and dissolved regions.
        """
        if not center or len(center) < 2:
            return "Error: center must be an [x, y] coordinate pair."
        cx, cy = int(center[0]), int(center[1])
        terrain = self.data.get("terrain_grid", [])
        region = self.data.get("region_grid", [])
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 32

        if not (0 <= cx < width and 0 <= cy < height):
            return f"Error: Center coordinate [{cx}, {cy}] is out of bounds."

        r = max(1, min(int(radius), 8))
        t_revert = str(target_terrain).strip()[:1] if target_terrain and str(target_terrain).strip() in (".", "#", ",") else "."

        tg = [list(row) for row in terrain]
        rg = [list(row) for row in region]

        reclaimed_coords = []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy > r * r + r:
                    continue
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue

                curr_t = tg[ny][nx]
                # Only dissolve farmlands (:) or wastelands (*)
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
    ) -> str:
        """Updates an existing regional biome's lore, name, or classification as history transforms the realm.

        Use this tool when a region's ecology, atmosphere, dangers, or reputation evolves across epochs
        (e.g., an ancient primeval forest becomes blighted, corrupted, or logged; a mountain range becomes haunted
        by dragons or excavated for iron mines; a desolate wasteland is cleansed; or uncharted wilderness is settled).

        Args:
            region_id: Single-character alphanumeric ID of the region to update (e.g. 'I', 'D', '0', 'K').
            lore: Updated or expanded narrative lore describing the region's current state, history, threats, or ecology.
            name: Optional new display name for the region if renamed.
            region_type: Optional updated semantic category (e.g. 'forest', 'wasteland', 'mountains', 'wilderness', 'farmland').

        Returns:
            A confirmation string detailing the region updates.
        """
        reg_key = str(region_id).strip()[:1]
        if not reg_key:
            return "Error: region_id cannot be empty."

        regions = self.data.setdefault("regions", {})
        if reg_key not in regions or not isinstance(regions[reg_key], dict):
            return (
                f"Error: Region ID '{reg_key}' not found in registered regions. "
                f"Available region IDs: {list(regions.keys())}"
            )

        reg = regions[reg_key]
        changes: list[str] = []

        if name and str(name).strip():
            reg["name"] = str(name).strip()
            changes.append(f"name='{reg['name']}'")

        if region_type and str(region_type).strip():
            reg["type"] = str(region_type).strip().lower()
            changes.append(f"type='{reg['type']}'")

        if lore and str(lore).strip():
            reg["lore"] = str(lore).strip()
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
        model_name: str = "gemini-3.6-flash",
        thinking_level: str = "MEDIUM",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("historian.md")

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

    def _track_usage(self, response: Any) -> None:
        """Records token usage from response metadata."""
        meta = getattr(response, "usage_metadata", None)
        if meta:
            p = getattr(meta, "prompt_token_count", 0) or 0
            c = getattr(meta, "candidates_token_count", 0) or 0
            t = getattr(meta, "total_token_count", 0) or (p + c)
            th = getattr(meta, "thoughts_token_count", 0) or 0
            self.token_usage["prompt_tokens"] += p
            self.token_usage["candidates_tokens"] += c
            self.token_usage["total_tokens"] += t
            self.token_usage["thoughts_tokens"] += th

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

        response = self._execute_turn(turn_chat, user_prompt)
        self._track_usage(response)

        narrative = _extract_response_text(response)

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

        return HistorianEpochResult(
            epoch=epoch_num,
            narrative=narrative,
            timeline_entry=narrative,
            input_md_path=in_md,
            active_json_path=active_json,
            rendered_md_path=rendered_md,
            mutations=list(self.snapshot.mutations_log),
            features_count=features_count,
            token_usage=dict(self.token_usage),
            regions_history_path=reg_history_json,
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
        default="gemini-3.6-flash",
        help="Gemini model to use (default: gemini-3.6-flash)",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        default="MEDIUM",
        help="Thinking level for Gemini models (default: MEDIUM)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode, prompting for epoch directives in the same conversation",
    )

    args = parser.parse_args()
    load_dotenv()

    historian = Historian(model_name=args.model, thinking_level=args.thinking)

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
    print(" TOKEN USAGE SUMMARY")
    print("=" * 80)
    usage = historian.token_usage
    print(f"Prompt Tokens:     {usage['prompt_tokens']:,}")
    print(f"Candidate Tokens:  {usage['candidates_tokens']:,}")
    if usage.get("thoughts_tokens"):
        print(f"Thoughts Tokens:   {usage['thoughts_tokens']:,}")
    print(f"Total Tokens:      {usage['total_tokens']:,}")
    print("=" * 80)


if __name__ == "__main__":
    main()
