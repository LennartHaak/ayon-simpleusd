# -*- coding: utf-8 -*-
"""Validate the structure collection of a "SimpleUSD Model (via Houdini)"
instance has an Alembic Collection Exporter to publish with."""
import inspect

import bpy
import pyblish.api

from ayon_core.pipeline.publish import (
    PublishValidationError,
    RepairAction,
)
from ayon_blender.api import plugin

from ayon_simpleusd.blender_collection_export import (
    find_alembic_exporter,
    add_alembic_exporter,
)


def get_source_collection(instance):
    """Return the structure collection linked under the instance
    collection, raising PublishValidationError if there isn't exactly
    one."""
    instance_node = instance.data["transientData"]["instance_node"]
    if not isinstance(instance_node, bpy.types.Collection):
        raise PublishValidationError(
            "Instance node '{}' is not a collection.".format(
                instance_node.name))
    children = list(instance_node.children)
    if len(children) != 1:
        raise PublishValidationError(
            "Instance '{}' must contain exactly one collection (the "
            "structure collection to publish), found {}.".format(
                instance_node.name, len(children)),
            description=ValidateSimpleUSDCollectionExporter.get_description(),
        )
    return children[0]


class ValidateSimpleUSDCollectionExporter(plugin.BlenderInstancePlugin):
    """Structure collection has an Alembic Collection Exporter."""

    order = pyblish.api.ValidatorOrder
    hosts = ["blender"]
    families = ["simpleusdHoudiniModel"]
    label = "SimpleUSD Collection Exporter"
    actions = [RepairAction]

    def process(self, instance):
        collection = get_source_collection(instance)
        _, exporter = find_alembic_exporter(collection)
        if exporter is None:
            raise PublishValidationError(
                "Collection '{}' has no Alembic Collection Exporter.".format(
                    collection.name),
                description=self.get_description(),
            )

    @classmethod
    def repair(cls, instance):
        collection = get_source_collection(instance)
        _, exporter = find_alembic_exporter(collection)
        if exporter is None:
            add_alembic_exporter(collection)

    @staticmethod
    def get_description():
        return inspect.cleandoc("""
            ### Alembic Collection Exporter

            The structure collection is exported with its own Alembic
            Collection Exporter (Collection Properties > Exporters), so
            its export settings are used for the publish - only the file
            path is replaced by the publish staging path.

            The instance must hold exactly one collection. Use **Repair**
            to add an Alembic exporter with default settings.
        """)
