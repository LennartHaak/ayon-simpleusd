# -*- coding: utf-8 -*-
"""Collector building the metadata needed to assemble a single, combined
comparison review video out of every "Simple USD Render" variant in the
current Houdini scene.

Each variant gets published/rendered independently on the farm (its own
render job, its own publish job), but they all share one render folder
(see collect_simpleusd_render_paths.py) with deterministic, non-
overlapping filenames. Rather than trying to build the comparison video
as its own farm job (which would require teaching RoyalRender's simple,
order-based job-dependency graph to wait on an arbitrary set of sibling
jobs), the actual video gets built later, on whichever variant's own farm
republish pass happens to run last (see
build_simpleusd_comparison_review.py in ayon-royalrender's farm-side
plugins). This collector's only job is to compute, once per Houdini
publish session, the list of included variants (and their resolved
naming/frame-range/resolution) and stash an identical copy of it on
every "Simple USD Render" instance, so it can ride along inside each
variant's own farm publish-job metadata JSON independently.
"""
import hou
import pyblish.api

from ayon_houdini.api import lib, plugin


class CollectSimpleUSDComparisonMetadata(plugin.HoudiniContextPlugin):
    """Collect metadata for the combined Simple USD Render comparison
    review video."""

    label = "Collect Simple USD Comparison Metadata"
    # After CollectSimpleUSDRenderPaths has stashed naming info on every
    # instance, before RoyalRender job-creation plugins run.
    order = pyblish.api.CollectorOrder + 0.91

    DEFAULT_RESOLUTION = (1920, 1080)

    def process(self, context):
        variants = []
        included_instances = []
        for instance in context:
            if "usdrenderPackage" not in instance.data.get("families", []):
                continue
            creator_attributes = instance.data.get("creator_attributes", {})
            if not creator_attributes.get("review", True):
                continue
            if "simpleusdBaseName" not in instance.data:
                # CollectSimpleUSDRenderPaths didn't run for this instance
                # (e.g. not a farm-targeted render), nothing to compare.
                continue

            variant = instance.data.get("variant", instance.data["name"])
            variants.append({
                "variant": variant,
                "baseName": instance.data["simpleusdBaseName"],
                "renderDir": instance.data["simpleusdRenderDir"],
                "ext": instance.data["simpleusdExt"],
                "frameStart": instance.data["frameStartHandle"],
                "frameEnd": instance.data["frameEndHandle"],
            })
            included_instances.append(instance)

        if not variants:
            return

        width, height = self._get_resolution(context)
        sequence, shot = self._get_sequence_shot(context)
        version_str = "v{:03d}".format(included_instances[0].data["version"])
        comparison_data = {
            "variants": variants,
            "resolutionWidth": width,
            "resolutionHeight": height,
            "fps": hou.fps(),
            "sequence": sequence,
            "shot": shot,
            "versionStr": version_str,
        }

        for instance in included_instances:
            instance.data["comparisonReview"] = comparison_data

        self.log.debug(
            "Collected comparison review metadata for %d variant(s): %s",
            len(variants), comparison_data)

    def _get_sequence_shot(self, context):
        folder_path = context.data["folderPath"]
        parts = folder_path.strip("/").split("/")
        shot = parts[-1]
        sequence = parts[-2] if len(parts) >= 2 else ""
        return sequence, shot

    def _get_resolution(self, context):
        for entity in [
            context.data.get("taskEntity"),
            context.data.get("folderEntity"),
        ]:
            if not entity:
                continue
            try:
                resolution = lib.get_resolution_from_entity(entity)
            except ValueError:
                continue
            if resolution:
                return resolution
        return self.DEFAULT_RESOLUTION
