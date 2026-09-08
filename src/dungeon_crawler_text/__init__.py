"""dungeon_crawler_text package."""

from typing import TYPE_CHECKING, Any

from dungeon_crawler_text.loremaster import (
    DEFAULT_PRIMORDIAL_QUERY,
    Loremaster,
)

if TYPE_CHECKING:
    from dungeon_crawler_text.architect import (
        DEFAULT_INPUT_PROSE_PATH,
        DEFAULT_OUTPUT_MAP_PATH,
        Architect,
    )


def __getattr__(name: str) -> Any:
    if name in ("Architect", "DEFAULT_INPUT_PROSE_PATH", "DEFAULT_OUTPUT_MAP_PATH"):
        from dungeon_crawler_text import architect

        return getattr(architect, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Architect",
    "DEFAULT_INPUT_PROSE_PATH",
    "DEFAULT_OUTPUT_MAP_PATH",
    "Loremaster",
    "DEFAULT_PRIMORDIAL_QUERY",
]
