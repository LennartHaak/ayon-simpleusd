# -*- coding: utf-8 -*-
"""Register SimpleUSD context callbacks ($ASSET/$SQ update on task change),
build SimpleUSD workfile templates into new scenes and hide ayon-houdini's
own shipped creators/loaders."""
import hou

from ayon_simpleusd.houdini_vars import register_callbacks
from ayon_simpleusd.hide_official_houdini_plugins import (
    hide_official_houdini_plugins,
)

register_callbacks()

if hasattr(hou, "ui"):
    import hdefereval
    from ayon_simpleusd.workfile_templates import (
        register_callbacks as register_template_callbacks,
    )
    register_template_callbacks()
    hdefereval.executeDeferred(hide_official_houdini_plugins)
