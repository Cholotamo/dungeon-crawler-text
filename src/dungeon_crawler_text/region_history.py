"""Regional biome history tracking and compilation module.

Maintains continuous chronological history for all regions across epochs,
recording baseline primordial geography, ecological shifts, domain expansions,
and regional lore mutations in persistent JSON and Markdown artifacts.
"""

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Optional


def _extract_epoch_region_bullets(timeline_entry: str) -> list[tuple[str, str]]:
    """Extracts (subject_name, explanation) pairs from timeline bullet points.

    Matches bullets such as:
      - **Wind-Scoured Heathlands (Region Lore Mutation):** Transformed from desolate uplands...
      - **Heathgard Terraces (Domain Expansion):** Nomadic clans cleared the rocky slopes...
      - **The Sanctified Bluffs (Domain Cleansing):** Dissolved the necrotic blight...
    """
    if not timeline_entry or not isinstance(timeline_entry, str):
        return []

    results: list[tuple[str, str]] = []
    lines = timeline_entry.split("\n")
    for line in lines:
        line_clean = line.strip()
        if not line_clean.startswith("-"):
            continue

        # Match pattern: - **Name (Action):** Explanation or - **Name:** Explanation
        m = re.search(r"-\s+\*\*([^*]+?)(?::\*\*|\*\*:)\s*(.+)", line_clean)
        if m:
            raw_title = m.group(1).strip()
            explanation = m.group(2).strip()
            clean_name = re.sub(r"\(.*?\)", "", raw_title).strip()
            results.append((clean_name, explanation))

    return results


def _find_matching_bullet(name: str, bullets: list[tuple[str, str]]) -> str:
    """Finds matching timeline explanation for a region by name."""
    name_lower = name.lower()
    for b_name, b_exp in bullets:
        b_lower = b_name.lower()
        if b_lower == name_lower or b_lower in name_lower or name_lower in b_lower:
            return b_exp
    return ""


def _compute_associated_features(
    region_id: str,
    features: dict[str, Any],
    region_grid: list[str],
) -> list[str]:
    """Finds landmarks (cities, outposts, dungeons) anchored within a specific region."""
    associated: list[str] = []
    reg_char = str(region_id).strip()[:1]

    for f_key, feat in features.items():
        if not isinstance(feat, dict):
            continue
        ftype = feat.get("type", "")
        fchar = feat.get("char", "")
        if ftype in ("road", "bridge", "highway") or fchar in ("+", "="):
            continue

        tiles = feat.get("tiles", [])
        if not tiles and "pos" in feat:
            tiles = [feat["pos"]]
        elif tiles and isinstance(tiles[0], int):
            tiles = [tiles]

        for pt in tiles:
            x, y = pt[0], pt[1]
            if 0 <= y < len(region_grid) and 0 <= x < len(region_grid[y]):
                if region_grid[y][x] == reg_char:
                    fname = feat.get("name", f_key)
                    if fname not in associated:
                        associated.append(fname)
                    break

    return sorted(associated)


def compile_regions_history(
    artifacts_dir: Path = Path("artifacts"),
    base_name: str = "worldmap",
) -> dict[str, Any]:
    """Compiles complete region history across all existing epoch files into a single ledger."""
    artifacts_path = Path(artifacts_dir)
    base_map_path = artifacts_path / f"{base_name}.json"

    base_map: dict[str, Any] = {}
    if base_map_path.exists():
        with open(base_map_path, "r", encoding="utf-8") as f:
            base_map = json.load(f)

    epoch_files: list[tuple[int, Path]] = []
    for fpath in artifacts_path.glob(f"{base_name}_epoch_*.json"):
        m = re.search(rf"{re.escape(base_name)}_epoch_(\d+)\.json$", fpath.name)
        if m:
            epoch_files.append((int(m.group(1)), fpath))
    epoch_files.sort(key=lambda x: x[0])

    regions_history: dict[str, Any] = {
        "realm_name": base_map.get("name", "Unknown Realm"),
        "latest_epoch": epoch_files[-1][0] if epoch_files else 0,
        "regions": {},
    }

    # 1. Initialize Epoch 0 baseline regions
    for r_id, r_info in sorted(base_map.get("regions", {}).items()):
        if not isinstance(r_info, dict):
            continue
        r_name = r_info.get("name", f"Region {r_id}")
        r_type = r_info.get("type", "wilderness")
        r_lore = str(r_info.get("lore", "") or r_info.get("description", "")).strip()

        regions_history["regions"][r_id] = {
            "id": r_id,
            "current_name": r_name,
            "current_type": r_type,
            "origin_epoch": 0,
            "current_lore": r_lore,
            "associated_features": [],
            "chronological_log": [
                {
                    "epoch": 0,
                    "name": r_name,
                    "type": r_type,
                    "lore": r_lore,
                    "event_summary": "Primordial realm baseline geography at the dawn of creation.",
                }
            ],
        }

    # 2. Replay history across epochs
    latest_world_data: dict[str, Any] = deepcopy(base_map)

    for ep_num, ep_path in epoch_files:
        with open(ep_path, "r", encoding="utf-8") as f:
            ep_data = json.load(f)
        latest_world_data = ep_data

        epoch_bullets: list[tuple[str, str]] = []
        for entry in ep_data.get("timeline", []):
            if isinstance(entry, str):
                m = re.match(r"^##\s+Epoch\s+(\d+)", entry.strip())
                if m and int(m.group(1)) == ep_num:
                    epoch_bullets.extend(_extract_epoch_region_bullets(entry))
            elif isinstance(entry, dict) and entry.get("epoch") == ep_num:
                epoch_bullets.extend(_extract_epoch_region_bullets(entry.get("content", "")))

        cur_regions = ep_data.get("regions", {})
        for r_id, r_info in sorted(cur_regions.items()):
            if not isinstance(r_info, dict):
                continue

            r_name = r_info.get("name", f"Region {r_id}")
            r_type = r_info.get("type", "wilderness")
            r_lore = str(r_info.get("lore", "") or r_info.get("description", "")).strip()
            bullet_expl = _find_matching_bullet(r_name, epoch_bullets)

            if r_id not in regions_history["regions"]:
                regions_history["regions"][r_id] = {
                    "id": r_id,
                    "current_name": r_name,
                    "current_type": r_type,
                    "origin_epoch": ep_num,
                    "current_lore": r_lore,
                    "associated_features": [],
                    "chronological_log": [
                        {
                            "epoch": ep_num,
                            "name": r_name,
                            "type": r_type,
                            "lore": r_lore,
                            "event_summary": bullet_expl or f"Region registered in Epoch {ep_num}.",
                        }
                    ],
                }
            else:
                entry = regions_history["regions"][r_id]
                prev_log = entry["chronological_log"][-1]

                has_mutation = (
                    prev_log["name"] != r_name
                    or prev_log["type"] != r_type
                    or prev_log["lore"] != r_lore
                    or bool(bullet_expl)
                )

                if has_mutation:
                    entry["current_name"] = r_name
                    entry["current_type"] = r_type
                    entry["current_lore"] = r_lore
                    summary = bullet_expl or f"Region mutated in Epoch {ep_num}."
                    entry["chronological_log"].append(
                        {
                            "epoch": ep_num,
                            "name": r_name,
                            "type": r_type,
                            "lore": r_lore,
                            "event_summary": summary,
                        }
                    )

    features = latest_world_data.get("features", {})
    region_grid = latest_world_data.get("region_grid", [])
    for r_id, reg_data in regions_history["regions"].items():
        reg_data["associated_features"] = _compute_associated_features(r_id, features, region_grid)

    json_path = artifacts_path / "regions_history.json"
    md_path = artifacts_path / "regions_history.md"

    artifacts_path.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(regions_history, f, indent=2)

    md_content = render_regions_history_md(regions_history)
    md_path.write_text(md_content, encoding="utf-8")

    return regions_history


def update_regions_history(
    epoch_num: int,
    world_data: dict[str, Any],
    timeline_entry: str = "",
    artifacts_dir: Path = Path("artifacts"),
) -> Path:
    """Updates regions_history.json and regions_history.md incrementally for a completed epoch."""
    artifacts_path = Path(artifacts_dir)
    json_path = artifacts_path / "regions_history.json"

    if not json_path.exists():
        compile_regions_history(artifacts_dir=artifacts_path)

    with open(json_path, "r", encoding="utf-8") as f:
        history_data = json.load(f)

    history_data["realm_name"] = world_data.get("name", history_data.get("realm_name", "Unknown Realm"))
    history_data["latest_epoch"] = max(epoch_num, history_data.get("latest_epoch", 0))

    epoch_bullets = _extract_epoch_region_bullets(timeline_entry)
    cur_regions = world_data.get("regions", {})
    region_records = history_data.setdefault("regions", {})

    for r_id, r_info in sorted(cur_regions.items()):
        if not isinstance(r_info, dict):
            continue

        r_name = r_info.get("name", f"Region {r_id}")
        r_type = r_info.get("type", "wilderness")
        r_lore = str(r_info.get("lore", "") or r_info.get("description", "")).strip()
        bullet_expl = _find_matching_bullet(r_name, epoch_bullets)

        if r_id not in region_records:
            region_records[r_id] = {
                "id": r_id,
                "current_name": r_name,
                "current_type": r_type,
                "origin_epoch": epoch_num,
                "current_lore": r_lore,
                "associated_features": [],
                "chronological_log": [
                    {
                        "epoch": epoch_num,
                        "name": r_name,
                        "type": r_type,
                        "lore": r_lore,
                        "event_summary": bullet_expl or f"Region registered in Epoch {epoch_num}.",
                    }
                ],
            }
        else:
            entry = region_records[r_id]
            prev_log = entry["chronological_log"][-1]
            has_mutation = (
                prev_log["name"] != r_name
                or prev_log["type"] != r_type
                or prev_log["lore"] != r_lore
                or bool(bullet_expl)
            )

            if prev_log.get("epoch") == epoch_num:
                prev_log["name"] = r_name
                prev_log["type"] = r_type
                prev_log["lore"] = r_lore
                if bullet_expl:
                    prev_log["event_summary"] = bullet_expl
                entry["current_name"] = r_name
                entry["current_type"] = r_type
                entry["current_lore"] = r_lore
            elif has_mutation:
                entry["current_name"] = r_name
                entry["current_type"] = r_type
                entry["current_lore"] = r_lore
                summary = bullet_expl or f"Region updated in Epoch {epoch_num}."
                entry["chronological_log"].append(
                    {
                        "epoch": epoch_num,
                        "name": r_name,
                        "type": r_type,
                        "lore": r_lore,
                        "event_summary": summary,
                    }
                )

    features = world_data.get("features", {})
    region_grid = world_data.get("region_grid", [])
    for r_id, reg_data in region_records.items():
        reg_data["associated_features"] = _compute_associated_features(r_id, features, region_grid)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2)

    md_path = artifacts_path / "regions_history.md"
    md_content = render_regions_history_md(history_data)
    md_path.write_text(md_content, encoding="utf-8")

    return json_path


def render_regions_history_md(history_data: dict[str, Any]) -> str:
    """Renders the regions history dictionary to clean, LLM-readable Markdown."""
    realm = history_data.get("realm_name", "Unknown Realm")
    latest_epoch = history_data.get("latest_epoch", 0)
    regions = history_data.get("regions", {})

    lines: list[str] = [
        f"# Regional Biome History: {realm}",
        f"- **Current Realm Epoch:** Epoch {latest_epoch}",
        f"- **Total Registered Regions & Domains:** {len(regions)}",
        "",
        "---",
        "",
    ]

    for r_id, reg in sorted(regions.items()):
        name = reg.get("current_name", f"Region {r_id}")
        rtype = reg.get("current_type", "wilderness")
        origin = reg.get("origin_epoch", 0)
        curr_lore = reg.get("current_lore", "")
        features = reg.get("associated_features", [])
        features_str = ", ".join(features) if features else "*(None)*"

        lines.append(f"## Region '{r_id}': {name} (`{rtype}`)")
        lines.append(f"- **Origin Epoch:** Epoch {origin}")
        lines.append(f"- **Associated Landmarks:** {features_str}")
        lines.append(f"- **Active Epoch {latest_epoch} Lore:** {curr_lore}")
        lines.append("")
        lines.append("### Chronological Lore & Evolution Log:")

        for log in reg.get("chronological_log", []):
            ep = log.get("epoch", 0)
            l_name = log.get("name", name)
            l_type = log.get("type", rtype)
            l_summary = log.get("event_summary", "")
            l_lore = log.get("lore", "")

            lines.append(f"- **Epoch {ep} — {l_name} (`{l_type}`):**")
            if l_summary:
                lines.append(f"  - *Historical Event:* {l_summary}")
            if l_lore:
                lines.append(f"  - *Canonical Lore at Epoch {ep}:* {l_lore}")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def get_regional_context_for_location(
    x: int,
    y: int,
    world_data: dict[str, Any],
    regions_history: Optional[dict[str, Any]] = None,
    radius: int = 2,
) -> dict[str, Any]:
    """Extracts regional context and historical transformations for a location coordinate."""
    region_grid = world_data.get("region_grid", [])
    height = len(region_grid)
    width = len(region_grid[0]) if height > 0 else 32

    if not (0 <= y < height and 0 <= x < width):
        return {"error": "Coordinate out of bounds"}

    home_id = region_grid[y][x]

    neighbor_ids: set[str] = set()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx, ny = x + dx, y + dy
            if 0 <= ny < height and 0 <= nx < width:
                nid = region_grid[ny][nx]
                if nid != home_id:
                    neighbor_ids.add(nid)

    if regions_history is None:
        json_path = Path("artifacts") / "regions_history.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                regions_history = json.load(f)
        else:
            regions_history = compile_regions_history()

    reg_dict = regions_history.get("regions", {})
    home_data = reg_dict.get(home_id, {})

    neighbors_summary: list[dict[str, Any]] = []
    for nid in sorted(neighbor_ids):
        ndata = reg_dict.get(nid, {})
        neighbors_summary.append({
            "region_id": nid,
            "name": ndata.get("current_name", f"Region {nid}"),
            "type": ndata.get("current_type", "wilderness"),
            "current_lore": ndata.get("current_lore", ""),
            "past_lore": [
                {
                    "epoch": l.get("epoch", 0),
                    "lore": l.get("lore", ""),
                    "event": l.get("event_summary", ""),
                }
                for l in ndata.get("chronological_log", [])
            ],
        })

    return {
        "coordinates": [x, y],
        "home_region_id": home_id,
        "home_region_name": home_data.get("current_name", f"Region {home_id}"),
        "home_region_type": home_data.get("current_type", "wilderness"),
        "home_region_lore": home_data.get("current_lore", ""),
        "home_region_current_lore": home_data.get("current_lore", ""),
        "home_region_chronology": home_data.get("chronological_log", []),
        "home_region_past_lore": [
            {
                "epoch": l.get("epoch", 0),
                "name": l.get("name", ""),
                "type": l.get("type", ""),
                "lore": l.get("lore", ""),
                "event": l.get("event_summary", ""),
            }
            for l in home_data.get("chronological_log", [])
        ],
        "neighboring_regions": neighbors_summary,
    }
