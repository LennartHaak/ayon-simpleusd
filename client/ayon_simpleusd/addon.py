import os
from typing import Optional, List

from ayon_core.addon import AYONAddon, IPluginPaths

from .version import __version__

SIMPLEUSD_ADDON_ROOT = os.path.dirname(os.path.abspath(__file__))


class SimpleUSDAddon(AYONAddon, IPluginPaths):
    name = "simple-usd"
    version = __version__

    def initialize(self, studio_settings):
        self.enabled = studio_settings.get(self.name, {}).get("enabled", True)

    def get_plugin_paths(self):
        return {}

    def get_create_plugin_paths(self, host_name: Optional[str] = None) -> List[str]:
        create_dir = os.path.join(SIMPLEUSD_ADDON_ROOT, "plugins", "create")
        paths = []
        if host_name:
            host_path = os.path.join(create_dir, host_name)
            if os.path.isdir(host_path):
                paths.append(host_path)
        global_path = os.path.join(create_dir, "global")
        if os.path.isdir(global_path):
            paths.append(global_path)
        return paths

    def get_load_plugin_paths(self, host_name: Optional[str] = None) -> List[str]:
        load_dir = os.path.join(SIMPLEUSD_ADDON_ROOT, "plugins", "load")
        paths = []
        if host_name:
            host_path = os.path.join(load_dir, host_name)
            if os.path.isdir(host_path):
                paths.append(host_path)
        global_path = os.path.join(load_dir, "global")
        if os.path.isdir(global_path):
            paths.append(global_path)
        return paths

    def get_launch_hook_paths(self, app):
        return [os.path.join(SIMPLEUSD_ADDON_ROOT, "hooks")]

    def add_implementation_envs(self, env, app):
        if app.host_name != "houdini":
            return

        startup_path = os.path.join(SIMPLEUSD_ADDON_ROOT, "startup")
        new_houdini_path = [startup_path]

        old_houdini_path = env.get("HOUDINI_PATH") or ""
        for path in old_houdini_path.split(os.pathsep):
            if not path:
                continue
            norm_path = os.path.normpath(path)
            if norm_path not in new_houdini_path:
                new_houdini_path.append(norm_path)

        if "&" not in new_houdini_path:
            new_houdini_path.append("&")
        env["HOUDINI_PATH"] = os.pathsep.join(new_houdini_path)
