"""Littleman package initialization.

Install the post-release ``Y`` semantics before any executor imports
``littleman.sim.Machine``.  The installer is idempotent and preserves the fast
executor for every program that does not use dynamic splitting.
"""

from . import sim as _sim
from .y_semantics import install as _install_y_semantics

_install_y_semantics(_sim)

del _install_y_semantics, _sim
