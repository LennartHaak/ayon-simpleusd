AYON SimpleUSD Plugin
=============
This plugin aims to simplify AYONs USD workflow as it is a bit overkill for smaller productions.

📖 **Documentation:** see [docs/](docs/README.md) I generated the first version with AI. I'm currently rewriting it to be more usable.

Not Production Ready. It only supports the creation and loading of USD files for Assets.

At the moment it mainly supports Houdini; Blender can publish models through a headless Houdini conversion. Nuke support is planned.

This Plugin isn't an official AYON addon and has no affiliation with them.

### Requirements

- Houdini 22 (Python 3.13) needs an AYON dependency package **without** the old `future` 0.18.3 (its unguarded `import imp` crashes `import hou` on Python 3.12+). `ayon_2609041447` or newer is fine - Houdini then uses its own bundled, fixed `future`.
- simple-usd 0.3.0 and older shipped a workaround for this (a vendored `future` shim prepended to PYTHONPATH); 0.3.1 removed it. Only put 0.3.1+ into a bundle whose dependency package is already updated.

### AYON Setup

- The $ASSET env var is set automatically when Houdini is launched from AYON
  - Value: {project[code]}_{folder[name]}, sanitized like the loader prim paths (non-alphanumeric characters become underscores)
  - Note: switching the asset context inside a running Houdini session does not update $ASSET

### HDAs and Templates

- HDAs are loaded automatically when Houdini is launched from AYON - no manual install or network otls share needed
  - They live as plain `.hdanc` files in `client/ayon_simpleusd/startup/otls/`, which is on `HOUDINI_PATH` via the prelaunch hook (same approach as the official ayon-houdini addon)
  - They are non-commercial (`.hdanc`) assets; see `startup/otls/README.md` for how to update them
  - Remove old copies from any studio otls share, otherwise Houdini may pick the stale definition
- Workfile templates ship with the addon too (`client/ayon_simpleusd/templates/`) - no network share needed
  - Configure them in the web UI: Settings > Simple USD > Workfile Templates (studio or per project)
  - `Enabled` turns the whole feature on/off
  - Works in Houdini and Blender - one profile serves both, each app picks its own template file
  - Each profile filters by task type / task name / folder type / folder path (like the hosts' Templated Workfile Build) and picks a template:
    - `Included with Simple USD` - pick one of the bundled templates from the dropdown; bundled files are named `{host}_{name}_v###.{ext}` (e.g. `houdini_model_template_v001.hipnc`, `blender_model_template_v001.blend`; the version suffix is optional and the highest version wins), an app without its own version of the template (e.g. no `blender_shading_template.blend`) skips the profile
    - `Custom Path` - any template scene path, supports `{root[work]}` and `{ENV_VAR}` (Houdini also `$VAR`); the extension decides which app uses it (`.hip/.hipnc/.hiplc` Houdini, `.blend` Blender); the bundled templates are available as `{SIMPLEUSD_TEMPLATES}`
  - Defaults: Modeling task type -> Model template, Lookdev task type -> Shading template
  - The template is built into a new, unsaved scene (on launch, File > New or a new workfile from the Workfiles tool), placeholders are populated and - with `Create First Version` - the first workfile version is saved
    - Houdini merges the template into the scene, Blender opens it as the new scene
  - If a Houdini/Blender > Templated Workfile Build profile matches the same task, that one is used and Simple USD's is skipped - remove those profiles (and the network share copies) to use the bundled ones
  - Adding a template: drop `houdini_<name>_v001.hipnc` and/or `blender_<name>_v001.blend` into `client/ayon_simpleusd/templates/` and add `<name>` (without app prefix and version) to `INCLUDED_TEMPLATES` in `server/settings.py`
  - Updating a template: save it as the next version (`_v002`, ...) - no settings change needed; the old file can stay or be deleted

### SimpleUSD Publishers

##Assets

`SimpleUSD Asset publish`
- one creator with an "Asset Type" dropdown: Model, Material, Asset FX, Asset Groom
  (previously four separate publishers, now merged since they only differed
  in which product type they assigned)
- saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a single file (Material is treated as a look file)
- Asset FX / Asset Groom don't support .bgeo caching at the moment

`SimpleUSD Model (via Houdini)` (Blender)
- publishes a Blender collection as the same `model` product the Houdini SimpleUSD Asset (Model) creator makes - no Houdini session needed
- select the structure collection in the Outliner, then create the instance
  - the collection gets linked into the instance; if it has no Alembic Collection Exporter yet, one is added (Collection Properties > Exporters)
  - the collection's own exporter settings are used, only the file path is redirected to the publish staging dir
- the Alembic must follow the SimpleUSD Alembic Loader's structure: `element > geo > render|proxy|guide > meshes` (empties in Blender)
- on publish:
  1. the collection is exported with its Alembic exporter
  2. a headless `hython` runs it through the SimpleUSD Alembic Loader HDA and a `usd_rop` with the same settings as the Houdini creator (`flattenstage`, default prim `$ASSET`)
  3. Blender integrates the version with `usd` and `abc` representations, and - with `Update Root Asset` on - updates the asset's root like a Houdini publish
- if the conversion fails, the error shows the hython log and a debug `.hipnc` saved to the staging dir
- Settings > Simple USD > Blender Model (via Houdini): Houdini variant (empty = latest installed) and timeout
- requires Blender 4.2+ (Collection Exporters) and a Houdini license that can run `hython`
- ayon-blender's own model extractors (blend/fbx/usd/abc) and the Transform Zero / UV map1 validators are switched off on the instance by default

Root Asset Publish
- saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a single file referencing all other asset files

### SimpleUSD Loaders

Reference USD
- works as a normal Houdini Reference Node with the $ASSET env variable set as sourcename

Sublayers USD (Not needed can be removed)
- works as a normal Houdini Sublayer Node

###To-Do
- Rig Publisher for Assets
 - Can you just publish the rig without the geo or does that break the skinning and weights?

- Create Shot implementation
  - Make USD Shot Structure HDA
  - Create Shot Publish
    - What exactly needs to be published?
      - Animation
        - should just be deformed mesh without controls
        - in Shot should load root asset and animation file
          - or should the animation file just be a single reference file?
      - FX
        - first figure out how it can support .bgeo caches/how we can automate the process
        - Will also need a selector for farm caching
        - user can set variant manually
      - Lighting/Rendering File
        - We treat Lighting as our file before the render
        - This should also be the file that gets send to royal render
        - maybe we can integrate the save with the royal render plugin so we don't need two publishers
        - ~~If we have multiple render layers that we publish all at once as different render packages can we get a contact sheet of all layers together send to ShotGrid?~~ (done: comparison review)

  - Create Shot Loader
    - Although this will mainly be needed for Multi Shot and can be done later

- Automatically create Turntable for Assets
  - Model Turntable
    - Loads Model Publish
  - Shading Turntable
    - Loads Model Publish
    - Loads Material Publish
  - FX/Groom Turntable
    - Loads Model Publish
    - Loads FX/Groom Publish
  - Root Asset Turntable
    - Loads Root Asset Publish

  - Turntable Rendering should work similar to the render package
    - renders should be saved in the tasks folder not a render folder
      - Asset Turbtable should be saved in: Project --> Assets --> Asset_Name --> work --> task_name --> turntable
        - publish should be saved in: Project --> Assets --> Asset_Name --> publish --> task_name --> turntable --> version
        - Turntable version should always be the same as the asset version it was created from
    - It should create a reviewable to be uploaded to AYON (synced to ShotGrid)
      - Royal Render should render the turntable as a exr sequence and create a mov as reviewable in sRGB
      - It should move the move to the publish folder and remove the exr sequence from the work folder. It doesn't need to be saved


- Get Multi Shot to work somehow
  - This is the thing I will do if no to-dos are left :)
  - Have the user switch between lighting files as we don't have a assembly file
  - The first version of a lighting file has to be created for it to show inside the multi shot loader

- Root File
  - Loading a root file into a task mutes the task its loaded into
    - have a layer break under the root file to allow for task specific overrides

- Rendering Task
- Match Move Task

- create HDAs to move lights directly under the light primitive so artists don't have to do it manually
- Assets when loaded to shot get put in correct location based on filepath
- OpenGL Output on Farm
