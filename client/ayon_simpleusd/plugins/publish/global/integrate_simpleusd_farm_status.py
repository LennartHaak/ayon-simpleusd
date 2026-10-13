# -*- coding: utf-8 -*-
"""Set the linked AYON task's status once a Simple USD Render instance
has actually been submitted to the render farm.

`instance.data["farm"]` is set upstream by ayon-houdini's
CollectFarmInstances (CollectorOrder - 0.49) for every render_target
that results in a farm job ("farm", "farm_split",
"local_export_farm_render") - "local"/"local_no_render" leave it False.
Running at IntegratorOrder + 0.5 on targets=["local"] means this only
ever fires after ayon-royalrender's SubmitJobsToRoyalRender
(IntegratorOrder + 0.3) has already submitted successfully - it raises
and halts the whole publish on failure, so reaching this plugin is
itself confirmation the submission succeeded. targets=["local"] also
keeps this from re-firing during the deferred farm-side republish pass
(pyblish target "farm"), which rebuilds the render as a brand-new,
family-less-"usdrenderPackage" instance anyway (see
integrate_simpleusd_ayon_review_status.py's docstring for the full
two-pass explanation) - this plugin would never match it regardless.

Setting this status is an artist opt-in (the "Set Farm Status" creator
attribute, default True) rather than fully automatic - it doesn't make
sense to flag short renders, only long ones worth telegraphing as
"on the farm" to the rest of the team. Once the farm job actually
finishes, build_simpleusd_comparison_review.py is responsible for
moving the task on to the configured review status - not this plugin,
and not integrate_simpleusd_ayon_review_status.py (which is restricted
away from render instances entirely; see its own docstring).
"""
import ayon_api
import pyblish.api


class IntegrateSimpleUSDFarmStatus(pyblish.api.InstancePlugin):
    """Flip the linked task's AYON status once this render instance has
    been submitted to the farm."""

    label = "Integrate Simple USD Farm Status"
    order = pyblish.api.IntegratorOrder + 0.5
    targets = ["local"]
    families = ["usdrenderPackage"]

    def process(self, instance):
        if not instance.data.get("farm"):
            return

        creator_attrs = instance.data.get("creator_attributes", {})
        if not creator_attrs.get("set_farm_status", True):
            return

        settings = instance.context.data["project_settings"].get(
            "simple-usd", {})
        farm_settings = settings.get("farm_status", {})
        if not farm_settings.get("enabled", True):
            return
        status_name = farm_settings.get("status_name")
        if not status_name:
            return

        task_entity = instance.data.get("taskEntity")
        task_id = (task_entity or {}).get("id")
        if not task_id:
            self.log.debug(
                "No linked task - skipping farm status update for "
                "'%s'.", instance.data.get("productName"),
            )
            return

        project_name = instance.context.data["projectName"]
        try:
            ayon_api.update_task(project_name, task_id, status=status_name)
        except Exception:
            self.log.error(
                "Failed to set farm status for '%s'.",
                instance.data.get("productName"), exc_info=True,
            )
        else:
            self.log.info(
                "Set task status to '%s' for '%s'.",
                status_name, instance.data.get("productName"),
            )
