from ayon_server.settings import BaseSettingsModel, SettingsField


class SimpleUSDSettings(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
