# -*- coding: utf-8 -*-
"""Prelaunch hook putting the addon's startup dir on HOUDINI_PATH.

AYON only calls ``add_implementation_envs`` on the host addon itself
(ayon-houdini), never on this addon - so the startup dir (pythonrc
scripts, otls) must be added from a prelaunch hook instead.
"""
import os

from ayon_applications import PreLaunchHook, LaunchTypes


class AddHoudiniStartupPath(PreLaunchHook):
    """Prepend ayon_simpleusd/startup to HOUDINI_PATH."""

    app_groups = {"houdini"}
    launch_types = {LaunchTypes.local, LaunchTypes.farm_render}
    order = 0

    def execute(self):
        startup_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "startup",
        )
        new_houdini_path = [startup_path]

        old_houdini_path = self.launch_context.env.get("HOUDINI_PATH") or ""
        for path in old_houdini_path.split(os.pathsep):
            if not path:
                continue
            norm_path = os.path.normpath(path)
            if norm_path not in new_houdini_path:
                new_houdini_path.append(norm_path)

        # Houdini needs "&" (the default path) to stay at the end.
        if "&" not in new_houdini_path:
            new_houdini_path.append("&")
        self.launch_context.env["HOUDINI_PATH"] = (
            os.pathsep.join(new_houdini_path))
        self.log.debug("Prepended '%s' to HOUDINI_PATH", startup_path)
