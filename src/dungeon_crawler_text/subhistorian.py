"""Subhistorian Agent module.

Evolves 16x16 localemaps across historical epochs from one keyframe to the next
using sparse vector delta packets (vector_{i}.json / vector_{i}.md) and Gemini Python code execution.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import json
import logging
from pathlib import Path
import re
import sys
import threading
from typing import Any, Optional, Union

from dotenv import load_dotenv
from google import genai
from google.genai import types

from dungeon_crawler_text.retry import retry_with_backoff
from dungeon_crawler_text.seed import format_locale_vector_markdown
from dungeon_crawler_text.subarchitect import (
    GRID_DIM,
    VALID_TERRAIN_CHARS,
    build_composite_grid,
    extract_all_parts,
    format_localemap_for_llm,
    parse_localemap_json,
    print_localemap_preview,
    validate_localemap,
)

# Suppress the redundant SDK warning for stateless automatic function calling/code execution
try:
    from google.genai import models as _genai_models

    _genai_models.Models._logged_afc_warning = True
except Exception:
    pass

logger = logging.getLogger(__name__)

DEFAULT_LOCALES_DIR = Path("artifacts/locales")


def _load_prompt(filename: str = "subhistorian_localemap.md") -> str:
    """Loads a prompt template file from the prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Subhistorian prompt file not found at: {prompt_path}")


def parse_vector_markdown(md_text: str) -> dict[str, Any]:
    """Parses essential delta fields from a vector markdown string if JSON is unavailable."""
    packet: dict[str, Any] = {}
    title_m = re.search(r"#\s*Locale Evolution Vector:\s*([^\n\r]+)", md_text)
    if title_m:
        to_name = title_m.group(1).strip()
        packet["to_name"] = to_name
        packet["feature_id"] = to_name.lower().replace(" ", "_")

    name_chg_m = re.search(r"-\s*\*\*Name Change:\*\*\s*([^\n\r]+)", md_text)
    if name_chg_m:
        packet["name_change"] = name_chg_m.group(1).strip()

    status_m = re.search(r"### Status\s*\n([^\n\r]+)", md_text)
    if status_m:
        packet["status"] = status_m.group(1).strip()
        packet["has_new_development"] = False
        return packet

    packet["has_new_development"] = True

    scale_m = re.search(r'### Scale New Development\s*\n"?([^"\n\r]+)"?', md_text)
    if scale_m:
        packet["scale_new_development"] = scale_m.group(1).strip()

    locale_lore_m = re.search(r'### Locale Lore New Development\s*\n"?([^"\n\r]+)"?', md_text)
    if locale_lore_m:
        packet["locale_lore_new_development"] = locale_lore_m.group(1).strip()

    host_lore_m = re.search(r'### Host Region Lore New Development\s*\n"?([^"\n\r]+)"?', md_text)
    if host_lore_m:
        packet["host_region_lore_new_development"] = host_lore_m.group(1).strip()

    return packet


def load_keyframe(source: Union[dict[str, Any], str, Path]) -> dict[str, Any]:
    """Loads and validates a previous keyframe from a dict, file path, or JSON string."""
    if isinstance(source, dict):
        data = deepcopy(source)
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists() and p.is_file():
            text = p.read_text(encoding="utf-8")
            if p.suffix == ".json":
                data = json.loads(text)
            else:
                data = parse_localemap_json(text)
                if not data:
                    raise ValueError(f"Could not parse localemap JSON from markdown file: {p}")
        else:
            data = parse_localemap_json(str(source))
            if not data:
                raise ValueError(f"Could not parse localemap JSON from string or non-existent path: {source}")
    else:
        raise TypeError(f"Unsupported keyframe source type: {type(source)}")

    if not isinstance(data, dict) or ("terrain_grid" not in data and "district_grid" not in data):
        raise ValueError("Invalid keyframe data: missing 'terrain_grid' or 'district_grid'.")

    return data


def load_vector(source: Union[dict[str, Any], str, Path]) -> tuple[dict[str, Any], str]:
    """Loads a vector packet dict and companion markdown text from a dict, file path, or string.

    Returns:
        tuple[dict[str, Any], str]: (vector_packet_dict, vector_markdown_text)
    """
    if isinstance(source, dict):
        packet = deepcopy(source)
        md_text = format_locale_vector_markdown(packet)
        return packet, md_text

    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists() and p.is_file():
            if p.suffix == ".json":
                packet = json.loads(p.read_text(encoding="utf-8"))
                companion_md = p.with_suffix(".md")
                if companion_md.exists():
                    md_text = companion_md.read_text(encoding="utf-8")
                else:
                    md_text = format_locale_vector_markdown(packet)
                return packet, md_text
            elif p.suffix == ".md":
                md_text = p.read_text(encoding="utf-8")
                companion_json = p.with_suffix(".json")
                if companion_json.exists():
                    packet = json.loads(companion_json.read_text(encoding="utf-8"))
                else:
                    packet = parse_vector_markdown(md_text)
                return packet, md_text
            else:
                raw = p.read_text(encoding="utf-8")
                try:
                    packet = json.loads(raw)
                    return packet, format_locale_vector_markdown(packet)
                except Exception:
                    return parse_vector_markdown(raw), raw
        else:
            raw_str = str(source).strip()
            try:
                packet = json.loads(raw_str)
                return packet, format_locale_vector_markdown(packet)
            except Exception:
                return parse_vector_markdown(raw_str), raw_str

    raise TypeError(f"Unsupported vector source type: {type(source)}")


def validate_evolved_localemap(
    data: dict[str, Any],
    prev_keyframe: dict[str, Any],
    vector_packet: dict[str, Any],
    to_keyframe_index: Optional[int] = None,
    to_epoch: Optional[int] = None,
) -> dict[str, Any]:
    """Validates dimensions, layers, and context continuity for an evolved localemap keyframe."""
    if not isinstance(data, dict):
        raise ValueError("Evolved localemap data must be a dictionary.")

    # 1. Identity & Milestones
    fid = vector_packet.get("feature_id") or prev_keyframe.get("feature_id", "unknown_locale")
    data["feature_id"] = fid

    to_name = (
        vector_packet.get("to_name")
        or data.get("name")
        or prev_keyframe.get("name", fid.replace("_", " ").title())
    )
    data["name"] = to_name

    # Determine type
    prev_type = prev_keyframe.get("type", "settlement")
    vec_scale = str(vector_packet.get("scale_new_development", "")).lower()
    if "ruin" in to_name.lower() or "ruin" in vec_scale or "abandoned ruin" in vec_scale:
        data["type"] = "ruin"
    elif "to_type" in vector_packet:
        data["type"] = str(vector_packet["to_type"]).lower()
    else:
        data["type"] = str(data.get("type") or prev_type).lower()

    # Keyframe index & Epoch
    if to_keyframe_index is not None:
        data["keyframe_index"] = int(to_keyframe_index)
    elif "to_keyframe" in vector_packet:
        data["keyframe_index"] = int(vector_packet["to_keyframe"])
    else:
        data["keyframe_index"] = int(prev_keyframe.get("keyframe_index", 0)) + 1

    if to_epoch is not None:
        data["epoch"] = int(to_epoch)
    elif "to_epoch" in vector_packet:
        data["epoch"] = int(vector_packet["to_epoch"])
    else:
        data["epoch"] = int(prev_keyframe.get("epoch", 1)) + 1

    # 2. Extract & Validate terrain_grid (16x16)
    terrain_grid = data.get("terrain_grid")
    if terrain_grid is None:
        terrain_grid = data.get("overview_grid")
    if terrain_grid is None and "views" in data and isinstance(data["views"], dict):
        terrain_grid = data["views"].get("overview", {}).get("grid")

    if not isinstance(terrain_grid, list) or len(terrain_grid) != GRID_DIM:
        raise ValueError(
            f"terrain_grid must contain exactly {GRID_DIM} rows, "
            f"got {len(terrain_grid) if isinstance(terrain_grid, list) else type(terrain_grid)}."
        )
    for y, row in enumerate(terrain_grid):
        if not isinstance(row, str) or len(row) != GRID_DIM:
            raise ValueError(
                f"terrain_grid row {y} must have length {GRID_DIM}, "
                f"got len={len(row) if isinstance(row, str) else type(row)}."
            )
        invalid_chars = set(row) - VALID_TERRAIN_CHARS
        if invalid_chars:
            raise ValueError(f"terrain_grid row {y} contains invalid terrain chars: {invalid_chars}")
    data["terrain_grid"] = terrain_grid

    # 3. Extract & Validate district_grid (16x16)
    district_grid = data.get("district_grid")
    if district_grid is None and "views" in data and isinstance(data["views"], dict):
        district_grid = data["views"].get("district", {}).get("grid")

    if not isinstance(district_grid, list) or len(district_grid) != GRID_DIM:
        raise ValueError(
            f"district_grid must contain exactly {GRID_DIM} rows, "
            f"got {len(district_grid) if isinstance(district_grid, list) else type(district_grid)}."
        )
    for y, row in enumerate(district_grid):
        if not isinstance(row, str) or len(row) != GRID_DIM:
            raise ValueError(
                f"district_grid row {y} must have length {GRID_DIM}, "
                f"got len={len(row) if isinstance(row, str) else type(row)}."
            )
    data["district_grid"] = district_grid

    # 4. Districts Registry
    districts = data.get("districts")
    if not isinstance(districts, dict):
        districts = deepcopy(prev_keyframe.get("districts", {}))
    data["districts"] = districts

    # Ensure buffer '0'
    if "0" not in districts or not isinstance(districts["0"], dict):
        districts["0"] = prev_keyframe.get("districts", {}).get("0", {
            "name": "Frontier Buffer & Wilderness",
            "type": "buffer",
            "lore": "Unzoned natural perimeter buffer, shoreline, and exterior terrain.",
        })
    else:
        districts["0"].setdefault("name", "Frontier Buffer & Wilderness")
        districts["0"].setdefault("type", "buffer")
        districts["0"].setdefault("lore", "Natural perimeter buffer.")

    used_district_chars = {char for row in district_grid for char in row}
    for ch in used_district_chars:
        if ch not in districts:
            districts[ch] = prev_keyframe.get("districts", {}).get(ch, {
                "name": f"District {ch}",
                "type": "district",
                "lore": f"Functional zone {ch}.",
            })
        elif isinstance(districts[ch], str):
            districts[ch] = {
                "name": districts[ch],
                "type": "district",
                "lore": f"Functional zone: {districts[ch]}.",
            }
        elif isinstance(districts[ch], dict):
            districts[ch].setdefault("name", f"District {ch}")
            districts[ch].setdefault("type", "district")
            districts[ch].setdefault("lore", f"Functional zone for District {ch}.")

    # 5. Features Registry
    features = data.get("features")
    if not isinstance(features, dict):
        features = {}
    data["features"] = features

    cleaned_features: dict[str, dict[str, Any]] = {}
    for feat_id, feat in features.items():
        if not isinstance(feat, dict):
            continue
        f_name = str(feat.get("name", str(feat_id).replace("_", " ").title()))
        f_type = str(feat.get("type", "structure"))
        f_char = str(feat.get("char", "X"))[:1]
        f_lore = str(feat.get("lore") or feat.get("description", "A regional landmark structure."))

        raw_tiles = feat.get("tiles")
        if raw_tiles is None and "pos" in feat:
            raw_tiles = [feat["pos"]]
        elif raw_tiles is None and "coord" in feat:
            raw_tiles = [feat["coord"]]

        valid_tiles: list[list[int]] = []
        if isinstance(raw_tiles, (list, tuple)):
            for pt in raw_tiles:
                if isinstance(pt, (list, tuple)) and len(pt) == 2:
                    try:
                        px, py = int(pt[0]), int(pt[1])
                        if 0 <= px < GRID_DIM and 0 <= py < GRID_DIM:
                            valid_tiles.append([px, py])
                    except (ValueError, TypeError):
                        continue

        cleaned_features[feat_id] = {
            "name": f_name,
            "type": f_type,
            "char": f_char,
            "tiles": valid_tiles,
            "lore": f_lore,
        }
    data["features"] = cleaned_features

    # 6. Context & World Relations
    context = data.get("context")
    if not isinstance(context, dict):
        context = {}
    prev_context = prev_keyframe.get("context", {})

    summary = (
        context.get("summary")
        or context.get("lore")
        or vector_packet.get("locale_lore_new_development")
        or prev_context.get("summary", f"{to_name} in Epoch {data['epoch']}.")
    )

    host_region = (
        context.get("host_region")
        or prev_context.get("host_region")
        or ""
    )

    host_region_lore = (
        vector_packet.get("host_region_lore_new_development")
        or vector_packet.get("home_region_lore_new_development")
        or context.get("host_region_lore")
        or prev_context.get("host_region_lore")
        or ""
    )

    scale_profile = (
        vector_packet.get("scale_new_development")
        or context.get("scale_profile")
        or prev_context.get("scale_profile")
        or ""
    )

    # Perimeters
    perimeters = context.get("perimeters") or []
    if not perimeters:
        perimeters = deepcopy(prev_context.get("perimeters", []))

    # Incorporate perimeter developments from vector if present
    perimeter_devs = vector_packet.get("perimeter_new_development", [])
    if perimeter_devs:
        for p_dev in perimeter_devs:
            dev_border = p_dev.get("border", "").upper()
            dev_delta = p_dev.get("delta", "")
            matched = False
            for p in perimeters:
                if isinstance(p, dict):
                    cur_border = p.get("border", "").upper()
                    if dev_border and (dev_border in cur_border or cur_border in dev_border):
                        p["lore"] = dev_delta
                        matched = True
                        break
            if not matched and dev_border:
                perimeters.append({
                    "border": p_dev.get("border", "Perimeter"),
                    "description": p_dev.get("neighbor_name", "Border Region"),
                    "lore": dev_delta,
                })

    # Approaches
    approaches = context.get("approaches") or []
    if not approaches:
        approaches = deepcopy(prev_context.get("approaches", []))

    road_devs = vector_packet.get("road_new_development", [])
    if road_devs:
        for r_dev in road_devs:
            r_name = r_dev.get("road_name", "").strip().lower()
            r_dir = r_dev.get("direction", "").strip().upper()
            r_delta = r_dev.get("delta", "")
            r_status = r_dev.get("status", "modified")

            matched = False
            for a in approaches:
                if isinstance(a, dict):
                    cur_road = a.get("road", "").strip().lower()
                    cur_dir = a.get("direction", "").strip().upper()
                    if (r_name and r_name in cur_road) or (r_dir and r_dir == cur_dir):
                        if r_status == "lost":
                            a["road_lore"] = f"(Severed / Abandoned) {r_delta}"
                        else:
                            a["road_lore"] = r_delta
                        matched = True
                        break
            if not matched and r_status != "lost":
                approaches.append({
                    "direction": r_dev.get("direction", "PERIMETER"),
                    "road": r_dev.get("road_name", "New Road"),
                    "road_lore": r_delta,
                    "destination": "Regional Trail",
                    "destination_lore": "Connected trade approach.",
                })

    dest_devs = vector_packet.get("neighbouring_destination_new_development", [])
    if dest_devs:
        for d_dev in dest_devs:
            d_name = d_dev.get("destination", "").strip().lower()
            d_delta = d_dev.get("delta", "")
            for a in approaches:
                if isinstance(a, dict):
                    cur_dest = a.get("destination", "").strip().lower()
                    if d_name and (d_name in cur_dest or cur_dest in d_name):
                        a["destination_lore"] = d_delta
                        break

    world_relations = (
        context.get("world_relations")
        or prev_context.get("world_relations")
        or f"Evolving regional interdependence in Epoch {data['epoch']}."
    )

    arch_rationale = (
        context.get("architectural_rationale")
        or prev_context.get("architectural_rationale")
        or f"Structures and functional wards evolved to reflect historical developments in Epoch {data['epoch']}."
    )

    data["context"] = {
        "summary": summary,
        "host_region": host_region,
        "host_region_lore": host_region_lore,
        "scale_profile": scale_profile,
        "perimeters": perimeters,
        "approaches": approaches,
        "world_relations": world_relations,
        "architectural_rationale": arch_rationale,
    }

    # Clean legacy keys
    data.pop("overview_grid", None)
    data.pop("views", None)
    data.pop("legend", None)
    data.pop("metadata", None)

    return data


def evolve_stagnant_keyframe(
    prev_keyframe: dict[str, Any],
    vector_packet: dict[str, Any],
    to_keyframe_index: Optional[int] = None,
    to_epoch: Optional[int] = None,
) -> dict[str, Any]:
    """Evolves a keyframe when has_new_development is False without mutating the spatial layout."""
    evolved = deepcopy(prev_keyframe)
    kf_idx = (
        to_keyframe_index
        if to_keyframe_index is not None
        else vector_packet.get("to_keyframe", prev_keyframe.get("keyframe_index", 0) + 1)
    )
    ep = (
        to_epoch
        if to_epoch is not None
        else vector_packet.get("to_epoch", prev_keyframe.get("epoch", 1) + 1)
    )
    to_name = vector_packet.get("to_name", prev_keyframe.get("name", ""))

    evolved["keyframe_index"] = int(kf_idx)
    evolved["epoch"] = int(ep)
    if to_name:
        evolved["name"] = to_name

    status_msg = vector_packet.get(
        "status",
        f"No recorded developments, environmental shifts, or infrastructure changes occurred for {to_name} in Epoch {ep}.",
    )
    if "context" not in evolved or not isinstance(evolved["context"], dict):
        evolved["context"] = {}

    cur_rationale = evolved["context"].get("architectural_rationale", "")
    evolved["context"]["architectural_rationale"] = (
        f"{cur_rationale} In Epoch {ep}, the site experienced architectural stagnancy: {status_msg}".strip()
    )

    return validate_localemap(evolved)


class Subhistorian:
    """Subhistorian agent that evolves a 16x16 localemap from one keyframe to the next using sparse vector packets and code execution."""

    def __init__(
        self,
        model_name: str = "gemini-3.8-flash",
        thinking_level: str = "MEDIUM",
        client: Optional[genai.Client] = None,
    ) -> None:
        self.model_name = model_name
        self.thinking_level = thinking_level
        self.client = client or genai.Client()
        self.system_prompt = _load_prompt("subhistorian_localemap.md")
        self.tools = [types.Tool(code_execution=types.ToolCodeExecution())]
        self._usage_lock = threading.Lock()
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
            with self._usage_lock:
                self.token_usage["prompt_tokens"] += p
                self.token_usage["candidates_tokens"] += c
                self.token_usage["total_tokens"] += t
                self.token_usage["thoughts_tokens"] += th

    @retry_with_backoff(max_retries=4, initial_delay=2.0)
    def evolve_localemap(
        self,
        previous_keyframe: Union[dict[str, Any], str, Path],
        vector: Union[dict[str, Any], str, Path],
        to_keyframe_index: Optional[int] = None,
        to_epoch: Optional[int] = None,
        allow_stagnant_short_circuit: bool = True,
    ) -> dict[str, Any]:
        """Statelessly evolves the 16x16 localemap from previous_keyframe to next keyframe using code execution."""
        prev_kf = load_keyframe(previous_keyframe)
        vec_packet, vec_md = load_vector(vector)

        from_kf = prev_kf.get("keyframe_index", 0)
        from_ep = prev_kf.get("epoch", 1)
        target_kf = (
            to_keyframe_index
            if to_keyframe_index is not None
            else vec_packet.get("to_keyframe", from_kf + 1)
        )
        target_ep = (
            to_epoch
            if to_epoch is not None
            else vec_packet.get("to_epoch", from_ep + 1)
        )

        has_dev = vec_packet.get("has_new_development", True)
        if not has_dev and allow_stagnant_short_circuit:
            logger.info(
                f"Short-circuiting stagnant evolution for '{vec_packet.get('to_name', 'locale')}' (Epoch {target_ep})"
            )
            return evolve_stagnant_keyframe(
                prev_keyframe=prev_kf,
                vector_packet=vec_packet,
                to_keyframe_index=target_kf,
                to_epoch=target_ep,
            )

        prev_kf_md = format_localemap_for_llm(prev_kf)
        prev_kf_json = json.dumps(prev_kf, indent=2, ensure_ascii=False)

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            tools=self.tools,
        )

        user_content = (
            f"Please evolve the 16x16 localemap from Keyframe {from_kf} (Epoch {from_ep}) "
            f"to Keyframe {target_kf} (Epoch {target_ep}) using Python code execution according to "
            f"the following evolution vector packet:\n\n"
            f"### PREVIOUS KEYFRAME (Keyframe {from_kf}, Epoch {from_ep}):\n"
            f"{prev_kf_md.strip()}\n\n"
            f"### PREVIOUS KEYFRAME JSON:\n"
            f"```json\n{prev_kf_json}\n```\n\n"
            f"### ALLOCATED EVOLUTION VECTOR:\n"
            f"{vec_md.strip()}\n\n"
            f"Execute Python code to mutate the terrain_grid, district_grid, districts, features, and context "
            f"into Keyframe {target_kf} (Epoch {target_ep}), and print the final JSON."
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_content,
            config=config,
        )
        self._track_usage(response)

        text_content, code_output = extract_all_parts(response)
        combined_text = f"{code_output}\n\n{text_content}"

        parsed_data = (
            parse_localemap_json(code_output)
            or parse_localemap_json(text_content)
            or parse_localemap_json(combined_text)
        )

        if not parsed_data:
            raise ValueError(
                f"Failed to parse evolved localemap JSON from Subhistorian code execution output.\n"
                f"Code Output preview:\n{code_output[:500]}\n"
                f"Text preview:\n{text_content[:500]}"
            )

        validated_map = validate_evolved_localemap(
            data=parsed_data,
            prev_keyframe=prev_kf,
            vector_packet=vec_packet,
            to_keyframe_index=target_kf,
            to_epoch=target_ep,
        )
        return validated_map

    @staticmethod
    def save_localemap(
        map_data: dict[str, Any],
        output_path: Optional[Union[Path, str]] = None,
        base_dir: Optional[Union[Path, str]] = None,
    ) -> tuple[Path, Path]:
        """Saves validated localemap JSON and companion Markdown to disk."""
        kf_idx = map_data.get("keyframe_index", 1)
        json_filename = f"localemap_keyframe_{kf_idx}.json"

        if output_path:
            target_p = Path(output_path)
            if target_p.is_dir() or target_p.suffix == "":
                target_p.mkdir(parents=True, exist_ok=True)
                json_file = target_p / json_filename
            else:
                target_p.parent.mkdir(parents=True, exist_ok=True)
                json_file = target_p
        elif base_dir:
            base_p = Path(base_dir)
            base_p.mkdir(parents=True, exist_ok=True)
            json_file = base_p / json_filename
        else:
            fid = map_data.get("feature_id", "unknown")
            locale_dir = DEFAULT_LOCALES_DIR / fid
            locale_dir.mkdir(parents=True, exist_ok=True)
            json_file = locale_dir / json_filename

        json_file.write_text(json.dumps(map_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Companion Markdown
        md_file = json_file.with_suffix(".md")
        md_content = format_localemap_for_llm(map_data)
        md_file.write_text(md_content, encoding="utf-8")

        return json_file, md_file


# Alias for naming consistency
SubHistorian = Subhistorian


def evolve_locale_series(
    locale_dir: Union[Path, str],
    subhistorian: Optional[Subhistorian] = None,
    allow_stagnant_short_circuit: bool = True,
    overwrite: bool = False,
) -> list[tuple[Path, Path]]:
    """Sequentially evolves all consecutive keyframes for a single locale.

    Keyframe evolution within a single locale must execute sequentially (0 -> 1 -> 2 ...),
    maintaining strict spatial and historical continuity.

    Args:
        locale_dir: Directory of the locale (e.g. artifacts/locales/eldenmere).
        subhistorian: Subhistorian instance to use. If None, creates a default instance.
        allow_stagnant_short_circuit: If True, stagnant epochs bypass LLM execution.
        overwrite: If True, re-evolves and overwrites existing target keyframes.

    Returns:
        list[tuple[Path, Path]]: List of (json_path, md_path) for each evolved keyframe.
    """
    loc_dir = Path(locale_dir)
    if not loc_dir.exists() or not loc_dir.is_dir():
        logger.warning(f"Locale directory not found: {loc_dir}")
        return []

    agent = subhistorian or Subhistorian()
    saved_files: list[tuple[Path, Path]] = []

    # Discover all vector files sorted by starting keyframe index
    vec_files = sorted(
        loc_dir.glob("vector_*.json"),
        key=lambda p: int(re.search(r"vector_(\d+)", p.stem).group(1)) if re.search(r"vector_(\d+)", p.stem) else 0,
    )

    for v_file in vec_files:
        m = re.search(r"vector_(\d+)", v_file.stem)
        if not m:
            continue
        from_idx = int(m.group(1))
        to_idx = from_idx + 1

        target_json = loc_dir / f"localemap_keyframe_{to_idx}.json"
        target_md = loc_dir / f"localemap_keyframe_{to_idx}.md"

        if target_json.exists() and not overwrite:
            logger.info(f"Skipping existing evolved keyframe {target_json}")
            saved_files.append((target_json, target_md))
            continue

        prev_kf = loc_dir / f"localemap_keyframe_{from_idx}.json"
        if not prev_kf.exists():
            prev_kf = loc_dir / f"localemap_keyframe_{from_idx}.md"
            if not prev_kf.exists():
                logger.warning(f"Base keyframe {from_idx} not found for {loc_dir.name} at {prev_kf}, skipping.")
                continue

        logger.info(f"Evolving {loc_dir.name}: keyframe {from_idx} -> {to_idx}")
        evolved_map = agent.evolve_localemap(
            previous_keyframe=prev_kf,
            vector=v_file,
            to_keyframe_index=to_idx,
            allow_stagnant_short_circuit=allow_stagnant_short_circuit,
        )
        j_path, m_path = Subhistorian.save_localemap(evolved_map, base_dir=loc_dir)
        saved_files.append((j_path, m_path))

    return saved_files


def evolve_all_locales_concurrently(
    locales_dir: Union[Path, str] = DEFAULT_LOCALES_DIR,
    max_workers: int = 4,
    subhistorian: Optional[Subhistorian] = None,
    allow_stagnant_short_circuit: bool = True,
    overwrite: bool = False,
) -> dict[str, list[tuple[Path, Path]]]:
    """Concurrently evolves keyframe series across all discovered locales.

    Each locale's internal keyframe sequence evolves sequentially (0 -> 1 -> 2 ...),
    while distinct locales execute concurrently in separate worker threads.

    Args:
        locales_dir: Root directory containing locale subdirectories.
        max_workers: Maximum number of worker threads for parallel locale evolution.
        subhistorian: Shared Subhistorian agent instance (thread-safe token counting).
        allow_stagnant_short_circuit: If True, stagnant epochs bypass LLM execution.
        overwrite: If True, overwrites existing keyframes.

    Returns:
        dict[str, list[tuple[Path, Path]]]: Mapping of feature_id -> list of (json_path, md_path) files.
    """
    root_p = Path(locales_dir)
    if not root_p.exists():
        logger.warning(f"Locales directory does not exist: {root_p}")
        return {}

    agent = subhistorian or Subhistorian()

    # Find locale directories that contain at least one vector_*.json
    candidate_dirs: list[Path] = []
    for l_dir in sorted(root_p.iterdir()):
        if l_dir.is_dir() and list(l_dir.glob("vector_*.json")):
            candidate_dirs.append(l_dir)

    if not candidate_dirs:
        logger.warning(f"No locales with vector_*.json found in {root_p}")
        return {}

    results: dict[str, list[tuple[Path, Path]]] = {}
    workers = max(1, min(max_workers, len(candidate_dirs)))
    print(f"[CONCURRENCY] Evolving {len(candidate_dirs)} locales across {workers} worker threads...", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_fid = {
            executor.submit(
                evolve_locale_series,
                locale_dir=ldir,
                subhistorian=agent,
                allow_stagnant_short_circuit=allow_stagnant_short_circuit,
                overwrite=overwrite,
            ): ldir.name
            for ldir in candidate_dirs
        }

        for future in as_completed(future_to_fid):
            fid = future_to_fid[future]
            try:
                evolved_paths = future.result()
                results[fid] = evolved_paths
                print(f"[CONCURRENCY] Completed evolution for '{fid}': {len(evolved_paths)} keyframe(s) processed.", flush=True)
            except Exception as exc:
                logger.exception(f"Error evolving locale series for '{fid}': {exc}")
                print(f"[ERROR] Failed to evolve locale series for '{fid}': {exc}", file=sys.stderr, flush=True)

    return results


def main() -> None:
    """CLI entry point for the Subhistorian agent."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Evolve 16x16 localemaps across epochs using the Subhistorian agent and code execution."
    )
    parser.add_argument(
        "--locale",
        "-f",
        "--feature",
        type=str,
        default="",
        help="Feature ID to evolve (e.g. eldenmere). Searches in artifacts/locales/<feature>/.",
    )
    parser.add_argument(
        "--keyframe",
        "-k",
        type=int,
        default=0,
        help="Keyframe index to evolve from (default: 0 -> produces keyframe 1)",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="",
        help="Path to previous localemap keyframe file (.json or .md)",
    )
    parser.add_argument(
        "--vector",
        "-v",
        type=str,
        default="",
        help="Path to specific vector delta packet file (.json or .md)",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Evolve all available consecutive keyframes for the specified locale, or all locales.",
    )
    parser.add_argument(
        "--concurrency",
        "-j",
        type=int,
        default=4,
        help="Number of concurrent workers for multi-locale evolution (default: 4)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing evolved keyframes instead of skipping.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="",
        help="Custom output file or directory path.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.8-flash",
        help="Gemini model to use (default: gemini-3.8-flash)",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        default="MEDIUM",
        help="Thinking level for Gemini models (default: MEDIUM)",
    )
    parser.add_argument(
        "--force-llm",
        action="store_true",
        help="Force LLM execution even when vector packet indicates no new development.",
    )

    args = parser.parse_args()
    load_dotenv()

    print("=" * 80, flush=True)
    print(" SUBHISTORIAN: 16x16 LOCALE MAP EVOLUTION", flush=True)
    print("=" * 80, flush=True)
    print(f"Model: {args.model} | Thinking: {args.thinking} | Code Execution: ON\n", flush=True)

    subhistorian = Subhistorian(model_name=args.model, thinking_level=args.thinking)

    # Multi-locale concurrent branch
    if args.all and not args.locale and not args.input:
        results = evolve_all_locales_concurrently(
            locales_dir=DEFAULT_LOCALES_DIR,
            max_workers=args.concurrency,
            subhistorian=subhistorian,
            allow_stagnant_short_circuit=not args.force_llm,
            overwrite=args.overwrite,
        )
        print(f"\nCompleted evolution across {len(results)} locale(s).", flush=True)
        for fid, kfs in sorted(results.items()):
            print(f"  - {fid}: {len(kfs)} keyframe(s)", flush=True)

    elif args.locale and args.all:
        locale_dir = DEFAULT_LOCALES_DIR / args.locale
        if not locale_dir.exists():
            print(f"[ERROR] Locale directory not found: {locale_dir}", file=sys.stderr)
            sys.exit(1)
        kfs = evolve_locale_series(
            locale_dir=locale_dir,
            subhistorian=subhistorian,
            allow_stagnant_short_circuit=not args.force_llm,
            overwrite=args.overwrite,
        )
        print(f"\nCompleted evolution for '{args.locale}': {len(kfs)} keyframe(s).", flush=True)

    else:
        # Single keyframe evolution task
        tasks: list[tuple[Path, Path, Path]] = []
        if args.input and args.vector:
            in_p = Path(args.input)
            vec_p = Path(args.vector)
            if not in_p.exists():
                print(f"[ERROR] Input keyframe not found: {in_p}", file=sys.stderr)
                sys.exit(1)
            if not vec_p.exists():
                print(f"[ERROR] Vector file not found: {vec_p}", file=sys.stderr)
                sys.exit(1)
            out_dir = Path(args.output) if args.output else in_p.parent
            tasks.append((in_p, vec_p, out_dir))
        elif args.locale:
            locale_dir = DEFAULT_LOCALES_DIR / args.locale
            if not locale_dir.exists():
                print(f"[ERROR] Locale directory not found: {locale_dir}", file=sys.stderr)
                sys.exit(1)
            idx = args.keyframe
            kf_file = Path(args.input) if args.input else locale_dir / f"localemap_keyframe_{idx}.json"
            v_file = Path(args.vector) if args.vector else locale_dir / f"vector_{idx}.json"
            tasks.append((kf_file, v_file, Path(args.output) if args.output else locale_dir))
        else:
            default_dir = DEFAULT_LOCALES_DIR / "eldenmere"
            kf_file = default_dir / "localemap_keyframe_0.json"
            v_file = default_dir / "vector_0.json"
            if kf_file.exists() and v_file.exists():
                tasks.append((kf_file, v_file, default_dir))
            else:
                parser.print_help()
                sys.exit(1)

        for kf_path, vec_path, out_dir in tasks:
            if not kf_path.exists():
                print(f"[SKIP] Base keyframe not found: {kf_path}", flush=True)
                continue
            if not vec_path.exists():
                print(f"[SKIP] Evolution vector not found: {vec_path}", flush=True)
                continue

            print(f"--> Evolving: {kf_path.name} + {vec_path.name}", flush=True)

            try:
                evolved_map = subhistorian.evolve_localemap(
                    previous_keyframe=kf_path,
                    vector=vec_path,
                    allow_stagnant_short_circuit=not args.force_llm,
                )
                json_file, md_file = subhistorian.save_localemap(
                    evolved_map,
                    output_path=out_dir if out_dir.suffix else None,
                    base_dir=out_dir if not out_dir.suffix else None,
                )

                print_localemap_preview(evolved_map)
                print(f"JSON saved to:     {json_file}", flush=True)
                print(f"Markdown saved to: {md_file}\n", flush=True)

            except Exception as e:
                logger.exception("Error evolving localemap")
                print(f"[ERROR] Failed to evolve {kf_path.name}: {e}", file=sys.stderr)

    print("=" * 80, flush=True)
    print(" TOKEN USAGE SUMMARY", flush=True)
    print("=" * 80, flush=True)
    usage = subhistorian.token_usage
    print(f"Prompt Tokens:     {usage['prompt_tokens']:,}", flush=True)
    print(f"Candidate Tokens:  {usage['candidates_tokens']:,}", flush=True)
    if usage.get("thoughts_tokens"):
        print(f"Thoughts Tokens:   {usage['thoughts_tokens']:,}", flush=True)
    print(f"Total Tokens:      {usage['total_tokens']:,}", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
