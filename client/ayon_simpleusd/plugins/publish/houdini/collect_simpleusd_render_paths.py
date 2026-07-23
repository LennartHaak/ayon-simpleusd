# -*- coding: utf-8 -*-
"""Collector redirecting Simple USD Render output into a versioned folder.

By default the USD export (set at creation time) lands in AYON's staging
"ayon" folder, separate from wherever the artist's own Render Settings
network writes the actual image frames (a plain Houdini/Karma default).
This moves both into one shared, per-version location:

    <task work dir>/render/v###/<sequence>_<shot>_render_<variant>_v###.usd
    <task work dir>/render/v###/<sequence>_<shot>_render_<variant>_v###.$F4.<ext>

Version isn't known until the publish pipeline resolves it (AYON's own
CollectAnatomyInstanceData, order CollectorOrder + 0.49), so this can't
be baked in at node-creation time - it has to run as a publish step,
before any extraction/job-creation plugin reads these paths.
"""
import os

import hou
import pyblish.api

from ayon_houdini.api import plugin


class CollectSimpleUSDRenderPaths(plugin.HoudiniInstancePlugin):
    """Redirect the USD export and Render Product output into a shared,
    versioned render/v### folder."""

    label = "Collect Simple USD Render Paths"
    # After CollectAnatomyInstanceData (CollectorOrder + 0.49) resolves
    # instance.data["version"], before any Validator/Extractor plugin
    # reads the node's output paths.
    order = pyblish.api.CollectorOrder + 0.9
    families = ["usdrenderPackage"]

    def process(self, instance):
        rop_node = hou.node(instance.data["instance_node"])
        if not rop_node:
            return

        base_name = self._get_base_name(instance)
        render_dir = self._get_render_dir(instance)

        lopoutput = "{}/{}.usd".format(render_dir, base_name)
        rop_node.parm("lopoutput").set(lopoutput)
        self.log.debug("Set '%s' lopoutput to: %s", rop_node.path(),
                        lopoutput)

        ext = self._set_render_product_names(rop_node, render_dir, base_name)

        # Stash the resolved naming so later publish steps (e.g. the
        # comparison-review builder) don't need to re-derive it.
        instance.data["simpleusdBaseName"] = base_name
        instance.data["simpleusdRenderDir"] = render_dir
        instance.data["simpleusdExt"] = ext

    def _get_base_name(self, instance):
        folder_path = instance.context.data["folderPath"]
        parts = folder_path.strip("/").split("/")
        shot = parts[-1]
        sequence = parts[-2] if len(parts) >= 2 else ""
        version = instance.data["version"]
        version_str = "v{:03d}".format(version)
        variant = instance.data.get("variant", "")

        return "_".join(
            part for part in
            [sequence, shot, "render", variant, version_str]
            if part
        )

    def _get_render_dir(self, instance):
        version = instance.data["version"]
        version_str = "v{:03d}".format(version)
        hip_dir = hou.expandString("$HIP").replace("\\", "/")
        return "{}/render/{}".format(hip_dir, version_str)

    def _set_render_product_names(self, rop_node, render_dir, base_name):
        """Rename every render output found on the ROP's ancestor
        network into our shared render_dir/base_name naming.

        A "Karma Render Settings" node (type "karmarendersettings")
        defines its own single default render product directly via its
        "picture" parm - by default something like
        "$HIP/render/$HIPNAME.$OS.$F4.exr" - there is no separate
        "renderproduct"-type node in the ancestor chain in that (the
        most common) case, confirmed via hython on Houdini 22. Explicit
        "renderproduct" nodes and multi-AOV "karmarenderproducts" nodes
        (parm "products" holding the count, instances "productName_N")
        are also handled, for scenes that use those instead.

        Returns the resolved file extension (from whichever product got
        renamed, "exr" if none were found).
        """
        ext = "exr"
        for node in rop_node.inputAncestors():
            type_name = node.type().name()

            if type_name == "renderproduct":
                parm = node.parm("productName")
                ext = self._get_extension(parm)
                product_name = "{}/{}.$F4.{}".format(
                    render_dir, base_name, ext)
                parm.set(product_name)
                self.log.debug("Set '%s' productName to: %s",
                                node.path(), product_name)

            elif type_name in (
                "karmarenderproducts", "karmarenderproducts::2.0"
            ):
                count = node.parm("products").eval()
                for index in range(count):
                    parm = node.parm("productName_{}".format(index))
                    if parm is None:
                        continue
                    ext = self._get_extension(parm)
                    if count > 1:
                        primname_parm = node.parm(
                            "primname_{}".format(index))
                        suffix = (
                            primname_parm.eval() if primname_parm
                            else str(index)
                        )
                        product_name = "{}/{}_{}.$F4.{}".format(
                            render_dir, base_name, suffix, ext)
                    else:
                        product_name = "{}/{}.$F4.{}".format(
                            render_dir, base_name, ext)
                    parm.set(product_name)
                    self.log.debug("Set '%s' productName_%d to: %s",
                                    node.path(), index, product_name)

            elif type_name == "karmarendersettings":
                parm = node.parm("picture")
                if parm is None:
                    continue
                ext = self._get_extension(parm)
                product_name = "{}/{}.$F4.{}".format(
                    render_dir, base_name, ext)
                parm.set(product_name)
                self.log.debug("Set '%s' picture to: %s",
                                node.path(), product_name)

        return ext

    def _get_extension(self, parm):
        current = parm.eval()
        if current:
            ext = os.path.splitext(current)[-1].lstrip(".")
            if ext:
                return ext
        return "exr"
