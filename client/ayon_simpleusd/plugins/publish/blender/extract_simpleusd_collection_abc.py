# -*- coding: utf-8 -*-
"""Export the structure collection of a "SimpleUSD Model (via Houdini)"
instance with its own Alembic Collection Exporter."""
import os

import pyblish.api

from ayon_core.pipeline.publish import KnownPublishError
from ayon_blender.api import plugin

from ayon_simpleusd.blender_collection_export import (
    find_alembic_exporter,
    export_collection,
)


class ExtractSimpleUSDCollectionAbc(plugin.BlenderExtractor):
    """Export the structure collection as Alembic for Houdini."""

    label = "Extract SimpleUSD Collection Alembic"
    order = pyblish.api.ExtractorOrder
    hosts = ["blender"]
    families = ["simpleusdHoudiniModel"]

    def process(self, instance):
        instance_node = instance.data["transientData"]["instance_node"]
        # Exactly one child is guaranteed by
        # ValidateSimpleUSDCollectionExporter.
        collection = instance_node.children[0]
        index, _ = find_alembic_exporter(collection)
        if index is None:
            raise KnownPublishError(
                "Collection '{}' has no Alembic Collection Exporter.".format(
                    collection.name))

        staging_dir = self.staging_dir(instance)
        folder_name = instance.data["folderEntity"]["name"]
        filename = "{}_{}.abc".format(
            folder_name, instance.data["productName"])
        filepath = os.path.join(staging_dir, filename)

        result = export_collection(collection, index, filepath)
        if "FINISHED" not in result or not os.path.isfile(filepath):
            raise KnownPublishError(
                "Alembic export of collection '{}' failed ({}).".format(
                    collection.name, ", ".join(result)))

        instance.data.setdefault("representations", []).append({
            "name": "abc",
            "ext": "abc",
            "files": filename,
            "stagingDir": staging_dir,
        })
        instance.data["simpleusdAbcPath"] = filepath

        self.log.info(
            "Exported collection '%s' to %s", collection.name, filepath)
