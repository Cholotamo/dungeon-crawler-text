"""Cartographer Agent module.

Translates ongoing historical chronicles into 32x32 ASCII world maps using Gemini LLM
and mutates persistent world state snapshots (world_epoch_latest.json) via dedicated tools.
"""

from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from dungeon_crawler_text.tools import CartographerTools
from dungeon_crawler_text.world_state import WorldStateManager


def _load_prompt(filename: str) -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


class Cartographer:
    """Cartographer agent that maintains and updates the persistent 32x32 world map

    based on narrative input from the Historian.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.7-flash",
        thinking_level: str = "HIGH",
        client: Optional[genai.Client] = None,
        manager: Optional[WorldStateManager] = None,
        tools: Optional[CartographerTools] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.manager = manager or WorldStateManager()
        self.tools = tools or CartographerTools(self.manager)
        self.system_prompt = _load_prompt("Cartographer.md")

        tool_functions = [
            self.tools.initialize_world,
            self.tools.add_point_location,
            self.tools.modify_terrain,
            self.tools.build_road,
            self.tools.update_location_status,
            self.tools.commit_epoch_snapshot,
            self.tools.inspect_map,
            self.tools.get_world_overview,
            self.tools.inspect_tile,
            self.tools.get_location_details,
        ]

        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.7,
                thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
                tools=tool_functions,
            ),
        )

    def start_chronicle(self) -> str:
        """Returns the initial query asking the Historian for the lay of the land."""
        return (
            "What is the lay of the land? Describe the foundational geography "
            "(oceans, mountain chains, hills, major rivers, and ancient forests) of this world."
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def process_narrative(self, historian_narrative: str, epoch: int = 1) -> str:
        """Sends the Historian's narrative to Gemini, executes world state mutations via tools,

        and returns the cartographer's response log and updated map.
        """
        if epoch == 1:
            prompt = (
                f"Epoch 1 Primordial Landscape Description:\n{historian_narrative}\n\n"
                f"[Cartographer Directive]: Synthesize this landscape into a 32x32 baseline ASCII map. "
                f"Call initialize_world(realm_name, grid_ascii, locations_json) to create world_epoch_1.json "
                f"and world_epoch_latest.json. Provide your rendered map, Cartographic Log, and follow-up query."
            )
        else:
            prompt = (
                f"Epoch {epoch} Historical Chronicle:\n{historian_narrative}\n\n"
                f"[Cartographer Directive]: Parse the coordinate tags [X: xx, Y: yy] and apply state transformations "
                f"using your tools (add_point_location, modify_terrain, build_road, update_location_status). "
                f"You MUST call commit_epoch_snapshot(epoch={epoch}, notes=...) to persist world_epoch_{epoch}.json "
                f"and overwrite world_epoch_latest.json. Provide your rendered map, Cartographic Log, and follow-up query."
            )

        response = self.chat.send_message(prompt)
        text = response.text or ""

        # Persistence check: Ensure world_epoch_{epoch}.json and world_epoch_latest.json are saved
        epoch_file = self.manager.epoch_file_path(epoch)
        if not epoch_file.exists():
            if self.tools._working_state:
                self.tools.commit_epoch_snapshot(
                    epoch=epoch,
                    notes=f"Epoch {epoch} state committed.",
                )
            else:
                # Attempt to parse grid from model's ASCII output if provided
                try:
                    import re
                    from dungeon_crawler_text.world_state import parse_grid_text
                    grid = parse_grid_text(text)
                    latest = self.manager.load_latest_state() or self.manager.get_working_state()
                    realm = latest.get("realm_name", "Aldenor")
                    locs = dict(latest.get("locations", {}))

                    realm_match = re.search(r"(?:Map of|Chronicle of|Realm:?)\s+\*\*?([A-Za-z0-9\s'-]+?)\*\*?", text)
                    if realm_match:
                        found_realm = realm_match.group(1).strip()
                        if len(found_realm) > 2 and "epoch" not in found_realm.lower():
                            realm = found_realm

                    # Extract bold coordinates from narrative and log
                    for match in re.finditer(r"\*\*([^*]+)\*\*\s*(?:\([^\)]+\)\s*)?\[X:\s*(\d+),\s*Y:\s*(\d+)\]", text + "\n" + historian_narrative):
                        name = match.group(1).strip()
                        x, y = int(match.group(2)), int(match.group(3))
                        if 0 <= x < 32 and 0 <= y < 32 and name not in locs:
                            sym = grid[y][x] if 0 <= y < len(grid) else "o"
                            ltype = "settlement"
                            if sym == "!":
                                ltype = "dungeon"
                            elif sym == "O":
                                ltype = "city"
                            elif sym == "o":
                                ltype = "outpost"
                            elif sym == "=":
                                ltype = "bridge"
                            elif sym == ":":
                                ltype = "farmland"
                            locs[name] = {
                                "type": ltype,
                                "symbol": sym,
                                "coord": [x, y],
                                "status": "ruined" if sym == "!" else "active",
                            }

                    self.manager.save_epoch(
                        epoch=epoch,
                        realm_name=realm,
                        grid=grid,
                        locations=locs,
                        history_notes=f"Epoch {epoch} snapshot.",
                    )
                except Exception:
                    pass

        return text
