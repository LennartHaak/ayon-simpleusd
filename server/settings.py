from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum,
    folder_types_enum,
)

# Template names - the client picks the file for the running app from
# client/ayon_simpleusd/templates, named "{host}_{name}[_v###].{ext}"
# (e.g. houdini_model_template_v001.hipnc, blender_model_template_v001.blend)
# - the highest version wins.
# Add new templates here and in the WorkfileTemplatesSettings default profiles.
INCLUDED_TEMPLATES = [
    {"value": "model_template", "label": "Model"},
    {"value": "shading_template", "label": "Shading"},
    {"value": "assetfx_template", "label": "Asset FX"},
    {"value": "assetgroom_template", "label": "Asset Groom"},
]

TEMPLATE_SOURCES = [
    {"value": "included", "label": "Included with Simple USD"},
    {"value": "custom", "label": "Custom Path"},
]


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


class BlenderHoudiniModelSettings(BaseSettingsModel):
    houdini_app: str = SettingsField(
        "",
        title="Houdini Application",
        description=(
            "Houdini application variant (e.g. 'houdini/21-0') whose "
            "hython converts the Alembic exported by Blender's 'SimpleUSD "
            "Model (via Houdini)' publish. Empty uses the latest variant "
            "with an existing executable."
        ),
    )
    timeout: int = SettingsField(
        600,
        title="Timeout (seconds)",
        ge=1,
        description="Fail the publish if the conversion takes longer.",
    )


class TemplateSourceModel(BaseSettingsModel):
    # Kept as its own model - conditional_enum hides every sibling field
    # that isn't named by the selected value.
    _layout = "expanded"
    source: str = SettingsField(
        "included",
        title="Template Source",
        enum_resolver=lambda: TEMPLATE_SOURCES,
        conditional_enum=True,
    )
    included: str = SettingsField(
        "model_template",
        title="Included Template",
        enum_resolver=lambda: INCLUDED_TEMPLATES,
        description=(
            "Each app uses its own version of the template (Houdini "
            "houdini_<name>_v###.hipnc, Blender blender_<name>_v###.blend, "
            "highest version wins). Apps without one skip this profile."
        ),
    )
    custom: str = SettingsField(
        "",
        title="Custom Path",
        description=(
            "Path to a template scene. The extension decides which app "
            "uses it: .hip/.hipnc/.hiplc for Houdini, .blend for "
            "Blender. Supports anatomy roots ({root[work]}), environment "
            "variables ({ENV_VAR}) and in Houdini also Houdini variables "
            "($VAR). The bundled templates are available under "
            "{SIMPLEUSD_TEMPLATES}."
        ),
    )


class WorkfileTemplateProfile(BaseSettingsModel):
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task Types",
        enum_resolver=task_types_enum,
    )
    task_names: list[str] = SettingsField(
        default_factory=list,
        title="Task Names",
    )
    folder_types: list[str] = SettingsField(
        default_factory=list,
        title="Folder Types",
        enum_resolver=folder_types_enum,
    )
    folder_paths: list[str] = SettingsField(
        default_factory=list,
        title="Folder Paths",
    )
    template: TemplateSourceModel = SettingsField(
        default_factory=TemplateSourceModel,
        title="Template",
        section="Template Configuration",
    )
    keep_placeholder: bool = SettingsField(
        False,
        title="Keep Placeholders",
    )
    create_first_version: bool = SettingsField(
        True,
        title="Create First Version",
        description=(
            "Save the built scene as the task's first workfile version "
            "when no workfile exists yet."
        ),
    )


class WorkfileTemplatesSettings(BaseSettingsModel):
    """Template scene built into a new, unsaved Houdini or Blender scene.

    Works like the hosts' own 'Templated Workfile Build', but can use the
    templates shipped with this addon - one profile serves both apps, each
    picks its own template file. If a Houdini/Blender 'Templated Workfile
    Build' profile matches the same task, that one wins and these are
    skipped.
    """
    #New ones also have to be added at the top at included templates
    enabled: bool = SettingsField(True, title="Enabled")
    profiles: list[WorkfileTemplateProfile] = SettingsField(
        default_factory=lambda: [
            WorkfileTemplateProfile(
                task_types=["Model"],
                template=TemplateSourceModel(
                    source="included",
                    included="model_template",
                ),
            ),
            WorkfileTemplateProfile(
                task_types=["Shading"],
                template=TemplateSourceModel(
                    source="included",
                    included="shading_template",
                ),
            ),
            WorkfileTemplateProfile(
                task_types=["Asset_FX"],
                template=TemplateSourceModel(
                    source="included",
                    included="assetfx_template",
                ),
            ),
            WorkfileTemplateProfile(
                task_types=["Asset_Groom"],
                template=TemplateSourceModel(
                    source="included",
                    included="assetgroom_template",
                ),
            ),
        ],
        title="Profiles",
    )


class SimpleUSDSettings(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    hide_official_houdini_plugins: bool = SettingsField(
        True,
        title="Hide Official Houdini Plugins",
        description=(
            "Hide ayon-houdini's own creators/loaders in the Publisher "
            "and Loader, keeping only Simple USD's visible (the Houdini "
            "Workfile and Review creators stay available). Takes effect "
            "on the next Houdini launch."
        ),
    )
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
    blender_houdini_model: BlenderHoudiniModelSettings = SettingsField(
        default_factory=BlenderHoudiniModelSettings,
        title="Blender Model (via Houdini)",
    )
    workfile_templates: WorkfileTemplatesSettings = SettingsField(
        default_factory=WorkfileTemplatesSettings,
        title="Workfile Templates",
    )
