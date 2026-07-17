# -*- coding: utf-8 -*-
"""Prelaunch hook setting the $ASSET environment variable for Houdini."""
import re

from ayon_applications import PreLaunchHook, LaunchTypes


class AddAssetEnvVar(PreLaunchHook):
    """Set $ASSET to '<project_code>_<folder_name>' before Houdini launches."""

    app_groups = {"houdini"}
    launch_types = {LaunchTypes.local, LaunchTypes.farm_render}
    order = 0  # after GlobalHostDataHook (-100) fills project/folder entities

    def execute(self):
        project_entity = self.data.get("project_entity")
        folder_entity = self.data.get("folder_entity")
        if not project_entity or not folder_entity:
            self.log.warning("Missing context data, $ASSET was not set.")
            return
        asset_name = "{}_{}".format(
            project_entity["code"], folder_entity["name"]
        )
        # Mirror Tf.MakeValidIdentifier so $ASSET matches loader prim paths
        # (pxr is not importable in the launcher process)
        asset_name = re.sub(r"\W", "_", asset_name) or "_"
        if asset_name[0].isdigit():
            asset_name = "_" + asset_name[1:]
        self.launch_context.env["ASSET"] = asset_name
        self.log.debug("Set $ASSET to '%s'", asset_name)
