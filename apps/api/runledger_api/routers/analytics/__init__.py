"""Analytics routes, split by area (review Wave 0.2).

Modules are imported in the original declaration order, so route registration (and
therefore path matching) is unchanged. Keep this order when adding modules.
"""
# isort: skip_file
# ruff: noqa: E402, F401, I001

from ._shared import router
from . import spend
from . import users
from . import economics
from . import scores
from . import scoped
from . import explorer
from . import optimization
from . import monitoring

__all__ = ["router"]
