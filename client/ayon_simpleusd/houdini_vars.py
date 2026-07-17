# -*- coding: utf-8 -*-
"""Keep the $ASSET Houdini variable in sync with the AYON context.

At launch $ASSET is set by the prelaunch hook (hooks/pre_asset_env.py);
this module updates it when the artist switches task context inside a
running Houdini session, mirroring ayon-houdini's "Houdini Vars" feature
but hardcoded instead of settings-driven.
"""
import os


def _compute_asset_var():
    from pxr import Tf
    from ayon_core.pipeline.context_tools import get_current_context

    context = get_current_context()
    folder_name = context["folder_path"].rsplit("/", 1)[-1]
    return Tf.MakeValidIdentifier(folder_name)


def update_asset_var():
    import hou

    value = _compute_asset_var()
    current = hou.hscript("echo -n `$ASSET`")[0]
    if current == value:
        return
    hou.hscript("set ASSET={}".format(value))
    os.environ["ASSET"] = value
    # Recook nodes whose parms reference $ASSET (e.g. locked defaultprim)
    hou.hscript("varchange ASSET")
    print("Updated $ASSET to {}".format(value))


def _on_hip_event(event_type):
    import hou

    if event_type in (
        hou.hipFileEventType.AfterLoad,
        hou.hipFileEventType.AfterClear,
    ):
        update_asset_var()


def register_callbacks():
    import hou
    from ayon_core.lib import register_event_callback

    register_event_callback("taskChanged", update_asset_var)
    # Hip files store the session's global variables and restore them on
    # load, so any scene load can revert $ASSET to a stale saved value
    # (e.g. a startup template, or workfiles - which emits taskChanged
    # BEFORE loading the file). Houdini's own hip events catch every
    # load, including ones AYON emits no event for.
    hou.hipFile.addEventCallback(_on_hip_event)
