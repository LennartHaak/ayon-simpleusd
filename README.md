AYON SimpleUSD Plugin
=============
This plugin aims to simplify AYONs USD workflow as it is a bit overkill for smaller productions.

At the moment it only supports Houdini but we are planning on adding Nuke and Blender support.

This Plugin isn't an official AYON addon and has no affiliation with them.

### AYON Setup

- Set the $ASSET as a custom Env Var inside the Ayon-Houdini Plugin
  - Can be anything that represents your asset Name
    - I use: {project[name]_folder[name]}

### HDAs and Templates

- The plugin doesn't auto install HDAs or Templates at the moment (...yet)
  - You can find them in the HDA and the templates folder of this repo and can add them manually to your project

### SimpleUSD Publishers

Model publish
-saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a single file

Material publish
- saves to:
  - model_name --> work --> task --> usd
  - model_name --> publish --> task --> usd
- Treated as a look file


### SimpleUSD Loaders

Reference USD
- works as a normal Houdini Reference Node with the $ASSET env variable set as sourcename

Sublayers USD
- works as a normal Houdini Sublayer Node
