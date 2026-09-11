"""Subarchitect Agent module.

Procedurally generates 16x16 localemaps (base terrain_grid, district_grid zoning, and overlaid features)
from deterministic Locale Generation Seeds (`seed.md`) using Gemini with Python code execution.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import re
import sys
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff

# Suppress the redundant SDK warning for stateless automatic function calling/code execution
try:
    from google.genai import models as _genai_models
    _genai_models.Models._logged_afc_warning = True
except Exception:
    pass

logger = logging.getLogger(__name__)

DEFAULT_LOCALES_DIR = Path("artifacts/locales")
GRID_DIM = 16

TERRAIN_LEGEND = {
    ".": "Floor / Open Dirt / Flagstone / Chamber Floor",
    ",": "Turf / Wild Grass / Meadow / Moss / Lichen",
    ":": "Cultivated Farmland / Scree / Rubble / Debris",
    "~": "Deep Water / River / Lake / Subterranean Pool",
    ";": "Shallows / Shoreline / Mud Bank / Flooded Floor",
    "&": "Overgrowth / Thicket / Brambles / Fungi / Webbing",
    "^": "Elevated Stone / Rocky Ridge / Chasm / Stalagmites",
    "+": "Thoroughfare / Road / Path / Corridor / Hallway",
    "=": "Span / Bridge / Boardwalk / Pier / Chasm Walkway",
    "#": "Solid Wall / Masonry / Palisade / Hewn Rock / Bedrock",
    "/": "Ingress / Doorway / Gate / Portal / Cavern Mouth",
    "|": "Partition / Fence / Low Hurdle / Iron Grate / Portcullis",
}

VALID_TERRAIN_CHARS = set(TERRAIN_LEGEND.keys())


def _load_prompt(filename: str = "subarchitect_localemap.md") -> str:
    """Loads a prompt template file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Subarchitect prompt file not found at: {prompt_path}")


def parse_seed_metadata(seed_text: str) -> dict[str, Any]:
    """Extracts classification, lore, borders, and infrastructural metadata from seed markdown text."""
    meta: dict[str, Any] = {}
    fid_m = re.search(r"-\s*\*\*Feature ID:\*\*\s*`?([a-zA-Z0-9_\-]+)`?", seed_text)
    if fid_m:
        meta["feature_id"] = fid_m.group(1).strip()

    name_m = re.search(r"-\s*\*\*Name:\*\*\s*([^\n\r]+)", seed_text)
    if name_m:
        meta["name"] = name_m.group(1).strip()

    type_m = re.search(r"-\s*\*\*Type:\*\*\s*([^\n\r]+)", seed_text)
    if type_m:
        meta["type"] = type_m.group(1).strip().lower()

    scale_m = re.search(r"-\s*\*\*Scale Category:\*\*\s*([^\n\r]+)", seed_text)
    if scale_m:
        meta["scale_category"] = scale_m.group(1).strip()

    lore_m = re.search(r"-\s*\*\*(?:[^\*]+?)\s*Lore:\*\*\s*\"?([^\n\r\"]+)\"?", seed_text)
    if lore_m:
        meta["lore"] = lore_m.group(1).strip()

    host_m = re.search(r"-\s*\*\*Host Region:\*\*\s*([^\n\r]+)", seed_text)
    if host_m:
        meta["host_region"] = host_m.group(1).strip()

    host_eco_m = re.search(r"-\s*\*\*Host Region Ecology:\*\*\s*\"?([^\n\r\"]+)\"?", seed_text)
    if host_eco_m:
        meta["host_ecology"] = host_eco_m.group(1).strip()

    # Section 3: Perimeter Edge Constraints
    s3_m = re.search(r"## 3\.\s*Perimeter Edge Constraints\s*\n(.*?)(?=\n##|\Z)", seed_text, re.DOTALL)
    if s3_m:
        perims: list[str] = []
        for line in s3_m.group(1).splitlines():
            line_s = line.strip()
            if line_s.startswith("- **"):
                m = re.search(r"^-\s*\*\*(.*?)\*\*:?\s*(.*)", line_s)
                if m:
                    label = m.group(1).rstrip(":").strip()
                    val = m.group(2).strip()
                    perims.append(f"{label}: {val}")
        if perims:
            meta["perimeters"] = perims

    # Section 4: Ingress & Approaches
    s4_m = re.search(r"## 4\.\s*Ingress & Approaches\s*\n(.*?)(?=\n##|\Z)", seed_text, re.DOTALL)
    if s4_m:
        approaches: list[dict[str, str]] = []
        cur_approach, road_info, dest_info, dest_lore = "", "", "", ""
        for line in s4_m.group(1).splitlines():
            line_s = line.strip()
            if "Other Borders:" in line_s:
                continue
            if "Road Ingress:" in line_s:
                val = re.sub(r"^-\s*\*\*Road Ingress:\*\*\s*", "", line_s).strip()
                approaches.append({
                    "direction": "Perimeter",
                    "road": "None",
                    "destination": "Wilderness Traversal",
                    "destination_lore": val if val else "Isolated wilderness site; entry via local terrain.",
                })
            elif line_s.startswith("- **") and "Approach:" in line_s:
                if cur_approach:
                    approaches.append({
                        "direction": cur_approach,
                        "road": road_info,
                        "destination": dest_info,
                        "destination_lore": dest_lore,
                    })
                m = re.search(r"\*\*(.*?)\*\*", line_s)
                cur_approach = m.group(1).replace(" Approach:", "").replace(" Approach", "").strip() if m else ""
                road_info, dest_info, dest_lore = "", "", ""
            elif line_s.startswith("- *Road:*"):
                road_info = re.sub(r"^-\s*\*Road:\*\s*", "", line_s).strip()
            elif line_s.startswith("- *Destination:*"):
                dest_info = re.sub(r"^-\s*\*Destination:\*\s*", "", line_s).strip()
            elif line_s.startswith("- *Destination Lore:*"):
                m_lore = re.search(r'\"([^\"]+)\"', line_s)
                dest_lore = m_lore.group(1).strip() if m_lore else re.sub(r"^-\s*\*Destination Lore:\*\s*", "", line_s).strip().strip('"')
        if cur_approach:
            approaches.append({
                "direction": cur_approach,
                "road": road_info,
                "destination": dest_info,
                "destination_lore": dest_lore,
            })
        if approaches:
            meta["approaches"] = approaches

    return meta


def extract_all_parts(response: Any) -> tuple[str, str]:
    """Extracts combined markdown text and code execution stdout from response parts."""
    texts: list[str] = []
    code_outputs: list[str] = []

    if hasattr(response, "candidates") and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        texts.append(text)
                    code_res = getattr(part, "code_execution_result", None)
                    if code_res and getattr(code_res, "output", None):
                        code_outputs.append(code_res.output)

    full_text = "\n".join(texts)
    if not full_text and hasattr(response, "text") and response.text:
        full_text = response.text

    full_code_output = "\n".join(code_outputs)
    return full_text, full_code_output


def parse_localemap_json(raw_text: str) -> Optional[dict[str, Any]]:
    """Attempts to extract and parse localemap JSON from text or code execution stdout."""
    # 1. Direct JSON parse (standard clean code execution stdout)
    raw_clean = raw_text.strip()
    try:
        data = json.loads(raw_clean)
        if isinstance(data, dict) and ("terrain_grid" in data or "overview_grid" in data or "district_grid" in data):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Try explicit delimiter extraction (if present)
    delimiter_match = re.search(
        r"___LOCALEMAP_START___\s*(\{.*?\})\s*___LOCALEMAP_END___",
        raw_text,
        re.DOTALL,
    )
    if delimiter_match:
        try:
            return json.loads(delimiter_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Try markdown fenced code block extraction
    code_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    for block in code_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and ("terrain_grid" in data or "overview_grid" in data or "district_grid" in data):
                return data
        except json.JSONDecodeError:
            continue

    # 4. Try outermost curly braces enclosing keys
    outer_match = re.search(
        r"(\{\s*\"(?:feature_id|name|terrain_grid|overview_grid)\".*?\})",
        raw_text,
        re.DOTALL,
    )
    if outer_match:
        try:
            data = json.loads(outer_match.group(1))
            if isinstance(data, dict) and ("terrain_grid" in data or "overview_grid" in data or "district_grid" in data):
                return data
        except json.JSONDecodeError:
            pass

    # 5. Fallback raw decoder search
    start_idx = raw_text.find("{")
    while start_idx != -1:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(raw_text[start_idx:])
            if isinstance(obj, dict) and ("terrain_grid" in obj or "overview_grid" in obj or "district_grid" in obj):
                return obj
        except json.JSONDecodeError:
            pass
        start_idx = raw_text.find("{", start_idx + 1)

    return None


def build_composite_grid(locale_map: dict[str, Any]) -> list[str]:
    """Overlays registered features onto the base terrain_grid."""
    terrain = locale_map.get("terrain_grid", [])
    screen = [list(row) for row in terrain]
    features = locale_map.get("features", {})

    if isinstance(features, dict):
        for feat in features.values():
            if not isinstance(feat, dict):
                continue
            char = str(feat.get("char", "X"))[:1]
            tiles = feat.get("tiles", [])
            for tile in tiles:
                if isinstance(tile, (list, tuple)) and len(tile) == 2:
                    tx, ty = tile
                    if 0 <= ty < len(screen) and 0 <= tx < len(screen[ty]):
                        screen[ty][tx] = char

    return ["".join(row) for row in screen]


def validate_localemap(
    data: dict[str, Any],
    seed_meta: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Validates dimensions, terrain_grid, district_grid, districts registry, and features."""
    if not isinstance(data, dict):
        raise ValueError("Locale map data must be a dictionary.")

    seed_meta = seed_meta or {}

    # Feature ID, Name, Type, Keyframe Index
    if not data.get("feature_id"):
        data["feature_id"] = seed_meta.get("feature_id", "unknown_locale")
    if not data.get("name"):
        data["name"] = seed_meta.get("name", str(data["feature_id"]).replace("_", " ").title())
    if not data.get("type"):
        data["type"] = seed_meta.get("type", "settlement")
    if "keyframe_index" not in data:
        data["keyframe_index"] = 0
    else:
        try:
            data["keyframe_index"] = int(data["keyframe_index"])
        except (ValueError, TypeError):
            data["keyframe_index"] = 0

    # Extract & Validate terrain_grid (ground + enclosures + infrastructure)
    terrain_grid = data.get("terrain_grid")
    if terrain_grid is None:
        terrain_grid = data.get("overview_grid")
    if terrain_grid is None and "views" in data and isinstance(data["views"], dict):
        terrain_grid = data["views"].get("overview", {}).get("grid")

    if not isinstance(terrain_grid, list) or len(terrain_grid) != GRID_DIM:
        raise ValueError(
            f"terrain_grid must contain exactly {GRID_DIM} rows, "
            f"got {len(terrain_grid) if isinstance(terrain_grid, list) else type(terrain_grid)}."
        )
    for y, row in enumerate(terrain_grid):
        if not isinstance(row, str) or len(row) != GRID_DIM:
            raise ValueError(
                f"terrain_grid row {y} must have length {GRID_DIM}, "
                f"got len={len(row) if isinstance(row, str) else type(row)}."
            )
    data["terrain_grid"] = terrain_grid

    # Extract & Validate district_grid (district/zoning map)
    district_grid = data.get("district_grid")
    if district_grid is None and "views" in data and isinstance(data["views"], dict):
        district_grid = data["views"].get("district", {}).get("grid")

    if not isinstance(district_grid, list) or len(district_grid) != GRID_DIM:
        raise ValueError(
            f"district_grid must contain exactly {GRID_DIM} rows, "
            f"got {len(district_grid) if isinstance(district_grid, list) else type(district_grid)}."
        )
    for y, row in enumerate(district_grid):
        if not isinstance(row, str) or len(row) != GRID_DIM:
            raise ValueError(
                f"district_grid row {y} must have length {GRID_DIM}, "
                f"got len={len(row) if isinstance(row, str) else type(row)}."
            )
    data["district_grid"] = district_grid

    # Validate and populate Districts Registry
    districts = data.get("districts")
    if not isinstance(districts, dict):
        districts = {}
    data["districts"] = districts

    # Ensure default '0' for unzoned buffer/nature
    if "0" not in districts or not isinstance(districts["0"], dict):
        districts["0"] = {
            "name": "Frontier Buffer & Wilderness",
            "type": "buffer",
            "lore": "Unzoned natural perimeter buffer, shoreline, and exterior terrain.",
        }
    else:
        if "name" not in districts["0"]:
            districts["0"]["name"] = "Frontier Buffer & Wilderness"
        if "type" not in districts["0"]:
            districts["0"]["type"] = "buffer"
        if "lore" not in districts["0"]:
            districts["0"]["lore"] = districts["0"].get("description", "Natural perimeter buffer.")

    used_district_chars = {char for row in district_grid for char in row}
    for ch in used_district_chars:
        if ch not in districts:
            districts[ch] = {
                "name": f"District {ch}",
                "type": "district",
                "lore": f"Designated functional district {ch}.",
            }
        elif isinstance(districts[ch], str):
            districts[ch] = {
                "name": districts[ch],
                "type": "district",
                "lore": f"Functional zone: {districts[ch]}.",
            }
        elif isinstance(districts[ch], dict):
            if "name" not in districts[ch]:
                districts[ch]["name"] = f"District {ch}"
            if "type" not in districts[ch]:
                districts[ch]["type"] = "district"
            if "lore" not in districts[ch]:
                districts[ch]["lore"] = districts[ch].get("description", f"Functional zone for District {ch}.")

    # Validate and populate Features Registry (Structures / POIs)
    features = data.get("features")
    if not isinstance(features, dict):
        features = {}
    data["features"] = features

    cleaned_features = {}
    for feat_id, feat in features.items():
        if not isinstance(feat, dict):
            continue

        f_name = str(feat.get("name", str(feat_id).replace("_", " ").title()))
        f_type = str(feat.get("type", "structure"))
        f_char = str(feat.get("char", "X"))[:1]
        f_lore = str(feat.get("lore") or feat.get("description", "A regional structure."))

        # Extract tiles
        raw_tiles = feat.get("tiles")
        if raw_tiles is None and "pos" in feat:
            raw_tiles = [feat["pos"]]
        elif raw_tiles is None and "coord" in feat:
            raw_tiles = [feat["coord"]]

        valid_tiles: list[list[int]] = []
        if isinstance(raw_tiles, (list, tuple)):
            for pt in raw_tiles:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    try:
                        px, py = int(pt[0]), int(pt[1])
                        if 0 <= px < GRID_DIM and 0 <= py < GRID_DIM:
                            valid_tiles.append([px, py])
                    except (ValueError, TypeError):
                        continue

        cleaned_features[feat_id] = {
            "name": f_name,
            "type": f_type,
            "char": f_char,
            "tiles": valid_tiles,
            "lore": f_lore,
        }
    data["features"] = cleaned_features

    # Validate and populate Context & Architectural Rationale
    context = data.get("context")
    if not isinstance(context, dict):
        context = {}

    summary = (
        context.get("summary")
        or context.get("lore")
        or seed_meta.get("lore")
        or f"{data['name']} ({data['type']})."
    )
    host_region = (
        context.get("host_region")
        or seed_meta.get("host_region")
        or ""
    )
    scale_profile = (
        context.get("scale_profile")
        or context.get("scale")
        or seed_meta.get("scale_category")
        or ""
    )

    raw_perims = (
        context.get("perimeters")
        or context.get("surroundings")
        or seed_meta.get("perimeters")
        or []
    )
    if isinstance(raw_perims, str):
        perimeters = [raw_perims]
    elif isinstance(raw_perims, list):
        perimeters = [str(p).strip() for p in raw_perims if str(p).strip()]
    else:
        perimeters = []

    raw_apps = (
        context.get("approaches")
        or context.get("trade_and_access")
        or seed_meta.get("approaches")
        or []
    )
    approaches = []
    if isinstance(raw_apps, (list, tuple)):
        for a in raw_apps:
            if isinstance(a, dict):
                approaches.append(a)
            elif isinstance(a, str) and str(a).strip():
                approaches.append(str(a).strip())
    elif isinstance(raw_apps, (str, dict)):
        approaches = [raw_apps]

    # World Relations & Symbiosis
    world_relations = context.get("world_relations")
    if not world_relations or not str(world_relations).strip():
        if seed_meta.get("approaches"):
            dest_notes = []
            for app in seed_meta["approaches"]:
                if isinstance(app, dict):
                    d_dest = app.get("destination", "").replace("Leads toward ", "").strip()
                    d_lore = app.get("destination_lore", "").strip()
                    if d_dest and d_lore:
                        dest_notes.append(f"{d_dest} (\"{d_lore}\")")
            if dest_notes:
                world_relations = (
                    f"Maintains active regional interdependence and resource exchange with {'; '.join(dest_notes)}."
                )
            else:
                world_relations = "Interacts with bordering regions and connected trade paths to exchange local resources."
        else:
            world_relations = "An isolated landmark largely self-contained within its local wild perimeter."

    arch_rationale = (
        context.get("architectural_rationale")
        or context.get("rationale")
        or "Structures and functional zones are situated according to natural terrain boundaries and primary thoroughfare access."
    )

    data["context"] = {
        "summary": summary,
        "host_region": host_region,
        "scale_profile": scale_profile,
        "perimeters": perimeters,
        "approaches": approaches,
        "world_relations": world_relations,
        "architectural_rationale": arch_rationale,
    }

    # Remove any redundant legacy grids or metadata so JSON stores strictly map state and context
    data.pop("overview_grid", None)
    data.pop("views", None)
    data.pop("legend", None)
    data.pop("metadata", None)

    return data


def format_localemap_for_llm(data: dict[str, Any]) -> str:
    """Renders the localemap into an LLM-readable Markdown companion mirroring worldmap.md."""
    name = data.get("name", "Unknown Locale")
    fid = data.get("feature_id", "unknown")
    ltype = str(data.get("type", "settlement")).title()
    composite_grid = build_composite_grid(data)
    district_grid = data.get("district_grid", [])
    districts = data.get("districts", {})
    features = data.get("features", {})
    context = data.get("context", {})

    lines: list[str] = [
        f"# Locale Map: {name}",
        f"- **Feature ID:** `{fid}`",
        f"- **Classification:** {ltype}",
    ]

    host_region = context.get("host_region")
    if host_region:
        lines.append(f"- **Host Region:** {host_region}")

    scale_profile = context.get("scale_profile")
    if scale_profile:
        lines.append(f"- **Scale Profile:** {scale_profile}")

    lines.append(f"- **Registered Features:** {len(features)}")
    lines.append("")

    # Geographic & World Context
    summary = context.get("summary")
    perimeters = context.get("perimeters", [])
    approaches = context.get("approaches", [])
    world_relations = context.get("world_relations")
    arch_rationale = context.get("architectural_rationale")

    if summary or perimeters or approaches:
        lines.append("### Geographic & World Context")
        if summary:
            lines.append(f"- **Overview Lore:** {summary}")
        if perimeters:
            lines.append("- **Surrounding Perimeters:**")
            for p in perimeters:
                lines.append(f"  - {p}")
        if approaches:
            lines.append("- **External Ingress & Connected Destinations:**")
            for a in approaches:
                if isinstance(a, dict):
                    dir_name = a.get("direction") or a.get("approach", "Ingress")
                    r_name = a.get("road", "Path")
                    d_name = a.get("destination", "")
                    d_lore = a.get("destination_lore", "")
                    route_str = f"**{dir_name} Approach:** {r_name}" + (f" -> {d_name}" if d_name else "")
                    lines.append(f"  - {route_str}")
                    if d_lore:
                        lines.append(f"    - *Destination Context:* \"{d_lore}\"")
                else:
                    lines.append(f"  - {a}")
        lines.append("")

    if world_relations:
        lines.append("### World Relations & Material Flow")
        lines.append(world_relations)
        lines.append("")

    if arch_rationale:
        lines.append("### Architectural & Spatial Rationale")
        lines.append(arch_rationale)
        lines.append("")

    lines.append("### Map Inspection (Side-by-Side)")
    lines.append("```text")
    lines.append("    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]")
    lines.append("    0123456789012345                                     0123456789012345")

    for idx in range(max(len(composite_grid), len(district_grid))):
        c_row = composite_grid[idx] if idx < len(composite_grid) else " " * GRID_DIM
        d_row = district_grid[idx] if idx < len(district_grid) else " " * GRID_DIM
        lines.append(f"{idx:02d}: {c_row}                            |    {idx:02d}: {d_row}")

    lines.append("```")
    lines.append("")

    # Features Registry
    lines.append("### Features Registry")
    if not features:
        lines.append("*(No features registered yet)*")
    else:
        for f_id, f_data in sorted(features.items()):
            f_name = f_data.get("name", f_id)
            f_char = f_data.get("char", "X")
            f_type = f_data.get("type", "structure")
            f_lore = f_data.get("lore", "")
            tiles = f_data.get("tiles", [])

            if len(tiles) == 1:
                pos_str = f"Position: [X: {tiles[0][0]:02d}, Y: {tiles[0][1]:02d}]"
            elif len(tiles) > 1:
                min_x = min(t[0] for t in tiles)
                max_x = max(t[0] for t in tiles)
                min_y = min(t[1] for t in tiles)
                max_y = max(t[1] for t in tiles)
                pos_str = f"Footprint: {len(tiles)} tiles ([X: {min_x:02d}..{max_x:02d}, Y: {min_y:02d}..{max_y:02d}])"
            else:
                pos_str = "Position: Unplaced"

            lines.append(f"- ID '{f_id}': **{f_name}** ['{f_char}'] ({f_type})")
            lines.append(f"  - {pos_str}")
            if f_lore:
                lines.append(f"  - Lore: {f_lore}")
    lines.append("")

    # Districts Registry
    lines.append("### Districts Registry")
    for d_id in sorted(districts.keys()):
        d_info = districts[d_id]
        d_name = d_info.get("name", f"District {d_id}")
        d_type = d_info.get("type", "district")
        d_lore = d_info.get("lore", "")
        lines.append(f"- ID '{d_id}': **{d_name}** ({d_type})")
        if d_lore:
            lines.append(f"  - Lore: {d_lore}")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


class Subarchitect:
    """Subarchitect agent that designs 16x16 localemaps (terrain_grid, district_grid, features) from seeds."""

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        thinking_level: str = "MEDIUM",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("subarchitect_localemap.md")
        self.tools = [types.Tool(code_execution=types.ToolCodeExecution())]
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
    def generate_localemap(
        self,
        seed_text: str,
        keyframe_index: int = 0,
    ) -> dict[str, Any]:
        """Statelessly generates the 16x16 localemap JSON using code execution."""
        seed_meta = parse_seed_metadata(seed_text)

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            tools=self.tools,
        )

        user_content = (
            f"Please generate the 16x16 localemap JSON (terrain_grid, district_grid, districts, features) "
            f"for Keyframe {keyframe_index} using Python code execution according to the following locale seed:\n\n"
            f"{seed_text.strip()}"
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_content,
            config=config,
        )
        self._track_usage(response)

        text_content, code_output = extract_all_parts(response)
        combined_text = f"{code_output}\n\n{text_content}"

        parsed_data = (
            parse_localemap_json(code_output)
            or parse_localemap_json(text_content)
            or parse_localemap_json(combined_text)
        )

        if not parsed_data:
            raise ValueError(
                f"Failed to parse localemap JSON from Subarchitect code execution output.\n"
                f"Code Output preview:\n{code_output[:500]}\n"
                f"Text preview:\n{text_content[:500]}"
            )

        parsed_data["keyframe_index"] = keyframe_index
        validated_map = validate_localemap(parsed_data, seed_meta=seed_meta)
        return validated_map

    @staticmethod
    def save_localemap(
        map_data: dict[str, Any],
        output_path: Optional[Path | str] = None,
        base_dir: Optional[Path | str] = None,
    ) -> tuple[Path, Path]:
        """Saves validated localemap JSON and companion Markdown to disk."""
        kf_idx = map_data.get("keyframe_index", 0)
        json_filename = f"localemap_keyframe_{kf_idx}.json"

        if output_path:
            target_p = Path(output_path)
            if target_p.is_dir() or target_p.suffix == "":
                target_p.mkdir(parents=True, exist_ok=True)
                json_file = target_p / json_filename
            else:
                target_p.parent.mkdir(parents=True, exist_ok=True)
                json_file = target_p
        elif base_dir:
            base_p = Path(base_dir)
            base_p.mkdir(parents=True, exist_ok=True)
            json_file = base_p / json_filename
        else:
            fid = map_data.get("feature_id", "unknown")
            locale_dir = DEFAULT_LOCALES_DIR / fid
            locale_dir.mkdir(parents=True, exist_ok=True)
            json_file = locale_dir / json_filename

        json_file.write_text(json.dumps(map_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Companion Markdown
        md_file = json_file.with_suffix(".md")
        md_content = format_localemap_for_llm(map_data)
        md_file.write_text(md_content, encoding="utf-8")

        return json_file, md_file


# Alias for naming consistency
SubArchitect = Subarchitect


def print_localemap_preview(map_data: dict[str, Any]) -> None:
    """Pretty-prints side-by-side composite and district grid preview with registries."""
    name = map_data.get("name", "Unknown Locale")
    fid = map_data.get("feature_id", "")
    ltype = str(map_data.get("type", "settlement")).title()
    kf_idx = map_data.get("keyframe_index", 0)
    composite = build_composite_grid(map_data)
    district_grid = map_data.get("district_grid", [])
    districts = map_data.get("districts", {})
    features = map_data.get("features", {})

    print("\n" + "=" * 80)
    print(f" LOCALE: {name} (ID: {fid}, Type: {ltype}, Keyframe: {kf_idx})")
    print("=" * 80)

    print("\n[MAP INSPECTION: SIDE-BY-SIDE (16x16)]")
    print("    [--- COMPOSITE (Terrain + Features) ---]     [--- DISTRICT GRID (Zoning) ---]")
    print("    0123456789012345                             0123456789012345")
    for idx in range(max(len(composite), len(district_grid))):
        c_row = composite[idx] if idx < len(composite) else " " * GRID_DIM
        d_row = district_grid[idx] if idx < len(district_grid) else " " * GRID_DIM
        print(f"{idx:02d}: {c_row}                    |    {idx:02d}: {d_row}")

    print("\nREGISTERED FEATURES:")
    if not features:
        print("  *(No features registered)*")
    else:
        for f_id, f in sorted(features.items()):
            t_count = len(f.get("tiles", []))
            print(f"  ['{f.get('char')}'] {f.get('name')} ({f.get('type')}, {t_count} tiles) - \"{f.get('lore', '')}\"")

    print("\nDISTRICTS REGISTRY:")
    for d_id, d in sorted(districts.items()):
        print(f"  [{d_id}] {d.get('name')} ({d.get('type')}): \"{d.get('lore', '')}\"")

    print("=" * 80)


def main() -> None:
    """CLI entry point for the Subarchitect agent."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Procedurally generate 16x16 localemaps using the Subarchitect agent."
    )
    parser.add_argument(
        "--seed",
        "-s",
        "--input",
        "-i",
        type=str,
        default="",
        help="Path to a specific seed.md file.",
    )
    parser.add_argument(
        "--locale",
        "-f",
        "--feature",
        type=str,
        default="",
        help="Feature ID to generate (e.g. eldenmere). Searches in artifacts/locales/<feature>/seed.md.",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Generate localemaps for all seeds found in artifacts/locales.",
    )
    parser.add_argument(
        "--keyframe",
        "-k",
        type=int,
        default=0,
        help="Keyframe index to generate (default: 0)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="",
        help="Custom output file or directory path.",
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

    args = parser.parse_args()
    load_dotenv()

    seed_targets: list[tuple[Path, Path]] = []  # (seed_file, output_dir)

    if args.all:
        for seed_p in sorted(DEFAULT_LOCALES_DIR.glob("*/seed.md")):
            seed_targets.append((seed_p, seed_p.parent))
        if not seed_targets:
            print(f"[ERROR] No seed.md files found in {DEFAULT_LOCALES_DIR}", file=sys.stderr)
            sys.exit(1)
    elif args.seed:
        sp = Path(args.seed)
        if not sp.exists():
            print(f"[ERROR] Seed file not found: {sp}", file=sys.stderr)
            sys.exit(1)
        out_target = Path(args.output) if args.output else sp.parent
        seed_targets.append((sp, out_target))
    elif args.locale:
        sp = DEFAULT_LOCALES_DIR / args.locale / "seed.md"
        if not sp.exists():
            print(f"[ERROR] Locale seed not found at: {sp}", file=sys.stderr)
            sys.exit(1)
        out_target = Path(args.output) if args.output else sp.parent
        seed_targets.append((sp, out_target))
    else:
        # Default fallback: check eldenmere
        default_sp = DEFAULT_LOCALES_DIR / "eldenmere" / "seed.md"
        if default_sp.exists():
            seed_targets.append((default_sp, default_sp.parent))
        else:
            parser.print_help()
            sys.exit(1)

    print("=" * 80, flush=True)
    print(" SUBARCHITECT: 16x16 LOCALE MAP GENERATION", flush=True)
    print("=" * 80, flush=True)
    print(f"Model: {args.model} | Thinking: {args.thinking} | Code Execution: ON\n", flush=True)

    subarchitect = Subarchitect(model_name=args.model, thinking_level=args.thinking)

    for seed_path, out_dir in seed_targets:
        print(f"--> Processing seed: {seed_path}", flush=True)
        seed_text = seed_path.read_text(encoding="utf-8")

        try:
            locale_map = subarchitect.generate_localemap(seed_text=seed_text, keyframe_index=args.keyframe)
            json_file, md_file = subarchitect.save_localemap(
                locale_map,
                output_path=out_dir if out_dir.suffix else None,
                base_dir=out_dir if not out_dir.suffix else None,
            )

            print_localemap_preview(locale_map)
            print(f"JSON saved to:     {json_file}", flush=True)
            print(f"Markdown saved to: {md_file}\n", flush=True)

        except Exception as e:
            logger.exception("Error generating localemap")
            print(f"[ERROR] Failed to generate localemap for {seed_path}: {e}", file=sys.stderr)

    print("=" * 80, flush=True)
    print(" TOKEN USAGE SUMMARY", flush=True)
    print("=" * 80, flush=True)
    usage = subarchitect.token_usage
    print(f"Prompt Tokens:     {usage['prompt_tokens']:,}", flush=True)
    print(f"Candidate Tokens:  {usage['candidates_tokens']:,}", flush=True)
    if usage.get("thoughts_tokens"):
        print(f"Thoughts Tokens:   {usage['thoughts_tokens']:,}", flush=True)
    print(f"Total Tokens:      {usage['total_tokens']:,}", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
