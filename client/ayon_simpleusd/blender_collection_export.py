# -*- coding: utf-8 -*-
"""Helpers for Blender's Collection Exporters (Blender 4.2+), shared by the
Blender "SimpleUSD Model (via Houdini)" creator and publish plugins.

The instance collection created by the creator holds the artist's
structure collection as its only child; that child carries the Alembic
Collection Exporter whose settings are used for the publish.
"""
import bpy

from ayon_blender.api.plugin import create_blender_context

ALEMBIC_FILE_HANDLER = "IO_FH_alembic"
# `export_properties` of a Collection Exporter are the properties of the
# operator the file handler exports with.
ALEMBIC_EXPORT_OPERATOR = "WM_OT_alembic_export"


def _collection_context(collection):
    """Context override running the collection exporter operators on
    `collection`.

    The Publisher runs outside Blender's own event handling, where
    bpy.context has no window. The Alembic export operator's poll needs
    one, so without it the nested export is silently skipped and
    `exporter_export` returns PASS_THROUGH - borrow the window/area of the
    UI like ayon-blender's own extractors do.
    """
    override = {
        key: value
        for key, value in create_blender_context().items()
        if key in {"window", "screen", "area", "region"}
    }
    override["collection"] = collection
    return override


def find_alembic_exporter(collection):
    """Return (index, exporter) of the collection's first Alembic exporter,
    or (None, None) if it has none."""
    for index, exporter in enumerate(collection.exporters):
        identifier = exporter.export_properties.bl_rna.identifier
        if identifier == ALEMBIC_EXPORT_OPERATOR:
            return index, exporter
    return None, None


def add_alembic_exporter(collection):
    """Add an Alembic Collection Exporter with default settings."""
    with bpy.context.temp_override(**_collection_context(collection)):
        bpy.ops.collection.exporter_add(name=ALEMBIC_FILE_HANDLER)
    return find_alembic_exporter(collection)


def export_collection(collection, index, filepath):
    """Run the collection's exporter at `index`, writing to `filepath`
    instead of the exporter's own path for this one export."""
    exporter = collection.exporters[index]
    original_filepath = exporter.export_properties.filepath
    exporter.export_properties.filepath = filepath
    try:
        with bpy.context.temp_override(**_collection_context(collection)):
            result = bpy.ops.collection.exporter_export(index=index)
    finally:
        exporter.export_properties.filepath = original_filepath
    return result
