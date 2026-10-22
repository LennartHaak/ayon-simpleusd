# -*- coding: utf-8 -*-
"""Creator publishing a Blender collection as a SimpleUSD model.

Replaces the manual round trip of exporting the structure collection with
its Alembic Collection Exporter, loading it in Houdini through the
SimpleUSD Alembic Loader HDA and publishing that with the SimpleUSD Asset
(Model) creator. The publish exports the Alembic, converts it in a
headless Houdini (see ayon_simpleusd/houdini_conversion.py) and integrates
the resulting USD from Blender as the same "model" product a Houdini
publish would create.
"""
from ayon_core.lib import BoolDef
from ayon_core.pipeline.create import CreatorError
from ayon_blender.api import plugin, lib

from ayon_simpleusd.blender_collection_export import (
    find_alembic_exporter,
    add_alembic_exporter,
)


class CreateSimpleUSDModel(plugin.BlenderCreator):
    """Publish a collection as a SimpleUSD model via headless Houdini."""

    identifier = "io.ayon.creators.blender.simpleusd.model"
    label = "SimpleUSD Model"
    description = __doc__
    product_base_type = "model"
    product_type = product_base_type
    icon = "cubes"

    # Same loader group as the Houdini SimpleUSD Asset creator.
    product_group = "SimpleUSD Layers"

    def create(self, product_name, instance_data, pre_create_data):
        selected_collections = lib.get_selected_collections()
        if len(selected_collections) != 1:
            raise CreatorError(
                "Select exactly one collection in the Outliner - the "
                "structure collection to publish.")
        source_collection = selected_collections[0]

        instance_data["productGroup"] = self.product_group
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        creator_attributes["update_root_asset"] = pre_create_data.get(
            "update_root_asset", True)

        # The USD comes from Houdini - switch off ayon-blender's own
        # "model" extractors, plus validators that don't fit a structure
        # hierarchy (its empties carry transforms, UV map names are
        # irrelevant for USD). All optional, so they can be re-enabled.
        publish_attributes = instance_data.setdefault(
            "publish_attributes", dict())
        publish_attributes.update({
            "ExtractBlend": {"active": False},
            "ExtractFBX": {"active": False},
            "ExtractModelUSD": {"active": False},
            "ExtractModelABC": {"active": False},
            "ValidateTransformZero": {"active": False},
            "ValidateModelMeshUvMap1": {"active": False},
            "IntegrateHeroVersion": {"active": False},
        })

        instance_node = super().create(
            product_name, instance_data, pre_create_data)
        instance_node.children.link(source_collection)

        _, exporter = find_alembic_exporter(source_collection)
        if exporter is None:
            add_alembic_exporter(source_collection)
            self.log.info(
                "Added an Alembic Collection Exporter to '%s'.",
                source_collection.name)

        return instance_node

    def get_publish_families(self):
        return [self.product_base_type, "simpleusdHoudiniModel"]

    def get_instance_attr_defs(self):
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
        ]

    def get_pre_create_attr_defs(self):
        # No "Use selection" toggle - the selected collection is required.
        return self.get_instance_attr_defs()
