# -*- coding: utf-8 -*-
"""Write a short publish note into the AYON version comment when a Simple
USD asset part (model/look/fx/groom) or root asset is published.

AYON's ShotGrid sync runs server-side off AYON entities, so the note has
to be part of the AYON version itself to reach the ShotGrid Version.
Runs right after ayon-core's CollectComment (ExtractorOrder - 0.49),
which resolves the artist's own comment, and before IntegrateAsset,
which writes instance.data["comment"] into the version it creates - so
the note is there from the moment the version exists.

Deliberately plain pyblish.api.InstancePlugin (no ayon_houdini/hou import)
since nothing here needs a live Houdini session - everything runs purely
off pyblish instance data collected earlier in the publish, so it also
covers the Blender "SimpleUSD Model (via Houdini)" creator.
"""
import pyblish.api

PART_PRODUCT_TYPES = {"model", "look", "fx", "groom"}
# "fx" is also used as a product type by the unrelated SimpleUSD Shot
# creator (create_usd_shot.py) - gate on the actual creator too so a
# shot FX publish doesn't get swept into this asset-part-only pathway.
ASSET_CREATOR_IDENTIFIERS = {
    "io.ayon.creators.houdini.simpleusd.asset",
    # Blender model converted through headless Houdini.
    "io.ayon.creators.blender.simpleusd.model",
}


class CollectSimpleUSDVersionComment(pyblish.api.InstancePlugin):
    """Append a part/root publish note (and the publisher's name) to the
    AYON version comment."""

    label = "Collect Simple USD Version Comment"
    # After CollectComment (ExtractorOrder - 0.49), before IntegrateAsset.
    order = pyblish.api.ExtractorOrder - 0.48

    def process(self, instance):
        product_type = instance.data.get("productType")
        if product_type == "root":
            note = self._get_root_note(instance)
        elif (
            product_type in PART_PRODUCT_TYPES
            and instance.data.get("creator_identifier")
            in ASSET_CREATOR_IDENTIFIERS
        ):
            note = self._get_part_note(instance)
        else:
            return

        from ayon_simpleusd.publish_comment import (
            append_comment, get_publisher_name)

        publisher = get_publisher_name(instance.context.data.get("user"))
        if publisher:
            note += " Published by {}.".format(publisher)

        append_comment(instance, note)
        self.log.debug(
            "Version comment for '%s': %s",
            instance.data.get("productName"), instance.data["comment"],
        )

    def _get_part_note(self, instance):
        note_lines = [
            "Published {} '{}' v{:03d}.".format(
                instance.data["productType"],
                instance.data["productName"],
                instance.data["version"],
            )
        ]

        merge_info = instance.data.get("simpleusdRootMerge")
        if merge_info:
            note_lines.append(
                "Merged into root '{}' v{:03d}.".format(
                    merge_info["rootProductName"],
                    merge_info["rootVersion"],
                )
            )
        else:
            creator_attrs = instance.data.get("creator_attributes", {})
            if not creator_attrs.get("update_root_asset", True):
                note_lines.append(
                    "Root Asset update was disabled for this publish.")
            else:
                note_lines.append("Not merged into root asset.")

        return " ".join(note_lines)

    def _get_root_note(self, instance):
        version = instance.data["version"]
        contributions = instance.data.get("simpleusdRootContributions")
        if not contributions:
            return "Root asset published: v{:03d}.".format(version)

        # Already-published contributions resolved from the server can have
        # an unknown version (None) - don't let formatting choke on it.
        parts = [
            "{} '{}' {} ({})".format(
                c["productType"], c["productName"],
                "v{:03d}".format(c["version"])
                if c["version"] is not None else "v???",
                c["arc"],
            )
            for c in contributions
        ]
        note = "Root asset updated to v{:03d}. Includes: {}.".format(
            version, "; ".join(parts))

        source_instances = instance.data.get("source_instances") or []
        if source_instances:
            note += " Triggered by: {}.".format(", ".join(
                i.data["productName"] for i in source_instances))
        return note
