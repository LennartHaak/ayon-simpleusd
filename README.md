AYON SimpleUSD Plugin
=============
This plugin aims to simplify AYONs USD workflow as it is a bit overkill for smaller productions.

Not Production Ready. It only supports the creation and loading of USD files for Assets.

At the moment it only supports Houdini but we are planning on adding Nuke and Blender support.

This Plugin isn't an official AYON addon and has no affiliation with them.

### AYON Setup

- The $ASSET env var is set automatically when Houdini is launched from AYON
  - Value: {project[code]}_{folder[name]}, sanitized like the loader prim paths (non-alphanumeric characters become underscores)
  - Note: switching the asset context inside a running Houdini session does not update $ASSET

### HDAs and Templates

- The plugin doesn't auto install HDAs or Templates at the moment (...yet)
  - You can find them in the HDA and the templates folder of this repo and can add them manually to your project

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
- Include HDAs and Templates in the Plugin and automatically install them

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
        - If we have multiple render layers that we publish all at once as different render packages can we get a contact sheet of all layers together send to Kitsu/Shotgrid?

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
    - It should create a reviewable to be uploaded to Kitsu/Shotgrid
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

- OpenGL Output on Farm
