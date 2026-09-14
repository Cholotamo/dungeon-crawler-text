"""dungeon_crawler_text package."""

from typing import TYPE_CHECKING, Any

from dungeon_crawler_text.historian import (
    DEFAULT_EPOCH_1_QUERY,
    DEFAULT_SUBSEQUENT_EPOCH_QUERY,
    Historian,
    HistorianEpochResult,
    ToolRejectionError,
    WorldStateSnapshot,
    calculate_cost,
    resolve_epoch_paths,
)
from dungeon_crawler_text.loremaster import (
    DEFAULT_PRIMORDIAL_QUERY,
    Loremaster,
)
from dungeon_crawler_text.world_state import format_world_for_llm

if TYPE_CHECKING:
    from dungeon_crawler_text.architect import (
        DEFAULT_INPUT_PROSE_PATH,
        DEFAULT_OUTPUT_MAP_PATH,
        Architect,
    )
    from dungeon_crawler_text.dossier import (
        harvest_all_dossiers,
        harvest_landmark_keyframes,
    )
    from dungeon_crawler_text.viewer import (
        build_viewer_html,
        generate_html_viewer,
        open_viewer,
        serve_viewer,
    )
    from dungeon_crawler_text.subarchitect import (
        Subarchitect,
        format_localemap_for_llm,
        validate_localemap,
    )
    from dungeon_crawler_text.subhistorian import (
        Subhistorian,
        load_keyframe,
        load_vector,
        validate_evolved_localemap,
    )


def __getattr__(name: str) -> Any:
    if name in ("Architect", "DEFAULT_INPUT_PROSE_PATH", "DEFAULT_OUTPUT_MAP_PATH"):
        from dungeon_crawler_text import architect

        return getattr(architect, name)
    if name in ("harvest_all_dossiers", "harvest_landmark_keyframes"):
        from dungeon_crawler_text import dossier

        return getattr(dossier, name)
    if name in (
        "generate_locale_seed",
        "generate_all_locale_seeds",
        "clean_global_updates",
        "clean_world_updates",
        "build_locale_vector_packet",
        "format_locale_vector_markdown",
        "generate_locale_vector",
        "save_locale_vector",
        "generate_all_locale_vectors",
    ):
        from dungeon_crawler_text import seed

        return getattr(seed, name)
    if name in ("build_viewer_html", "generate_html_viewer", "open_viewer", "serve_viewer"):
        from dungeon_crawler_text import viewer

        return getattr(viewer, name)
    if name in ("print_composite_map",):
        from dungeon_crawler_text import map_printer

        return getattr(map_printer, name)
    if name in (
        "Subarchitect",
        "SubArchitect",
        "validate_localemap",
        "format_localemap_for_llm",
        "generate_locale_localemap",
        "generate_all_localemaps_concurrently",
    ):
        from dungeon_crawler_text import subarchitect

        return getattr(subarchitect, name)
    if name in (
        "Subhistorian",
        "SubHistorian",
        "load_keyframe",
        "load_vector",
        "validate_evolved_localemap",
        "evolve_stagnant_keyframe",
        "evolve_locale_series",
        "evolve_all_locales_concurrently",
    ):
        from dungeon_crawler_text import subhistorian

        return getattr(subhistorian, name)
    if name in ("run_full_pipeline", "PipelineMetrics"):
        from dungeon_crawler_text import pipeline

        return getattr(pipeline, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Architect",
    "DEFAULT_INPUT_PROSE_PATH",
    "DEFAULT_OUTPUT_MAP_PATH",
    "DEFAULT_PRIMORDIAL_QUERY",
    "DEFAULT_EPOCH_1_QUERY",
    "DEFAULT_SUBSEQUENT_EPOCH_QUERY",
    "Historian",
    "HistorianEpochResult",
    "Loremaster",
    "PipelineMetrics",
    "SubArchitect",
    "Subarchitect",
    "SubHistorian",
    "Subhistorian",
    "ToolRejectionError",
    "WorldStateSnapshot",
    "build_locale_vector_packet",
    "build_viewer_html",
    "calculate_cost",
    "clean_global_updates",
    "clean_world_updates",
    "evolve_all_locales_concurrently",
    "evolve_locale_series",
    "evolve_stagnant_keyframe",
    "format_locale_vector_markdown",
    "format_localemap_for_llm",
    "format_world_for_llm",
    "generate_all_locale_seeds",
    "generate_all_locale_vectors",
    "generate_all_localemaps_concurrently",
    "generate_html_viewer",
    "generate_locale_localemap",
    "generate_locale_seed",
    "generate_locale_vector",
    "harvest_all_dossiers",
    "harvest_landmark_keyframes",
    "load_keyframe",
    "load_vector",
    "open_viewer",
    "print_composite_map",
    "resolve_epoch_paths",
    "run_full_pipeline",
    "save_locale_vector",
    "serve_viewer",
    "validate_evolved_localemap",
    "validate_localemap",
]
