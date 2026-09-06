"""Reconciler Agent module.

Inspects uncommitted Scribe drafts across active locations for the current epoch,
detects cross-location discrepancies (e.g. naming conflicts, contradictory events),
and harmonizes them into an authoritative, consistent historical canon.
"""

from pathlib import Path
import re
from typing import Any, Optional

from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff
from dungeon_crawler_text.scribe import (
    extract_chronicle,
    extract_delimited_block,
    extract_dispatch,
    parse_metadata_update,
)

RECONCILIATION_LOG_START = "___RECONCILIATION_LOG_START___"
RECONCILIATION_LOG_END = "___RECONCILIATION_LOG_END___"
NO_CONFLICTS = "___NO_CONFLICTS___"
RECONCILED_LOC_PATTERN = re.compile(
    r"___RECONCILED_LOCATION_START:\s*([^_]+)___(.*?)___RECONCILED_LOCATION_END___",
    re.DOTALL,
)


def _load_prompt(filename: str) -> str:
    """Loads a prompt file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


def parse_reconciliation_log(text: str) -> list[str]:
    """Extracts bulleted items from the RECONCILIATION_LOG block."""
    raw = extract_delimited_block(text, RECONCILIATION_LOG_START, RECONCILIATION_LOG_END)
    if not raw or "NO_CONFLICTS" in raw:
        return []

    items: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("-") or line.startswith("*"):
            items.append(line.lstrip("-* ").strip())
        elif line:
            items.append(line)
    return items


def parse_reconciled_locations(text: str) -> dict[str, dict[str, Any]]:
    """Extracts updated location drafts from RECONCILED_LOCATION blocks."""
    reconciled: dict[str, dict[str, Any]] = {}
    for match in RECONCILED_LOC_PATTERN.finditer(text):
        loc_key = match.group(1).strip()
        block_text = match.group(2).strip()

        meta = parse_metadata_update(block_text)
        disp = extract_dispatch(block_text)
        chron = extract_chronicle(block_text)

        reconciled[loc_key] = {
            "metadata": meta,
            "dispatch": disp,
            "chronicle": chron,
        }
    return reconciled


class Reconciler:
    """Agent that reconciles and harmonizes Scribe drafts across active locations."""

    def __init__(
        self,
        model_name: str = "gemini-3.7-flash",
        thinking_level: str = "HIGH",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("Reconciler.md")
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
    def reconcile_epoch_drafts(
        self,
        drafts: dict[str, dict[str, Any]],
        historian_narrative: str,
        cartographer_log: str,
        epoch: int,
    ) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """Harmonizes active location drafts for the current epoch.

        Args:
            drafts: Mapping of landmark_key to dict containing:
                - landmark_data: dict
                - dispatch: str
                - chronicle: str
                - metadata: dict
                - existing_history: Optional[str]
            historian_narrative: Grand Historian narrative for this epoch
            cartographer_log: Cartographer alteration log for this epoch
            epoch: Current simulation epoch

        Returns:
            (reconciled_drafts, reconciliation_log_items)
        """
        if len(drafts) < 2:
            return drafts, []

        # Build prompt listing all active drafts
        draft_sections: list[str] = []
        for l_key, d_info in drafts.items():
            l_data = d_info.get("landmark_data", {})
            name = l_data.get("name", l_key)
            pos = l_data.get("pos", [0, 0])
            char = l_data.get("char", "o")
            l_type = l_data.get("type", "settlement")

            meta = d_info.get("metadata", {})
            disp = d_info.get("dispatch", "")
            chron = d_info.get("chronicle", "")
            existing = d_info.get("existing_history", "None")

            draft_text = (
                f"### LOCATION DRAFT: {l_key} (Name: '{name}', Symbol: '{char}', Type: '{l_type}', Coords: {pos})\n"
                f"**Prior Location History Context (excerpt/summary):**\n"
                f"{existing[:1200] if existing else 'None'}\n\n"
                f"**Draft Living Metadata:**\n"
                f"- Current Status: {meta.get('current status', '')}\n"
                f"- Active Factions: {meta.get('active factions', '')}\n\n"
                f"**Draft Frontier Dispatch:**\n"
                f"{disp}\n\n"
                f"**Draft Epoch Chronicle:**\n"
                f"{chron}\n"
                f"--------------------------------------------------"
            )
            draft_sections.append(draft_text)

        all_drafts_str = "\n\n".join(draft_sections)

        user_prompt = (
            f"## Current Simulation Context:\n"
            f"- Current Epoch: {epoch}\n\n"
            f"## Grand Historian's Macro Narrative for Epoch {epoch}:\n"
            f"{historian_narrative}\n\n"
            f"## Cartographer's Physical Alteration Log:\n"
            f"{cartographer_log}\n\n"
            f"## Uncommitted Scribe Drafts for Active Locations ({len(drafts)}):\n"
            f"{all_drafts_str}\n\n"
            f"Carefully evaluate these drafts for cross-location naming collisions, contradictory figures, "
            f"divergent battle or mutiny accounts, or inconsistent timeline references.\n"
            f"If discrepancies are found, reconcile them into an authoritative canon. "
            f"Provide the Reconciliation Log, and output the reconciled version of each modified location."
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.4,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config,
        )
        self._track_usage(response)

        raw_text = getattr(response, "text", "") or ""
        log_items = parse_reconciliation_log(raw_text)
        reconciled_patches = parse_reconciled_locations(raw_text)

        # Merge reconciled patches back into drafts
        final_drafts = dict(drafts)
        for loc_key, patch in reconciled_patches.items():
            # Try exact key, then match by slug or case
            matched_key = None
            if loc_key in final_drafts:
                matched_key = loc_key
            else:
                for k in final_drafts:
                    if k.lower() == loc_key.lower() or k.replace(" ", "_").lower() == loc_key.replace(" ", "_").lower():
                        matched_key = k
                        break

            if matched_key:
                final_drafts[matched_key]["metadata"] = patch.get("metadata") or final_drafts[matched_key]["metadata"]
                if patch.get("dispatch"):
                    final_drafts[matched_key]["dispatch"] = patch["dispatch"]
                if patch.get("chronicle"):
                    final_drafts[matched_key]["chronicle"] = patch["chronicle"]

        return final_drafts, log_items
