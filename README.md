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

Sublayers USD
- works as a normal Houdini Sublayer Node

###To-Do

- remove mat/render and mat/proxy scopes from Structure Builder HDA

- Get Payloading of assets to work
  - It shouldn't be to complicated I just don't know how it works yet

- Include HDAs and Templates in the Plugin

- remove the project code prefix in $ASSET and usd_reference and usd_root_reference loaders

- Support conversion of .bgeo caches

- Create Shot implementation
  - Make USD Shot Structure HDA
  - Create Shot Publish
  - Create Shot Loader

- either copy over USDRenderPackage from royalrender plugin or see if with the current plugin it can just work on the farm
  - get to work that it puts all the render packages in a overall folder to keep the loader clean
  - change the naming of the finished render so it doesn't have the long USDRenderPackage prefix to make it easier to find in the loader

- Get Multi Shot to work somehow
  - This is the thing I will do if no to-dos are left :)

