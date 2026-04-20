"""Production settings aliasing `prod.py` for consistency.

This file intentionally imports everything from `prod.py` so that
deploy pipelines or configs that reference `climweb.config.settings.production`
use the same robust production settings implemented in `prod.py`.
"""

from .prod import *  # noqa: F401,F403