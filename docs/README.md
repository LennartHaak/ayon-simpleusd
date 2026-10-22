# Simple USD documentation

Simple USD is an unofficial [AYON](https://ayon.ynput.io/) addon that simplifies AYON's USD workflow. It is very specific to our needs so expect more complex features to be missing unless we need them. Feel free to contribute more features tough.

> [!WARNING]
> Simple USD is not production ready and isn't affiliated with Ynput/AYON.
> The entire Project was built with Houdini education licenses, so it is not suitable for commercial use. Templates and HDAs are also non-commercial.
> Houdini is the main host. Blender can publish models through a headless
> Houdini conversion.

## Pages

| Page | What it covers |
| --- | --- |
| [Installation & setup](installation.md) | Requirements, building and uploading the package, what happens when an app launches |
| [Houdini](houdini.md) | Session setup, bundled HDAs, the **SimpleUSD Asset**, **SimpleUSD Shot** and **Simple USD Render** creators |
| [Blender model publish](blender-model.md) | **SimpleUSD Model (via Houdini)**: publishing a Blender collection as a USD model |
| [Loaders](loaders.md) | Reference USD, Reference Root USD, Sublayer USD, Load Image (MaterialX) |
| [Root asset](root-asset.md) | How the asset's root USD file is rebuilt automatically after every part publish |
| [Rendering & review](rendering-and-review.md) | Versioned render folders, the farm comparison review video, task status automation |
| [Workfile templates](workfile-templates.md) | Bundled Houdini/Blender start scenes per task type |
| [Settings reference](settings.md) | Every setting under *Settings > Simple USD* |
| [Development](development.md) | Repository layout, plugin discovery and order, updating HDAs/templates, packaging |

## Features at a glance

| Feature | Host | Page |
| --- | --- | --- |
| Asset part publish (Model / Material / Asset FX / Asset Groom / Root Asset) | Houdini | [houdini.md](houdini.md#simpleusd-asset) |
| Shot part publish (Layout / Animation / FX / Lighting / Rendering) | Houdini | [houdini.md](houdini.md#simpleusd-shot) |
| USD render publish with local or farm rendering | Houdini | [houdini.md](houdini.md#simple-usd-render) |
| Model publish from a Blender collection through headless Houdini | Blender | [blender-model.md](blender-model.md) |
| Automatic root asset update after each part publish | Houdini, Blender | [root-asset.md](root-asset.md) |
| Combined comparison review video of all render variants | Farm (RoyalRender) | [rendering-and-review.md](rendering-and-review.md#comparison-review) |
| AYON task status updates (farm / awaiting review) | Houdini, farm | [rendering-and-review.md](rendering-and-review.md#task-status-automation) |
| Publish notes in the AYON version comment (synced to ShotGrid) | Houdini, Blender, farm | [root-asset.md](root-asset.md#version-comments) |
| `$ASSET` / `$SQ` context variables | Houdini | [houdini.md](houdini.md#context-variables-asset-and-sq) |
| Bundled HDAs loaded automatically | Houdini | [houdini.md](houdini.md#bundled-hdas) |
| Hiding ayon-houdini's own creators/loaders | Houdini | [houdini.md](houdini.md#hiding-ayon-houdinis-own-creators-and-loaders) |
| Workfile templates per task | Houdini, Blender | [workfile-templates.md](workfile-templates.md) |

## Glossary

**Product types**

| Product type | Made by | Meaning |
| --- | --- | --- |
| `model` | SimpleUSD Asset (Model), SimpleUSD Model (Blender) | Geometry layer of an asset. Becomes a **payload** in root. |
| `look` | SimpleUSD Asset (Material) | Materials and assignments. Becomes a **reference** in root. |
| `fx` | SimpleUSD Asset (Asset FX), SimpleUSD Shot (FX) | Asset FX layer (reference in root) or shot FX layer |
| `groom` | SimpleUSD Asset (Asset Groom) | Groom layer. Becomes a **reference** in root. |
| `root` | Automatic root update, SimpleUSD Asset (Root Asset) | One file per asset that composes all of its parts |
| `layout`, `animation`, `lighting`, `render` | SimpleUSD Shot | Shot department layers |
| `usdrenderPackage` | Simple USD Render | USD render export plus the rendered frames |

**Product groups.** These are the folders the Loader shows products under:

| Group | Contents |
| --- | --- |
| `SimpleUSD Layers` | Asset parts and root |
| `SimpleUSD Shot Layers` | Shot parts |
| `SimpleUSD Renders` | Render publishes |
| `SimpleUSD Turntables` | Render publishes with *Turntable* enabled |

**Context variables**

- `$ASSET`: the current folder's name, made into a valid USD identifier (for example `sh010`, or `_01_chair` for `01-chair`). Asset layers use it as their default prim.
- `$SQ`: the parent folder's name, usually the sequence. Shot layers use it as their default prim.
