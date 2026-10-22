# Loaders

Simple USD adds four Houdini loaders. Each creates a node in the current scene and marks it as an AYON container, so the **Scene Inventory** can update, switch and remove it.

| Loader | Product types | Node created | Location |
| --- | --- | --- | --- |
| [Reference Root USD](#reference-root-usd) | `root` | `SimpleUSD_Asset_Load` HDA | `/stage` |
| [Reference USD](#reference-usd) | asset parts, shot parts, `usd` | `reference` LOP | `/stage` |
| [Sublayer USD](#sublayer-usd) | `model`, `look` | `sublayer` LOP | `/stage` |
| [Load Image (MaterialX)](#load-image-materialx) | images, renders, plates, reviews | MaterialX image node | current network |

Nodes are named `<folder>_<product>`, for example `chair_modelMain`. File paths are written as plain paths with forward slashes, not AYON entity URIs.

---

## Reference Root USD

Source: [`load_usd_root_reference.py`](../client/ayon_simpleusd/plugins/load/houdini/load_usd_root_reference.py)

Use this to bring a whole asset into a shot. It loads the asset's [root file](root-asset.md), which brings in all the asset's parts.

- It only accepts `root` products. Right-clicking the `SimpleUSD Layers` group in the Loader offers it and loads only the root, not the other layers.
- It's the topmost entry in the right-click menu (order −1).
- It creates the **SimpleUSD Asset Load** HDA (`LennartHaak::SimpleUSD_Asset_Load`, always the newest installed version) with:
  - `filepath1`: the published root file
  - `primpath1`: `/<folder name>`, made into a valid identifier
- If the HDA isn't installed, it falls back to a plain `reference` LOP and logs a warning.
- **Update** sets the new path and presses *Reload* on the HDA, or on the reference LOP inside it for older scenes.

## Reference USD

Source: [`load_usd_reference.py`](../client/ayon_simpleusd/plugins/load/houdini/load_usd_reference.py)

References any single published Simple USD layer into `/stage`.

- Product base types: `model`, `look`, `fx`, `groom`, `layout`, `animation`, `lighting`, `render`, `usd`.
- Representations: `usd`, `usda`, `usdlc`, `usdnc`.
- Creates a `reference` LOP with `filepath1` and `primpath1`. The prim path matches the default prim the layer was published with:

  | Product group | `primpath1` | Mirrors |
  | --- | --- | --- |
  | `SimpleUSD Shot Layers` | `/<parent folder>` (sequence) | the shot creator's `$SQ` |
  | anything else | `/<folder name>` | the asset creator's `$ASSET` |

  The product group is used because it's the only reliable way to tell the two apart: both creators can publish `fx`.
- **Update** and **switch** set the new path and press *Reload*.

## Sublayer USD

Source: [`load_usd_sublayer.py`](../client/ayon_simpleusd/plugins/load/houdini/load_usd_sublayer.py)

Sublayers a `model` or `look` layer into `/stage` with a `sublayer` LOP. You rarely need it; *Reference USD* or *Reference Root USD* is usually the right choice.

## Load Image (MaterialX)

Source: [`load_image_materialx.py`](../client/ayon_simpleusd/plugins/load/houdini/load_image_materialx.py)

Loads a published image or image sequence as a texture node, for example for a MaterialX shading network.

- Product types: `imagesequence`, `review`, `render`, `plate`, `image`, `online`. Any representation.
- The node is created in the network the Network Editor is currently showing, with `/stage` (or `/obj`) as a fallback.
- It tries these node types in order and uses the first that can be created: `mtlximport`, `mtlximage`, `mtlxtexture`, `texture`, `material`.
- The path is adjusted before it's set:
  - Frame sequences: the frame number is replaced by `$F4`.
  - UDIM tiles (`1001`–`1999`) are replaced by `<UDIM>`.
- On Houdini 20+, the representation's colorspace is written to the node's `colorspace` parm if it exists.
- **Remove** deletes the node, and also its parent and grandparent if they're left empty.
