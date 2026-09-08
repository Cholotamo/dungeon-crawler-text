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
                lines.append(f"- [{k}] '{f.get('name')}' ['{f.get('char')}'] ({f.get('type')}) {pos_str}")
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
        """Updates an existing feature on the world map (e.g. upgrade village to city, ruin a site, extend road).

        Args:
            feature_id: Unique identifier of the feature to update.
            name: New display name (leave empty to keep current name).
            char: New map character symbol, e.g. 'O' when upgraded to major city, or '!' when ruined.
            feature_type: New semantic category, e.g. 'major_city', 'ruin' (leave empty to keep current).
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

        if name and str(name).strip():
            feat["name"] = str(name).strip()
            changes.append(f"name='{feat['name']}'")

        if char and str(char).strip():
            feat["char"] = str(char).strip()[0]
            changes.append(f"char='{feat['char']}'")

        if feature_type and str(feature_type).strip():
            feat["type"] = str(feature_type).strip()
            changes.append(f"type='{feat['type']}'")

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
            feat["tiles"] = norm_tiles
            changes.append(f"tiles={norm_tiles}")

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
        crud_tools = [
            self.snapshot.create_feature,
            self.snapshot.read_feature,
            self.snapshot.update_feature,
            self.snapshot.delete_feature,
        ]
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            tools=crud_tools,
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

        # 6. Update file tracking (stateless: no chat session or message history retained)
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
