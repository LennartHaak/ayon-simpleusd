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
