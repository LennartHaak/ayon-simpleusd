# -*- coding: utf-8 -*-
"""Loader plugin for referencing a published USD model into Solaris."""
import hou
from pxr import Tf

from ayon_core.pipeline import AYON_CONTAINER_ID
from ayon_houdini.api import lib, plugin

# CreateSimpleUSDShot (create_usd_shot.py) publishes its parts with
# defaultprim "$SQ" (the parent/sequence folder name) instead of "$ASSET"
# (the product's own folder name) that every other SimpleUSD creator
# uses - so referencing one back in needs a matching primpath. productGroup
# is the only signal on a loaded product that reliably tells the two apart
# (productBaseType doesn't: both creators can publish "fx").
SHOT_PRODUCT_GROUP = "SimpleUSD Shot Layers"


class USDModelReferenceLoader(plugin.HoudiniLoader):
    """Reference a published USD model into Solaris (/stage)."""

    product_types = {"model","look"}
    product_base_types = {
        "model", "look", "fx", "groom",
        "layout", "animation", "lighting", "render",
    }
    label = "Reference USD"
    representations = {"usd", "usda", "usdlc", "usdnc"}
    order = 0
    icon = "code-fork"
    color = "orange"
    use_ayon_entity_uri = False

    @staticmethod
    def _get_primpath(context):
        product_attrib = context["product"].get("attrib") or {}
        if product_attrib.get("productGroup") == SHOT_PRODUCT_GROUP:
            # Mirror create_usd_shot.py's "$SQ" - the parent (sequence)
            # folder's name, not the shot's own name.
            parts = context["folder"]["path"].strip("/").split("/")
            anchor_name = parts[-2] if len(parts) >= 2 else parts[-1]
        else:
            # Mirror every other creator's "$ASSET" - the product's own
            # folder name.
            anchor_name = context["folder"]["name"]
        return "/{}".format(Tf.MakeValidIdentifier(anchor_name))

    def load(self, context, name=None, namespace=None, data=None):
        file_path = self.filepath_from_context(context).replace("\\", "/")
        stage = hou.node("/stage")
        namespace = namespace if namespace else context["folder"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name
        primpath = self._get_primpath(context)

    #NOTE:Is it possible to also create subnet with custom Icon and custom settings?
    #WARN:If the loader is an HDA it might not be detected on the Farm or do they work like Toolsets in Nuke where it just treats them like normal nodes?
        container = stage.createNode("reference", node_name=node_name)
        container.setParms({
            "filepath1": file_path,
            "primpath1": primpath,
        })
        container.moveToGoodPosition()

        data = {
            "schema": "ayon:container-3.0",
            "id": AYON_CONTAINER_ID,
            "name": node_name,
            "namespace": namespace,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["id"],
        }
        lib.imprint(container, data)
        return container

    def update(self, container, context):
        node = container["node"]
        file_path = self.filepath_from_context(context).replace("\\", "/")
        node.setParms({
            "filepath1": file_path,
            "representation": context["representation"]["id"],
        })
        node.parm("reload").pressButton()

    def remove(self, container):
        container["node"].destroy()

    def switch(self, container, context):
        self.update(container, context)
