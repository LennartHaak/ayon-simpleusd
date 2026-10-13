# -*- coding: utf-8 -*-
"""Move a Kitsu task to the configured review status with a comment when
a Simple USD asset part (model/look/fx/groom) or root asset is published.

ayon-kitsu's generic CollectKitsuFamily/IntegrateKitsuNote pipeline never
fires for these product types in this studio (see
strip_render_kitsu_family.py and build_simpleusd_comparison_review.py for
the full explanation of why the render pathway already has to bypass it
directly via gazu) - so these plugins do the same thing directly, using
the shared kitsu_lib helpers.

Deliberately plain pyblish.api.InstancePlugin (no ayon_houdini/hou import)
since nothing here needs a live Houdini session - both classes run purely
off pyblish instance data collected earlier in the publish.
"""
import pyblish.api

PART_PRODUCT_TYPES = {"model", "look", "fx", "groom"}


class IntegrateSimpleUSDPartKitsuStatus(pyblish.api.InstancePlugin):
    """Post a Kitsu status/comment for a published asset part, noting
    whether it was merged into the asset's root USD file."""

    label = "Integrate Simple USD Part Kitsu Status"
    # After standard integration, so `version` is final and the publish
    # actually succeeded before announcing it to Kitsu.
    order = pyblish.api.IntegratorOrder + 0.5

    def process(self, instance):
        if instance.data.get("productType") not in PART_PRODUCT_TYPES:
            return

        from ayon_simpleusd.kitsu_lib import (
            get_kitsu_task_id, is_kitsu_enabled, post_kitsu_status_comment)

        project_name = instance.context.data["projectName"]
        if not is_kitsu_enabled(project_name):
            return

        kitsu_id = get_kitsu_task_id(instance.data.get("taskEntity"))
        if not kitsu_id:
            self.log.debug(
                "No Kitsu task linked - skipping Kitsu status update for "
                "'%s'.", instance.data["productName"],
            )
            return

        comment_lines = [
            "Published {} '{}' v{:03d}.".format(
                instance.data["productType"],
                instance.data["productName"],
                instance.data["version"],
            )
        ]

        merge_info = instance.data.get("simpleusdRootMerge")
        if merge_info:
            comment_lines.append(
                "Merged into root '{}' v{:03d}.".format(
                    merge_info["rootProductName"],
                    merge_info["rootVersion"],
                )
            )
        else:
            creator_attrs = instance.data.get("creator_attributes", {})
            if not creator_attrs.get("update_root_asset", True):
                comment_lines.append(
                    "Root Asset update was disabled for this publish.")
            else:
                comment_lines.append("Not merged into root asset.")

        comment_text = " ".join(comment_lines)
        try:
            post_kitsu_status_comment(
                project_name, kitsu_id, comment_text, log=self.log)
        except Exception:
            self.log.error(
                "Failed to post Kitsu status update for '%s'.",
                instance.data["productName"], exc_info=True,
            )


class IntegrateSimpleUSDRootKitsuStatus(pyblish.api.InstancePlugin):
    """Post a Kitsu status/comment for a published root asset - a
    detailed per-part breakdown when auto-updated, or a generic version
    note for a manual root publish."""

    label = "Integrate Simple USD Root Kitsu Status"
    order = pyblish.api.IntegratorOrder + 0.5

    def process(self, instance):
        if instance.data.get("productType") != "root":
            return

        from ayon_simpleusd.kitsu_lib import (
            get_kitsu_task_id, is_kitsu_enabled, post_kitsu_status_comment)

        project_name = instance.context.data["projectName"]
        if not is_kitsu_enabled(project_name):
            return

        kitsu_id = get_kitsu_task_id(instance.data.get("taskEntity"))
        if not kitsu_id:
            self.log.debug(
                "No Kitsu task linked - skipping Kitsu status update for "
                "'%s'.", instance.data["productName"],
            )
            return

        version = instance.data["version"]
        contributions = instance.data.get("simpleusdRootContributions")
        if contributions:
            parts = [
                "{} '{}' v{:03d} ({})".format(
                    c["productType"], c["productName"], c["version"],
                    c["arc"],
                )
                for c in contributions
            ]
            comment_text = "Root asset updated to v{:03d}. Includes: {}.".format(
                version, "; ".join(parts))
        else:
            comment_text = "Root asset published: v{:03d}.".format(version)

        try:
            post_kitsu_status_comment(
                project_name, kitsu_id, comment_text, log=self.log)
        except Exception:
            self.log.error(
                "Failed to post Kitsu status update for '%s'.",
                instance.data["productName"], exc_info=True,
            )
