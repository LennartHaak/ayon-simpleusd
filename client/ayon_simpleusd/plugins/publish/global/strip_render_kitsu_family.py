# -*- coding: utf-8 -*-
"""Stops per-variant Simple USD Render packages from getting their own
Kitsu comment/status update.

ayon-kitsu's CollectKitsuFamily (CollectorOrder + 0.499) adds a "kitsu"
family to every "usdrenderPackage" instance per studio settings, which
then makes IntegrateKitsuNote/IntegrateKitsuReview post one comment per
variant every time a package finishes rendering. We only want a single,
combined message once the comparison review video is built (see
build_simpleusd_comparison_review.py, which posts that message directly
via gazu) - so strip "kitsu" back off these instances right after
CollectKitsuFamily runs, before any Integrate step sees it.
"""
import pyblish.api


class StripRenderKitsuFamily(pyblish.api.ContextPlugin):
    """Remove the "kitsu" family from Simple USD Render package
    instances so they don't each get their own Kitsu note."""

    label = "Strip Kitsu Family From Render Packages"
    # Right after CollectKitsuFamily (CollectorOrder + 0.499), before any
    # Integrate step.
    order = pyblish.api.CollectorOrder + 0.5
    targets = ["farm"]

    def process(self, context):
        for instance in context:
            families = instance.data.get("families", [])
            if "usdrenderPackage" not in families:
                continue
            if "kitsu" in families:
                families.remove("kitsu")
                self.log.debug(
                    "Removed 'kitsu' family from instance '%s'",
                    instance.data.get("name"),
                )
