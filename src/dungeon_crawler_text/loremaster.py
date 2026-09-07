"""Loremaster Agent module.

Describes the primordial landscape and geography of a fantasy realm using Gemini LLM.
"""

from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff

DEFAULT_PRIMORDIAL_QUERY = (
    "Describe the primordial geography of a temperate fantasy realm: "
    "its natural boundaries, coastlines, mountain ridges, waterways, and untamed biomes."
)


def _load_prompt(filename: str = "loremaster_worldprose.md") -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


class Loremaster:
    """Loremaster agent that describes the primordial fantasy realm."""

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        thinking_level: str = "MEDIUM",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("loremaster_worldprose.md")
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
    def generate_primordial_world(
        self, query: str = DEFAULT_PRIMORDIAL_QUERY
    ) -> str:
        """Generates the narrative description of the primordial landscape."""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.8,
                thinking_config=types.ThinkingConfig(
                    thinking_level=self.thinking_level
                ),
            ),
        )
        self._track_usage(response)
        return response.text or ""



__all__ = [
    "Loremaster",
    "DEFAULT_PRIMORDIAL_QUERY",
]

