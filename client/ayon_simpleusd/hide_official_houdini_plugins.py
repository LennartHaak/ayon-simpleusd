# -*- coding: utf-8 -*-
"""Hide ayon-houdini's own shipped creators/loaders from the AYON UI.

Some of them lack a settings-exposed "enabled" toggle, so this
deregisters ayon-houdini's whole creator/loader plugin paths instead,
using AYON's public plugin-path deregistration API - keeping only
SimpleUSD's own creators/loaders visible in the Publisher and Loader,
without editing ayon-houdini itself.

Per-class deregistration (deregister_creator_plugin/deregister_loader_plugin)
does NOT work here: `discover()` always re-scans the registered plugin
*paths* fresh on every call (e.g. every time the Publisher/Loader is
opened), so a deregistered class simply gets rediscovered again on the
next call. Deregistering the whole path is the only way to actually
stop them from being found.

The workfile auto-creator and the stock Review (OpenGL/Flipbook)
creator are re-enabled afterwards via register_creator_plugin(), which
stores each class separately from the path-based scan - so they keep
showing up even though CREATE_PATH itself stays deregistered.
"""


def hide_official_houdini_plugins():
    import os

    from ayon_core.pipeline import (
        deregister_creator_plugin_path,
        deregister_loader_plugin_path,
        register_creator_plugin,
    )
    from ayon_houdini.api.pipeline import CREATE_PATH, LOAD_PATH
    from ayon_houdini.plugins.create.create_workfile import CreateWorkfile
    from ayon_houdini.plugins.create.create_review import CreateReview

    # register_plugin_path() normalizes the path before storing it, so
    # match that here to guarantee the deregister lookup finds it.
    deregister_creator_plugin_path(os.path.normpath(CREATE_PATH))
    deregister_loader_plugin_path(os.path.normpath(LOAD_PATH))

    register_creator_plugin(CreateWorkfile)
    register_creator_plugin(CreateReview)
