"""Historian Agent module.

Narrates world history, geopolitical changes, and fantasy world lore using Gemini LLM.
Maintains persistent conversation memory across epochs.
"""

from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff


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
        model_name: str = "gemini-3.7-flash",
        thinking_level: str = "HIGH",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("Historian.md")
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.8,
                thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            ),
        )
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
            p = getattr(meta, "prompt_token_count", 0)
            c = getattr(meta, "candidates_token_count", 0)
            t = getattr(meta, "total_token_count", 0)
            th = getattr(meta, "thoughts_token_count", 0)
            p = p if isinstance(p, int) else 0
            c = c if isinstance(c, int) else 0
            t = t if isinstance(t, int) else (p + c)
            th = th if isinstance(th, int) else 0
            self.token_usage["prompt_tokens"] += p
            self.token_usage["candidates_tokens"] += c
            self.token_usage["total_tokens"] += t
            self.token_usage["thoughts_tokens"] += th

    @retry_with_backoff(max_retries=4, initial_delay=2.0)
    def generate_primordial_world(self, query: str) -> str:
        """Turn 1: Responds to initial query with primordial world description."""
        response = self.chat.send_message(query)
        self._track_usage(response)
        return response.text or ""

    @retry_with_backoff(max_retries=4, initial_delay=2.0)
    def chronicle_epoch(
        self,
        snapshot_injection: str,
        cartographer_log: str,
        epoch: int,
        query: str = "What happened next in the chronicle of this land?",
    ) -> str:
        """Turn 2+: Ingests world state snapshot injection and previous log,

        then generates next chronicle events. Retains conversation memory.
        """
        user_prompt = (
            f"## Current World State (Epoch {epoch - 1}):\n"
            f"{snapshot_injection}\n\n"
            f"## Cartographer's Previous Turn Log:\n"
            f"{cartographer_log}\n\n"
            f"{query}"
        )
        response = self.chat.send_message(user_prompt)
        self._track_usage(response)
        return response.text or ""
