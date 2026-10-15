# -*- coding: utf-8 -*-
"""Creator plugin for publishing a USD asset part from Solaris (/stage).

Replaces the previously separate Model/Material/Asset FX/Asset Groom
creators with a single creator and an "Asset Type" dropdown, since they
were identical apart from which product (base) type they assigned. Root
Asset was later merged in too - the only genuine differences were that
it didn't set "savestyle" and had no "Update Root Asset" toggle (see the
asset_type == "root" handling below and get_attr_defs_for_instance()).
"""
from ayon_houdini.api import plugin
from ayon_core.lib import BoolDef, EnumDef

import hou


class CreateSimpleUSDAsset(plugin.HoudiniCreator):
    """Publish a USD asset part (model/material/fx/groom) from Solaris
    (/stage)."""

    identifier = "io.ayon.creators.houdini.simpleusd.asset"
    label = "SimpleUSD Asset"
    product_type = "model"
    product_base_type = "model"
    icon = "cubes"
    enabled = True
    description = (
        "Create USD Asset (Model / Material / Asset FX / Asset Groom / "
        "Root Asset)"
    )

    render_target = "local"

    # Loader group the published products are put under. Any name creates
    # its own group folder; "USD Layer" would merge with AYON's default
    # USD contribution workflow group.
    product_group = "SimpleUSD Layers"

    # Single source of truth for the asset type dropdown - each entry
    # maps to the product (base) type assigned to the created instance.
    ASSET_TYPES = {
        "model": {
            "product_type": "model",
            "product_base_type": "model",
            "label": "Model",
        },
        "look": {
            "product_type": "look",
            "product_base_type": "look",
            "label": "Material",
        },
        "fx": {
            "product_type": "fx",
            "product_base_type": "fx",
            "label": "Asset FX",
        },
        "groom": {
            "product_type": "groom",
            "product_base_type": "groom",
            "label": "Asset Groom",
        },
        "root": {
            "product_type": "root",
            "product_base_type": "root",
            "label": "Root Asset",
        },
    }

    def create(self, product_name, instance_data, pre_create_data):
        asset_type = pre_create_data.get("asset_type", "model")
        type_info = self.ASSET_TYPES[asset_type]

        # The Create dialog computes `product_name` from this creator's
        # static class-level `product_type` (the row shown in the Create
        # list is not aware of the "Asset Type" dropdown), so it needs to
        # be recomputed here using the actually selected type.
        folder_path = instance_data["folderPath"]
        task_name = instance_data.get("task")
        variant = instance_data["variant"]
        folder_entity = self.create_context.get_folder_entity(folder_path)
        task_entity = self.create_context.get_task_entity(
            folder_path, task_name)
        product_name = self.get_product_name(
            self.project_name,
            folder_entity,
            task_entity,
            variant,
            product_type=type_info["product_type"],
        )

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
        if asset_type == "look":
            publish_attributes["ValidateUsdLookAssignments"] = {
                "active": False}

        # `HoudiniCreator.create()` builds the instance from `self.
        # product_type`/`self.product_base_type` rather than from
        # `instance_data`, so temporarily point them at the selected type
        # for the duration of the call.
        original_product_type = self.product_type
        original_product_base_type = self.product_base_type
        self.product_type = type_info["product_type"]
        self.product_base_type = type_info["product_base_type"]
        try:
            instance = super().create(
                product_name,
                instance_data,
                pre_create_data)
        finally:
            self.product_type = original_product_type
            self.product_base_type = original_product_base_type

        instance_node = hou.node(instance.get("instance_node"))

        parms = {
            "enableoutputprocessor_simplerelativepaths": False,
            "defaultprim": "$ASSET",
        }
        if asset_type != "root":
            # Matches the original standalone Root Asset creator, which
            # left this on the node's default (unset) rather than forcing
            # "flattenstage" the way every other asset part does.
            parms["savestyle"] = "flattenstage"
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
            BoolDef("update_root_asset",
                    label="Update Root Asset",
                    tooltip=(
                        "After this publish, automatically republish the "
                        "asset's 'root' USD file so it references the "
                        "latest published version of every model/look/fx/"
                        "groom part. Creates the first root version if "
                        "none exists yet."
                    ),
                    default=True),
            EnumDef("render_target",
                    items=render_target_items,
                    label="Render target",
                    default=self.render_target)
        ]

    def get_attr_defs_for_instance(self, instance):
        # "Update Root Asset" doesn't make sense on a root instance
        # itself - it's meant for the model/look/fx/groom parts that
        # feed into root. Only affects the attribute panel of an
        # already-created instance; the pre-create dialog has no
        # instance yet to check against, so it still shows there
        # regardless of the chosen Asset Type (harmless - nothing reads
        # it for root instances).
        attr_defs = self.get_instance_attr_defs()
        if instance.data.get("productType") == "root":
            attr_defs = [
                attr_def for attr_def in attr_defs
                if attr_def.key != "update_root_asset"
            ]
        return attr_defs

    def get_pre_create_attr_defs(self):
        asset_type_items = {
            key: type_info["label"]
            for key, type_info in self.ASSET_TYPES.items()
        }

        attrs = super().get_pre_create_attr_defs()
        attrs += [
            EnumDef("asset_type",
                    items=asset_type_items,
                    label="Asset Type",
                    default="model"),
        ]

        return attrs + self.get_instance_attr_defs()
