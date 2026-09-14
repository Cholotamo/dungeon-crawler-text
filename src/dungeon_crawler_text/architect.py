"""Architect Agent module.

Crafts the 32x32 terrain and region geography from primordial world prose using Gemini LLM
with Python code execution enabled, running statelessly.
"""

import argparse
from collections import deque
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
from dungeon_crawler_text.world_state import format_world_for_llm

# Suppress the redundant SDK warning for stateless automatic function calling/code execution
try:
    from google.genai import models as _genai_models
    _genai_models.Models._logged_afc_warning = True
except Exception:
    pass

DEFAULT_INPUT_PROSE_PATH = Path("artifacts/worldprose.md")
DEFAULT_OUTPUT_MAP_PATH = Path("artifacts/worldmap.json")

VALID_TERRAIN_CHARS = {
    ".",  # Open Plains / Wilderness
    ",",  # Hills / Slopes
    "#",  # Forest / Woods
    "&",  # Dense Forest / Deep Jungle
    "%",  # Swamp / Bog / Marsh
    "~",  # Water / River / Ocean
    ";",  # Coast / Beach / Shallows
    "^",  # Mountain Peak / Ridge
    "/",  # Cliffs / Edges / Chasms
    "*",  # Wastelands / Barrier / Dam
    ":",  # Farmland
}


def _load_prompt(filename: str = "architect_worldmap.md") -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


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


def parse_world_map_json(raw_text: str) -> Optional[dict[str, Any]]:
    """Attempts to extract and parse the world map JSON dictionary from text or stdout."""
    # 1. Try explicit delimiter extraction
    delimiter_match = re.search(
        r"___WORLD_MAP_START___\s*(\{.*?\})\s*___WORLD_MAP_END___",
        raw_text,
        re.DOTALL,
    )
    if delimiter_match:
        try:
            return json.loads(delimiter_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Try markdown fenced code block extraction
    code_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    for block in code_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and "terrain_grid" in data:
                return data
        except json.JSONDecodeError:
            continue

    # 3. Try outermost curly braces enclosing terrain_grid
    outer_match = re.search(r"(\{\s*\"name\".*\"terrain_grid\".*?\})", raw_text, re.DOTALL)
    if outer_match:
        try:
            data = json.loads(outer_match.group(1))
            if isinstance(data, dict) and "terrain_grid" in data:
                return data
        except json.JSONDecodeError:
            pass

    # 4. Fallback search for any JSON object containing terrain_grid
    start_idx = raw_text.find("{")
    while start_idx != -1:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(raw_text[start_idx:])
            if isinstance(obj, dict) and "terrain_grid" in obj:
                return obj
        except json.JSONDecodeError:
            pass
        start_idx = raw_text.find("{", start_idx + 1)

    return None


def enforce_river_monotonicity(
    terrain: list[str],
    region: list[str],
    regions: dict[str, Any],
    elev_grid: list[list[int]],
) -> list[list[int]]:
    """Enforces strictly non-increasing downstream elevation along all connected river paths."""
    height = len(terrain)
    width = len(terrain[0]) if height > 0 else 0
    if height == 0 or width == 0:
        return elev_grid

    river_tiles = [
        (x, y) for y in range(height) for x in range(width)
        if terrain[y][x] in ("~", ";") and regions.get(region[y][x], {}).get("type", "").lower() in ("river", "stream")
    ]
    if not river_tiles:
        return elev_grid

    all_water = {(x, y) for y in range(height) for x in range(width) if terrain[y][x] in ("~", ";")}

    # Tier 1: True Marine Sinks (Ocean, Bay)
    sinks = {
        (x, y) for (x, y) in all_water
        if regions.get(region[y][x], {}).get("type", "").lower() in ("ocean", "bay")
    }
    # Tier 2: Continental South edge or other map boundaries if no ocean
    if not sinks:
        sinks = {(x, y) for (x, y) in all_water if y == height - 1}
    if not sinks:
        sinks = {(x, y) for (x, y) in all_water if x in (0, width - 1) or y in (0, height - 1)}
    # Tier 3: Inland Lake sinks
    if not sinks:
        for x, y in river_tiles:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if regions.get(region[ny][nx], {}).get("type", "").lower() == "lake":
                        sinks.add((nx, ny))
    if not sinks and river_tiles:
        sinks = {max(river_tiles, key=lambda pt: pt[1])}

    dist: dict[tuple[int, int], int] = {pt: 0 for pt in sinks}
    q = deque(sinks)
    while q:
        cx, cy = q.popleft()
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in all_water and (nx, ny) not in dist:
                dist[(nx, ny)] = dist[(cx, cy)] + 1
                q.append((nx, ny))

    sorted_rivers = sorted(river_tiles, key=lambda pt: dist.get(pt, 0), reverse=True)

    # Downstream clamping pass: from headwaters to mouth
    for cx, cy in sorted_rivers:
        curr_z = elev_grid[cy][cx]
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in dist and dist[(nx, ny)] < dist.get((cx, cy), 0):
                if elev_grid[ny][nx] > curr_z:
                    elev_grid[ny][nx] = curr_z

    return elev_grid


def generate_fallback_elevation(
    terrain: list[str],
    region: list[str],
    regions: dict[str, Any],
) -> list[str]:
    """Procedurally generates a 32x32 elevation grid when not supplied by the Architect."""
    height = len(terrain)
    width = len(terrain[0]) if height > 0 else 32

    REGION_BASE = {
        "mountains": 8, "mountain": 8,
        "cliffs": 6, "chasm": 6, "canyon": 6,
        "hills": 5, "highland": 5,
        "forest": 3, "jungle": 3, "woods": 3,
        "wilderness": 2, "plains": 2, "farmland": 2, "wasteland": 2,
        "river": 1, "stream": 1, "canal": 1,
        "lake": 1, "bay": 0, "swamp": 1, "wetland": 1, "bog": 1,
        "ocean": 0, "sea": 0,
    }
    TERRAIN_BASE = {
        "^": 9, "/": 7, ",": 5, "&": 4, "#": 3,
        ":": 2, ".": 2, "%": 1, ";": 1, "~": 0,
    }

    # 1. Base terrain elevation calculation
    elev = [[0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            t_char = terrain[y][x]
            r_type = regions.get(region[y][x], {}).get("type", "").lower()
            r_b = REGION_BASE.get(r_type, 2)
            t_b = TERRAIN_BASE.get(t_char, 2)
            base = (r_b + t_b) / 2.0
            slope = (height - 1 - y) / height * 2.0
            lvl = int(round(base + slope))
            elev[y][x] = max(0, min(9, lvl))

    # 2. Sinks and distance for river flow gradient
    water_tiles = [(x, y) for y in range(height) for x in range(width) if terrain[y][x] in ("~", ";")]
    sinks = set()
    for x, y in water_tiles:
        r_type = regions.get(region[y][x], {}).get("type", "").lower()
        if r_type in ("ocean", "bay") or y == height - 1 or x in (0, width - 1):
            sinks.add((x, y))

    if not sinks and water_tiles:
        sinks.add(max(water_tiles, key=lambda pt: pt[1]))

    dist_to_sink: dict[tuple[int, int], int] = {pt: 0 for pt in sinks}
    q = deque(sinks)
    while q:
        cx, cy = q.popleft()
        d = dist_to_sink[(cx, cy)]
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in water_tiles and (nx, ny) not in dist_to_sink:
                dist_to_sink[(nx, ny)] = d + 1
                q.append((nx, ny))

    # River tiles: scale elevation monotonically by distance to sink
    river_tiles = [
        (x, y) for (x, y) in water_tiles
        if regions.get(region[y][x], {}).get("type", "").lower() in ("river", "stream")
    ]
    if river_tiles and dist_to_sink:
        max_dist = max(dist_to_sink.get(pt, 0) for pt in river_tiles) or 1
        for x, y in river_tiles:
            d = dist_to_sink.get((x, y), 0)
            land_neighbors = [
                elev[y + dy][x + dx]
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                if 0 <= x + dx < width and 0 <= y + dy < height and terrain[y + dy][x + dx] not in ("~", ";")
            ]
            headwater_z = max(land_neighbors) if land_neighbors else 6
            max_river_z = max(2, min(headwater_z - 1, 6))
            r_elev = 1 + int(round((d / max_dist) * (max_river_z - 1)))
            elev[y][x] = max(1, min(9, r_elev))

    elev = enforce_river_monotonicity(terrain, region, regions, elev)
    return ["".join(str(elev[y][x]) for x in range(width)) for y in range(height)]


def validate_world_map(data: dict[str, Any]) -> dict[str, Any]:
    """Validates and enforces map dimensions, legends, and registry integrity."""
    if not isinstance(data, dict):
        raise ValueError("World map data must be a dictionary.")

    # Realm Name
    if not data.get("name") or not isinstance(data["name"], str):
        data["name"] = "The Primordial Realm"

    # Terrain Grid
    terrain = data.get("terrain_grid")
    if not isinstance(terrain, list) or len(terrain) != 32:
        raise ValueError(
            f"terrain_grid must contain exactly 32 rows, got {len(terrain) if isinstance(terrain, list) else type(terrain)}"
        )
    for y, row in enumerate(terrain):
        if not isinstance(row, str) or len(row) != 32:
            raise ValueError(f"terrain_grid row {y} must have length 32, got len={len(row) if isinstance(row, str) else type(row)}")

    # Region Grid
    region = data.get("region_grid")
    if not isinstance(region, list) or len(region) != 32:
        raise ValueError(
            f"region_grid must contain exactly 32 rows, got {len(region) if isinstance(region, list) else type(region)}"
        )
    for y, row in enumerate(region):
        if not isinstance(row, str) or len(row) != 32:
            raise ValueError(f"region_grid row {y} must have length 32, got len={len(row) if isinstance(row, str) else type(row)}")

    # Regions Registry
    regions = data.setdefault("regions", {})
    if not isinstance(regions, dict):
        regions = {}
        data["regions"] = regions

    # Ensure default wilderness '0'
    if "0" not in regions or not isinstance(regions["0"], dict):
        regions["0"] = {
            "name": "Unnamed Wilderness",
            "type": "wilderness",
            "lore": "Untamed and primeval wilderness connecting the distinct geographic landmarks of the realm.",
        }
    else:
        if "name" not in regions["0"]:
            regions["0"]["name"] = "Unnamed Wilderness"
        if "type" not in regions["0"]:
            regions["0"]["type"] = "wilderness"
        if "lore" not in regions["0"]:
            regions["0"]["lore"] = regions["0"].get(
                "description",
                "Untamed and primeval wilderness connecting the distinct geographic landmarks of the realm.",
            )

    # Ensure all region characters in region_grid exist in regions registry
    used_region_chars = {char for row in region for char in row}
    for char in used_region_chars:
        if char not in regions or not isinstance(regions[char], dict):
            regions[char] = {
                "name": f"Region {char}",
                "type": "wilderness",
                "lore": f"Wild and uncharted territory designated as Region {char}.",
            }
        else:
            r_info = regions[char]
            if "name" not in r_info:
                r_info["name"] = f"Region {char}"
            if "type" not in r_info:
                r_info["type"] = "wilderness"
            if "lore" not in r_info:
                r_info["lore"] = r_info.get("description", "")

    # Features: strictly empty dictionary for primordial stage
    data["features"] = {}

    # Elevation Grid: 32 strings of 32 characters representing topographical heights ('0'-'9')
    elev = data.get("elevation_grid")
    valid_elev = False
    if isinstance(elev, list) and len(elev) == 32:
        if all(isinstance(row, str) and len(row) == 32 and all(ch.isdigit() for ch in row) for row in elev):
            int_grid = [[int(ch) for ch in row] for row in elev]
            int_grid = enforce_river_monotonicity(terrain, region, regions, int_grid)
            data["elevation_grid"] = ["".join(str(min(9, max(0, val))) for val in row) for row in int_grid]
            valid_elev = True
        elif all(isinstance(row, (list, tuple)) and len(row) == 32 for row in elev):
            try:
                int_grid = [[int(val) for val in row] for row in elev]
                int_grid = enforce_river_monotonicity(terrain, region, regions, int_grid)
                data["elevation_grid"] = [
                    "".join(str(min(9, max(0, val))) for val in row)
                    for row in int_grid
                ]
                valid_elev = True
            except (ValueError, TypeError):
                valid_elev = False

    if not valid_elev:
        data["elevation_grid"] = generate_fallback_elevation(terrain, region, regions)

    return data


class Architect:
    """Architect agent that designs the physical 32x32 world map geography from narrative prose."""

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        thinking_level: str = "MEDIUM",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("architect_worldmap.md")
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
    def generate_world_map(self, worldprose: str) -> dict[str, Any]:
        """Statelessly generates the 32x32 world map JSON from primordial world prose."""
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            tools=self.tools,
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=worldprose.strip(),
            config=config,
        )
        self._track_usage(response)

        text_content, code_output = extract_all_parts(response)
        combined_text = f"{code_output}\n\n{text_content}"

        # Direct extraction: check code execution result output first, then text fallback
        parsed_data = parse_world_map_json(code_output) or parse_world_map_json(text_content) or parse_world_map_json(combined_text)

        if not parsed_data:
            raise ValueError(
                f"Failed to parse world map JSON from Architect code execution output.\n"
                f"Code Output preview:\n{code_output[:500]}\n"
                f"Text preview:\n{text_content[:500]}"
            )

        validated_map = validate_world_map(parsed_data)
        return validated_map

    @staticmethod
    def save_world_map(map_data: dict[str, Any], output_path: Path = DEFAULT_OUTPUT_MAP_PATH) -> Path:
        """Saves the validated world map dictionary to disk as JSON and LLM-readable Markdown."""
        if output_path.is_dir() or output_path.suffix == "":
            output_path.mkdir(parents=True, exist_ok=True)
            target_file = output_path / "worldmap.json"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            target_file = output_path

        target_file.write_text(json.dumps(map_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Save LLM-readable Markdown companion right after JSON
        md_file = target_file.with_suffix(".md")
        md_content = format_world_for_llm(map_data)
        md_file.write_text(md_content, encoding="utf-8")

        return target_file


def print_map_preview(map_data: dict[str, Any]) -> None:
    """Prints a visual ASCII render and regional breakdown of the generated map."""
    print("\n" + "=" * 68)
    print(f" REALM: {map_data.get('name', 'Unknown Realm')}")
    print("=" * 68)
    print("TERRAIN GRID (32x32):")
    print("    01234567890123456789012345678901")
    for idx, row in enumerate(map_data["terrain_grid"]):
        print(f"{idx:02d}: {row}")

    print("\nREGION REGISTRY:")
    for rid, info in sorted(map_data.get("regions", {}).items()):
        lore = info.get("lore", "")
        lore_snippet = f" - \"{lore[:60]}...\"" if len(lore) > 60 else (f" - \"{lore}\"" if lore else "")
        print(f"  [{rid}] {info.get('name')} ({info.get('type')}){lore_snippet}")

    if "elevation_grid" in map_data and map_data["elevation_grid"]:
        eg = map_data["elevation_grid"]
        all_z = [int(ch) for row in eg for ch in row if ch.isdigit()]
        if all_z:
            print(f"\nELEVATION PROFILE: min={min(all_z)} (lowest), max={max(all_z)} (highest), avg={sum(all_z)/len(all_z):.1f}")
    print("=" * 68)


def main() -> None:
    """CLI entry point for generating the world map with the Architect agent."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Generate a 32x32 world map geography from primordial world prose using the Architect agent."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(DEFAULT_INPUT_PROSE_PATH),
        help=f"Path to input world prose markdown file (default: {DEFAULT_INPUT_PROSE_PATH})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(DEFAULT_OUTPUT_MAP_PATH),
        help=f"Path to save output world map JSON file (default: {DEFAULT_OUTPUT_MAP_PATH})",
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

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input world prose file not found at: {input_path}", file=sys.stderr)
        sys.exit(1)

    worldprose = input_path.read_text(encoding="utf-8")

    print("=" * 80, flush=True)
    print(" ARCHITECT: PRIMORDIAL MAP GEOGRAPHY GENERATION", flush=True)
    print("=" * 80, flush=True)
    print(f"\nInitializing Architect agent ({args.model}, thinking={args.thinking}, code_execution=ON)...", flush=True)

    architect = Architect(model_name=args.model, thinking_level=args.thinking)

    print(f"\nReading world prose from: {input_path} ({len(worldprose)} chars)...", flush=True)
    print("Generating 32x32 terrain and region geography...", flush=True)

    try:
        world_map = architect.generate_world_map(worldprose=worldprose)
        output_file = architect.save_world_map(world_map, output_path=Path(args.output))

        print_map_preview(world_map)
        print(f"\nWorld map JSON successfully saved to:     {output_file}", flush=True)
        print(f"World map Markdown successfully saved to: {output_file.with_suffix('.md')}", flush=True)

        print("\n" + "=" * 80, flush=True)
        print(" TOKEN USAGE SUMMARY", flush=True)
        print("=" * 80, flush=True)
        usage = architect.token_usage
        print(f"Prompt Tokens:     {usage['prompt_tokens']:,}", flush=True)
        print(f"Candidate Tokens:  {usage['candidates_tokens']:,}", flush=True)
        if usage.get("thoughts_tokens"):
            print(f"Thoughts Tokens:   {usage['thoughts_tokens']:,}", flush=True)
        print(f"Total Tokens:      {usage['total_tokens']:,}", flush=True)
        print("=" * 80, flush=True)

    except Exception as e:
        print(f"\n[ERROR] Architect map generation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
