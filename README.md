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

`Model publish`
-saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a single file

Material publish
- saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a look file

Asset FX publish
- saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a single file
- Doesnt support .bgeo caching at the moment

Asset Groom publish
- saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a single file
- Doesnt support .bgeo caching at the moment if that is even what is used for grooming

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

- Get Payloading of assets to work
  - It shouldn't be to complicated I just don't know how it works yet

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

- RenderPackage Publisher
  - should work like the USDRenderPackage from royalrender plugin
  - should be called something like SimpleUSD Render
  - put all Renders in a Group to keep loader clean
    - remove the USDRenderPackage prefix in the loader to find passes easier
  - It should upload a reviewable to Kitsu/Shotgrid
    - It should create a contact sheet of all passes send at once and upload it as a reviewable
      - The contact sheet should be automatically generated and adjusted based on how many render packages are send at once
      - It should label the passes with the name of the render package
  - If we don't use AYON Nodes we can maybe use the default USD Render option inside Ayon-Houdini as a base instead of the royalrender plugins version

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
