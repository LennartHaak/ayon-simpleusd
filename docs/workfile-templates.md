# Workfile templates

Simple USD can start new Houdini and Blender scenes from a template scene for the current task. For example, Modeling tasks start from the bundled model template, and Lookdev tasks start from the shading template. The templates ship inside the addon, so you don't need a network share.

It works like the hosts' own *Templated Workfile Build*, and reuses their template builders, so placeholders work the same way. The differences:

- It can use the templates bundled with the addon.
- One profile serves both Houdini and Blender. Each app picks its own template file.

## When a template is built

A template is only built into a **new, unsaved** scene:

- when the app is launched from AYON into a task without a workfile,
- on *File > New*, or
- when a new workfile is created from the Workfiles tool.

Once the template is built, its placeholders are populated. If **Create First Version** is on, the scene is saved as the task's first workfile version.

| | Houdini | Blender |
| --- | --- | --- |
| How the template is applied | Merged into the empty scene | Opened as the new scene |
| Registered from | `pythonrc.py` (UI sessions only) | `SimpleUSDAddon.on_host_install` (not in background mode) |
| Code | [`workfile_templates.py`](../client/ayon_simpleusd/workfile_templates.py) | [`blender_workfile_templates.py`](../client/ayon_simpleusd/blender_workfile_templates.py) |

> [!IMPORTANT]
> If a profile in *Houdini/Blender > Templated Workfile Build* matches the
> same task, the host's own build is used and Simple USD's is skipped.
> To use the bundled templates, remove those profiles (and any copies on a
> network share).

## Configuration

*Studio or Project Settings > Simple USD > Workfile Templates*

| Field | Meaning |
| --- | --- |
| **Enabled** | Turns the whole feature on or off |
| **Profiles** | The first profile that matches the current context wins |

Each profile has these fields:

| Field | Meaning |
| --- | --- |
| Task Types / Task Names / Folder Types / Folder Paths | Filters for when the profile applies. An empty filter matches everything. |
| **Template Source** | *Included with Simple USD* or *Custom Path* |
| Included Template | The bundled template to use (*Model*, *Shading*) |
| Custom Path | A path to any template scene |
| Keep Placeholders | Keep the placeholder nodes after they're populated |
| Create First Version | Save the built scene as version 1 if the task has no workfile yet (default on) |

Default profiles:

| Task type | Template |
| --- | --- |
| Modeling | Model (`model_template`) |
| Lookdev | Shading (`shading_template`) |

### Included with Simple USD

Bundled templates live in [`client/ayon_simpleusd/templates/`](../client/ayon_simpleusd/templates) and are named:

```
{host}_{name}[_v###].{ext}
```

| File | Used by |
| --- | --- |
| `houdini_model_template_v001.hipnc` | Houdini, *Model* |
| `houdini_shading_template_v001.hipnc` | Houdini, *Shading* |
| `blender_model_template_v001.blend` | Blender, *Model* |

- The version suffix is optional. If there are several versions, the **highest one wins**.
- If an app has no file for the selected template, that app skips the profile. For example, Blender has no shading template, so Blender ignores the Lookdev profile.

### Custom Path

The custom path can be any template scene. The file extension decides which app uses it: `.hip`, `.hipnc` and `.hiplc` for Houdini, `.blend` for Blender. A path without an extension is passed to both.

The path can contain:

- anatomy roots, for example `{root[work]}/templates/houdini_layout.hipnc`
- environment variables, for example `{STUDIO_TEMPLATES}/…`. Houdini also understands `$VAR`.
- `{SIMPLEUSD_TEMPLATES}`, the bundled templates folder, for example `{SIMPLEUSD_TEMPLATES}/houdini_model_template_v001.hipnc`

## Adding or updating a template

- **Add:**
  1. Put `houdini_<name>_v001.hipnc` and/or `blender_<name>_v001.blend` into `client/ayon_simpleusd/templates/`.
  2. Add `<name>` (without the app prefix and version) to `INCLUDED_TEMPLATES` in [`server/settings.py`](../server/settings.py) so it shows up in the dropdown.
  3. Bump the addon version and rebuild the package.
- **Update:** save the template as the next version (`_v002`, …). No settings change is needed, and the old file can stay or be deleted.
