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
            border_lines.append(f"- **ALL BORDERS:** Transition into host region ({host_name} — {host_type}).")
        else:
            cardinal_label = " & ".join(unassigned)
            border_lines.append(
                f"- **{cardinal_label} BORDERS:** Transition into host region ({host_name} — {host_type})."
            )

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize deterministic Locale Generation Seed markdown files from landmark dossiers."
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
        help="Output directory to save seed.md files into each locale folder (default: artifacts/locales)",
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
        help="Keyframe index to extract (default: 0 for first keyframe / genesis)",
    )
    args = parser.parse_args()

    dossiers_p = Path(args.dossiers)
    out_p = Path(args.output) if args.output else None

    if args.feature:
        # Check both nested {feature}/dossier.json and flat {feature}_dossier.json
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
