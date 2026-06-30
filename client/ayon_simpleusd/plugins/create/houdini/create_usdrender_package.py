# -*- coding: utf-8 -*-
"""Creator plugin for creating USD renders."""
from ayon_houdini.api import plugin
from ayon_core.lib import BoolDef, EnumDef

import hou

class CreateUSDRenderPackage(plugin.HoudiniCreator):
    """USD Render ROP in /stage"""
    identifier = "io.ayon.creators.houdini.simpleusd.usdrender.package"
    label = "USD Render Package2"
    product_type = "usdrenderPackage2"
    icon = "magic"
    description = "Create USD Render Packagelol"

    render_target = "farm"

    def create(self, product_name, instance_data, pre_create_data):
        # Transfer settings from pre create to instance
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())

        creator_attributes["review"] = pre_create_data["review"]

        # TODO: Support creation in /stage if wanted by user
        # pre_create_data["parent"] = "/stage"
        instance_data.update({"node_type": "usd"})
        instance_data.update({
            "node_custom_parameter": {
                "rendersettings": {
                    "type": "string",
                    "label": "Render Settings",
                    "default": "",
                    "tags": {"sidefx::usdpathtype": "prim"},
                    "position_after": "loppath",
                    # "menu_script": "import loputils\nlop = kwargs['node'].input(0)\nif not isinstance(lop, hou.LopNode):\n    lop = kwargs['node'].node(kwargs['node'].evalParm('loppath'))\nstage = lop.stage() if isinstance(lop, hou.LopNode) else None\nreturn loputils.createRenderSettingsPrimMenu(stage)",
                    "menu_script": """import loputils
lop = kwargs['node'].input(0)
if not isinstance(lop, hou.LopNode):
    lop = kwargs['node'].node(kwargs['node'].evalParm('loppath'))
stage = lop.stage() if isinstance(lop, hou.LopNode) else None
return loputils.createRenderSettingsPrimMenu(stage)""",
                    "items": ["setting_1", "setting_2"],
                    "labels": ["Render Setting 1", "Render Setting 2"],
                    "menu_type": "replace"
                },
                "renderer": {
                    "type": "string",
                    "label": "Render Delegate",
                    "default": "",
                    "tags": {"sidefx::usdpathtype": "prim"},
                    "position_after": "rendersettings",
                    "items": ["Karma", "KarmaXPU", "Arnold", "Arnold-Husk", "renderman", "prman-xpu", "Redshift", "vray"],
                    "labels": ["Karma", "Karma XPU", "Arnold via kick", "Arnold via husk", "Renderman", "Renderman XPU", "Redshift", "V-Ray"],
                    "menu_type": "normal"
                },
            }
        })

        instance_data.update({"node_type": "usd"})

        instance = super(CreateUSDRenderPackage, self).create(
            product_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        parms = {
            # Render frame range
            "trange": 1
        }
        if self.selected_nodes:
            parms["loppath"] = self.selected_nodes[0].path()

        # By default strip any Houdini custom data from the output file
        # since the renderer doesn't care about it
        parms["clearhoudinicustomdata"] = True

        # Use the first selected LOP node if "Use Selection" is enabled
        # and the user had any nodes selected
        if self.selected_nodes:
            for node in self.selected_nodes:
                if node.type().category() == hou.lopNodeTypeCategory():
                    parms["loppath"] = node.path()
                    break

        instance_node.setParms(parms)

        # Lock some AYON attributes
        to_lock = ["productType", "id"]
        self.lock_parameters(instance_node, to_lock)

    def set_node_staging_dir(
            self, node, staging_dir, instance, pre_create_data):
        node.parm("lopoutput").set(f"{staging_dir}/$OS.usd")

    def get_instance_attr_defs(self):
        """get instance attribute definitions.
        Attributes defined in this method are exposed in
            publish tab in the publisher UI.
        """

        render_target_items = {
            # "local": "Local machine rendering",
            # "local_no_render": "Use existing frames (local)",
            "farm": "Local Export & Farm Rendering",
            "farm_split": "Farm Export & Farm Rendering",
        }

        return [
            BoolDef("review",
                    label="Review",
                    tooltip="Mark as reviewable",
                    default=True),
            EnumDef("render_target",
                    items=render_target_items,
                    label="Render target",
                    default=self.render_target)
        ]

    def get_pre_create_attr_defs(self):
        attrs = super(CreateUSDRenderPackage, self).get_pre_create_attr_defs()
        return attrs + self.get_instance_attr_defs()

    def get_publish_families(self):
        return ["render", "usdrenderPackage"]
