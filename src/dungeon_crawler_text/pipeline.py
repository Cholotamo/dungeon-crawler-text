"""End-to-end Master Pipeline Orchestrator.

Orchestrates the entire world generation lifecycle in a single command:
1. Loremaster: Primordial World Narrative Prose (artifacts/worldprose.md)
2. Architect: 32x32 Primordial World Map Geography (artifacts/worldmap.json & .md)
3. Historian: Historical Epoch Simulation (artifacts/worldmap_epoch_{1..N}.json & .md)
4. Dossier Harvester: Extracts deterministic landmark dossiers (artifacts/locales/{fid}/dossier.json)
5. Seed & Vector Synthesizer: Generates initial seed.md and vector_{i}.json delta packets
6. Subarchitect: Concurrently generates 16x16 Keyframe 0 localemaps across locales
7. Subhistorian: Concurrently evolves Keyframes 1..N localemaps across locales (preserving serial continuity per locale)
8. Viewer: Compiles the interactive HTML Map Viewer (artifacts/viewer.html & viewer.html)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Optional, Union

from dotenv import load_dotenv

from dungeon_crawler_text.architect import Architect
from dungeon_crawler_text.dossier import harvest_all_dossiers
from dungeon_crawler_text.historian import (
    DEFAULT_EPOCH_1_QUERY,
    DEFAULT_SUBSEQUENT_EPOCH_QUERY,
    Historian,
)
from dungeon_crawler_text.loremaster import DEFAULT_PRIMORDIAL_QUERY, Loremaster
from dungeon_crawler_text.seed import generate_all_locale_seeds, generate_all_locale_vectors
from dungeon_crawler_text.subarchitect import Subarchitect, generate_all_localemaps_concurrently
from dungeon_crawler_text.subhistorian import Subhistorian, evolve_all_locales_concurrently
from dungeon_crawler_text.viewer import generate_html_viewer, open_viewer

logger = logging.getLogger(__name__)

DEFAULT_ARTIFACTS_DIR = Path("artifacts")
DEFAULT_LOCALES_DIR = Path("artifacts/locales")


@dataclass
class PipelineMetrics:
    """Tracks token consumption and timing across all pipeline stages."""

    elapsed_seconds: float = 0.0
    prompt_tokens: int = 0
    candidates_tokens: int = 0
    thoughts_tokens: int = 0
    total_tokens: int = 0
    stage_durations: dict[str, float] = field(default_factory=dict)
    locales_generated: list[str] = field(default_factory=list)
    keyframes_generated: int = 0

    def add_usage(self, usage: dict[str, int]) -> None:
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.candidates_tokens += usage.get("candidates_tokens", 0)
        self.thoughts_tokens += usage.get("thoughts_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)


def run_full_pipeline(
    query: str = DEFAULT_PRIMORDIAL_QUERY,
    epochs: int = 3,
    loremaster_model: str = "gemini-3.8-flash",
    architect_model: str = "gemini-3.6-flash",
    historian_model: str = "gemini-3.8-flash",
    subarchitect_model: str = "gemini-3.6-flash",
    subhistorian_model: str = "gemini-3.6-flash",
    thinking_level: str = "MEDIUM",
    concurrency: int = 4,
    skip_existing: bool = True,
    overwrite: bool = False,
    open_browser: bool = False,
    artifacts_dir: Union[Path, str] = DEFAULT_ARTIFACTS_DIR,
    locales_dir: Union[Path, str] = DEFAULT_LOCALES_DIR,
) -> PipelineMetrics:
    """Runs the complete fantasy world and localemap pipeline end-to-end."""
    load_dotenv()
    start_total_time = time.time()
    art_dir = Path(artifacts_dir)
    loc_dir = Path(locales_dir)
    art_dir.mkdir(parents=True, exist_ok=True)
    loc_dir.mkdir(parents=True, exist_ok=True)

    metrics = PipelineMetrics()

    print("=" * 80, flush=True)
    print(" DUNGEON CRAWLER TEXT: FULL GENERATION PIPELINE", flush=True)
    print("=" * 80, flush=True)
    print(f"Target Epochs: {epochs} | Locale Concurrency: {concurrency} workers", flush=True)
    print(f"Skip Existing: {skip_existing} | Overwrite: {overwrite}\n", flush=True)

    # -------------------------------------------------------------------------
    # STAGE 1: LOREMASTER (Primordial World Narrative Prose)
    # -------------------------------------------------------------------------
    t0 = time.time()
    worldprose_path = art_dir / "worldprose.md"
    print("\n" + "-" * 80, flush=True)
    print("[1/8] STAGE 1: LOREMASTER (Primordial Narrative)", flush=True)
    print("-" * 80, flush=True)

    if worldprose_path.exists() and skip_existing and not overwrite:
        print(f"--> Reusing existing primordial prose: {worldprose_path}", flush=True)
        worldprose = worldprose_path.read_text(encoding="utf-8")
    else:
        print(f"--> Invoking Loremaster ({loremaster_model})...", flush=True)
        loremaster = Loremaster(model_name=loremaster_model, thinking_level="HIGH")
        worldprose = loremaster.generate_primordial_world(query=query)
        worldprose_path.write_text(worldprose, encoding="utf-8")
        metrics.add_usage(loremaster.token_usage)
        print(f"Saved primordial prose to: {worldprose_path}", flush=True)

    metrics.stage_durations["1_loremaster"] = time.time() - t0

    # -------------------------------------------------------------------------
    # STAGE 2: ARCHITECT (32x32 Primordial World Map Geography)
    # -------------------------------------------------------------------------
    t0 = time.time()
    worldmap_json = art_dir / "worldmap.json"
    worldmap_md = art_dir / "worldmap.md"
    print("\n" + "-" * 80, flush=True)
    print("[2/8] STAGE 2: ARCHITECT (32x32 Primordial World Map)", flush=True)
    print("-" * 80, flush=True)

    if worldmap_json.exists() and worldmap_md.exists() and skip_existing and not overwrite:
        print(f"--> Reusing existing world map: {worldmap_json}", flush=True)
    else:
        print(f"--> Invoking Architect ({architect_model})...", flush=True)
        architect = Architect(model_name=architect_model, thinking_level=thinking_level)
        map_data = architect.generate_world_map(worldprose)
        architect.save_world_map(map_data, output_path=worldmap_json)
        metrics.add_usage(architect.token_usage)
        print(f"Saved primordial world map to: {worldmap_json} & {worldmap_md}", flush=True)

    metrics.stage_durations["2_architect"] = time.time() - t0

    # -------------------------------------------------------------------------
    # STAGE 3: HISTORIAN (Chronicle & World Evolution Epochs 1..N)
    # -------------------------------------------------------------------------
    t0 = time.time()
    print("\n" + "-" * 80, flush=True)
    print(f"[3/8] STAGE 3: HISTORIAN (Chronicle Epochs 1..{epochs})", flush=True)
    print("-" * 80, flush=True)

    historian = Historian(model_name=historian_model, thinking_level=thinking_level)
    for ep in range(1, epochs + 1):
        ep_json = art_dir / f"worldmap_epoch_{ep}.json"
        ep_md = art_dir / f"worldmap_epoch_{ep}.md"

        if ep_json.exists() and ep_md.exists() and skip_existing and not overwrite:
            print(f"--> Reusing existing Epoch {ep} state: {ep_json.name}", flush=True)
            historian.last_md_path = ep_md
            continue

        print(f"--> Simulating Epoch {ep} with Historian...", flush=True)
        prev_md = art_dir / ("worldmap.md" if ep == 1 else f"worldmap_epoch_{ep - 1}.md")
        ep_query = DEFAULT_EPOCH_1_QUERY if ep == 1 else DEFAULT_SUBSEQUENT_EPOCH_QUERY
        historian.run_epoch(input_md_path=prev_md, query=ep_query)
        print(f"Completed Epoch {ep} snapshot -> {ep_json.name}", flush=True)

    metrics.add_usage(historian.token_usage)
    metrics.stage_durations["3_historian"] = time.time() - t0

    # -------------------------------------------------------------------------
    # STAGE 4: DOSSIER HARVESTER
    # -------------------------------------------------------------------------
    t0 = time.time()
    print("\n" + "-" * 80, flush=True)
    print("[4/8] STAGE 4: DOSSIER HARVESTER (Landmark Vector Extraction)", flush=True)
    print("-" * 80, flush=True)

    dossiers = harvest_all_dossiers(
        artifacts_dir=art_dir,
        output_dir=loc_dir,
    )
    print(f"Harvested {len(dossiers)} landmark dossier(s) into {loc_dir}:", flush=True)
    for fid, d_info in sorted(dossiers.items()):
        k_count = len(d_info.get("keyframes", []))
        print(f"  - {fid} ({k_count} historical keyframe(s))", flush=True)
    metrics.locales_generated = sorted(dossiers.keys())
    metrics.stage_durations["4_dossier"] = time.time() - t0

    # -------------------------------------------------------------------------
    # STAGE 5: SEED & VECTOR SYNTHESIZER
    # -------------------------------------------------------------------------
    t0 = time.time()
    print("\n" + "-" * 80, flush=True)
    print("[5/8] STAGE 5: SEED & VECTOR SYNTHESIS (Keyframe 0 Seeds & Evolution Packets)", flush=True)
    print("-" * 80, flush=True)

    # 5a. Initial seeds
    seeds = generate_all_locale_seeds(
        dossiers_dir=loc_dir,
        output_dir=loc_dir,
        keyframe_index=0,
    )
    print(f"Compiled {len(seeds)} locale seed(s) (seed.md)", flush=True)

    # 5b. Evolution vectors
    vectors = generate_all_locale_vectors(
        dossiers_dir=loc_dir,
        artifacts_dir=art_dir,
        output_dir=loc_dir,
    )
    total_vec_count = sum(len(pkts) for pkts in vectors.values())
    print(f"Compiled {total_vec_count} evolution vector delta packet(s) across {len(vectors)} locale(s)", flush=True)
    metrics.stage_durations["5_seed_vector"] = time.time() - t0

    # -------------------------------------------------------------------------
    # STAGE 6: SUBARCHITECT (16x16 Keyframe 0 Concurrent Generation)
    # -------------------------------------------------------------------------
    t0 = time.time()
    print("\n" + "-" * 80, flush=True)
    print(f"[6/8] STAGE 6: SUBARCHITECT (16x16 Keyframe 0 Concurrent Generation, -j {concurrency})", flush=True)
    print("-" * 80, flush=True)

    subarchitect = Subarchitect(model_name=subarchitect_model, thinking_level=thinking_level)
    kf0_results = generate_all_localemaps_concurrently(
        locales_dir=loc_dir,
        max_workers=concurrency,
        subarchitect=subarchitect,
        keyframe_index=0,
        overwrite=overwrite,
    )
    metrics.add_usage(subarchitect.token_usage)
    metrics.keyframes_generated += len(kf0_results)
    print(f"Keyframe 0 localemaps ready for {len(kf0_results)} locale(s)", flush=True)
    metrics.stage_durations["6_subarchitect"] = time.time() - t0

    # -------------------------------------------------------------------------
    # STAGE 7: SUBHISTORIAN (16x16 Keyframe 1..N Concurrent Evolution)
    # -------------------------------------------------------------------------
    t0 = time.time()
    print("\n" + "-" * 80, flush=True)
    print(f"[7/8] STAGE 7: SUBHISTORIAN (16x16 Keyframes 1..N Concurrent Evolution, -j {concurrency})", flush=True)
    print("-" * 80, flush=True)

    subhistorian = Subhistorian(model_name=subhistorian_model, thinking_level=thinking_level)
    subhist_results = evolve_all_locales_concurrently(
        locales_dir=loc_dir,
        max_workers=concurrency,
        subhistorian=subhistorian,
        allow_stagnant_short_circuit=True,
        overwrite=overwrite,
    )
    metrics.add_usage(subhistorian.token_usage)
    total_evolved_kfs = sum(len(kfs) for kfs in subhist_results.values())
    metrics.keyframes_generated += total_evolved_kfs
    print(f"Evolved {total_evolved_kfs} subsequent keyframe(s) across {len(subhist_results)} locale(s)", flush=True)
    metrics.stage_durations["7_subhistorian"] = time.time() - t0

    # -------------------------------------------------------------------------
    # STAGE 8: MAP VIEWER GENERATION
    # -------------------------------------------------------------------------
    t0 = time.time()
    print("\n" + "-" * 80, flush=True)
    print("[8/8] STAGE 8: MAP VIEWER COMPILATION", flush=True)
    print("-" * 80, flush=True)

    viewer_target = generate_html_viewer(output_path=art_dir / "viewer.html")
    print(f"Viewer generated at: {viewer_target}", flush=True)

    if open_browser:
        print("Opening map viewer in default browser...", flush=True)
        open_viewer(viewer_target)

    metrics.stage_durations["8_viewer"] = time.time() - t0
    metrics.elapsed_seconds = time.time() - start_total_time

    # -------------------------------------------------------------------------
    # SUMMARY & METRICS REPORT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80, flush=True)
    print(" PIPELINE EXECUTION COMPLETE", flush=True)
    print("=" * 80, flush=True)
    print(f"Total Elapsed Time:    {metrics.elapsed_seconds:.2f}s", flush=True)
    print(f"Locales Processed:     {len(metrics.locales_generated)} ({', '.join(metrics.locales_generated)})", flush=True)
    print(f"Total Keyframes:       {metrics.keyframes_generated}", flush=True)
    print("\nStage Breakdown:", flush=True)
    for stage, dur in sorted(metrics.stage_durations.items()):
        print(f"  - {stage:<20} {dur:6.2f}s", flush=True)

    print("\nToken Consumption:", flush=True)
    print(f"  - Prompt Tokens:     {metrics.prompt_tokens:,}", flush=True)
    print(f"  - Candidate Tokens:  {metrics.candidates_tokens:,}", flush=True)
    if metrics.thoughts_tokens:
        print(f"  - Thoughts Tokens:   {metrics.thoughts_tokens:,}", flush=True)
    print(f"  - Total Tokens:      {metrics.total_tokens:,}", flush=True)
    print("=" * 80, flush=True)

    return metrics


def main() -> None:
    """CLI entry point for the end-to-end world generator pipeline."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Run the full Dungeon Crawler Text generation pipeline: from narrative prose to full world, epochs, and 16x16 localemaps."
    )
    parser.add_argument(
        "--epochs",
        "-e",
        type=int,
        default=3,
        help="Number of historical epochs to simulate (default: 3)",
    )
    parser.add_argument(
        "--concurrency",
        "-j",
        type=int,
        default=4,
        help="Number of parallel workers for Subarchitect and Subhistorian (default: 4)",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=DEFAULT_PRIMORDIAL_QUERY,
        help="Custom primordial realm prompt for Loremaster",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.8-flash",
        help="Default model for text generation agents (default: gemini-3.8-flash)",
    )
    parser.add_argument(
        "--architect-model",
        type=str,
        default="gemini-3.6-flash",
        help="Model for Architect, Subarchitect, and Subhistorian code execution (default: gemini-3.6-flash)",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        default="MEDIUM",
        help="Thinking level for Gemini models (default: MEDIUM)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Force regeneration and overwrite of all intermediate artifacts.",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Do not skip existing stages even if intermediate files exist.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the interactive HTML map viewer in your default browser upon completion.",
    )
    parser.add_argument(
        "--artifacts",
        "-a",
        type=str,
        default=str(DEFAULT_ARTIFACTS_DIR),
        help="Path to artifacts root directory (default: artifacts)",
    )

    args = parser.parse_args()

    run_full_pipeline(
        query=args.query,
        epochs=args.epochs,
        loremaster_model=args.model,
        architect_model=args.architect_model,
        historian_model=args.model,
        subarchitect_model=args.architect_model,
        subhistorian_model=args.architect_model,
        thinking_level=args.thinking,
        concurrency=args.concurrency,
        skip_existing=not args.no_skip,
        overwrite=args.overwrite,
        open_browser=args.open,
        artifacts_dir=Path(args.artifacts),
        locales_dir=Path(args.artifacts) / "locales",
    )


if __name__ == "__main__":
    main()
