AYON SimpleUSD Plugin
=============
This plugin aims to simplify AYONs USD workflow as it is a bit overkill for smaller productions.

📖 **Documentation:** see [docs/](docs/README.md)

Not Production Ready and non non-commercial only

This Plugin isn't an official AYON addon and has no affiliation with them.

### Requirements

- Houdini 22 (Python 3.13) needs an AYON dependency package **without** the old `future` 0.18.3 (its unguarded `import imp` crashes `import hou` on Python 3.12+). `ayon_2609041447` or newer is fine - Houdini then uses its own bundled, fixed `future`.

### AYON Setup

- The $ASSET env var is set automatically when Houdini is launched from AYON
  - Value: {project[code]}_{folder[name]}, sanitized like the loader prim paths (non-alphanumeric characters become underscores)
  - Note: switching the asset context inside a running Houdini session does not update $ASSET

### HDAs and Templates

- HDAs are loaded automatically when Houdini is launched from AYON - no manual install or network otls share needed
  - They live as plain `.hdanc` files in `client/ayon_simpleusd/startup/otls/`, which is on `HOUDINI_PATH` via the prelaunch hook (same approach as the official ayon-houdini addon)
  - They are non-commercial (`.hdanc`) assets; see `startup/otls/README.md` for how to update them
