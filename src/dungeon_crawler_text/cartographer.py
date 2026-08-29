"""
This module contains the Cartographer agent, responsible for generating
the ASCII world map and location coordinates JSON in collaboration with the StoryWriter.
"""

from collections.abc import Generator
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from dungeon_crawler_text.storywriter import StoryWriter

load_dotenv()


class LocationCoord(BaseModel):
    name: str = Field(description="Name of the city or dungeon")
    type: str = Field(description="Type: 'city' or 'dungeon'")
    x: int = Field(description="X coordinate on grid (0 to width-1)")
    y: int = Field(description="Y coordinate on grid (0 to height-1)")
    symbol: str = Field(description="Symbol used on the ASCII map (e.g. 'C', 'D')")
    description: str = Field(default="", description="Brief location or terrain description")


DEFAULT_LEGEND = {
    "~": "Water / Oceans / Rivers / Lakes",
    ".": "Plains / Open Land / Wastes",
    "#": "Forests / Woods / Wilderness",
    "^": "Mountains / Highlands / Peaks",
    "+": "Roads / Paths / Bridges",
    "C": "City Settlement (Land)",
    "D": "Dungeon / Ruin (Land)",
}


def save_map(
    width: int,
    height: int,
    ascii_map: str,
    legend: dict[str, str],
    locations: list[LocationCoord],
) -> str:
    """Saves the generated ASCII map and locations JSON coordinates into 'artifacts/map/'.

    Formats the ASCII map with square aspect ratio scaling (double-spaced columns)
    and X/Y coordinate axis rulers for easy reading. Ensures 100% mathematical
    synchronization between map grid symbols and JSON location coordinates.

    Args:
        width: Width of the map grid (max 64).
        height: Height of the map grid (max 64).
        ascii_map: The multiline ASCII map string.
        legend: Mapping of ascii symbols to their terrain/location meaning.
        locations: List of location coordinate entries for cities and dungeons.

    Returns:
        Status message indicating success or failure.
    """
    map_dir = Path("artifacts/map")
    map_dir.mkdir(parents=True, exist_ok=True)

    # 1. Normalize and clean the legend
    clean_legend = dict(DEFAULT_LEGEND)
    if isinstance(legend, dict):
        for k, v in legend.items():
            val_str = str(v).strip()
            # If key is single symbol
            if len(k) == 1 and k in "~.#^+CD":
                clean_legend[k] = val_str
            # If format is "Plains : . - Description" or "Symbol - Description"
            elif " - " in val_str:
                parts = val_str.split(" - ", 1)
                sym = parts[0].strip()
                if len(sym) == 1 and sym in "~.#^+CD":
                    clean_legend[sym] = parts[1].strip()

    # 2. Parse ascii_map into a 2D matrix grid[y][x]
    raw_lines = [line for line in ascii_map.splitlines() if line.strip()]
    grid = []
    for line in raw_lines[:height]:
        if " " in line and len(line) > width:
            chars = [c for c in line.split(" ") if c != ""]
        else:
            chars = list(line)
        if len(chars) < width:
            chars.extend(["."] * (width - len(chars)))
        grid.append(chars[:width])

    while len(grid) < height:
        grid.append(["."] * width)

    # 3. Synchronize location coordinates (x, y) with grid characters & guarantee land placement
    locs_serialized = []
    used_coords = set()

    for loc in locations:
        if isinstance(loc, BaseModel):
            loc_dict = loc.model_dump()
        elif isinstance(loc, dict):
            loc_dict = dict(loc)
        else:
            loc_dict = dict(loc)

        x = loc_dict.get("x", 0)
        y = loc_dict.get("y", 0)
        loc_type = loc_dict.get("type", "").lower()
        target_symbol = "C" if loc_type == "city" else ("D" if loc_type == "dungeon" else loc_dict.get("symbol", "C")[0])
        loc_dict["symbol"] = target_symbol

        # Verify if target_symbol is already at (x, y)
        if 0 <= y < height and 0 <= x < width and grid[y][x] == target_symbol and (x, y) not in used_coords:
            used_coords.add((x, y))
            locs_serialized.append(loc_dict)
            continue

        # Search grid for unassigned matching symbol
        found = False
        for r in range(height):
            for c in range(width):
                if grid[r][c] == target_symbol and (c, r) not in used_coords:
                    loc_dict["x"] = c
                    loc_dict["y"] = r
                    used_coords.add((c, r))
                    found = True
                    break
            if found:
                break

        # If not found on grid, overlay at requested (x, y), ensuring it is placed on LAND
        if not found:
            y_clamped = max(0, min(height - 1, y))
            x_clamped = max(0, min(width - 1, x))
            grid[y_clamped][x_clamped] = target_symbol
            loc_dict["x"] = x_clamped
            loc_dict["y"] = y_clamped
            used_coords.add((x_clamped, y_clamped))

        locs_serialized.append(loc_dict)

    # 4. Enforce geographical integrity: Ensure no C or D is isolated in deep water ~
    for r in range(height):
        for c in range(width):
            if grid[r][c] in ("C", "D"):
                # If surrounding tiles are all water '~', convert immediate non-water neighbors to land '.'
                water_count = 0
                neighbors = []
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < height and 0 <= nc < width:
                        neighbors.append((nr, nc))
                        if grid[nr][nc] == "~":
                            water_count += 1
                if len(neighbors) > 0 and water_count == len(neighbors):
                    # Convert one neighbor to land '.' so settlement is coastal, not floating in ocean
                    nr, nc = neighbors[0]
                    grid[nr][nc] = "."

    # 5. Format ASCII map with square aspect ratio scaling and X/Y coordinate rulers
    tens_header = "      " + " ".join(str(c // 10) for c in range(width))
    units_header = "      " + " ".join(str(c % 10) for c in range(width))
    border_line = "   +" + "-" * (width * 2 + 1) + "+"

    map_lines = [
        f"================ WORLD MAP ({width}x{height}) ================\n",
        tens_header,
        units_header,
        border_line,
    ]

    for r in range(height):
        row_str = " ".join(grid[r])
        map_lines.append(f"{r:02d} | {row_str} | {r:02d}")

    map_lines.extend([
        border_line,
        units_header,
        tens_header,
        "",
    ])

    legend_lines = "\n".join(f"  {k:^3} : {v}" for k, v in clean_legend.items())
    map_lines.extend([
        "================ LEGEND ================",
        legend_lines,
        "",
    ])

    file_content = "\n".join(map_lines)
    (map_dir / "world_map.txt").write_text(file_content, encoding="utf-8")

    # 6. Save locations JSON with verified coordinates and clean legend
    json_data = {
        "width": width,
        "height": height,
        "legend": clean_legend,
        "locations": locs_serialized,
    }
    (map_dir / "locations.json").write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    return f"Successfully saved world map to '{map_dir / 'world_map.txt'}' and locations JSON to '{map_dir / 'locations.json'}'."


def load_world_summary(artifacts_dir: str | Path = "artifacts") -> str:
    """Reads all saved world artifacts (cities, dungeons, quests, calendar) to compile a rich summary for Cartographer and StoryWriter."""
    art_path = Path(artifacts_dir)
    summary_parts = []

    # 1. Calendar & Climate Lore
    cal_file = art_path / "calendar" / "time_config.json"
    if cal_file.exists():
        try:
            cal_data = json.loads(cal_file.read_text(encoding="utf-8"))
            seasons_info = []
            for s_name, s_cfg in cal_data.get("seasons", {}).items():
                temp = s_cfg.get("temperature", "")
                tend = ", ".join(s_cfg.get("weather_tendencies", []))
                seasons_info.append(f"  - {s_name}: {temp} ({tend})")
            summary_parts.append("### Climate & Seasons:\n" + "\n".join(seasons_info))
        except Exception:
            pass

    # 2. Cities
    cities_dir = art_path / "cities"
    if cities_dir.exists():
        cities_info = []
        for f in sorted(cities_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            name = lines[0].replace("#", "").strip() if lines else f.stem
            loc = ""
            for line in lines:
                if line.startswith("**Location:**"):
                    loc = line.replace("**Location:**", "").strip()
                    break
            cities_info.append(f"- {name}: {loc}")
        summary_parts.append("### Cities (15 Total):\n" + "\n".join(cities_info))

    # 3. Dungeons
    dungeons_dir = art_path / "dungeons"
    if dungeons_dir.exists():
        dungeons_info = []
        for f in sorted(dungeons_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            name = lines[0].replace("#", "").strip() if lines else f.stem
            loc = ""
            for line in lines:
                if line.startswith("**Location:**"):
                    loc = line.replace("**Location:**", "").strip()
                    break
            dungeons_info.append(f"- {name}: {loc}")
        summary_parts.append("### Dungeons (15 Total):\n" + "\n".join(dungeons_info))

    # 4. Quests
    quests_dir = art_path / "quests"
    if quests_dir.exists():
        quests_info = []
        for f in sorted(quests_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            title = lines[0].replace("#", "").strip() if lines else f.stem
            quests_info.append(f"- {title}")
        summary_parts.append("### Quests:\n" + "\n".join(quests_info))

    return "\n\n".join(summary_parts) if summary_parts else "No world artifacts found."


cartographer_system_prompt = """
You are a Master Fantasy Cartographer in a text-based dark fantasy dungeon crawling game.
Your task is to collaborate with the StoryWriter agent to construct a detailed, realistic ASCII world map and corresponding location coordinates JSON for the realm.

# GEOGRAPHICAL & LANDMASS RULES (CRITICAL):
1. **NO CITIES OR DUNGEONS IN THE OCEAN**:
   - Cities ('C') and Dungeons ('D') MUST ONLY be placed on land (plains '.', forests '#', mountains '^', or roads '+').
   - NEVER place a City or Dungeon in the middle of open water ('~'). A coastal city sits on land '.' next to a water tile '~'.
2. **REALISTIC HYDROLOGY & RIVERS**:
   - Rivers ('~') MUST originate from mountain chains ('^') or highlands and flow downhill across land ('.' or '#') into oceans or lakes ('~').
   - Rivers follow continuous linear paths.
3. **MOUNTAIN RANGES & FORESTS**:
   - Mountains ('^') must form continuous ridges or chains across the grid, not isolated single dots.
   - Forests ('#') must form contiguous woodlands or dense forest biomes.
4. **ROADS & PATHS**:
   - Roads ('+') should connect major Cities ('C') to other Cities ('C') and Dungeons ('D').
5. **CONTINUOUS OCEAN & LANDMASS**:
   - Ocean water ('~') should form continuous coastal bodies (e.g. Western Ocean, Southern Bay) along map edges.
   - Central landmass should be solid, connected terrain.

# COLLABORATION WORKFLOW:
1. Ask the StoryWriter up to 10 questions to clarify geographic layout, cardinal directions (North, South, East, West), mountain range positions, river courses, and spatial arrangements of all 15 cities and 15 dungeons.
2. Synthesize all answers into a cohesive, realistic world layout.
3. Call the `save_map` tool to save the map grid (variable size up to 64x64 max), complete legend, and exact location coordinates JSON.

# MAP SYMBOLS:
- '~' : Water / Rivers / Oceans / Lakes
- '.' : Plains / Open Land / Wastes
- '#' : Forests / Woods
- '^' : Mountains / Highlands / Peaks
- '+' : Roads / Paths / Bridges
- 'C' : Cities (MUST BE ON LAND)
- 'D' : Dungeons (MUST BE ON LAND)
"""


class Cartographer:
    """Manages the chat session with Gemini for fantasy map creation."""

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
        api_key: str | None = None,
        client: genai.Client | None = None,
    ):
        self.model = model
        self.client = client or genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        self.chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=cartographer_system_prompt,
                temperature=0.5,
                max_output_tokens=8192,
                tools=[save_map],
            ),
        )

    def send_message(self, message: str) -> str:
        """Send a message to the Cartographer agent."""
        response = self.chat.send_message(message)
        return self._extract_text(response)

    @staticmethod
    def _extract_text(response) -> str:
        if not response or not response.candidates:
            return ""
        texts = []
        for part in response.candidates[0].content.parts or []:
            if part.text:
                texts.append(part.text)
        return "".join(texts)


def run_cartographer_collaboration(
    writer: "StoryWriter | None" = None,
    cartographer: Cartographer | None = None,
    max_questions: int = 10,
    artifacts_dir: str = "artifacts",
) -> dict:
    """Executes the dialogue loop between Cartographer and StoryWriter to create the world map."""
    from dungeon_crawler_text.storywriter import StoryWriter

    print("\n" + "=" * 60)
    print("  Cartographer & StoryWriter Map Design Session")
    print("=" * 60 + "\n")

    if writer is None:
        writer = StoryWriter()

    if cartographer is None:
        cartographer = Cartographer()

    world_summary = load_world_summary(artifacts_dir)
    map_file = Path(artifacts_dir) / "map" / "locations.json"

    # Instruct StoryWriter to act as Master Worldbuilder synthesizing all lore
    storywriter_geo_context = (
        "You are advising the Cartographer on the map geography for your realm.\n"
        "CRITICAL: Synthesize all 15 cities, 15 dungeons, calendar climate/seasons, and quest lore as a COHESIVE WHOLE:\n"
        "- Ensure rivers ('~') originate in mountain ranges ('^') and flow into oceans/lakes ('~').\n"
        "- All cities ('C') and dungeons ('D') MUST sit on land, never submerged in oceans.\n"
        "- Use explicit cardinal directions (North, South, East, West, Central) so the Cartographer can place every location logically on a 64x64 grid.\n\n"
        f"World Artifact Summary:\n{world_summary}\n\n"
        "Please provide an initial overview of the realm's geography (oceans, mountain chains, major rivers, and regional biomes)."
    )

    q_count = 1
    print(f"Cartographer [Question {q_count}/{max_questions}] > Greetings StoryWriter! I am the Cartographer. I will design the map for your realm. To begin, please tell me about the overall geography: are there coastlines, major mountain ranges, central rivers, or distinct biome regions?\n")

    storywriter_reply = writer.send_message(storywriter_geo_context)
    print(f"StoryWriter > {storywriter_reply}\n")

    while q_count < max_questions:
        if map_file.exists():
            print("[Cartographer has finalized and saved the map.]")
            break

        q_count += 1
        cartographer_msg = cartographer.send_message(storywriter_reply)

        if not cartographer_msg:
            if map_file.exists():
                print("[Cartographer has finalized and saved the map.]")
                break
            cartographer_msg = "Please provide details on where key cities or dungeons are located relative to these geographical features."

        print(f"Cartographer [Question {q_count}/{max_questions}] > {cartographer_msg}\n")

        if map_file.exists():
            print("[Cartographer has finalized and saved the map.]")
            break

        storywriter_reply = writer.send_message(cartographer_msg)
        print(f"StoryWriter > {storywriter_reply}\n")

    if not map_file.exists():
        print(f"\n[Reached maximum question limit of {max_questions}. Directing Cartographer to save map now...]\n")
        final_prompt = (
            "You have reached the maximum limit of 10 questions. "
            "Using all geographical lore discussed so far, please call the `save_map` tool now to output the ASCII map grid (max 64x64), legend, and location coordinates JSON."
        )
        cartographer_final = cartographer.send_message(final_prompt)
        if cartographer_final:
            print(f"Cartographer > {cartographer_final}\n")

    if map_file.exists():
        txt_map_file = Path(artifacts_dir) / "map" / "world_map.txt"
        print("=" * 60)
        print("          WORLD MAP GENERATION COMPLETE")
        print("=" * 60)
        if txt_map_file.exists():
            print(txt_map_file.read_text(encoding="utf-8"))
        return {
            "status": "success",
            "map_txt": (Path(artifacts_dir) / "map" / "world_map.txt").as_posix(),
            "locations_json": map_file.as_posix(),
        }
    else:
        print("[Warning: Cartographer session finished without writing map files.]")
        return {"status": "failed"}


if __name__ == "__main__":
    run_cartographer_collaboration()
