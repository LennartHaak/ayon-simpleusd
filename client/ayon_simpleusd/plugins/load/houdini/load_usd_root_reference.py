# -*- coding: utf-8 -*-
"""Loader plugin for referencing a published root USD into Solaris.

Because it is only compatible with "root" products, it shows up when
right-clicking a product group (e.g. "SimpleUSD Layers") containing a
root, and loads only that root file - not the other layers.
"""
import hou
from pxr import Tf

from ayon_core.pipeline import AYON_CONTAINER_ID
from ayon_houdini.api import lib, plugin
from ayon_houdini.api.lib import move_node_to_viewport


class USDRootReferenceLoader(plugin.HoudiniLoader):
    """Reference a published root USD into Solaris (/stage)."""

    product_types = {"root"}
    label = "Reference Root USD"
    representations = {"usd", "usda", "usdlc", "usdnc"}
    # Lower than the Reference (0) and Sublayer (1) loaders so this action
    # sits above them in the Loader's right-click menu.
    order = -1
    icon = "link"
    color = "orange"
    use_ayon_entity_uri = False

    def load(self, context, name=None, namespace=None, data=None):
        file_path = self.filepath_from_context(context).replace("\\", "/")
        stage = hou.node("/stage")
        namespace = namespace if namespace else context["folder"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name
        primpath = "/{}".format(
            Tf.MakeValidIdentifier(context["folder"]["name"]))

        container = stage.createNode("reference", node_name=node_name)
        container.setParms({
            "filepath1": file_path,
            "primpath1": primpath,
        })
        move_node_to_viewport(container)

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
