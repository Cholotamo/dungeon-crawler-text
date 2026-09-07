"""Historian Agent module.

Narrates world history, geopolitical changes, and fantasy world lore using Gemini LLM.
Maintains persistent conversation memory across epochs.
"""

import re
from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff
from dungeon_crawler_text.world_state import (
    get_world_chronicle_path,
    read_world_chronicle,
    save_world_chronicle,
)

CHRONOLOGY_START = "___CHRONOLOGY_START___"
CHRONOLOGY_END = "___CHRONOLOGY_END___"


def extract_chronology(text: str, epoch: int = 1) -> dict[str, str]:
    """Extracts calendar reckoning and elapsed years from Historian output."""
    if not text:
        default_reck = "Dawn Era (Year 0)" if epoch == 1 else f"Epoch {epoch}"
        return {"reckoning": default_reck, "years_passed": "0" if epoch == 1 else "Unspecified"}

    if CHRONOLOGY_START in text and CHRONOLOGY_END in text:
        start_idx = text.index(CHRONOLOGY_START) + len(CHRONOLOGY_START)
        end_idx = text.index(CHRONOLOGY_END, start_idx)
        block = text[start_idx:end_idx].strip()
        data = {"reckoning": f"Epoch {epoch}", "years_passed": "Unspecified"}
        for line in block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k_clean = k.strip().lower()
                v_clean = v.strip()
                if "pass" in k_clean or "elapse" in k_clean or "since" in k_clean:
                    data["years_passed"] = v_clean
                elif "reckon" in k_clean or "current" in k_clean or "calendar" in k_clean or "year" in k_clean or "date" in k_clean:
                    data["reckoning"] = v_clean
        return data

    # Fallback: regex search for calendar reckoning patterns (e.g. "340 IR", "Year 142")
    match = re.search(r"\b(\d{1,4}\s*(?:IR|AR|CE|BCE|A\.D\.|OE|Reckoning))\b", text, re.IGNORECASE)
    if match:
        return {"reckoning": match.group(1).strip(), "years_passed": "Unspecified"}

    match_year = re.search(r"\b(?:in\s+the\s+year|year)\s+(\d{1,4})\b", text, re.IGNORECASE)
    if match_year:
        return {"reckoning": f"Year {match_year.group(1)}", "years_passed": "Unspecified"}

    default_reckoning = "Dawn Era (Year 0)" if epoch == 1 else f"Epoch {epoch}"
    return {"reckoning": default_reckoning, "years_passed": "0" if epoch == 1 else "Unspecified"}


def extract_historian_prose(text: str) -> str:
    """Removes chronology delimiters from historian narrative prose."""
    if not text:
        return ""
    if CHRONOLOGY_START in text and CHRONOLOGY_END in text:
        pattern = re.escape(CHRONOLOGY_START) + r"[\s\S]*?" + re.escape(CHRONOLOGY_END)
        cleaned = re.sub(pattern, "", text)
        return cleaned.strip()
    return text.strip()


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
        rumors_and_dispatches: str = "",
    ) -> str:
        """Turn 2+: Ingests world state snapshot injection, previous log, and frontier dispatches,

        then generates next chronicle events. Retains conversation memory.
        """
        dispatches_section = ""
        if rumors_and_dispatches.strip():
            dispatches_section = (
                f"## Rumors & Frontier Dispatches (Epoch {epoch - 1} Aftermath):\n"
                f"{rumors_and_dispatches.strip()}\n\n"
            )

        user_prompt = (
            f"## Current World State (Epoch {epoch - 1}):\n"
            f"{snapshot_injection}\n\n"
            f"## Cartographer's Previous Turn Log:\n"
            f"{cartographer_log}\n\n"
            f"{dispatches_section}"
            f"{query}"
        )
        response = self.chat.send_message(user_prompt)
        self._track_usage(response)
        return response.text or ""
