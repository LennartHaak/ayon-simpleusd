# -*- coding: utf-8 -*-
"""Collectors that automatically republish an asset's "root" USD product
whenever a model/look/fx/groom "asset part" is published, so root always
references the latest published version of every part.

Split into two ContextPlugins around ayon-core's CollectAnatomyInstanceData
(CollectorOrder + 0.49):

  Phase 1 (CollectSimpleUSDRootAutoUpdateInstance, CollectorOrder + 0.3):
  detect triggering instances, dedupe per asset, synthesize a bare
  pyblish.api.Instance for product_type "root" with no "instance_node" -
  mirroring ayon-core's own CollectUSDLayerContributions bootstrap-instance
  pattern (see ayon_core/plugins/publish/extract_usd_layer_contributions.py,
  get_or_create_instance). Runs BEFORE CollectAnatomyInstanceData so the
  generic collector resolves this instance's version/anatomyData/staging
  the same way it does for every other instance in the context, for free.

  Phase 2 (CollectSimpleUSDRootAutoUpdateArcs, CollectorOrder + 0.5): now
  that every instance (including sibling model/look/fx/groom instances and
  our synthetic root instance) has anatomyData/version resolved, figure out
  the actual composition-arc source paths and stash them on the root
  instance for the extractor.
"""
import ayon_api
import pyblish.api

from ayon_core.pipeline.create import get_product_name
from ayon_core.pipeline.publish.lib import get_instance_expected_output_path
from ayon_core.pipeline.load.utils import get_representation_path_by_names

from ayon_houdini.api import plugin

TRIGGER_PRODUCT_TYPES = {"model", "look", "fx", "groom"}


class CollectSimpleUSDRootAutoUpdateInstance(plugin.HoudiniContextPlugin):
    """Synthesize a "root" instance when a model/look/fx/groom instance
    with "Update Root Asset" enabled is about to be published."""

    label = "Collect Simple USD Root Auto-Update"
    # Before CollectAnatomyInstanceData (CollectorOrder + 0.49) so it
    # resolves version/anatomyData for our synthetic instance too.
    order = pyblish.api.CollectorOrder + 0.3

    product_group = "SimpleUSD Layers"

    def process(self, context):
        triggers_by_asset = self._collect_triggers(context)
        if not triggers_by_asset:
            return

        project_name = context.data["projectName"]
        settings = context.data["project_settings"].get(
            "simple-usd", {}).get("root_asset", {})
        # Root always belongs to this dedicated task on the asset,
        # regardless of which task the triggering part was published
        # under (also affects the work/publish folder root's own files
        # land in, via anatomy templates keyed off the task name).
        task_name = settings.get("task_name", "root")
        # Variant used only the very first time an asset gets a root
        # product auto-created (no existing root product to inherit the
        # name from).
        variant = settings.get("default_variant", "Main")

        for folder_path, trigger_instances in triggers_by_asset.items():
            self._create_root_instance(
                context, project_name, folder_path, task_name, variant,
                trigger_instances,
            )

    def _collect_triggers(self, context):
        """Group active, toggle-enabled model/look/fx/groom instances by
        folderPath - regardless of which task each one was published
        under, since root always targets its own dedicated task
        (root_asset.task_name)."""
        triggers = {}
        for instance in context:
            if not instance.data.get("publish", True):
                continue
            product_type = instance.data.get("productType")
            if product_type not in TRIGGER_PRODUCT_TYPES:
                continue
            creator_attrs = instance.data.get("creator_attributes", {})
            # Default True: "on by default" even for instances created
            # before this toggle existed.
            if not creator_attrs.get("update_root_asset", True):
                continue

            folder_path = instance.data["folderPath"]
            triggers.setdefault(folder_path, []).append(instance)
        return triggers

    def _create_root_instance(
        self, context, project_name, folder_path, task_name, variant,
        trigger_instances,
    ):
        folder_entity = ayon_api.get_folder_by_path(
            project_name, folder_path
        )
        if not folder_entity:
            self.log.warning(
                "Could not resolve folder entity for '%s' - skipping "
                "automatic root update.", folder_path
            )
            return

        task_entity = ayon_api.get_task_by_name(
            project_name, folder_entity["id"], task_name
        )
        if not task_entity:
            self.log.warning(
                "Folder '%s' has no '%s' task - automatic root update "
                "will publish without a resolved task context.",
                folder_path, task_name,
            )

        # Reuse the *existing* root product's exact name if there is one,
        # so this always versions up the SAME product a manual "SimpleUSD
        # Root Asset" publish would (and vice-versa) - never creates a
        # second, parallel root product.
        root_products = list(ayon_api.get_products(
            project_name,
            folder_ids=[folder_entity["id"]],
            product_types=["root"],
        ))
        if root_products:
            if len(root_products) > 1:
                self.log.warning(
                    "Folder '%s' has more than one 'root' product (%s) - "
                    "using '%s'. Automatic root update only manages a "
                    "single root product per asset.", folder_path,
                    [p["name"] for p in root_products],
                    root_products[0]["name"],
                )
            product_name = root_products[0]["name"]
        else:
            product_name = get_product_name(
                project_name,
                folder_entity=folder_entity,
                task_entity=task_entity,
                product_base_type="root",
                product_type="root",
                host_name="houdini",
                variant=variant,
                project_settings=context.data["project_settings"],
            )

        new_instance = context.create_instance(name=product_name)
        new_instance.data.update({
            "folderPath": folder_path,
            "folderEntity": folder_entity,
            "task": task_name,
            "productName": product_name,
            "productType": "root",
            "productBaseType": "root",
            "family": "root",
            "families": ["root", "simpleusdAutoRoot"],
            "variant": variant,
            "productGroup": self.product_group,
            "label": "{} ({})".format(product_name, folder_path),
            "comment": "Automated root update triggered by: {}".format(
                ", ".join(i.data["productName"] for i in trigger_instances)
            ),
            # Always just increment from root's own last version - do not
            # try to follow whatever version number the workfile is on.
            "followWorkfileVersion": False,
            "active": True,
            "publish": True,
            # Marker consumed by CollectSimpleUSDRootAutoUpdateArcs and
            # ExtractSimpleUSDRootAutoUpdate.
            "simpleusdAutoRootUpdate": True,
            "source_instances": trigger_instances,
            # Mirror the manual SimpleUSD Root Asset creator's own
            # defensive publish_attributes so this behaves identically to
            # a manually authored root instance downstream.
            "publish_attributes": {
                "CollectUSDLayerContributions": {
                    "contribution_enabled": False},
                "ValidateUSDAssetContributionDefaultPrim": {
                    "active": False},
                "ValidateInstanceInContextHoudini": {"active": False},
                "IntegrateHeroVersion": {"active": False},
            },
        })
        if task_entity:
            new_instance.data["taskEntity"] = task_entity
        for trigger_instance in trigger_instances:
            new_instance.append(trigger_instance.id)

        self.log.info(
            "Synthesized automatic root update instance '%s' for '%s' "
            "(triggered by: %s)", product_name, folder_path,
            [i.data["productName"] for i in trigger_instances],
        )


class CollectSimpleUSDRootAutoUpdateArcs(plugin.HoudiniContextPlugin):
    """Resolve the model/look/fx/groom source paths for automatic root
    update instances, now that CollectAnatomyInstanceData has resolved
    version/anatomyData on every instance in the context (including the
    synthetic root instance and its trigger siblings)."""

    label = "Collect Simple USD Root Auto-Update Arcs"
    # After CollectAnatomyInstanceData (CollectorOrder + 0.49).
    order = pyblish.api.CollectorOrder + 0.5

    def process(self, context):
        for instance in context:
            if not instance.data.get("simpleusdAutoRootUpdate"):
                continue
            self._resolve_arcs(context, instance)

    def _resolve_arcs(self, context, instance):
        project_name = context.data["projectName"]
        anatomy = context.data.get("anatomy")
        folder_path = instance.data["folderPath"]

        # Single unified list of contributions, built up below, each a
        # dict of productName/productType/version/path/arc/source_instance.
        # "source_instance" is set only for contributions coming from this
        # session's own triggering instances - used afterwards to stamp
        # "merged into root" info back onto them for the Kitsu status
        # plugin (see integrate_simpleusd_kitsu_status.py).
        contributions = []
        covered_product_names = set()

        # 1) Session-sibling instances (being published *right now*) win
        #    over whatever is already on the server for the same product,
        #    since their integrated path is knowable in advance from their
        #    own resolved anatomyData/version - no race against
        #    not-yet-integrated data.
        for source_instance in instance.data.get("source_instances", []):
            product_type = source_instance.data.get("productType")
            if product_type not in TRIGGER_PRODUCT_TYPES:
                continue
            path = self._get_session_path(source_instance)
            if path is None:
                self.log.warning(
                    "Could not resolve in-session output path for '%s' - "
                    "skipping its contribution to root.",
                    source_instance.data["productName"],
                )
                continue
            product_name = source_instance.data["productName"]
            contributions.append({
                "productName": product_name,
                "productType": product_type,
                "version": source_instance.data["version"],
                "path": path,
                "arc": "payload" if product_type == "model" else
                       "reference",
                "source_instance": source_instance,
            })
            covered_product_names.add(product_name)

        # 2) Everything else already published for this asset, queried
        #    from AYON - latest version only, per product.
        folder_entity = instance.data.get("folderEntity") or (
            ayon_api.get_folder_by_path(project_name, folder_path)
        )
        if folder_entity:
            # Not filtering by `product_types` server-side: AYON's GraphQL
            # products query validates each filter value against a "name"
            # regex requiring >= 3 characters, which rejects short but
            # valid product types like "fx". Filter client-side instead.
            products = ayon_api.get_products(
                project_name,
                folder_ids=[folder_entity["id"]],
            )
            relevant_products = [
                product for product in products
                if product["productType"] in TRIGGER_PRODUCT_TYPES
                and product["name"] not in covered_product_names
            ]
            last_versions = {}
            if relevant_products:
                last_versions = ayon_api.get_last_versions(
                    project_name,
                    {product["id"] for product in relevant_products},
                    fields={"version"},
                )
            for product in relevant_products:
                path = get_representation_path_by_names(
                    project_name,
                    folder_path,
                    product["name"],
                    "latest",
                    "usd",
                    anatomy=anatomy,
                )
                if path is None:
                    self.log.warning(
                        "Could not resolve a published 'usd' "
                        "representation for product '%s' - skipping its "
                        "contribution to root.", product["name"],
                    )
                    continue
                last_version_entity = last_versions.get(product["id"])
                version = (
                    last_version_entity["version"]
                    if last_version_entity else None
                )
                product_type = product["productType"]
                contributions.append({
                    "productName": product["name"],
                    "productType": product_type,
                    "version": version,
                    "path": str(path).replace("\\", "/"),
                    "arc": "payload" if product_type == "model" else
                           "reference",
                    "source_instance": None,
                })

        instance.data["simpleusdRootPayloadPaths"] = [
            c["path"] for c in contributions if c["arc"] == "payload"
        ]
        instance.data["simpleusdRootReferencePaths"] = [
            c["path"] for c in contributions if c["arc"] == "reference"
        ]
        instance.data["simpleusdRootContributions"] = [
            {
                "productName": c["productName"],
                "productType": c["productType"],
                "version": c["version"],
                "arc": c["arc"],
            }
            for c in contributions
        ]

        # Stamp "merged into root" info back onto this session's own
        # triggering instances, consumed by
        # IntegrateSimpleUSDPartKitsuStatus to report the merge outcome
        # in that instance's own Kitsu comment.
        for c in contributions:
            source_instance = c["source_instance"]
            if source_instance is None:
                continue
            source_instance.data["simpleusdRootMerge"] = {
                "rootProductName": instance.data["productName"],
                "rootVersion": instance.data["version"],
            }

        self.log.debug(
            "Resolved root arcs for '%s': payload=%s references=%s",
            instance.data["productName"],
            instance.data["simpleusdRootPayloadPaths"],
            instance.data["simpleusdRootReferencePaths"],
        )

    def _get_session_path(self, source_instance):
        try:
            path = get_instance_expected_output_path(
                source_instance, representation_name="usd", ext="usd"
            )
        except KeyError:
            return None
        return str(path).replace("\\", "/") if path else None
