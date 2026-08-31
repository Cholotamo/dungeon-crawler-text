"""Historian Agent module.

Narrates world history, geopolitical changes, and fantasy world lore using Gemini LLM.
"""

from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types


def _load_prompt(filename: str) -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


class Historian:
    """Historian agent that chronicles the narrative evolution of the world."""

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("Historian.md")
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.8,
            ),
        )

    def narrate(self, cartographer_query: str) -> str:
        """Responds to the Cartographer's query with historical narrative events."""
        response = self.chat.send_message(cartographer_query)
        return response.text or ""
