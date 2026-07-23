# -*- coding: utf-8 -*-
"""Prelaunch hook setting $ASSET and $SQ environment variables for Houdini."""
import re

from ayon_applications import PreLaunchHook, LaunchTypes


def _sanitize(name):
    # Mirror Tf.MakeValidIdentifier so these match loader prim paths
    # (pxr is not importable in the launcher process)
    name = re.sub(r"\W", "_", name) or "_"
    if name[0].isdigit():
        name = "_" + name[1:]
    return name


class AddAssetEnvVar(PreLaunchHook):
    """Set $ASSET to the shot/asset folder name and $SQ to its parent
    (sequence) folder name before Houdini launches."""

    app_groups = {"houdini"}
    launch_types = {LaunchTypes.local, LaunchTypes.farm_render}
    order = 0  # after GlobalHostDataHook (-100) fills project/folder entities

    def execute(self):
        folder_entity = self.data.get("folder_entity")
        if not folder_entity:
            self.log.warning(
                "Missing context data, $ASSET/$SQ were not set.")
            return

        parts = folder_entity["path"].strip("/").split("/")
        asset_name = _sanitize(parts[-1])
        sequence_name = _sanitize(parts[-2]) if len(parts) >= 2 else ""

        self.launch_context.env["ASSET"] = asset_name
        self.launch_context.env["SQ"] = sequence_name
        self.log.debug(
            "Set $ASSET to '%s', $SQ to '%s'", asset_name, sequence_name)
