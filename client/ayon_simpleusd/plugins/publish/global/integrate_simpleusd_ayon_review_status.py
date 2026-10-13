# -*- coding: utf-8 -*-
"""Set the linked AYON task's status whenever a publish produces a
reviewable representation (tagged "review" or "webreview"), so AYON's
own ShotGrid sync (server-side, driven off AYON task status changes)
mirrors the status out to ShotGrid.

Deliberately host/product-type-agnostic - unlike
integrate_simpleusd_kitsu_status.py's model/look/fx/groom/root-specific
classes, this fires for *any* instance that actually published a
reviewable, mirroring how broadly ayon-kitsu's own
CollectKitsuFamily/IntegrateKitsuNote used to flip Kitsu status
(including workfile publishes that happened to carry a review-tagged
playblast/thumbnail, gated by the apply_to_workfile setting below).

A parallel, independent path - the existing Kitsu status plugins are
untouched.

Two deliberate exclusions, both found to cause this plugin to clobber
a status set elsewhere in the very same (or a related) publish:

- productType == "usdrenderPackage" is always skipped. Render task
  status is fully owned by integrate_simpleusd_farm_status.py
  (submission) and build_simpleusd_comparison_review.py (completion)
  instead. This matters because ayon-core's farm-side republish pass
  (CollectRenderedFiles, targets=["filesequence","farm"]) rebuilds the
  render as a brand-new instance via create_skeleton_instance() with
  families=["render","review"] (never "usdrenderPackage") once
  rendering finishes - without this exclusion (and the targets
  restriction below), this plugin would match that reconstructed
  instance and immediately overwrite the farm status that was set at
  submission time, no matter how the two plugins are ordered relative
  to each other (they're not even running in the same pyblish pass).
- targets = ["local"]: the farm-side republish pass above runs under
  pyblish target "farm", not "local" - restricting to "local" is a
  second, independent guard against the same race, and also means this
  plugin no longer needs to inspect every farm-side republish context
  at all.
- productType == "workfile" is skipped unless
  ayon_review_status.apply_to_workfile is enabled in settings (off by
  default) - the workfile instance publishes in the same local batch
  as everything else (including a farm render submission) and was
  observed to flip the task status on its own review-tagged
  thumbnail, independent of the render-specific exclusion above.
"""
import ayon_api
import pyblish.api

REVIEW_TAGS = {"review", "webreview"}
EXCLUDED_PRODUCT_TYPES = {"usdrenderPackage"}


class IntegrateSimpleUSDAyonReviewStatus(pyblish.api.InstancePlugin):
    """Flip the linked task's AYON status when this instance published
    a review/webreview-tagged representation."""

    label = "Integrate Simple USD AYON Review Status"
    # After standard integration, so `representations` reflects the
    # final published set (including anything IntegrateAYONReview/
    # ExtractReview added) and the publish actually succeeded.
    order = pyblish.api.IntegratorOrder + 0.5
    targets = ["local"]

    def process(self, instance):
        product_type = instance.data.get("productType")
        if product_type in EXCLUDED_PRODUCT_TYPES:
            return

        settings = instance.context.data["project_settings"].get(
            "simple-usd", {})
        review_settings = settings.get("ayon_review_status", {})

        if product_type == "workfile" and not review_settings.get(
                "apply_to_workfile", False):
            return

        representations = instance.data.get("representations") or []
        has_review = any(
            REVIEW_TAGS & set(repre.get("tags") or [])
            for repre in representations
        )
        if not has_review:
            return

        status_name = review_settings.get("status_name")
        if not status_name:
            return

        task_entity = instance.data.get("taskEntity")
        task_id = (task_entity or {}).get("id")
        if not task_id:
            self.log.debug(
                "No linked task - skipping AYON review status update "
                "for '%s'.", instance.data.get("productName"),
            )
            return

        project_name = instance.context.data["projectName"]
        try:
            ayon_api.update_task(project_name, task_id, status=status_name)
        except Exception:
            self.log.error(
                "Failed to set AYON review status for '%s'.",
                instance.data.get("productName"), exc_info=True,
            )
        else:
            self.log.info(
                "Set task status to '%s' for '%s'.",
                status_name, instance.data.get("productName"),
            )
