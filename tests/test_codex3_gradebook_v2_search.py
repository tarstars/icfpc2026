from __future__ import annotations

import importlib.util
import pathlib

from littleman import server_compat

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEARCH_PATH = (
    ROOT
    / "experiments"
    / "codex_3-gradebook-v2"
    / "search_extra_folds.py"
)
BASELINE_PATH = (
    ROOT / "submissions" / "gradebook" / "codex3_gradebook_06.man"
)


def _load_search():
    spec = importlib.util.spec_from_file_location("codex3_gradebook_v2_search", SEARCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_baseline_structure_is_frozen() -> None:
    search = _load_search()
    text = BASELINE_PATH.read_text()
    structure = search._structure(text)

    assert structure.dimensions == (379, 315)
    assert structure.footprint == 379**2
    assert len(structure.rooms) == 16
    assert len(structure.pipe_lengths) == 31
    assert structure.men == 14
    assert min(structure.pipe_lengths) >= 2
    server_compat.validate_layout(text)


def test_every_one_fold_successor_preserves_walls_and_pipe_capacity() -> None:
    search = _load_search()
    baseline = BASELINE_PATH.read_text()
    signature = search._structure(baseline)

    for room_index in search.SEARCH_ROOMS:
        successor = search._fold_once(baseline, room_index)
        if successor is None:
            continue
        assert search._structure(successor) == signature
        server_compat.validate_layout(successor)


def test_dimensions_ignore_unoccupied_padding() -> None:
    search = _load_search()
    assert search._dimensions("   +-+   \n   |I|   \n   +-+   \n") == (3, 3)
    assert search._dimensions("\n   \n") == (0, 0)
