# -*- coding: utf-8 -*-
"""Creator plugin for publishing a USD Render from Solaris (/stage)."""
from ayon_houdini.api import plugin
from ayon_core.lib import BoolDef, EnumDef

import hou


def get_usd_rop_renderers():
    """Return all available renderers supported by USD Render ROP.

    Note that the USD Render ROP does not include all Hydra renderers,
    because it excludes the GL ones like Houdini GL and Storm. USD Render
    ROP only lists the renderers that have `aovsupport` enabled.
    """
    return {
        info["name"]: info["displayname"] for info
        in hou.lop.availableRendererInfo() if info.get("aovsupport")
    }


class CreateSimpleUSDRender(plugin.HoudiniCreator):
    """Publish a USD Render from Solaris (/stage)."""

    identifier = "io.ayon.creators.houdini.simpleusd.render"
    label = "Simple USD Render"
    product_type = "usdrenderPackage"
    product_base_type = "render"
    icon = "magic"
    enabled = True
    description = "Create Simple USD Render"

    default_renderer = "Karma XPU"
    render_target = "farm_split"

    # Loader group the published products are put under. Any name creates
    # its own group folder; "USD Layer" would merge with AYON's default
    # USD contribution workflow group.
    product_group = "SimpleUSD Renders"
    turntable_product_group = "SimpleUSD Turntables"

    def create(self, product_name, instance_data, pre_create_data):
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        for key in [
            "render_target", "review", "isTurntable", "set_farm_status",
        ]:
            if key in pre_create_data:
                creator_attributes[key] = pre_create_data[key]

        instance_data.update({
            "node_type": "usdrender_rop",
            "productGroup": (
                self.turntable_product_group
                if pre_create_data.get("isTurntable")
                else self.product_group
            ),
        })

        instance = super().create(
            product_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        parms = {
            "trange": 1
        }
        if self.selected_nodes:
            parms["loppath"] = self.selected_nodes[0].path()

        if pre_create_data.get("render_target") in {
            "farm_split",
            "local_export_farm_render",
        }:
            parms["runcommand"] = False
            parms["allframesatonce"] = True

        parms["clearhoudinicustomdata"] = True
        parms["enableoutputprocessor_savetodirectory"] = False

        # Use the first selected LOP node if "Use Selection" is enabled
        # and the user had any nodes selected
        if self.selected_nodes:
            for node in self.selected_nodes:
                if node.type().category() == hou.lopNodeTypeCategory():
                    parms["loppath"] = node.path()
                    break

        if pre_create_data.get("renderer"):
            parms["renderer"] = pre_create_data.get("renderer")

        instance_node.setParms(parms)

        # Lock some AYON attributes
        to_lock = ["productType", "productBaseType", "id"]
        self.lock_parameters(instance_node, to_lock)

        return instance

    @staticmethod
    def create_instance_node(
        folder_path,
        node_name,
        parent,
        node_type="geometry",
        pre_create_data=None,
        instance_data=None
    ):
        # This creator always publishes from Solaris - force /stage
        # instead of AYON's default /out.
        return plugin.HoudiniCreatorBase.create_instance_node(
            folder_path,
            node_name,
            "/stage",
            node_type,
            pre_create_data,
            instance_data,
        )

    def set_node_staging_dir(
            self, node, staging_dir, instance, pre_create_data):
        node.parm("savetodirectory_directory").set(
            f"{staging_dir}/usd/$HIPNAME/$OS")

        if pre_create_data.get("render_target") in {
            "farm_split",
            "local_export_farm_render",
        }:
            # Full path (not a bare relative filename, unlike
            # ayon-houdini's official creator) so that RoyalRender's
            # ExtractUSDFarmSplit - which derives the staging dir via
            # os.path.dirname() on this parm - keeps working unmodified.
            node.parm("lopoutput").set(f"{staging_dir}/__render__.usd")

    def get_network_categories(self):
        return [hou.lopNodeTypeCategory()]

    def get_publish_families(self):
        return ["render", "usdrenderPackage"]

    def get_instance_attr_defs(self):
        render_target_items = {
            "local": "Local machine rendering",
            "local_no_render": "Use existing frames (local)",
            "farm": "Farm Rendering",
            "farm_split": "Farm Export & Farm Rendering",
            "local_export_farm_render": "Local Export & Farm Rendering",
        }

        return [
            BoolDef("review",
                    label="Create Reviewable",
                    tooltip="Creates a reviewable that gets uploaded to Kitsu/Shotgrid",
                    default=True),
            EnumDef("render_target",
                    items=render_target_items,
                    label="Render target",
                    default=self.render_target),
            BoolDef("set_farm_status",
                    label="Set Farm Status",
                    tooltip="Mark this task with the configured Farm "
                            "status once submitted to the farm. Leave "
                            "off for short renders where it's not "
                            "worth flagging.",
                    default=True),
            BoolDef("isTurntable",
                    label="Turntable",
                    tooltip="Assigns the Turntable Product Group to the output",
                    default=False),
        ]

    def get_pre_create_attr_defs(self):
        renderer_plugin_to_display_name = get_usd_rop_renderers()
        default_renderer = self.default_renderer or None
        if (
            default_renderer
            and default_renderer not in renderer_plugin_to_display_name
        ):
            for name, display_name in renderer_plugin_to_display_name.items():
                if default_renderer == display_name:
                    default_renderer = name
                    break
            else:
                default_renderer = None

        attrs = super().get_pre_create_attr_defs()
        attrs += [
            EnumDef("renderer",
                    label="Renderer",
                    default=default_renderer,
                    items=renderer_plugin_to_display_name),
        ]

        return attrs + self.get_instance_attr_defs()
