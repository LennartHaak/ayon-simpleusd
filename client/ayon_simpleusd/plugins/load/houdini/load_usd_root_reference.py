# -*- coding: utf-8 -*-
"""Loader plugin for referencing a published root USD into Solaris.

Because it is only compatible with "root" products, it shows up when
right-clicking a product group (e.g. "SimpleUSD Layers") containing a
root, and loads only that root file - not the other layers.

The root is loaded with the "SimpleUSD Load Asset" HDA (startup/otls),
which wraps a reference LOP and promotes its filepath1/primpath1 parms.
"""
import hou
from pxr import Tf

from ayon_core.pipeline import AYON_CONTAINER_ID
from ayon_houdini.api import lib, plugin


def _reload(node):
    """Press 'reload' on the node, or on the reference LOP inside the HDA
    (old scenes still hold plain reference containers)."""
    parm = node.parm("reload")
    if parm is None:
        for child in node.allSubChildren():
            if child.type().name().startswith("reference"):
                parm = child.parm("reload")
                if parm is not None:
                    break
    if parm is not None:
        parm.pressButton()


class USDRootReferenceLoader(plugin.HoudiniLoader):
    """Reference a published root USD into Solaris (/stage) using the
    SimpleUSD Load Asset HDA."""

    product_types = {"root"}
    product_base_types = {"root"}
    label = "Reference Root USD"
    representations = {"usd", "usda", "usdlc", "usdnc"}
    # Lower than the Reference (0) and Sublayer (1) loaders so this action
    # sits above them in the Loader's right-click menu.
    order = -1
    icon = "link"
    color = "orange"
    use_ayon_entity_uri = False
    # Unversioned so Houdini picks the newest installed HDA version.
    node_type = "LennartHaak::SimpleUSD_Asset_Load"

    def load(self, context, name=None, namespace=None, data=None):
        file_path = self.filepath_from_context(context).replace("\\", "/")
        stage = hou.node("/stage")
        namespace = namespace if namespace else context["folder"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name
        primpath = "/{}".format(
            Tf.MakeValidIdentifier(context["folder"]["name"]))

        try:
            container = stage.createNode(self.node_type, node_name=node_name)
        except hou.OperationFailed:
            self.log.warning(
                "HDA '%s' is not installed, falling back to a reference "
                "node.", self.node_type)
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
        _reload(node)

    def remove(self, container):
        container["node"].destroy()

    def switch(self, container, context):
        self.update(container, context)
