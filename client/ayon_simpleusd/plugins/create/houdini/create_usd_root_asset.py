# -*- coding: utf-8 -*-
"""Creator plugin for publishing a USD Root Asset from Solaris (/stage)."""
from ayon_houdini.api import plugin
from ayon_core.lib import EnumDef

import hou


class CreateSimpleUSDRootAsset(plugin.HoudiniCreator):
    """Publish a USD Root Asset from Solaris (/stage)."""

    identifier = "io.ayon.creators.houdini.simpleusd.root_asset"
    label = "SimpleUSD Root Asset"
    product_type = "root"
    product_base_type = "root"
    icon = "link"
    enabled = True
    description = "Create USD Root Asset"

    render_target = "local"

    # Loader group the published products are put under. Any name creates
    # its own group folder; "USD Layer" would merge with AYON's default
    # USD contribution workflow group.
    product_group = "SimpleUSD Layers"

    def create(self, product_name, instance_data, pre_create_data):
        # "usd" (Driver/usd) only exists in the ROP category; the native
        # LOP-context equivalent living directly inside /stage is "usd_rop".
        instance_data.update({
            "node_type": "usd_rop",
            "productGroup": self.product_group,
        })
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        creator_attributes["render_target"] = pre_create_data["render_target"]

        # Default some redundant/off-by-default publish switches so
        # artists don't have to toggle them manually on every instance.
        publish_attributes = instance_data.setdefault(
            "publish_attributes", dict())
        publish_attributes.update({
            # "USD Contribution > Enable" (CollectUSDLayerContributions)
            "CollectUSDLayerContributions": {"contribution_enabled": False},
            "ValidateUSDAssetContributionDefaultPrim": {"active": False},
            "ValidateInstanceInContextHoudini": {"active": False},
            "IntegrateHeroVersion": {"active": False},
        })

        instance = super().create(
            product_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        parms = {
            "enableoutputprocessor_simplerelativepaths": False,
            "defaultprim": "$ASSET",
        }
        if self.selected_nodes:
            parms["loppath"] = self.selected_nodes[0].path()

        instance_node.setParms(parms)

        # Lock some AYON attributes, including "defaultprim" so it can't
        # accidentally be overwritten with an unrelated value.
        to_lock = ["productType", "productBaseType", "id", "defaultprim"]
        self.lock_parameters(instance_node, to_lock)

        return instance

    @staticmethod
    def create_instance_node(
        folder_path,
        node_name,
        parent,
        node_type="geometry",
        pre_create_data=None,
        node_custom_parameter=None,
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
            node_custom_parameter,
            instance_data,
        )

    def set_node_staging_dir(
            self, node, staging_dir, instance, pre_create_data):
        node.parm("lopoutput").set("$HIP/usd/$HIPNAME.usd")

    def get_network_categories(self):
        return [hou.lopNodeTypeCategory()]

    def get_publish_families(self):
        return ["usd", "usdrop", "publish.hou"]

    def get_instance_attr_defs(self):
        render_target_items = {
            "local": "Local machine rendering",
            "local_no_render": "Use existing frames (local)",
            "farm": "Farm Rendering",
        }

        return [
            EnumDef("render_target",
                    items=render_target_items,
                    label="Render target",
                    default=self.render_target)
        ]

    def get_pre_create_attr_defs(self):
        attrs = super().get_pre_create_attr_defs()
        return attrs + self.get_instance_attr_defs()
