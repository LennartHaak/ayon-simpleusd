# Development

This page is for people changing the addon itself: how the repository is organized, how AYON finds the plugins, the order the publish plugins run in, and how to ship new HDAs, templates and versions.

## Repository layout

```
ayon-simple-usd/
├── package.py                  # addon name, version, client dir, required addons
├── create_package.py           # builds package/simple-usd-<version>.zip
├── server/
│   ├── __init__.py             # server addon (settings model only)
│   └── settings.py             # all settings - see docs/settings.md
├── client/ayon_simpleusd/
│   ├── addon.py                # client addon: plugin paths, launch hooks, Blender install
│   ├── version.py              # written by create_package.py
│   ├── hooks/                  # prelaunch hooks (HOUDINI_PATH, $ASSET/$SQ)
│   ├── startup/
│   │   ├── python3.*libs/pythonrc.py   # Houdini session setup
│   │   └── otls/               # bundled HDAs (.hdanc)
│   ├── templates/              # bundled workfile templates
│   ├── scripts/hython_abc_to_usd.py    # headless Alembic -> USD conversion
│   ├── plugins/
│   │   ├── create/{houdini,blender}/
│   │   ├── load/houdini/
│   │   └── publish/{houdini,blender,global}/
│   ├── houdini_vars.py         # $ASSET/$SQ sync in a running session
│   ├── hide_official_houdini_plugins.py
│   ├── workfile_templates.py   # Houdini templates + shared profile logic
│   ├── blender_workfile_templates.py
│   ├── blender_collection_export.py    # Blender Collection Exporter helpers
│   ├── houdini_conversion.py   # launches hython from another host
│   └── publish_comment.py      # version comment helpers
└── docs/                       # this documentation
```

## Plugin discovery

`SimpleUSDAddon._get_plugin_paths` in [`addon.py`](../client/ayon_simpleusd/addon.py) returns, for each plugin type (`create`, `load`, `publish`):

1. `plugins/<type>/<host>`, for example `plugins/publish/houdini`
2. `plugins/<type>/global`

Each folder is only returned if it exists. Plugins in `global` are loaded in **every** host and in farm publish jobs.

> [!IMPORTANT]
> `global` publish plugins must not import `hou` or `ayon_houdini` at
> module level. The RoyalRender farm publish runs as a plain Python
> process. A module that fails to import is silently skipped by pyblish.
> Import `pxr` inside methods too, so hosts without it can still load the
> module.

## Publish plugin order

| Order | Plugin | Hosts / target | Purpose |
| --- | --- | --- | --- |
| Collector + 0.05 | `BuildSimpleUSDComparisonReview` | farm | Build and upload the [comparison review](rendering-and-review.md#comparison-review) |
| Collector + 0.3 | `CollectSimpleUSDRootAutoUpdateInstance` | houdini, blender | Create the [root](root-asset.md) instance |
| *Collector + 0.49* | *CollectAnatomyInstanceData (ayon-core)* | | *Resolves version and anatomy* |
| Collector + 0.5 | `CollectSimpleUSDRootAutoUpdateArcs` | houdini, blender | Resolve root payloads and references |
| Collector + 0.9 | `CollectSimpleUSDRenderPaths` | houdini | [Versioned render folder](rendering-and-review.md#versioned-render-folder) |
| Collector + 0.91 | `CollectSimpleUSDComparisonMetadata` | houdini | Variant list for the comparison review |
| Validator | `ValidateSimpleUSDCollectionExporter` | blender | Collection has an Alembic exporter |
| Extractor − 0.48 | `CollectSimpleUSDVersionComment` | all | Version comment notes |
| Extractor | `ExtractSimpleUSDCollectionAbc` | blender | Alembic export |
| Extractor | `ExtractSimpleUSDRootAutoUpdate` | houdini, blender | Write `root.usd` |
| Extractor + 0.1 | `ExtractSimpleUSDHoudiniUsd` | blender | Headless Houdini conversion |
| Integrator + 0.5 | `IntegrateSimpleUSDAyonReviewStatus` | local | Review task status |
| Integrator + 0.5 | `IntegrateSimpleUSDFarmStatus` | local | Farm task status |

## Creator identifiers

| Creator | Identifier |
| --- | --- |
| SimpleUSD Asset | `io.ayon.creators.houdini.simpleusd.asset` |
| SimpleUSD Shot | `io.ayon.creators.houdini.simpleusd.shot` |
| Simple USD Render | `io.ayon.creators.houdini.simpleusd.render` |
| SimpleUSD Model (Blender) | `io.ayon.creators.blender.simpleusd.model` |

The root update and the version comment plugins check these identifiers, so a shot `fx` publish isn't treated as an asset part. If you rename one, update `ASSET_CREATOR_IDENTIFIERS` in both plugins.

## Updating HDAs

The HDAs are stored as single non-commercial `.hdanc` files in `client/ayon_simpleusd/startup/otls/`, named the way Houdini saves them: `lop_LennartHaak--<Name>-<version>.hdanc`.

1. Open the HDA in Houdini (from an AYON launch, so the bundled version is loaded) and make your changes.
2. Save it as a **new version** (*Assets > Asset Manager*, or *Type Properties > Save As*) into `startup/otls/`.
3. Delete the old version's file. The loaders and the conversion script create the HDA without a version, so the newest installed version is always used.
4. Commit the file. `.gitattributes` marks HDA and hip files as binary so their bytes aren't changed.
5. Bump the addon version and rebuild.

Remove any copies of the HDAs from studio otls shares. Houdini may otherwise pick up a stale definition.

## Releasing a new version

1. Bump `version` in [`package.py`](../package.py).
2. Run `python create_package.py`. It also updates `client/ayon_simpleusd/version.py`.
3. Upload `package/simple-usd-<version>.zip` to AYON and add it to a bundle. See [Installation](installation.md).

For quick local testing, `python create_package.py --only-client -o <dir>` extracts only the client code.
