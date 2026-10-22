# Installation & setup

This page lists what Simple USD needs, how to build and upload it to an AYON server, and what it sets up whenever Houdini or Blender is launched from AYON.

## Requirements

| Requirement | Needed for |
| --- | --- |
| AYON `core` addon > 0.3.3 | Everything (declared in [`package.py`](../package.py)) |
| `ayon-applications` | Launch hooks, finding Houdini for the Blender conversion |
| `ayon-houdini` | All Houdini creators, loaders and templates |
| `ayon-blender` and Blender 4.2+ | [Blender model publish](blender-model.md) (Collection Exporters were added in 4.2) and Blender workfile templates |
| A Houdini license that can run `hython` | [Blender model publish](blender-model.md) |
| `ayon-royalrender` | Farm render targets and the [comparison review](rendering-and-review.md#comparison-review) |

### Houdini 22 / Python 3.13

Houdini 22 (Python 3.12+) needs an AYON dependency package **without** the old `future` 0.18.3 package. That package's unguarded `import imp` crashes `import hou`. `ayon_2609041447` and newer are fine; Houdini then uses its own bundled, fixed `future`.

Simple USD 0.3.0 and older shipped a workaround (a vendored `future` shim on `PYTHONPATH`), and 0.3.1 removed it. Only put 0.3.1+ into a bundle whose dependency package is already updated.

## Building the package

The package is built with [`create_package.py`](../create_package.py) from the repository root:

```sh
python create_package.py
```

This writes `package/simple-usd-<version>.zip`. The version comes from [`package.py`](../package.py), and the script also writes it into `client/ayon_simpleusd/version.py`.

| Argument | Effect |
| --- | --- |
| `-o`, `--output <dir>` | Write the package somewhere else (the directory is purged first) |
| `--skip-zip` | Only create the folder structure, no zip |
| `--keep-sources` | Keep the unzipped folder next to the zip |
| `--only-client` | Only extract the client code into `--output` (for development) |
| `--debug` | Verbose logging |



## What happens on launch

The client addon ([`addon.py`](../client/ayon_simpleusd/addon.py)) registers its creator/loader/publish plugin folders and a folder of prelaunch hooks.

### Houdini

All Houdini default plugins get disabled. You can turn them back on in the server settings
Two prelaunch hooks run for local launches and for farm renders.

**[`hooks/pre_houdini_startup_path.py`](../client/ayon_simpleusd/hooks/pre_houdini_startup_path.py)**
- Prepends `client/ayon_simpleusd/startup` to `HOUDINI_PATH`, keeping `&` at the end. This makes Houdini:
  - run the addon's `pythonrc.py` (see [Houdini session setup](houdini.md#session-setup)), and
  - load every `.hdanc` in `startup/otls/`.
- Sets `SIMPLEUSD_TEMPLATES` to the bundled templates folder, for use in [custom template paths](workfile-templates.md#custom-path).

**[`hooks/pre_asset_env.py`](../client/ayon_simpleusd/hooks/pre_asset_env.py)**
- Sets `ASSET` to the folder name and `SQ` to the parent folder name.
- Non-alphanumeric characters become `_`, and a leading digit is replaced by `_`. This mirrors `Tf.MakeValidIdentifier`, so the values match the prim paths the loaders use.


### Blender

Blender has no startup script for this addon. Instead, `SimpleUSDAddon.on_host_install` registers the [workfile template](workfile-templates.md) callbacks once ayon-blender has installed its host.
