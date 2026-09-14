"""Locale Generation Seed synthesizer module.

Translates deterministic multi-epoch Landmark Vector Dossiers into standardized,
purely context-driven prompt seeds for the downstream Subarchitect grid generator.

Note: Tile legends, syntax schemas, and procedural code execution instructions
belong to the Subarchitect agent system prompt, not to individual locale seeds.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def resolve_scale_category(char: str) -> Optional[tuple[str, str]]:
    """Maps landmark glyph to a deterministic scale and layout profile.

    'o' -> Small / Compact
    'O' -> Large / Urban
    '!' -> None (Dungeons/ruins do not use settlement scale categories)

    Returns:
        Optional[tuple[str, str]]: (Scale Category Name, Descriptive Guidance), or None for dungeons.
    """
    c = str(char).strip()
    if c == "o":
        return (
            "Small / Compact",
            "Fledgling cluster. Small structural footprint with a high proportion of surrounding natural terrain, open yards, and frontier buffer.",
        )
    elif c == "O":
        return (
            "Large / Urban",
            "Expansive, high-density footprint. Distinct functional wards, formal thoroughfares, and fortified perimeter walls.",
        )
    return None


def synthesize_perimeter_borders(
    host_region: dict[str, Any],
    neighborhood_regions: list[dict[str, Any]],
) -> list[str]:
    """Resolves edge constraints for all 4 cardinal borders deterministically."""
    host_name = host_region.get("name", "Host Region")
    host_type = host_region.get("type", "wilderness").title()
    host_lore = host_region.get("lore", "").strip()

    cardinal_edges: dict[str, Optional[dict[str, Any]]] = {
        "NORTH": None,
        "SOUTH": None,
        "EAST": None,
        "WEST": None,
    }

    # Match neighbors to cardinal borders based on relative_position
    for neighbor in neighborhood_regions:
        pos = neighbor.get("relative_position", "").upper()
        for cardinal in cardinal_edges:
            if cardinal in pos and cardinal_edges[cardinal] is None:
                cardinal_edges[cardinal] = neighbor

    border_lines: list[str] = []
    processed_edges: set[str] = set()

    for cardinal in ["NORTH", "SOUTH", "EAST", "WEST"]:
        if cardinal in processed_edges:
            continue
        neighbor = cardinal_edges[cardinal]
        if neighbor:
            # Group all cardinal edges sharing this same neighbor
            matching_cardinals = [
                c
                for c in ["NORTH", "SOUTH", "EAST", "WEST"]
                if cardinal_edges[c] is not None
                and cardinal_edges[c].get("id") == neighbor.get("id")
            ]
            for c in matching_cardinals:
                processed_edges.add(c)

            cardinal_label = " & ".join(matching_cardinals)
            n_name = neighbor.get("name", f"Region {neighbor.get('id')}")
            n_type = neighbor.get("type", "wilderness").title()
            n_lore = neighbor.get("lore", "").strip()

            line = f"- **{cardinal_label} BORDER:** {n_name} ({n_type})"
            if n_lore:
                line += f'\n  - *Lore Context:* "{n_lore}"'
            border_lines.append(line)
        else:
            processed_edges.add(cardinal)

    # Any remaining unassigned borders transition into host region
    unassigned = [c for c in ["NORTH", "SOUTH", "EAST", "WEST"] if cardinal_edges[c] is None]
    if unassigned:
        if len(unassigned) == 4:
            line = f"- **ALL BORDERS:** Transition into host region ({host_name} — {host_type})."
        else:
            cardinal_label = " & ".join(unassigned)
            line = f"- **{cardinal_label} BORDERS:** Transition into host region ({host_name} — {host_type})."
        if host_lore:
            line += f'\n  - *Lore Context:* "{host_lore}"'
        border_lines.append(line)

    return border_lines


def generate_locale_seed(
    dossier: dict[str, Any],
    keyframe_index: int = 0,
) -> str:
    """Synthesizes a clean, deterministic Markdown generation seed from a landmark dossier keyframe."""
    keyframes = dossier.get("keyframes", [])
    if not keyframes:
        raise ValueError(f"Dossier '{dossier.get('feature_id')}' contains no keyframes.")

    if keyframe_index < 0 or keyframe_index >= len(keyframes):
        raise IndexError(
            f"Invalid keyframe_index {keyframe_index}; dossier has {len(keyframes)} keyframes (0..{len(keyframes)-1})."
        )

    kf = keyframes[keyframe_index]
    feature_id = dossier.get("feature_id", "unknown_feature")
    name = kf.get("name", feature_id.replace("_", " ").title())
    ftype = kf.get("type", "landmark").title()
    char = kf.get("char", "o")

    scale_info = resolve_scale_category(char)

    # 1. Classification & Scale
    section_title = "## 1. Classification & Scale" if scale_info else "## 1. Classification"
    lines: list[str] = [
        f"# Locale Generation Seed: {name}",
        "",
        section_title,
        f"- **Feature ID:** `{feature_id}`",
        f"- **Name:** {name}",
        f"- **Type:** {ftype}",
    ]
    if scale_info:
        scale_name, scale_guidance = scale_info
        lines.append(f"- **Scale Category:** {scale_name} ({scale_guidance})")
    lines.append("")

    # 2. Narrative Lore & Materials
    desc = kf.get("description") or kf.get("lore", "A notable regional landmark.")
    env = kf.get("environment", {})
    host_reg = env.get("host_region", {})
    host_name = host_reg.get("name", "Host Region")
    host_type = host_reg.get("type", "wilderness").title()
    host_lore = host_reg.get("lore", "").strip()

    lines.extend([
        "## 2. Narrative Lore & Materials",
        f'- **{name} Lore:** "{desc.strip()}"',
        f"- **Host Region:** {host_name} ({host_type})",
    ])
    if host_lore:
        lines.append(f'- **Host Region Ecology:** "{host_lore}"')
    lines.append("")

    # 3. Perimeter Edge Constraints
    neighborhood = env.get("neighborhood_regions", [])
    border_lines = synthesize_perimeter_borders(host_reg, neighborhood)
    lines.extend([
        "## 3. Perimeter Edge Constraints",
        *border_lines,
        "",
    ])

    # 4. Ingress & Approaches
    connected_roads = kf.get("connected_roads", [])
    lines.append("## 4. Ingress & Approaches")
    if connected_roads:
        for r in connected_roads:
            gate_dir = str(r.get("gate_approach", "Perimeter")).upper()
            r_name = r.get("road_name", r.get("road_id", "Road"))
            r_type = str(r.get("road_type", "road")).title()
            r_desc = str(r.get("description", "")).strip()
            dest = r.get("destination")

            lines.append(f"- **{gate_dir} Approach:**")
            lines.append(f"  - *Road:* {r_name} ({r_type})")
            if r_desc:
                lines.append(f'  - *Description:* "{r_desc}"')
            if dest and isinstance(dest, dict):
                d_name = dest.get("name", "Unknown")
                d_type = str(dest.get("type", "landmark")).title()
                lines.append(f"  - *Destination:* Leads toward {d_name} ({d_type})")
                d_lore = str(dest.get("description") or dest.get("lore") or "").strip()
                if d_lore:
                    lines.append(f'  - *Destination Lore:* "{d_lore}"')
        lines.append("- **Other Borders:** No external road infrastructure.")
    else:
        lines.append("- **Road Ingress:** None. (Isolated wilderness site; entry is via local terrain traversal).")
    lines.append("")

    # 5. Generation Directives
    scale_directive = (
        f"1. Construct the locale grid reflecting the **{scale_name}** scale and spatial density."
        if scale_info
        else f"1. Construct the locale grid reflecting a chambered {ftype.lower()} layout."
    )
    lines.extend([
        "## 5. Generation Directives",
        scale_directive,
        "2. Perimeter edges must faithfully transition into the bordering regions defined in Section 3.",
    ])
    if connected_roads:
        gate_approaches = ", ".join(sorted({str(r.get("gate_approach", "perimeter")).title() for r in connected_roads}))
        lines.append(
            f"3. Establish physical gate entrances and/or thoroughfares aligned to external road approaches ({gate_approaches})."
        )
    else:
        lines.append(
            "3. No external roads enter this site; entry point or structure threshold is reached via wild terrain."
        )
    lines.extend([
        f"4. Internal structures and architecture must strictly reflect the materials and narrative in the {name} Lore.",
        "5. Maintain 100% 4-way cardinal walking connectivity (N, S, E, W) between all entrances, primary structures, and key facilities.",
    ])

    return "\n".join(lines) + "\n"


def generate_all_locale_seeds(
    dossiers_dir: Path | str = "artifacts/locales",
    output_dir: Optional[Path | str] = "artifacts/locales",
    keyframe_index: int = 0,
) -> dict[str, str]:
    """Generates locale seed markdown files for all landmark dossiers in the directory."""
    dossiers_path = Path(dossiers_dir)
    if not dossiers_path.exists():
        logger.warning(f"Dossiers directory not found: {dossiers_path}")
        return {}

    out_path = Path(output_dir) if output_dir else None

    # Discover dossiers in both nested locale dirs (*/dossier.json) and flat dirs (*_dossier.json)
    dossier_files: list[Path] = []
    dossier_files.extend(dossiers_path.glob("*/dossier.json"))
    dossier_files.extend(dossiers_path.glob("*_dossier.json"))

    seeds: dict[str, str] = {}
    for fpath in sorted(dossier_files):
        try:
            dossier_data = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error reading {fpath}: {e}")
            continue

        fid = dossier_data.get("feature_id")
        if not fid or fid in seeds:
            continue

        try:
            seed_md = generate_locale_seed(dossier_data, keyframe_index=keyframe_index)
            seeds[fid] = seed_md

            if out_path:
                locale_dir = out_path / fid
                locale_dir.mkdir(parents=True, exist_ok=True)
                seed_name = "seed.md" if keyframe_index == 0 else f"seed_epoch_{dossier_data.get('keyframes', [{}])[keyframe_index].get('epoch', keyframe_index + 1)}.md"
                target = locale_dir / seed_name
                target.write_text(seed_md, encoding="utf-8")
                logger.info(f"Wrote locale seed for '{fid}' to {target}")
        except Exception as e:
            logger.error(f"Error generating seed for {fid}: {e}")

    return seeds


def describe_scale_transition(
    from_char: str,
    from_type: str,
    to_char: str,
    to_type: str,
) -> Optional[str]:
    """Generates a plain-English description of the scale and status transition, or None if unchanged."""
    c_from, c_to = str(from_char).strip(), str(to_char).strip()
    t_from, t_to = str(from_type).lower().replace("_", " "), str(to_type).lower().replace("_", " ")

    if c_from == c_to and t_from == t_to:
        return None

    if c_from == "o" and c_to == "O":
        phrase = "Settlement turned into big city"
        guidance = "Urban Densification & Fortification"
    elif c_from == "o" and c_to == "!":
        phrase = "Settlement fell into an abandoned ruin/dungeon"
        guidance = "Decay & Ruination"
    elif c_from == "O" and c_to == "!":
        phrase = "Metropolis collapsed into dangerous cataclysmic ruins"
        guidance = "Cataclysmic Ruination & Structural Collapse"
    elif c_from == "!" and c_to == "o":
        phrase = "Ruins reclaimed into a civilized outpost/settlement"
        guidance = "Frontier Reclamation & Reconstruction"
    elif c_from == "!" and c_to == "O":
        phrase = "Ruins reclaimed and rebuilt into a fortified city"
        guidance = "Major Urban Restoration"
    elif c_from == "O" and c_to == "o":
        phrase = "Metropolis declined into a diminished outpost"
        guidance = "Depopulation & Retraction"
    else:
        phrase = f"{t_from.title()} transitioned into a {t_to.title()}"
        guidance = "Structural Reclassification"

    from_scale = resolve_scale_category(c_from)
    to_scale = resolve_scale_category(c_to)
    scale_str = ""
    if from_scale and to_scale:
        scale_str = f" ({from_scale[0]} -> {to_scale[0]})"
    elif to_scale:
        scale_str = f" (Transitioned to {to_scale[0]})"

    return f"{phrase}{scale_str}. {guidance}."


def _find_epoch_timeline_entry(epoch: int, artifacts_dir: Optional[Path | str] = None) -> Optional[str]:
    """Retrieves the timeline text for the specified epoch from worldmap snapshots."""
    if not artifacts_dir:
        return None
    art_p = Path(artifacts_dir)
    ep_file = art_p / f"worldmap_epoch_{epoch}.json"
    if ep_file.exists():
        try:
            w = json.loads(ep_file.read_text(encoding="utf-8"))
            timeline = w.get("timeline", [])
            if isinstance(timeline, list):
                for item in timeline:
                    if isinstance(item, str) and (f"Epoch {epoch}" in item or f"epoch {epoch}" in item.lower()):
                        return item.strip()
                if timeline:
                    return str(timeline[-1]).strip()
        except Exception:
            pass

    wm_file = art_p / "worldmap.json"
    if wm_file.exists():
        try:
            w = json.loads(wm_file.read_text(encoding="utf-8"))
            timeline = w.get("timeline", [])
            if isinstance(timeline, list):
                for item in timeline:
                    if isinstance(item, str) and (f"Epoch {epoch}" in item or f"epoch {epoch}" in item.lower()):
                        return item.strip()
        except Exception:
            pass
    return None


def clean_global_updates(text: str) -> str:
    """Cleans epoch title headers, glyph mutations, landmark glyphs, and map coordinates from world timeline text."""
    if not text:
        return ""
    # 0. Strip epoch title header (e.g. '## Epoch 3: The Resonant Ruin and the Southern Quays')
    text = re.sub(r"^##\s*Epoch\s*\d+[^\n]*\n+", "", text.strip(), flags=re.IGNORECASE)
    # 1. Remove glyph transitions like ('o' -> 'O'), ('o' -> '!'), (o -> O)
    text = re.sub(
        r"\s*\(['\"]?[!oO*#~^@+%\-a-zA-Z0-9]{1,3}['\"]?\s*->\s*['\"]?[!oO*#~^@+%\-a-zA-Z0-9]{1,3}['\"]?\)",
        "",
        text,
    )
    # 2. Remove single character glyph mentions like (*), (o), (!), ('o')
    text = re.sub(r"\s*\(['\"]?[!oO*#~^@+%\-]('|\")?\)", "", text)
    # 3. Remove road coordinate ranges like [23, 12] <-> [23, 17]
    text = re.sub(r"\s*\[\s*\d+\s*,\s*\d+\s*\]\s*<->\s*\[\s*\d+\s*,\s*\d+\s*\]", "", text)
    # 4. Remove multi-coordinate lists like across [[20, 5], [21, 5]]
    text = re.sub(
        r"\s*(?:across|at|along|around)?\s*\[\[\s*\d+\s*,\s*\d+\s*\](?:\s*,\s*\[\s*\d+\s*,\s*\d+\s*\])*\]",
        "",
        text,
    )
    # 5. Remove single coordinate mentions like at [20, 5], at [23, 11] or just [20, 5]
    text = re.sub(r"\s*at\s*\[\s*\d+\s*,\s*\d+\s*\]", "", text)
    text = re.sub(r"\s*\[\s*\d+\s*,\s*\d+\s*\]", "", text)
    # Clean up double spaces or awkward punctuation
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\s+([,.:;])", r"\1", text)
    return text.strip()


# Backward compatibility alias
clean_world_updates = clean_global_updates


def build_locale_vector_packet(
    dossier: dict[str, Any],
    from_keyframe_index: int = 0,
    artifacts_dir: Optional[Path | str] = "artifacts",
) -> dict[str, Any]:
    """Synthesizes a sparse vector delta packet for evolving from from_keyframe_index to from_keyframe_index + 1.

    Omits any aspect that experienced no new development.
    """
    keyframes = dossier.get("keyframes", [])
    fid = dossier.get("feature_id", "unknown_feature")
    if not keyframes:
        raise ValueError(f"Dossier '{fid}' contains no keyframes.")

    if from_keyframe_index < 0 or from_keyframe_index + 1 >= len(keyframes):
        raise IndexError(
            f"Cannot synthesize vector packet: dossier '{fid}' has only {len(keyframes)} keyframe(s); "
            f"cannot evolve past keyframe {from_keyframe_index}."
        )

    prev_kf = keyframes[from_keyframe_index]
    curr_kf = keyframes[from_keyframe_index + 1]

    from_ep = prev_kf.get("epoch", from_keyframe_index + 1)
    to_ep = curr_kf.get("epoch", from_keyframe_index + 2)
    from_char = str(prev_kf.get("char", "o")).strip()
    to_char = str(curr_kf.get("char", "o")).strip()
    from_name = prev_kf.get("name", fid.replace("_", " ").title())
    to_name = curr_kf.get("name", fid.replace("_", " ").title())
    from_type = str(prev_kf.get("type", "landmark")).strip()
    to_type = str(curr_kf.get("type", "landmark")).strip()

    packet: dict[str, Any] = {
        "feature_id": fid,
        "from_keyframe": from_keyframe_index,
        "to_keyframe": from_keyframe_index + 1,
        "from_epoch": from_ep,
        "to_epoch": to_ep,
        "to_name": to_name,
    }

    if to_name != from_name:
        packet["name_change"] = f"{from_name} -> {to_name}"

    # 1a. Scale New Development
    scale_dev = describe_scale_transition(from_char, from_type, to_char, to_type)
    if scale_dev:
        packet["scale_new_development"] = scale_dev

    # 1b. Locale Lore New Development
    prev_desc = (prev_kf.get("description") or prev_kf.get("lore") or "").strip()
    curr_desc = (curr_kf.get("description") or curr_kf.get("lore") or "").strip()
    locale_lore_dev = curr_desc if (curr_desc and curr_desc != prev_desc) else None
    if locale_lore_dev:
        packet["locale_lore_new_development"] = locale_lore_dev

    # 1c. Host Region Lore New Development
    prev_host = prev_kf.get("environment", {}).get("host_region", {})
    curr_host = curr_kf.get("environment", {}).get("host_region", {})
    host_region_dev = None
    if curr_host:
        prev_h_lore = (prev_host.get("lore") or "").strip()
        curr_h_lore = (curr_host.get("lore") or "").strip()
        if curr_h_lore and curr_h_lore != prev_h_lore:
            host_region_dev = curr_h_lore
        elif curr_host.get("name") != prev_host.get("name") and curr_host.get("name"):
            host_region_dev = (
                f"Host region transformed into {curr_host.get('name')} ({curr_host.get('type', 'farmland')})."
            )
    if host_region_dev:
        packet["host_region_lore_new_development"] = host_region_dev
        packet["home_region_lore_new_development"] = host_region_dev

    # 2. Surrounding Perimeter Deltas
    prev_neighbors = {
        n.get("id"): n for n in prev_kf.get("environment", {}).get("neighborhood_regions", []) if isinstance(n, dict) and "id" in n
    }
    curr_neighbors = {
        n.get("id"): n for n in curr_kf.get("environment", {}).get("neighborhood_regions", []) if isinstance(n, dict) and "id" in n
    }
    perimeter_devs: list[dict[str, str]] = []
    for nid, c_n in curr_neighbors.items():
        p_n = prev_neighbors.get(nid)
        border = c_n.get("relative_position") or "Perimeter"
        n_name = c_n.get("name", f"Region {nid}")
        if not p_n:
            c_lore = c_n.get("lore", "").strip()
            delta_msg = f"New neighboring biome appeared: {c_lore}" if c_lore else f"New neighboring biome: {c_n.get('type', 'wilderness')}."
            perimeter_devs.append({"border": border, "neighbor_name": n_name, "delta": delta_msg})
        else:
            c_lore = c_n.get("lore", "").strip()
            p_lore = p_n.get("lore", "").strip()
            c_hist = c_n.get("historical_context", "").strip()
            p_hist = p_n.get("historical_context", "").strip()
            is_generic_hist = c_hist.startswith("Active region in Epoch")
            if c_lore != p_lore and c_lore:
                perimeter_devs.append({"border": border, "neighbor_name": n_name, "delta": c_lore})
            elif c_hist != p_hist and c_hist and not is_generic_hist:
                perimeter_devs.append({"border": border, "neighbor_name": n_name, "delta": c_hist})
    if perimeter_devs:
        packet["perimeter_new_development"] = perimeter_devs

    # 3. Road Deltas & 4. Neighbouring Destination Deltas
    prev_roads_list = [r for r in prev_kf.get("connected_roads", []) if isinstance(r, dict)]
    curr_roads_list = [r for r in curr_kf.get("connected_roads", []) if isinstance(r, dict)]

    prev_roads = {r.get("road_id"): r for r in prev_roads_list if r.get("road_id")}
    curr_roads = {r.get("road_id"): r for r in curr_roads_list if r.get("road_id")}

    road_devs: list[dict[str, str]] = []
    dest_devs: list[dict[str, str]] = []

    # New & Modified roads
    for rid, r in curr_roads.items():
        r_name = r.get("road_name", rid.replace("_", " ").title())
        r_dir = str(r.get("gate_approach", "PERIMETER")).upper()
        dest = r.get("destination", {})
        d_name = dest.get("name", "Unknown Destination") if isinstance(dest, dict) else str(dest)
        d_type = dest.get("type", "landmark").title() if isinstance(dest, dict) else ""
        dest_label = f"{d_name} ({d_type})" if d_type else d_name

        if rid not in prev_roads:
            r_desc = r.get("description") or r.get("road_lore") or "Newly paved or established road."
            road_devs.append({
                "road_name": r_name,
                "direction": r_dir,
                "status": "new",
                "delta": f"New road established leading toward {dest_label}. {r_desc}".strip(),
            })
            if isinstance(dest, dict):
                d_lore = (dest.get("description") or dest.get("lore") or "").strip()
                dest_devs.append({
                    "destination": d_name,
                    "direction": f"{r_dir} via {r_name}",
                    "delta": f"Leads toward {dest_label}. {d_lore}".strip(),
                })
        else:
            prev_r = prev_roads[rid]
            # Check for road changes (lore, type)
            p_desc = (prev_r.get("description") or prev_r.get("road_lore") or "").strip()
            c_desc = (r.get("description") or r.get("road_lore") or "").strip()
            p_type = prev_r.get("road_type")
            c_type = r.get("road_type")
            if (c_desc != p_desc and c_desc) or (c_type != p_type and c_type):
                road_devs.append({
                    "road_name": r_name,
                    "direction": r_dir,
                    "status": "upgraded" if c_type == "paved" and p_type != "paved" else "modified",
                    "delta": c_desc or f"Road updated to {c_type} route.",
                })

            # Check for destination changes
            if isinstance(dest, dict):
                prev_dest = prev_r.get("destination", {})
                if not isinstance(prev_dest, dict) or prev_dest != dest:
                    d_lore = (dest.get("description") or dest.get("lore") or "").strip()
                    p_dlore = (prev_dest.get("description") or prev_dest.get("lore") or "").strip() if isinstance(prev_dest, dict) else ""
                    if d_lore != p_dlore or dest.get("type") != getattr(prev_dest, "get", lambda *_: None)("type"):
                        dest_devs.append({
                            "destination": d_name,
                            "direction": f"{r_dir} via {r_name}",
                            "delta": f"{dest_label}: {d_lore}".strip(),
                        })

    # Lost roads
    for rid, r in prev_roads.items():
        if rid not in curr_roads:
            r_name = r.get("road_name", rid.replace("_", " ").title())
            r_dir = str(r.get("gate_approach", "PERIMETER")).upper()
            road_devs.append({
                "road_name": r_name,
                "direction": r_dir,
                "status": "lost",
                "delta": "Road severed or fallen into disuse.",
            })

    if road_devs:
        packet["road_new_development"] = road_devs
    if dest_devs:
        packet["neighbouring_destination_new_development"] = dest_devs

    has_changes = bool(
        scale_dev
        or locale_lore_dev
        or host_region_dev
        or perimeter_devs
        or road_devs
        or dest_devs
    )

    packet["has_new_development"] = has_changes

    # 5. Global Developments (only included if the epoch experienced active developments)
    if has_changes:
        timeline_entry = _find_epoch_timeline_entry(to_ep, artifacts_dir=artifacts_dir)
        if timeline_entry:
            clean_updates = clean_global_updates(timeline_entry)
            packet["global_developments"] = clean_updates
            packet["global_updates"] = clean_updates
            packet["world_updates"] = clean_updates
            packet["epoch_timeline_content"] = clean_updates
    else:
        packet["status"] = (
            f"No recorded developments, environmental shifts, or infrastructure changes occurred for {to_name} in Epoch {to_ep}."
        )

    return packet


def format_locale_vector_markdown(packet: dict[str, Any]) -> str:
    """Renders a sparse vector delta packet into clean LLM/human readable Markdown."""
    fid = packet.get("feature_id", "unknown_feature")
    to_name = packet.get("to_name", fid.replace("_", " ").title())
    from_ep = packet.get("from_epoch", 1)
    to_ep = packet.get("to_epoch", 2)

    lines: list[str] = [
        f"# Locale Evolution Vector: {to_name}",
        "",
    ]

    if "name_change" in packet:
        lines.extend([
            f"- **Name Change:** {packet['name_change']}",
            "",
        ])

    if not packet.get("has_new_development", True):
        status_msg = packet.get(
            "status",
            f"No recorded developments, environmental shifts, or infrastructure changes occurred for {to_name} in Epoch {to_ep}.",
        )
        lines.extend([
            "### Status",
            status_msg,
            "",
        ])
        return "\n".join(lines).strip() + "\n"

    # 5. Global Developments
    global_devs = (
        packet.get("global_developments")
        or packet.get("global_updates")
        or packet.get("world_updates")
        or packet.get("epoch_timeline_content")
    )
    if global_devs:
        lines.extend([
            "## Global Developments",
            global_devs,
            "",
            "---",
            "",
            f"## Locale ({to_name}) Developments",
            "",
        ])
    else:
        lines.extend([
            f"## Locale ({to_name}) Developments",
            "",
        ])

    # 1a. Scale New Development
    if "scale_new_development" in packet:
        lines.extend([
            "### Scale New Development",
            f'"{packet["scale_new_development"]}"',
            "",
        ])

    # 1b. Locale Lore New Development
    if "locale_lore_new_development" in packet:
        lines.extend([
            "### Locale Lore New Development",
            f'"{packet["locale_lore_new_development"]}"',
            "",
        ])

    # 1c. Host Region Lore New Development
    host_reg_dev = packet.get("host_region_lore_new_development") or packet.get("home_region_lore_new_development")
    if host_reg_dev:
        lines.extend([
            "### Host Region Lore New Development",
            f'"{host_reg_dev}"',
            "",
        ])

    # 2. Perimeter New Development
    if "perimeter_new_development" in packet:
        lines.append("### Perimeter New Development")
        for item in packet["perimeter_new_development"]:
            border = item.get("border", "Perimeter")
            neighbor = item.get("neighbor_name", "Neighbor")
            delta = item.get("delta", "")
            lines.append(f"- **{border} ({neighbor}):** {delta}")
        lines.append("")

    # 3. Road New Development
    if "road_new_development" in packet:
        lines.append("### Road New Development")
        for item in packet["road_new_development"]:
            r_name = item.get("road_name", "Road")
            r_dir = item.get("direction", "Perimeter")
            delta = item.get("delta", "")
            lines.append(f"- **{r_name} ({r_dir}):** {delta}")
        lines.append("")

    # 4. Neighbouring Destination New Development
    if "neighbouring_destination_new_development" in packet:
        lines.append("### Neighbouring Destination New Development")
        for item in packet["neighbouring_destination_new_development"]:
            dest = item.get("destination", "Destination")
            dir_str = item.get("direction", "Road")
            delta = item.get("delta", "")
            lines.append(f"- **{dest} ({dir_str}):** {delta}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_locale_vector(
    dossier: dict[str, Any],
    from_keyframe_index: int = 0,
    artifacts_dir: Optional[Path | str] = "artifacts",
) -> str:
    """Synthesizes a clean, deterministic Markdown evolution vector for the keyframe transition."""
    packet = build_locale_vector_packet(
        dossier=dossier,
        from_keyframe_index=from_keyframe_index,
        artifacts_dir=artifacts_dir,
    )
    return format_locale_vector_markdown(packet)


def save_locale_vector(
    dossier: dict[str, Any],
    from_keyframe_index: int = 0,
    output_dir: Path | str = "artifacts/locales",
    artifacts_dir: Optional[Path | str] = "artifacts",
) -> tuple[Path, Path]:
    """Generates and saves both the .json and .md vector delta packet files."""
    packet = build_locale_vector_packet(
        dossier=dossier,
        from_keyframe_index=from_keyframe_index,
        artifacts_dir=artifacts_dir,
    )
    md_content = format_locale_vector_markdown(packet)

    fid = packet.get("feature_id", "unknown_feature")
    locale_dir = Path(output_dir) / fid
    locale_dir.mkdir(parents=True, exist_ok=True)

    json_path = locale_dir / f"vector_{from_keyframe_index}.json"
    md_path = locale_dir / f"vector_{from_keyframe_index}.md"

    json_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    md_path.write_text(md_content, encoding="utf-8")

    logger.info(f"Saved vector delta packet for '{fid}' to {json_path} and {md_path}")
    return json_path, md_path


def generate_all_locale_vectors(
    dossiers_dir: Path | str = "artifacts/locales",
    artifacts_dir: Optional[Path | str] = "artifacts",
    output_dir: Optional[Path | str] = "artifacts/locales",
) -> dict[str, list[dict[str, Any]]]:
    """Compiles and saves .json and .md vector delta packets for all eligible landmark keyframe transitions."""
    dossiers_path = Path(dossiers_dir)
    if not dossiers_path.exists():
        logger.warning(f"Dossiers directory not found: {dossiers_path}")
        return {}

    out_path = Path(output_dir) if output_dir else dossiers_path

    dossier_files: list[Path] = []
    dossier_files.extend(dossiers_path.glob("*/dossier.json"))
    dossier_files.extend(dossiers_path.glob("*_dossier.json"))

    results: dict[str, list[dict[str, Any]]] = {}

    for fpath in sorted(dossier_files):
        try:
            dossier_data = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error reading {fpath}: {e}")
            continue

        fid = dossier_data.get("feature_id")
        if not fid or fid in results:
            continue

        keyframes = dossier_data.get("keyframes", [])
        if len(keyframes) < 2:
            continue

        fid_packets: list[dict[str, Any]] = []
        for i in range(len(keyframes) - 1):
            try:
                packet = build_locale_vector_packet(
                    dossier=dossier_data,
                    from_keyframe_index=i,
                    artifacts_dir=artifacts_dir,
                )
                if out_path:
                    save_locale_vector(
                        dossier=dossier_data,
                        from_keyframe_index=i,
                        output_dir=out_path,
                        artifacts_dir=artifacts_dir,
                    )
                fid_packets.append(packet)
            except Exception as e:
                logger.error(f"Error generating vector for '{fid}' keyframe {i}: {e}")

        if fid_packets:
            results[fid] = fid_packets

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize deterministic Locale Generation Seeds or Vector Delta Packets from landmark dossiers."
    )
    parser.add_argument(
        "--dossiers",
        "-d",
        type=str,
        default="artifacts/locales",
        help="Directory containing locales or dossier.json files (default: artifacts/locales)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="artifacts/locales",
        help="Output directory to save generated files into each locale folder (default: artifacts/locales)",
    )
    parser.add_argument(
        "--artifacts",
        "-a",
        type=str,
        default="artifacts",
        help="Artifacts directory containing worldmap snapshots (default: artifacts)",
    )
    parser.add_argument(
        "--feature",
        "-f",
        type=str,
        default="",
        help="Feature ID to extract (default: all landmarks)",
    )
    parser.add_argument(
        "--keyframe",
        "-k",
        type=int,
        default=0,
        help="Keyframe index to extract (default: 0)",
    )
    parser.add_argument(
        "--vector",
        "-v",
        action="store_true",
        help="Synthesize vector delta packets (.json and .md) instead of initial seed.md",
    )
    args = parser.parse_args()

    dossiers_p = Path(args.dossiers)
    out_p = Path(args.output) if args.output else None
    artifacts_p = Path(args.artifacts)

    if args.vector:
        if args.feature:
            fpath = dossiers_p / args.feature / "dossier.json"
            if not fpath.exists():
                fpath = dossiers_p / f"{args.feature}_dossier.json"
            if not fpath.exists():
                print(f"Error: Dossier file not found for feature '{args.feature}' in {dossiers_p}")
                return
            dossier_data = json.loads(fpath.read_text(encoding="utf-8"))
            json_target, md_target = save_locale_vector(
                dossier=dossier_data,
                from_keyframe_index=args.keyframe,
                output_dir=out_p or dossiers_p,
                artifacts_dir=artifacts_p,
            )
            print(f"Saved vector delta packet for '{args.feature}' (Keyframe {args.keyframe} -> {args.keyframe + 1}):")
            print(f"  - JSON: {json_target}")
            print(f"  - MD:   {md_target}")
            print("\n" + md_target.read_text(encoding="utf-8"))
        else:
            results = generate_all_locale_vectors(
                dossiers_dir=dossiers_p,
                artifacts_dir=artifacts_p,
                output_dir=out_p,
            )
            print(f"Compiled vector delta packets for {len(results)} landmarks in {out_p}:")
            for fid, pkts in results.items():
                print(f"  - {fid}: {len(pkts)} evolution packet(s)")
    else:
        if args.feature:
            fpath = dossiers_p / args.feature / "dossier.json"
            if not fpath.exists():
                fpath = dossiers_p / f"{args.feature}_dossier.json"
            if not fpath.exists():
                print(f"Error: Dossier file not found for feature '{args.feature}' in {dossiers_p}")
                return
            dossier_data = json.loads(fpath.read_text(encoding="utf-8"))
            seed_md = generate_locale_seed(dossier_data, keyframe_index=args.keyframe)
            if out_p:
                locale_dir = out_p / args.feature
                locale_dir.mkdir(parents=True, exist_ok=True)
                seed_name = "seed.md" if args.keyframe == 0 else f"seed_epoch_{dossier_data.get('keyframes', [{}])[args.keyframe].get('epoch', args.keyframe + 1)}.md"
                target = locale_dir / seed_name
                target.write_text(seed_md, encoding="utf-8")
                print(f"Saved seed for '{args.feature}' to {target}")
            print("\n" + seed_md)
        else:
            results = generate_all_locale_seeds(
                dossiers_dir=dossiers_p,
                output_dir=out_p,
                keyframe_index=args.keyframe,
            )
            print(f"Compiled {len(results)} locale generation seeds in {out_p}:")
            for fid in results:
                print(f"  - {fid}")


if __name__ == "__main__":
    main()
