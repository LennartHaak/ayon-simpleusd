# -*- coding: utf-8 -*-
"""Keep $ASSET and $SQ Houdini variables in sync with the AYON context.

At launch they're set by the prelaunch hook (hooks/pre_asset_env.py);
this module updates them when the artist switches task context inside a
running Houdini session, mirroring ayon-houdini's "Houdini Vars" feature
but hardcoded instead of settings-driven.
"""
import os


def _compute_context_vars():
    from pxr import Tf
    from ayon_core.pipeline.context_tools import get_current_context

    context = get_current_context()
    parts = context["folder_path"].strip("/").split("/")
    asset_name = Tf.MakeValidIdentifier(parts[-1])
    sequence_name = Tf.MakeValidIdentifier(parts[-2]) if len(parts) >= 2 \
        else ""
    return {"ASSET": asset_name, "SQ": sequence_name}


def update_context_vars():
    import hou

    changed = []
    for var, value in _compute_context_vars().items():
        current = hou.hscript("echo -n `${}`".format(var))[0]
        if current == value:
            continue
        hou.hscript("set {}={}".format(var, value))
        os.environ[var] = value
        changed.append(var)
        print("Updated ${} to {}".format(var, value))

    if changed:
        # Recook nodes whose parms reference these vars (e.g. locked
        # defaultprim).
        hou.hscript("varchange {}".format(" ".join(changed)))


def _on_hip_event(event_type):
    import hou

    if event_type in (
        hou.hipFileEventType.AfterLoad,
        hou.hipFileEventType.AfterClear,
    ):
        update_context_vars()


def register_callbacks():
    import hou
    from ayon_core.lib import register_event_callback

    register_event_callback("taskChanged", update_context_vars)
    # Hip files store the session's global variables and restore them on
    # load, so any scene load can revert these vars to stale saved values
    # (e.g. a startup template, or workfiles - which emits taskChanged
    # BEFORE loading the file). Houdini's own hip events catch every
    # load, including ones AYON emits no event for.
    hou.hipFile.addEventCallback(_on_hip_event)
