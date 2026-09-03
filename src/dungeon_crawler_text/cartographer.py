"""Cartographer Agent module.

Translates ongoing historical chronicles into ASCII world maps using Gemini LLM.
Optimized to run statelessly using generate_content to save tokens.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff
from dungeon_crawler_text.world_state import (
    extract_cartographic_log,
    extract_snapshot_from_text,
    format_snapshot_injection,
)


def _load_prompt(filename: str) -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


class Cartographer:
    """Cartographer agent that generates and updates 32x32 ASCII world maps

    based on narrative input from the Historian using Python code execution.
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

        self.tools = (
            [types.Tool(code_execution=types.ToolCodeExecution())]
            if enable_code_execution
            else None
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

    def start_chronicle(self) -> str:
        """Returns the initial query asking the Historian for the lay of the land."""
        return (
            "What is the lay of the land? Describe the foundational geography "
            "(oceans, mountain chains, hills, major rivers, and ancient forests) of this world."
        )

    def _extract_all_parts(self, response: Any) -> tuple[str, str]:
        """Extracts text content and code execution stdout from response parts."""
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

    @retry_with_backoff(max_retries=4, initial_delay=2.0)
    def generate_primordial_map(
        self, historian_narrative: str
    ) -> tuple[Optional[dict[str, Any]], str, str]:
        """Turn 1: Generates initial terrain_grid, region_grid, and empty registries.

        Returns (snapshot_dict, cartographic_log, raw_response_text).
        """
        user_prompt = (
            "Here is the Historian's primordial world description:\n\n"
            f"{historian_narrative}\n\n"
            "Execute a Python script to procedurally generate the baseline geography:\n"
            "1. Generate a full 32x32 terrain_grid first (natural ground only).\n"
            "2. Map biomes onto a parallel 32x32 region_grid with IDs mapped in regions dictionary.\n"
            "3. Initialize empty landmarks: {} and roads: {}.\n"
            "4. Print the complete JSON world state snapshot wrapped in the designated delimiters:\n"
            "   print('___WORLD_STATE_SNAPSHOT_START___')\n"
            "   print(json.dumps(state))\n"
            "   print('___WORLD_STATE_SNAPSHOT_END___')\n"
            "5. Provide your Cartographic Log and end with: 'What happened next in the chronicle of this land?'"
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            tools=self.tools,
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        )
        self._track_usage(response)

        text_content, code_output = self._extract_all_parts(response)
        combined_output = f"{code_output}\n\n{text_content}"

        snapshot = extract_snapshot_from_text(combined_output)
        cartographic_log = extract_cartographic_log(text_content)

        return snapshot, cartographic_log, combined_output

    @retry_with_backoff(max_retries=4, initial_delay=2.0)
    def evolve_map(
        self,
        historian_narrative: str,
        previous_state: dict[str, Any],
        epoch: int,
    ) -> tuple[Optional[dict[str, Any]], str, str]:
        """Turn 2+: Mutates map state according to the historical chronicle.

        Runs statelessly without prior chat memory to save tokens.
        Returns (snapshot_dict, cartographic_log, raw_response_text).
        """
        snapshot_injection = format_snapshot_injection(previous_state)
        state_json_str = json.dumps(previous_state, indent=2)

        user_prompt = (
            f"## Previous World State (Epoch {epoch - 1}):\n"
            f"{snapshot_injection}\n\n"
            f"## Previous State JSON (Initialize `state` in your Python script with this data):\n"
            f"```json\n{state_json_str}\n```\n\n"
            f"## Chronicle of Historical Events:\n"
            f"{historian_narrative}\n\n"
            "## Instructions:\n"
            "Execute Python code to apply the chronicle updates to the world state:\n"
            "1. Initialize `state` in Python using the JSON above.\n"
            f"2. Set state['epoch'] = {epoch}.\n"
            "3. Parse bracketed coordinates (e.g., [X: 14, Y: 22]) and add/update landmarks, roads, and terraformed tiles.\n"
            "4. Ensure dual-grid synchronization if biomes or terrain change.\n"
            "5. Print the updated JSON snapshot wrapped in the designated delimiters:\n"
            "   print('___WORLD_STATE_SNAPSHOT_START___')\n"
            "   print(json.dumps(state))\n"
            "   print('___WORLD_STATE_SNAPSHOT_END___')\n"
            "6. Output your Cartographic Log (2–3 bullet points) and end with: 'What happened next in the chronicle of this land?'"
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            tools=self.tools,
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        )
        self._track_usage(response)

        text_content, code_output = self._extract_all_parts(response)
        combined_output = f"{code_output}\n\n{text_content}"

        snapshot = extract_snapshot_from_text(combined_output)
        cartographic_log = extract_cartographic_log(text_content)

        return snapshot, cartographic_log, combined_output
