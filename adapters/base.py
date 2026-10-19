"""The Adapter interface every engine or game adapter implements.

An adapter is the only code that understands a game's text format. Everything
else in the template works on translation units (see
references/translation-units.md). An adapter:

- never writes inside ``game_root``;
- returns the same units, in the same order, every time it extracts the same
  files;
- writes localized files only into the ``out_dir`` given to ``rebuild``;
- passes ``python scripts/adapter_contract.py`` before any bulk translation.

Load adapters with ``load_adapter``. An adapter module imports this file as
``from loc_adapter_base import Adapter`` and sets ``ADAPTER = <its class>``.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_units():
    if "loc_units" not in sys.modules:
        spec = importlib.util.spec_from_file_location("loc_units", ROOT / "scripts" / "loc_units.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["loc_units"] = module
        spec.loader.exec_module(module)
    return sys.modules["loc_units"]


loc_units = _load_units()


class Adapter:
    """Base class. Subclasses set ``engine`` and implement the four methods."""

    engine = "generic"
    # Token profile passed to loc_qa.tokens (generic, renpy, rpgmaker, paradox).
    token_profile = "generic"

    def __init__(self, game_root: Path, options: dict | None = None):
        self.game_root = Path(game_root)
        self.options = dict(options or {})

    def inventory(self) -> list[str]:
        """Text-bearing files this adapter reads, relative to game_root, sorted."""
        raise NotImplementedError

    def extract(self) -> list[dict]:
        """Units for every player-visible string, built with ``loc_units.new_unit``."""
        raise NotImplementedError

    def rebuild(self, units: list[dict], out_dir: Path) -> list[str]:
        """Write localized files for units with a non-empty target into out_dir.

        Mirror paths relative to game_root, write only files that change, leave
        everything else in each written file byte-identical, and return the
        written relative paths. Status filtering is the caller's job.
        """
        raise NotImplementedError

    def read_back(self, root: Path) -> dict[str, str]:
        """The text the game would show for each unit id in the tree at ``root``."""
        raise NotImplementedError


def load_adapter(path: Path, game_root: Path, options: dict | None = None) -> Adapter:
    """Import an adapter module by path and instantiate its ``ADAPTER`` class."""
    sys.modules.setdefault("loc_adapter_base", sys.modules[__name__])
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(f"loc_adapter_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, "ADAPTER", None)
    if not (isinstance(cls, type) and issubclass(cls, Adapter)):
        raise TypeError(f"{path.name} must set ADAPTER to an Adapter subclass")
    return cls(game_root, options)
