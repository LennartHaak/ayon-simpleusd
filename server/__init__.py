from typing import Type

from ayon_server.addons import BaseServerAddon

from .settings import SimpleUSDSettings


class SimpleUSDAddon(BaseServerAddon):
    settings_model: Type[SimpleUSDSettings] = SimpleUSDSettings
