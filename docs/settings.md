# Settings reference

All settings are under **Studio Settings > Simple USD** and can be overridden per project in **Project Settings > Simple USD**. They're defined in [`server/settings.py`](../server/settings.py). The key path in `project_settings["simple-usd"]` is shown in brackets.

## General

| Setting | Default | Effect |
| --- | --- | --- |
| Enabled (`enabled`) | on | Turns the addon on or off |
| Hide Official Houdini Plugins (`hide_official_houdini_plugins`) | on | Hide ayon-houdini's own creators and loaders, keeping its Workfile and Review creators. Takes effect on the next Houdini launch. [More](houdini.md#hiding-ayon-houdinis-own-creators-and-loaders) |

## AYON Review Status (`ayon_review_status`)

| Setting | Default | Effect |
| --- | --- | --- |
| Status Name (`status_name`) | `Aw. Review` | Task status set when a publish produces a `review` or `webreview` representation, and when the farm comparison review is built. Must match a project status exactly. Leave it empty to turn this off. |
| Apply To Workfile Publishes (`apply_to_workfile`) | off | Also let `workfile` publishes set this status |

See [Task status automation](rendering-and-review.md#task-status-automation).

## Farm Status (`farm_status`)

| Setting | Default | Effect |
| --- | --- | --- |
| Enabled (`enabled`) | on | Set a task status when a Simple USD Render is submitted to the farm |
| Status Name (`status_name`) | `farm` | The status to set. Must match a project status exactly. |

Artists can also turn this off per instance with **Set Farm Status**.

## Root Asset (`root_asset`)

| Setting | Default | Effect |
| --- | --- | --- |
| Task Name (`task_name`) | `root` | The task every automatic root update is published under. The asset needs a task with this name. |
| Default Variant (`default_variant`) | `Main` | Variant used when an asset's root product is created for the first time |

See [Root asset](root-asset.md).

## Blender Model (via Houdini) (`blender_houdini_model`)

| Setting | Default | Effect |
| --- | --- | --- |
| Houdini Application (`houdini_app`) | *(empty)* | Houdini variant used for the conversion, for example `houdini/21-0`. Empty uses the latest variant whose executable exists. |
| Timeout (seconds) (`timeout`) | `600` | Fail the publish if the conversion takes longer |

See [Blender model publish](blender-model.md).

## Workfile Templates (`workfile_templates`)

| Setting | Default | Effect |
| --- | --- | --- |
| Enabled (`enabled`) | on | Turns the feature on or off |
| Profiles (`profiles`) | Modeling → Model, Lookdev → Shading | Filters plus a template per profile |

Profile fields: `task_types`, `task_names`, `folder_types`, `folder_paths`, `template.source` (`included` / `custom`), `template.included`, `template.custom`, `keep_placeholder`, `create_first_version`.

See [Workfile templates](workfile-templates.md).

## Per-instance options

These are set on each instance in the Publisher, not in the settings:

| Creator | Option | Default |
| --- | --- | --- |
| SimpleUSD Asset | Update Root Asset, Render target | on, Local |
| SimpleUSD Shot | Render target | Local |
| Simple USD Render | Create Reviewable, Render target, Set Farm Status, Turntable | on, Farm Export & Farm Rendering, on, off |
| SimpleUSD Model (Blender) | Update Root Asset | on |
