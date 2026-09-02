"""Historian Agent module.

Narrates world history, geopolitical changes, and fantasy world lore using Gemini LLM.
Accesses persistent world state (world_epoch_latest.json) via inspection tools.
"""

from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from dungeon_crawler_text.tools import HistorianTools
from dungeon_crawler_text.world_state import WorldStateManager


def _load_prompt(filename: str) -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


class Historian:
    """Historian agent that chronicles the narrative evolution of the world,

    grounded by inspecting the persistent world state.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.7-flash",
        thinking_level: str = "HIGH",
        client: Optional[genai.Client] = None,
        manager: Optional[WorldStateManager] = None,
        tools: Optional[HistorianTools] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.manager = manager or WorldStateManager()
        self.tools = tools or HistorianTools(self.manager)
        self.system_prompt = _load_prompt("Historian.md")

        tool_functions = [
            self.tools.get_world_overview,
            self.tools.inspect_map,
            self.tools.get_location_details,
            self.tools.inspect_tile,
        ]

        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.8,
                thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
                tools=tool_functions,
            ),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def narrate(self, cartographer_query: str, epoch: int = 1) -> str:
        """Responds to the Cartographer's query with historical narrative events.

        For Epoch 2+, instructs the model to inspect latest world state first.
        """
        prompt = cartographer_query
        if epoch > 1:
            prompt = (
                f"🧭 CARTOGRAPHER REPORT & QUERY (From Previous Epoch):\n"
                f"{cartographer_query}\n\n"
                f"[System Directive for Epoch {epoch}]:\n"
                f"1. Review the Cartographer's log above to see what was mapped, founded, or decayed.\n"
                f"2. Use your tools (get_world_overview, inspect_map, inspect_tile) to examine the current state of world_epoch_latest.json.\n"
                f"3. Compose your historical chronicle for Epoch {epoch}, anchoring all developments with exact coordinates [X: xx, Y: yy]."
            )

        response = self.chat.send_message(prompt)
        return response.text or ""
