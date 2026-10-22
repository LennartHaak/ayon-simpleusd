# -*- coding: utf-8 -*-
"""Creator plugin for publishing a USD shot part from Solaris (/stage).

Mirrors create_usd_asset.py's "single creator + type dropdown" pattern,
but for shot-side departments instead of asset parts.
"""
from ayon_houdini.api import plugin
from ayon_core.lib import EnumDef

import hou


class CreateSimpleUSDShot(plugin.HoudiniCreator):
    """Publish a USD shot part (layout/animation/fx/lighting/rendering/
    compositing) from Solaris (/stage)."""

    identifier = "io.ayon.creators.houdini.simpleusd.shot"
    label = "SimpleUSD Shot"
    product_type = "layout"
    product_base_type = "layout"
    icon = "film"
    enabled = True
    description = (
        "Create USD Shot (Layout / Animation / FX / Lighting / Rendering)"
    )

    render_target = "local"

    # Loader group the published products are put under. Any name creates
    # its own group folder; "USD Layer" would merge with AYON's default
    # USD contribution workflow group.
    product_group = "SimpleUSD Shot Layers"

    # Single source of truth for the shot type dropdown - each entry
    # maps to the product (base) type assigned to the created instance.
    SHOT_TYPES = {
        "layout": {
            "product_type": "layout",
            "product_base_type": "layout",
            "label": "Layout",
        },
        "animation": {
            "product_type": "animation",
            "product_base_type": "animation",
            "label": "Animation",
        },
        "fx": {
            "product_type": "fx",
            "product_base_type": "fx",
            "label": "FX",
        },
        "lighting": {
            "product_type": "lighting",
            "product_base_type": "lighting",
            "label": "Lighting",
        },
        "render": {
            "product_type": "render",
            "product_base_type": "render",
            "label": "Rendering",
        },
    }

    def create(self, product_name, instance_data, pre_create_data):
        shot_type = pre_create_data.get("shot_type", "layout")
        type_info = self.SHOT_TYPES[shot_type]

        # The Create dialog computes `product_name` from this creator's
        # static class-level `product_type` (the row shown in the Create
        # list is not aware of the "Shot Type" dropdown), so it needs to
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

        # The Create dialog also passes the static class-level type in
        # `instance_data["productType"]`/`["productBaseType"]`, and
        # `HoudiniCreator.create()` prefers that over `self.product_type`
        # - overwrite it with the actually selected type, otherwise e.g.
        # an Animation publishes as product type "layout".
        instance_data["productType"] = type_info["product_type"]
        instance_data["productBaseType"] = type_info["product_base_type"]

        # `HoudiniCreator.create()` still falls back to `self.
        # product_type`/`self.product_base_type` (e.g. it always passes
        # `product_base_type=self.product_base_type`), so temporarily point
        # them at the selected type for the duration of the call too.
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
            "defaultprim": "$SQ",
            "savestyle": "flattenstage",
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
            EnumDef("render_target",
                    items=render_target_items,
                    label="Render target",
                    default=self.render_target)
        ]

    def get_pre_create_attr_defs(self):
        shot_type_items = {
            key: type_info["label"]
            for key, type_info in self.SHOT_TYPES.items()
        }

        attrs = super().get_pre_create_attr_defs()
        attrs += [
            EnumDef("shot_type",
                    items=shot_type_items,
                    label="Shot Type",
                    default="layout"),
        ]

        return attrs + self.get_instance_attr_defs()
