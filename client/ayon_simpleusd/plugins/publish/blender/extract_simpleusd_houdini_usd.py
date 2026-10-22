# -*- coding: utf-8 -*-
"""Convert the exported Alembic to the SimpleUSD model layer in a headless
Houdini (see ayon_simpleusd/houdini_conversion.py)."""
import os

import pyblish.api

from ayon_core.pipeline.publish import PublishError
from ayon_blender.api import plugin

from ayon_simpleusd.houdini_conversion import (
    HoudiniConversionError,
    run_abc_to_usd,
)

# Lines of hython output shown in the Publisher's error details.
LOG_TAIL_LINES = 40


class ExtractSimpleUSDHoudiniUsd(plugin.BlenderExtractor):
    """Run the Alembic through the SimpleUSD Alembic Loader HDA in a
    headless Houdini and write the USD model layer."""

    label = "Extract SimpleUSD Model USD (Houdini)"
    # After ExtractSimpleUSDCollectionAbc.
    order = pyblish.api.ExtractorOrder + 0.1
    hosts = ["blender"]
    families = ["simpleusdHoudiniModel"]

    def process(self, instance):
        context = instance.context
        settings = context.data["project_settings"].get(
            "simple-usd", {}).get("blender_houdini_model", {})

        abc_path = instance.data["simpleusdAbcPath"]
        staging_dir = self.staging_dir(instance)
        filename = "{}.usd".format(instance.data["productName"])
        usd_path = os.path.join(staging_dir, filename)
        debug_hip_path = os.path.join(
            staging_dir, "{}_conversion.hipnc".format(
                instance.data["productName"]))

        try:
            run_abc_to_usd(
                context.data["projectName"],
                instance.data["folderPath"],
                instance.data.get("task"),
                abc_path,
                usd_path,
                debug_hip_path,
                app_name=settings.get("houdini_app") or None,
                timeout=settings.get("timeout", 600),
                log=self.log,
            )
        except HoudiniConversionError as exc:
            detail = "\n".join(exc.output.splitlines()[-LOG_TAIL_LINES:])
            if os.path.isfile(debug_hip_path):
                detail += "\n\nDebug scene: {}".format(debug_hip_path)
            raise PublishError(
                str(exc),
                title="Houdini conversion failed",
                description=(
                    "The Alembic could not be converted to USD in "
                    "headless Houdini. See the details for the hython "
                    "log; if a debug scene was saved, open it in "
                    "Houdini to inspect the SimpleUSD Alembic Loader."
                ),
                detail=detail,
            )

        instance.data.setdefault("representations", []).append({
            "name": "usd",
            "ext": "usd",
            "files": filename,
            "stagingDir": staging_dir,
        })
        self.log.info("Converted %s -> %s", abc_path, usd_path)
