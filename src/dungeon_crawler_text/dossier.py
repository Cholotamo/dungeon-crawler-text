"""Settlement & Landmark Vector Dossier extraction module.

Extracts deterministic spatial, geographic, and infrastructural vectors across epochs
for towns, cities, and dungeons to feed into downstream Subarchitect models.
"""

from copy import deepcopy
import json
import logging
from pathlib import Path
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

TERRAIN_LABELS: dict[str, str] = {
    ".": "plains",
    ",": "hills",
    "#": "forest",
    "&": "dense_forest",
    "%": "swamp_marsh",
    "~": "water",
    ";": "coast_beach",
    "^": "mountain_peak",
    "/": "cliff_chasm",
    "*": "wasteland",
    ":": "farmland",
}

LANDMARK_TYPES: set[str] = {
    "settlement",
    "outpost",
    "village",
    "major_city",
    "city",
    "metropolis",
    "town",
    "hamlet",
    "dungeon",
    "ruin",
    "stronghold",
}


def extract_grid_slice(
    grid: list[str],
    center_x: int,
    center_y: int,
    radius: int = 2,
    default_char: str = "?",
) -> list[str]:
    """Extracts a (2*radius+1) x (2*radius+1) slice from a 2D string grid centered at (center_x, center_y)."""
    if not grid:
        dim = 2 * radius + 1
        return [default_char * dim for _ in range(dim)]

    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    slice_lines: list[str] = []

    for y in range(center_y - radius, center_y + radius + 1):
        row_chars: list[str] = []
        for x in range(center_x - radius, center_x + radius + 1):
            if 0 <= y < height and 0 <= x < width:
                row_chars.append(grid[y][x])
            else:
                row_chars.append(default_char)
        slice_lines.append("".join(row_chars))

    return slice_lines


def compute_cardinal_bias(
    coords: list[tuple[int, int]],
    center: tuple[int, int] = (1, 1),
    slice_size: int = 3,
) -> str:
    """Computes cardinal position bias (e.g. 'NORTH & WEST', 'CENTER', 'EASTERN BORDER') for coordinates in a slice."""
    if not coords:
        return "UNKNOWN"

    if len(coords) >= slice_size * slice_size:
        return "ENTIRE_AREA"

    cx, cy = center
    is_center = center in coords

    # Average offset from center
    avg_dx = sum(x - cx for x, _ in coords) / len(coords)
    avg_dy = sum(y - cy for _, y in coords) / len(coords)

    # Check boundaries
    at_north = any(y == 0 for _, y in coords)
    at_south = any(y == slice_size - 1 for _, y in coords)
    at_west = any(x == 0 for x, _ in coords)
    at_east = any(x == slice_size - 1 for x, _ in coords)

    dirs: list[str] = []
    if avg_dy < -0.3 or (at_north and not at_south):
        dirs.append("NORTH")
    elif avg_dy > 0.3 or (at_south and not at_north):
        dirs.append("SOUTH")

    if avg_dx < -0.3 or (at_west and not at_east):
        dirs.append("WEST")
    elif avg_dx > 0.3 or (at_east and not at_west):
        dirs.append("EAST")

    if not dirs:
        return "CENTER" if is_center else "LOCAL_SURROUNDINGS"

    direction_str = " & ".join(dirs)
    if is_center:
        return f"CENTER & {direction_str}"
    return f"{direction_str} BORDER" if (at_north or at_south or at_west or at_east) else direction_str


def resolve_gate_direction(pos: tuple[int, int], adjacent_step: tuple[int, int]) -> str:
    """Calculates cardinal entry direction for a road entering pos from an adjacent coordinate."""
    px, py = pos
    ax, ay = adjacent_step
    dx = ax - px
    dy = ay - py

    if dx == 0 and dy < 0:
        return "NORTH"
    if dx == 0 and dy > 0:
        return "SOUTH"
    if dx > 0 and dy == 0:
        return "EAST"
    if dx < 0 and dy == 0:
        return "WEST"
    if dx > 0 and dy < 0:
        return "NORTH_EAST"
    if dx < 0 and dy < 0:
        return "NORTH_WEST"
    if dx > 0 and dy > 0:
        return "SOUTH_EAST"
    if dx < 0 and dy > 0:
        return "SOUTH_WEST"
    return "INTERNAL"


def _resolve_destination(
    road_id: str,
    other_end: tuple[int, int],
    features: dict[str, Any],
    origin_pos: Optional[tuple[int, int]] = None,
) -> Optional[dict[str, Any]]:
    """Resolves destination feature for a road/bridge endpoint."""
    ox, oy = other_end

    # 1. Exact match on any other feature
    for other_id, other_feat in features.items():
        if other_id == road_id or not isinstance(other_feat, dict):
            continue
        o_tiles = [(t[0], t[1]) for t in other_feat.get("tiles", []) if isinstance(t, (list, tuple))]
        if (ox, oy) in o_tiles:
            return {
                "feature_id": other_id,
                "name": other_feat.get("name", other_id),
                "type": other_feat.get("type", "feature"),
                "description": other_feat.get("description", ""),
            }

    # 2. Adjacent match (bridges, landmarks, or roads terminating at approach)
    # Exclude origin_pos so we don't loop back to the host landmark
    adjacent_matches: list[tuple[int, dict[str, Any]]] = []
    for other_id, other_feat in features.items():
        if other_id == road_id or not isinstance(other_feat, dict):
            continue
        o_tiles = [(t[0], t[1]) for t in other_feat.get("tiles", []) if isinstance(t, (list, tuple))]
        if origin_pos and origin_pos in o_tiles:
            continue
        if any(max(abs(t[0] - ox), abs(t[1] - oy)) <= 1 for t in o_tiles):
            f_type = str(other_feat.get("type", "")).lower()
            f_char = str(other_feat.get("char", ""))
            # Prioritize landmarks (settlement, dungeon) and bridges over roads
            priority = 0
            if f_char in ("o", "O", "!") or f_type in ("settlement", "outpost", "major_city", "dungeon", "city", "town"):
                priority = 2
            elif f_char == "=" or f_type in ("bridge", "viaduct"):
                priority = 1

            dest_info = {
                "feature_id": other_id,
                "name": other_feat.get("name", other_id),
                "type": other_feat.get("type", "feature"),
                "description": other_feat.get("description", ""),
            }
            adjacent_matches.append((priority, dest_info))

    if adjacent_matches:
        adjacent_matches.sort(key=lambda x: -x[0])
        return adjacent_matches[0][1]

    return None


def find_connected_roads(
    pos: tuple[int, int],
    features: dict[str, Any],
) -> list[dict[str, Any]]:
    """Identifies all road and bridge infrastructure connected to the given coordinates."""
    px, py = pos
    connected: list[dict[str, Any]] = []

    for f_id, feat in features.items():
        if not isinstance(feat, dict):
            continue

        f_type = str(feat.get("type", "")).lower()
        f_char = str(feat.get("char", ""))
        if f_type not in ("road", "highway", "bridge", "viaduct", "path", "trail") and f_char not in ("+", "="):
            continue

        tiles = feat.get("tiles", [])
        if not tiles or not isinstance(tiles[0], (list, tuple)):
            continue

        tile_tuples = [(t[0], t[1]) for t in tiles]

        # Case 1: Direct coordinate overlap (px, py in road tiles)
        if (px, py) in tile_tuples:
            indices = [idx for idx, t in enumerate(tile_tuples) if t == (px, py)]
            for idx in indices:
                adjacent_step = None
                if idx == 0 and len(tile_tuples) > 1:
                    adjacent_step = tile_tuples[1]
                    other_end = tile_tuples[-1]
                elif idx == len(tile_tuples) - 1 and len(tile_tuples) > 1:
                    adjacent_step = tile_tuples[-2]
                    other_end = tile_tuples[0]
                else:
                    adjacent_step = tile_tuples[idx - 1] if idx > 0 else (tile_tuples[idx + 1] if len(tile_tuples) > 1 else None)
                    other_end = tile_tuples[-1] if idx == 0 else tile_tuples[0]

                gate_dir = resolve_gate_direction((px, py), adjacent_step) if adjacent_step else "CENTER"
                destination = _resolve_destination(f_id, other_end, features, origin_pos=pos)

                connected.append({
                    "road_id": f_id,
                    "road_name": feat.get("name", f_id),
                    "road_type": f_type or ("bridge" if f_char == "=" else "road"),
                    "gate_approach": gate_dir,
                    "description": feat.get("description", ""),
                    "destination": destination,
                    "destination_coord": list(other_end) if other_end else None,
                })
        else:
            # Case 2: Endpoint adjacency (bridges spanning river/chasm at gate, or roads terminating at approach)
            start_tile = tile_tuples[0]
            end_tile = tile_tuples[-1]
            connections: list[tuple[tuple[int, int], tuple[int, int]]] = []

            if max(abs(start_tile[0] - px), abs(start_tile[1] - py)) <= 1:
                connections.append((start_tile, end_tile))

            if end_tile != start_tile and max(abs(end_tile[0] - px), abs(end_tile[1] - py)) <= 1:
                connections.append((end_tile, start_tile))

            for near_tile, other_end in connections:
                gate_dir = resolve_gate_direction((px, py), near_tile)
                destination = _resolve_destination(f_id, other_end, features, origin_pos=pos)

                connected.append({
                    "road_id": f_id,
                    "road_name": feat.get("name", f_id),
                    "road_type": f_type or ("bridge" if f_char == "=" else "road"),
                    "gate_approach": gate_dir,
                    "description": feat.get("description", ""),
                    "destination": destination,
                    "destination_coord": list(other_end) if other_end else None,
                })

    return connected


def extract_cardinal_egress_guide(
    x: int,
    y: int,
    terrain_grid: list[str],
    region_grid: list[str],
    regions: dict[str, Any],
    distance: int = 2,
) -> dict[str, str]:
    """Inspects natural geography in cardinal directions away from (x, y)."""
    height = len(terrain_grid)
    width = len(terrain_grid[0]) if height > 0 else 0

    probes = {
        "NORTH": (x, y - distance),
        "SOUTH": (x, y + distance),
        "EAST": (x + distance, y),
        "WEST": (x - distance, y),
    }

    guide: dict[str, str] = {}
    for direction, (px, py) in probes.items():
        if 0 <= py < height and 0 <= px < width:
            t_char = terrain_grid[py][px]
            r_id = region_grid[py][px]
            t_label = TERRAIN_LABELS.get(t_char, "wilderness")
            r_name = regions.get(r_id, {}).get("name", f"Region {r_id}")
            guide[direction] = f"{t_label.title()} ({r_name})"
        else:
            guide[direction] = "Realm Boundary"

    return guide


def extract_neighborhood_regions(
    region_slice: list[str],
    current_regions: dict[str, Any],
    regions_history: Optional[dict[str, Any]] = None,
    epoch: int = 1,
    host_region_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Analyzes unique neighboring regions present in the local slice, excluding the host region."""
    counts: dict[str, int] = {}
    positions: dict[str, list[tuple[int, int]]] = {}

    slice_dim = len(region_slice)
    center = (slice_dim // 2, slice_dim // 2)

    for y, row in enumerate(region_slice):
        for x, r_id in enumerate(row):
            if r_id in ("?", " "):
                continue
            if host_region_id and r_id == host_region_id:
                continue
            counts[r_id] = counts.get(r_id, 0) + 1
            positions.setdefault(r_id, []).append((x, y))

    neighborhood: list[dict[str, Any]] = []
    # Sort by tile count descending
    for r_id, count in sorted(counts.items(), key=lambda x: -x[1]):
        r_info = current_regions.get(r_id, {})
        pos_label = compute_cardinal_bias(positions[r_id], center=center, slice_size=slice_dim)

        # Query regions_history if available
        historical_context = ""
        if regions_history and "regions" in regions_history:
            hist_reg = regions_history["regions"].get(r_id, {})
            log_entries = hist_reg.get("chronological_log", [])
            # Find latest entry up to this epoch
            valid_entries = [e for e in log_entries if e.get("epoch", 0) <= epoch]
            if valid_entries:
                latest = valid_entries[-1]
                historical_context = latest.get("event_summary") or latest.get("lore", "")

        neighborhood.append({
            "id": r_id,
            "name": r_info.get("name", f"Region {r_id}"),
            "type": r_info.get("type", "wilderness"),
            "tile_count": count,
            "relative_position": f"{pos_label} ({count} tiles)",
            "lore": r_info.get("lore", ""),
            "historical_context": historical_context or f"Active region in Epoch {epoch}.",
        })

    return neighborhood


def _extract_epoch_number(filename: str, base_name: str) -> Optional[int]:
    """Extracts integer epoch number from filenames like worldmap_epoch_3.json."""
    m = re.search(rf"{re.escape(base_name)}_epoch_(\d+)\.json$", filename)
    return int(m.group(1)) if m else None


def harvest_landmark_keyframes(
    feature_id: str,
    artifacts_dir: Path = Path("artifacts"),
    base_name: str = "worldmap",
    scan_radius: int = 1,
) -> Optional[dict[str, Any]]:
    """Compiles the full deterministic vector dossier for a specific landmark across all available epochs."""
    artifacts_path = Path(artifacts_dir)
    epoch_files: list[tuple[int, Path]] = []

    for fpath in artifacts_path.glob(f"{base_name}_epoch_*.json"):
        ep_num = _extract_epoch_number(fpath.name, base_name)
        if ep_num is not None:
            epoch_files.append((ep_num, fpath))

    epoch_files.sort(key=lambda x: x[0])
    if not epoch_files:
        logger.warning(f"No epoch files found in {artifacts_path} for base name '{base_name}'")
        return None

    # Load regions history if available
    regions_hist_path = artifacts_path / "regions_history.json"
    regions_history: Optional[dict[str, Any]] = None
    if regions_hist_path.exists():
        try:
            regions_history = json.loads(regions_hist_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to load regions_history.json: {e}")

    keyframes: list[dict[str, Any]] = []
    prev_state: Optional[dict[str, Any]] = None
    first_epoch: Optional[int] = None
    latest_epoch: Optional[int] = None
    world_coords: Optional[list[int]] = None
    elevation_label: str = "unknown"

    for ep_num, file_path in epoch_files:
        try:
            world = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            continue

        features = world.get("features", {})
        feat = features.get(feature_id)
        if not feat:
            continue

        tiles = feat.get("tiles", [])
        if not tiles and "pos" in feat:
            tiles = [feat["pos"]]
        elif tiles and isinstance(tiles[0], int):
            tiles = [tiles]

        if not tiles:
            continue

        px, py = tiles[0][0], tiles[0][1]
        world_coords = [px, py]
        latest_epoch = ep_num
        if first_epoch is None:
            first_epoch = ep_num

        terrain_grid = world.get("terrain_grid", [])
        region_grid = world.get("region_grid", [])
        regions = world.get("regions", {})

        height = len(terrain_grid)
        width = len(terrain_grid[0]) if height > 0 else 0
        t_char = terrain_grid[py][px] if 0 <= py < height and 0 <= px < width else "?"
        r_id = region_grid[py][px] if 0 <= py < len(region_grid) and 0 <= px < len(region_grid[py]) else "?"
        r_info = regions.get(r_id, {})

        f_char = str(feat.get("char", "o"))
        f_name = str(feat.get("name", feature_id))
        f_type = str(feat.get("type", "landmark"))
        elevation_label = TERRAIN_LABELS.get(t_char, "plains")

        # Local slices (default 3x3 for scan_radius=1)
        dim = 2 * scan_radius + 1
        t_slice = extract_grid_slice(terrain_grid, px, py, radius=scan_radius, default_char="?")
        r_slice = extract_grid_slice(region_grid, px, py, radius=scan_radius, default_char="0")
        neighborhood = extract_neighborhood_regions(
            r_slice,
            regions,
            regions_history,
            epoch=ep_num,
            host_region_id=r_id,
        )
        connected_roads = find_connected_roads((px, py), features)

        # Detect mutations & keyframe triggers
        triggers: list[str] = []
        delta_dict: Optional[dict[str, Any]] = None

        if prev_state is None:
            triggers.append("genesis")
        else:
            if f_char != prev_state["char"]:
                triggers.append(f"char_mutation ({prev_state['char']} -> {f_char})")
            if f_name != prev_state["name"]:
                triggers.append(f"name_mutation ('{prev_state['name']}' -> '{f_name}')")
            if r_id != prev_state["region_id"]:
                triggers.append(f"domain_mutation (Region '{prev_state['region_id']}' -> '{r_id}')")
            if t_char != prev_state["terrain_char"]:
                triggers.append(f"terrain_mutation ('{prev_state['terrain_char']}' -> '{t_char}')")

            # Check for newly connected roads
            prev_road_ids = {r["road_id"] for r in prev_state["connected_roads"]}
            curr_road_ids = {r["road_id"] for r in connected_roads}
            new_road_ids = curr_road_ids - prev_road_ids
            if new_road_ids:
                triggers.append(f"new_roads ({', '.join(sorted(new_road_ids))})")

            # Build deterministic delta
            new_roads_info = [r for r in connected_roads if r["road_id"] in new_road_ids]
            delta_dict = {
                "biome_mutation": (
                    f"Region '{prev_state['region_id']}' ({prev_state['region_name']}) -> "
                    f"Region '{r_id}' ({r_info.get('name', f'Region {r_id}')})"
                    if r_id != prev_state["region_id"]
                    else "None"
                ),
                "terrain_transition": (
                    f"'{prev_state['terrain_char']}' ({TERRAIN_LABELS.get(prev_state['terrain_char'], 'terrain')}) -> "
                    f"'{t_char}' ({TERRAIN_LABELS.get(t_char, 'terrain')})"
                    if t_char != prev_state["terrain_char"]
                    else "None"
                ),
                "status_transition": (
                    f"'{prev_state['char']}' ({prev_state['type']}) -> '{f_char}' ({f_type})"
                    if f_char != prev_state["char"]
                    else "None"
                ),
                "new_roads": new_roads_info,
            }

        keyframe_data = {
            "keyframe_index": len(keyframes),
            "epoch": ep_num,
            "char": f_char,
            "name": f_name,
            "type": f_type,
            "is_keyframe": len(triggers) > 0,
            "keyframe_triggers": triggers,
            "environment": {
                "host_region": {
                    "id": r_id,
                    "name": r_info.get("name", f"Region {r_id}"),
                    "type": r_info.get("type", "wilderness"),
                    "lore": r_info.get("lore", ""),
                },
                "terrain_char": t_char,
                "terrain_label": elevation_label,
                "terrain_slice": t_slice,
                "region_slice": r_slice,
                "neighborhood_regions": neighborhood,
            },
            "connected_roads": connected_roads,
            "delta_from_previous": delta_dict,
        }

        keyframes.append(keyframe_data)
        prev_state = {
            "char": f_char,
            "name": f_name,
            "type": f_type,
            "region_id": r_id,
            "region_name": r_info.get("name", f"Region {r_id}"),
            "terrain_char": t_char,
            "connected_roads": connected_roads,
        }

    if not keyframes:
        return None

    return {
        "feature_id": feature_id,
        "world_coords": world_coords,
        "first_seen_epoch": first_epoch,
        "latest_epoch": latest_epoch,
        "total_keyframes": len(keyframes),
        "keyframes": keyframes,
    }


def harvest_all_dossiers(
    artifacts_dir: Path = Path("artifacts"),
    base_name: str = "worldmap",
    output_dir: Optional[Path] = None,
    landmark_chars: set[str] = ("o", "O", "!"),
    scan_radius: int = 1,
) -> dict[str, dict[str, Any]]:
    """Discovers all landmarks in the latest epoch and compiles dossiers for each."""
    artifacts_path = Path(artifacts_dir)
    epoch_files: list[tuple[int, Path]] = []

    for fpath in artifacts_path.glob(f"{base_name}_epoch_*.json"):
        ep_num = _extract_epoch_number(fpath.name, base_name)
        if ep_num is not None:
            epoch_files.append((ep_num, fpath))

    epoch_files.sort(key=lambda x: x[0])
    if not epoch_files:
        return {}

    latest_world = json.loads(epoch_files[-1][1].read_text(encoding="utf-8"))
    features = latest_world.get("features", {})

    all_dossiers: dict[str, dict[str, Any]] = {}
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    for fid, feat in sorted(features.items()):
        f_char = str(feat.get("char", ""))
        f_type = str(feat.get("type", "")).lower()

        # Filter to landmarks (settlements, cities, dungeons)
        is_landmark = f_char in landmark_chars or f_type in LANDMARK_TYPES
        if not is_landmark:
            continue

        dossier = harvest_landmark_keyframes(
            fid,
            artifacts_dir=artifacts_path,
            base_name=base_name,
            scan_radius=scan_radius,
        )
        if dossier:
            all_dossiers[fid] = dossier
            if output_dir:
                file_out = Path(output_dir) / f"{fid}_dossier.json"
                file_out.write_text(json.dumps(dossier, indent=2, ensure_ascii=False), encoding="utf-8")
                logger.info(f"Wrote dossier for '{fid}' to {file_out}")

    return all_dossiers


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Harvest deterministic vector dossiers for settlements and dungeons.")
    parser.add_argument("--feature", "-f", type=str, default="", help="Feature ID to extract (default: all landmarks)")
    parser.add_argument("--artifacts", "-a", type=str, default="artifacts", help="Artifacts directory path")
    parser.add_argument("--output", "-o", type=str, default="artifacts/dossiers", help="Output directory to save JSON dossiers")
    parser.add_argument("--radius", "-r", type=int, default=1, help="Environmental scan radius (default: 1 for 3x3)")
    args = parser.parse_args()

    artifacts_p = Path(args.artifacts)
    out_p = Path(args.output) if args.output else None

    if args.feature:
        res = harvest_landmark_keyframes(args.feature, artifacts_dir=artifacts_p, scan_radius=args.radius)
        if res:
            if out_p:
                out_p.mkdir(parents=True, exist_ok=True)
                target = out_p / f"{args.feature}_dossier.json"
                target.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"Saved dossier for '{args.feature}' to {target}")
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"Feature '{args.feature}' not found or has no keyframes.")
    else:
        all_res = harvest_all_dossiers(artifacts_dir=artifacts_p, output_dir=out_p, scan_radius=args.radius)
        print(f"Compiled {len(all_res)} landmark dossiers in {out_p}")
        for k in all_res:
            print(f"  - {k} ({len(all_res[k]['keyframes'])} keyframes)")
