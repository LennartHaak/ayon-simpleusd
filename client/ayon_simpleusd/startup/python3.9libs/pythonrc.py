# -*- coding: utf-8 -*-
"""Register SimpleUSD context callbacks ($ASSET/$SQ update on task change)
and hide ayon-houdini's own shipped creators/loaders."""
import hou

from ayon_simpleusd.houdini_vars import register_callbacks
from ayon_simpleusd.hide_official_houdini_plugins import (
    hide_official_houdini_plugins,
)

register_callbacks()

if hasattr(hou, "ui"):
    import hdefereval
    hdefereval.executeDeferred(hide_official_houdini_plugins)
