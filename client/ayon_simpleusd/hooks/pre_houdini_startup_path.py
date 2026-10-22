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

        # Bundled workfile templates, usable in custom template paths
        # (e.g. $SIMPLEUSD_TEMPLATES/houdini_model_template_v001.hipnc).
        self.launch_context.env["SIMPLEUSD_TEMPLATES"] = os.path.join(
            os.path.dirname(startup_path), "templates")

        # Houdini only scans $HOUDINI_PATH/otls through the default
        # HOUDINI_OTLSCAN_PATH (@/otls). If the env overrides it (e.g. with a
        # studio otls share) our HDAs would be skipped, so add them explicitly.
        old_otlscan_path = self.launch_context.env.get("HOUDINI_OTLSCAN_PATH")
        if old_otlscan_path:
            otls_path = os.path.join(startup_path, "otls")
            new_otlscan_path = [otls_path]
            for path in old_otlscan_path.split(os.pathsep):
                if not path:
                    continue
                norm_path = os.path.normpath(path) if path != "&" else path
                if norm_path not in new_otlscan_path:
                    new_otlscan_path.append(norm_path)
            self.launch_context.env["HOUDINI_OTLSCAN_PATH"] = (
                os.pathsep.join(new_otlscan_path))
            self.log.debug(
                "Prepended '%s' to HOUDINI_OTLSCAN_PATH", otls_path)
