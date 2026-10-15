from ayon_server.settings import BaseSettingsModel, SettingsField


class AyonReviewStatusSettings(BaseSettingsModel):
    status_name: str = SettingsField(
        "Aw. Review",
        title="Status Name",
        description=(
            "AYON task status name to set on a published instance's "
            "linked task whenever it produces a 'review' or "
            "'webreview'-tagged representation - this is what AYON's "
            "own ShotGrid sync mirrors outward. Must exactly match a "
            "status name configured on the project's status list "
            "(Project Settings > Anatomy > Statuses). Leave empty to "
            "disable."
        ),
    )
    apply_to_workfile: bool = SettingsField(
        False,
        title="Apply To Workfile Publishes",
        description=(
            "Whether publishing the Houdini workfile itself (product "
            "type 'workfile') is also allowed to set the AYON Review "
            "Status. Off by default, since the workfile publishes in "
            "the same batch as everything else (including a farm "
            "render submission) and can clash with/overwrite other "
            "status updates set in that same publish."
        ),
    )


class FarmStatusSettings(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    status_name: str = SettingsField(
        "farm",
        title="Status Name",
        description=(
            "AYON task status name to set on a Simple USD Render "
            "instance's linked task once it has actually been "
            "submitted to the render farm. Must exactly match a status "
            "name configured on the project's status list (Project "
            "Settings > Anatomy > Statuses)."
        ),
    )


class RootAssetSettings(BaseSettingsModel):
    task_name: str = SettingsField(
        "root",
        title="Task Name",
        description=(
            "Name of the task each asset's automatically-updated 'root' "
            "USD product is published under, regardless of which task "
            "the triggering model/look/fx/groom part was published "
            "from. Must match an existing task name on the asset."
        ),
    )
    default_variant: str = SettingsField(
        "Main",
        title="Default Variant",
        description=(
            "Variant name used the first time an asset's 'root' USD "
            "product gets automatically created (no effect once a root "
            "product already exists - its existing name is always "
            "reused)."
        ),
    )


class SimpleUSDSettings(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    ayon_review_status: AyonReviewStatusSettings = SettingsField(
        default_factory=AyonReviewStatusSettings,
        title="AYON Review Status",
    )
    farm_status: FarmStatusSettings = SettingsField(
        default_factory=FarmStatusSettings,
        title="Farm Status",
    )
    root_asset: RootAssetSettings = SettingsField(
        default_factory=RootAssetSettings,
        title="Root Asset",
    )
