"""Cartographer Agent module.

Translates ongoing historical chronicles into ASCII world maps using Gemini LLM.
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


class Cartographer:
    """Cartographer agent that generates and updates 32x32 ASCII world maps

    based on narrative input from the Historian.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.7-flash",
        thinking_level: str = "HIGH",
        client: Optional[genai.Client] = None,
        enable_code_execution: bool = True,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("Cartographer.md")
        self.enable_code_execution = enable_code_execution

        tools = (
            [types.Tool(code_execution=types.ToolCodeExecution())]
            if enable_code_execution
            else None
        )

        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.7,
                thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
                tools=tools,
            ),
        )

    def start_chronicle(self) -> str:
        """Returns the initial query asking the Historian for the lay of the land."""
        return (
            "What is the lay of the land? Describe the foundational geography "
            "(oceans, mountain chains, hills, major rivers, and ancient forests) of this world."
        )

    def process_narrative(self, historian_narrative: str) -> str:
        """Sends the Historian's narrative to Gemini and returns the updated map,

        cartographic log, and follow-up query.
        """
        response = self.chat.send_message(historian_narrative)
        return response.text or ""
