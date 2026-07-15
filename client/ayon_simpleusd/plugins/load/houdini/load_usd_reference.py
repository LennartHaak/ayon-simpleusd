# -*- coding: utf-8 -*-
"""Loader plugin for referencing a published USD model into Solaris."""
import hou

from ayon_core.pipeline import AYON_CONTAINER_ID
from ayon_houdini.api import lib, plugin
from ayon_houdini.api.lib import move_node_to_viewport


class USDModelReferenceLoader(plugin.HoudiniLoader):
    """Reference a published USD model into Solaris (/stage)."""

    product_types = {"model","look"}
    label = "Reference USD"
    representations = {"usd", "usda", "usdlc", "usdnc"}
    order = -8
    icon = "code-fork"
    color = "orange"
    use_ayon_entity_uri = False

    def load(self, context, name=None, namespace=None, data=None):
        file_path = self.filepath_from_context(context).replace("\\", "/")
        stage = hou.node("/stage")
        namespace = namespace if namespace else context["folder"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        container = stage.createNode("reference", node_name=node_name)
        container.setParms({
            "filepath1": file_path,
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
