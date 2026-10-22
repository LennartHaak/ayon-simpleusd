# Houdini

Houdini is Simple USD's main host. This page covers what the addon sets up in every Houdini session, the HDAs it ships, and its three creators. All three creators build their output node in **Solaris (`/stage`)**.

- [Session setup](#session-setup)
- [Context variables `$ASSET` and `$SQ`](#context-variables-asset-and-sq)
- [Hiding ayon-houdini's own creators and loaders](#hiding-ayon-houdinis-own-creators-and-loaders)
- [Bundled HDAs](#bundled-hdas)
- [SimpleUSD Asset](#simpleusd-asset)
- [SimpleUSD Shot](#simpleusd-shot)
- [Simple USD Render](#simple-usd-render)

For loading published files, see [Loaders](loaders.md).

---

## Session setup

When Houdini starts, it runs `startup/python3.*libs/pythonrc.py` (on `HOUDINI_PATH` through the [prelaunch hook](installation.md#houdini)). There is one identical copy per Houdini Python version (3.9, 3.10, 3.11, 3.13). It:

1. Registers the `$ASSET`/`$SQ` sync callbacks ([`houdini_vars.py`](../client/ayon_simpleusd/houdini_vars.py)).
2. In a UI session only:
   - registers the [workfile template](workfile-templates.md) callbacks, and
   - after startup (deferred), hides ayon-houdini's own creators and loaders.

## Context variables `$ASSET` and `$SQ`

| Variable | Value | Used by |
| --- | --- | --- |
| `$ASSET` | Current folder name, as a valid USD identifier | Default prim of asset layers, root prim of loaded assets |
| `$SQ` | Parent folder name (sequence) | Default prim of shot layers |

They're set at launch by `hooks/pre_asset_env.py`. Inside a running session, [`houdini_vars.py`](../client/ayon_simpleusd/houdini_vars.py) keeps them up to date:

- After AYON's `taskChanged` event (switching context in the Workfiles tool).
- After every hip file load or clear. Hip files save their global variables and restore them on load, so opening a file could otherwise bring back a stale `$ASSET`.

When a value changes, it's written with `set` and to `os.environ`. Then `varchange` recooks the nodes that reference it, such as the locked `defaultprim` parms.

## Hiding ayon-houdini's own creators and loaders

With **Hide Official Houdini Plugins** on (the default; see [settings](settings.md)), [`hide_official_houdini_plugins.py`](../client/ayon_simpleusd/hide_official_houdini_plugins.py) removes ayon-houdini's whole creator and loader plugin paths. The Publisher and Loader then show only Simple USD's tools.

- ayon-houdini's **Workfile** and **Review** (OpenGL/Flipbook) creators are registered again, so they stay available.
- The whole path has to go: AYON re-scans plugin paths each time the Publisher or Loader opens, so deregistering single classes doesn't stick.
- Changes take effect on the next Houdini launch.

## Bundled HDAs

The HDAs are non-commercial `.hdanc` files in [`client/ayon_simpleusd/startup/otls/`](../client/ayon_simpleusd/startup/otls). They load automatically in every Houdini launched from AYON. All of them are LOP (Solaris) nodes in the `LennartHaak` namespace.

| HDA | Version | Purpose |
| --- | --- | --- |
| `SimpleUSD_Alembic_Loader` | 1.4 | Loads an Alembic with the SimpleUSD structure (`element > geo > render\|proxy\|guide > meshes`) into a SimpleUSD model layout. Used by the [Blender model publish](blender-model.md). |
| `SimpleUSD_Asset_Load` | 1.6 | Wraps a Reference LOP and promotes `filepath1`/`primpath1`. Used by the [Reference Root USD](loaders.md#reference-root-usd) loader. |
| `SimpleUSD_Asset_USD_Structure` | 2.2 | Builds the USD prim structure for an asset |
| `SimpleUSD_Model_Builder` | 1.1 | Helps build a model in the SimpleUSD structure |
| `SimpleUSD_Shot_USD_Structure` | 4.2 | Builds the USD prim structure for a shot |
| `SimpleUSD_Mute_Layers` | 1.1 | Mutes layers on the stage |

Loaders refer to HDAs by type name without a version, so Houdini always uses the newest installed version. See [Development > Updating HDAs](development.md#updating-hdas) for how to ship a new version.

---

## SimpleUSD Asset

*Publisher > Create > **SimpleUSD Asset***. Source: [`create_usd_asset.py`](../client/ayon_simpleusd/plugins/create/houdini/create_usd_asset.py).

Publishes one part of an asset as a single, flattened USD layer.

### Artist usage

1. In `/stage`, select the LOP node whose stage should be published (with *Use selection* on).
2. Create a **SimpleUSD Asset** instance and choose an **Asset Type**:

   | Asset Type | Product type | Notes |
   | --- | --- | --- |
   | Model | `model` | Payload in root |
   | Material | `look` | Reference in root, "Validate USD Look Assignments" switched off |
   | Asset FX | `fx` | Reference in root. `.bgeo` caching isn't supported yet. |
   | Asset Groom | `groom` | Reference in root. `.bgeo` caching isn't supported yet. |
   | Root Asset | `root` | Manual root publish (usually not needed, see [Root asset](root-asset.md)) |

3. Publish.

### Instance options

| Option | Default | Effect |
| --- | --- | --- |
| **Update Root Asset** | on | After publishing, rebuild the asset's root file so it points to the latest version of every part ([details](root-asset.md)). Hidden on Root Asset instances. |
| **Render target** | Local | Local machine / use existing frames / farm |

### What the creator sets up

- A `usd_rop` node in `/stage` with these parms:
  - `loppath`: the selected node.
  - `defaultprim = $ASSET`, locked so it can't be changed by accident.
  - `savestyle = flattenstage`. Root Asset keeps the node default, so it stays a composition of references.
  - `enableoutputprocessor_simplerelativepaths = off`.
  - `lopoutput = $HIP/usd/$HIPNAME.usd`, the local work output.
- Product group `SimpleUSD Layers`.
- These publish plugins are off by default, since they belong to AYON's own USD contribution workflow:
  - *USD Contribution*
  - *Validate USD Asset Contribution Default Prim*
  - *Validate Instance In Context*
  - *Integrate Hero Version*
- The *Asset Type* changes the product type. The creator also recomputes the product name (for example `modelMain` or `lookMain`) so it matches that type.

Published files follow the project anatomy. With the default templates, that's `<asset>/work/<task>/usd/` for work and `<asset>/publish/<task>/usd/` for publish.

---

## SimpleUSD Shot

*Publisher > Create > **SimpleUSD Shot***. Source: [`create_usd_shot.py`](../client/ayon_simpleusd/plugins/create/houdini/create_usd_shot.py).

Works like *SimpleUSD Asset*, but for shot departments.

| Shot Type | Product type |
| --- | --- |
| Layout | `layout` |
| Animation | `animation` |
| FX | `fx` |
| Lighting | `lighting` |
| Rendering | `render` |

Differences from the asset creator:

- `defaultprim = $SQ` (the sequence) instead of `$ASSET`. It's always `flattenstage`.
- Product group `SimpleUSD Shot Layers`. The [Reference USD](loaders.md#reference-usd) loader uses this group to pick the matching prim path.
- No *Update Root Asset* option. Shot FX never triggers a root update.

---

## Simple USD Render

*Publisher > Create > **Simple USD Render***. Source: [`create_usd_render.py`](../client/ayon_simpleusd/plugins/create/houdini/create_usd_render.py).

Renders a Solaris stage locally or on the farm, and publishes the frames as a `usdrenderPackage` product (base type `render`).

### Artist usage

1. Select the LOP node to render, typically the end of the lighting network that contains your Karma Render Settings.
2. Create a **Simple USD Render** instance and choose the **Renderer**. The list shows every renderer the USD Render ROP supports (those with AOV support); the default is *Karma XPU*.
3. Create one instance per **variant** you want to compare, for example `Main`, `KeyLightWarm` and `KeyLightCool`. All farm-rendered variants with *Create Reviewable* on are combined into one [comparison review](rendering-and-review.md#comparison-review).
4. Publish.

### Instance options

| Option | Default | Effect |
| --- | --- | --- |
| **Create Reviewable** | on | Include this variant in the comparison review video uploaded to AYON (and synced to ShotGrid) |
| **Render target** | Farm Export & Farm Rendering | See below |
| **Set Farm Status** | on | Set the task to the [farm status](rendering-and-review.md#task-status-automation) once submitted. Turn it off for short renders. |
| **Turntable** | off | Put the product in the `SimpleUSD Turntables` group instead of `SimpleUSD Renders` |

| Render target | Meaning |
| --- | --- |
| Local machine rendering | Export and render locally |
| Use existing frames (local) | Publish frames that are already rendered |
| Farm Rendering | Render on the farm |
| Farm Export & Farm Rendering | Export the USD on the farm, then render it (default) |
| Local Export & Farm Rendering | Export the USD locally, then render on the farm |

### What the creator sets up

- A `usdrender_rop` node in `/stage` with:
  - `trange = 1`
  - `clearhoudinicustomdata` on
  - *save to directory* off
  - the chosen renderer
- For the two "farm render" targets: `runcommand` off and `allframesatonce` on. `lopoutput` is set to `<staging>/__render__.usd` as a full path, so ayon-royalrender's farm-split extractor works unmodified.
- At publish time, the USD and the frames are redirected into a versioned render folder. See [Rendering & review](rendering-and-review.md#versioned-render-folder).
