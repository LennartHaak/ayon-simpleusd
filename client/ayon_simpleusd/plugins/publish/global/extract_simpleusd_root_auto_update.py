# -*- coding: utf-8 -*-
"""Extractor for automatically-synthesized "root" update instances (see
collect_simpleusd_root_auto_update.py).

Builds the root USD layer directly via the pxr Sdf API - no Houdini LOP
node network is created or cooked. The triggering publish runs inside
Houdini or Blender, both of which ship `pxr`, but using an actual usd_rop
node here would mean loading/cooking a separate root scene/HDA network
the way the manual "SimpleUSD Root Asset" creator does - which is exactly
what this feature must avoid.

`pxr` is imported inside the methods so other hosts can still discover
this global plugin module without it.
"""
import os

import pyblish.api

# Module import, not `from ... import Extractor` - pyblish would discover
# the imported base class as a plugin of its own.
from ayon_core.pipeline import publish


class ExtractSimpleUSDRootAutoUpdate(publish.Extractor):
    """Write the automatically-updated root USD file."""

    label = "Extract Simple USD Root Auto-Update"
    order = pyblish.api.ExtractorOrder
    hosts = ["houdini", "blender"]
    families = ["simpleusdAutoRoot"]

    def process(self, instance):
        from pxr import Sdf, Tf
        from ayon_core.pipeline.usdlib import (
            set_layer_defaults,
            get_or_define_prim_spec,
        )

        folder_path = instance.data["folderPath"]
        asset_name = Tf.MakeValidIdentifier(folder_path.rsplit("/", 1)[-1])

        layer = Sdf.Layer.CreateAnonymous("LOP")
        set_layer_defaults(layer, default_prim=asset_name)

        prim_path = Sdf.Path("/{}".format(asset_name))
        prim_spec = get_or_define_prim_spec(layer, prim_path, "Xform")

        payload_paths = instance.data.get("simpleusdRootPayloadPaths", [])
        if payload_paths:
            prim_spec.payloadList.prependedItems[:] = [
                Sdf.Payload(assetPath=path) for path in payload_paths
            ]

        reference_paths = instance.data.get(
            "simpleusdRootReferencePaths", []
        )
        if reference_paths:
            prim_spec.referenceList.prependedItems[:] = [
                Sdf.Reference(assetPath=path) for path in reference_paths
            ]

        if not payload_paths and not reference_paths:
            self.log.warning(
                "No model/look/fx/groom contributions resolved for '%s' - "
                "writing an empty root asset prim.", folder_path,
            )

        self._fix_typeless_prims(layer)

        staging_dir = self.staging_dir(instance)
        filename = "{}.usd".format(instance.data["productName"])
        filepath = os.path.join(staging_dir, filename)

        # Binary crate (.usd) - matches the extension every other simpleusd
        # creator's usd_rop lopoutput already publishes with.
        layer.Export(filepath, args={"format": "usdc"})

        instance.data["representations"] = [{
            "name": "usd",
            "ext": "usd",
            "files": filename,
            "stagingDir": staging_dir,
        }]

        self.log.info(
            "Wrote automatic root update '%s' -> %s",
            instance.data["productName"], filepath,
        )

    def _fix_typeless_prims(self, layer):
        """Author an explicit Scope type for any prim in the composed
        asset that has no type at all.

        A layer break used before publishing each individual asset part
        can leave pure "grouping" prims (e.g. a look file's /lookdev/mat)
        without a type opinion in that part's own flattened USD file, so
        the composed result under the root ends up typeless too. Since
        this spec is authored directly in the root layer - the strongest
        opinion for that prim path once anyone composes root.usd - it
        overrides the missing type from the weaker payloaded/referenced
        part files.
        """
        from pxr import Usd
        from ayon_core.pipeline.usdlib import get_or_define_prim_spec

        stage = Usd.Stage.Open(layer)
        for prim in stage.TraverseAll():
            if prim.GetTypeName():
                continue
            self.log.debug(
                "Assigning missing type 'Scope' to '%s'.", prim.GetPath())
            get_or_define_prim_spec(layer, prim.GetPath(), "Scope")
