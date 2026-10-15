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
        return self._get_plugin_paths("create", host_name)

    def get_load_plugin_paths(self, host_name: Optional[str] = None) -> List[str]:
        return self._get_plugin_paths("load", host_name)

    def get_publish_plugin_paths(self, host_name: Optional[str] = None) -> List[str]:
        return self._get_plugin_paths("publish", host_name)

    def _get_plugin_paths(self, plugin_type: str, host_name: Optional[str]) -> List[str]:
        """Return existing plugins/<plugin_type>/<host_name> and
        plugins/<plugin_type>/global dirs, in that order."""
        plugin_dir = os.path.join(SIMPLEUSD_ADDON_ROOT, "plugins", plugin_type)
        paths = []
        for sub_dir in (host_name, "global"):
            if not sub_dir:
                continue
            path = os.path.join(plugin_dir, sub_dir)
            if os.path.isdir(path):
                paths.append(path)
        return paths

    def get_launch_hook_paths(self, app):
        # HOUDINI_PATH/startup is set up by hooks/pre_houdini_startup_path.py
        # - ayon-applications only calls add_implementation_envs() on the
        # host addon (ayon-houdini), never on this one.
        return [os.path.join(SIMPLEUSD_ADDON_ROOT, "hooks")]
