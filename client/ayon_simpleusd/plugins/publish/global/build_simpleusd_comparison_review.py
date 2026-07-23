# -*- coding: utf-8 -*-
"""Builds the combined Simple USD Render comparison review video on the
RoyalRender farm control node, once every included variant's frames have
actually been rendered.

Deliberately a plain pyblish.api.ContextPlugin with no ayon_houdini/hou
import anywhere in this module: the RR farm republish pass runs as a
bare Python process on the render node, not inside Houdini - any plugin
discovered there that imports "hou" at module level (directly or via
ayon_houdini.api.plugin) fails to even import, and gets silently
skipped by pyblish's discovery. Same reason CreatePublishRoyalRenderJob
in ayon-royalrender is a plain pyblish plugin too.

Targets ["farm"] - confirmed via the actual farm log which instances
actually get built by ayon-core's own generic CollectRenderedFiles
(targets=["filesequence", "farm"]), reading AYON_PUBLISH_DATA and
rehydrating instances straight from the metadata JSON's "instances"
list. ayon-royalrender's own collect_sequences_from_job.py (targeting
"rr_control") turned out to never actually run in this deployment - the
farm log explicitly lists only "royalrender" and "farm" as active
targets, never "rr_control". Matching "farm" here (also used by
ayon-royalrender's own extract_frames_fix.py) is what actually gets
this plugin selected to run.

Every "Simple USD Render" variant in a scene renders as its own
independent farm job with its own dependent publish job, and AYON's
Integrate step *moves* each variant's rendered frames out of the shared
staging render folder as soon as that variant's own publish completes -
so by the time a slower sibling's own publish job runs, a faster
sibling's frames are typically already gone from the shared folder.
To make this robust regardless of relative timing, every republish pass
unconditionally snapshots *its own* still-present frames into a
persistent ".comparison_cache/<variant>/" folder before checking
completeness (its own frames are always still there in this same
session - Integrate hasn't run for this instance yet within it). Once
every expected variant's frames have appeared in the cache (across
however many of these passes it took), whichever pass observes that
builds the video and uploads it, guarded by a lock file so only one
of them actually does it.
"""
import os
import json
import math
import shutil

import pyblish.api


class BuildSimpleUSDComparisonReview(pyblish.api.ContextPlugin):
    """Assemble the combined comparison review video once all included
    Simple USD Render variants have finished rendering."""

    label = "Build Simple USD Comparison Review"
    order = pyblish.api.CollectorOrder + 0.05
    targets = ["farm"]

    def process(self, context):
        publish_data_paths = os.environ.get("AYON_PUBLISH_DATA")
        if not publish_data_paths:
            return

        for path in publish_data_paths.split(os.pathsep):
            if not path.endswith(".json"):
                continue
            self._process_metadata_file(context, path)

    def _process_metadata_file(self, context, path):
        with open(path, "r") as f:
            data = json.load(f)

        comparison = data.get("comparisonReview")
        if not comparison:
            return

        variants = comparison["variants"]
        for variant in variants:
            self._cache_variant_frames(variant)

        if not all(self._cache_complete(variant) for variant in variants):
            self.log.debug(
                "Not all comparison review variants have finished "
                "rendering yet - skipping for now."
            )
            return

        render_dir = variants[0]["renderDir"]
        lock_path = os.path.join(
            render_dir, ".comparison_{}.lock".format(comparison["versionStr"])
        )
        if not self._claim_lock(lock_path):
            self.log.debug(
                "Comparison review already built by another variant's "
                "publish job - skipping."
            )
            return

        output_path = os.path.join(
            render_dir,
            "{}_{}_comparison_{}.mp4".format(
                comparison["sequence"],
                comparison["shot"],
                comparison["versionStr"],
            ),
        )
        self._build_video(comparison, output_path)
        self._upload_to_kitsu(context, comparison, output_path)
        self._cleanup_cache(render_dir)

    # -- frame caching -----------------------------------------------

    def _cache_dir(self, variant):
        return os.path.join(
            variant["renderDir"], ".comparison_cache", variant["variant"]
        )

    def _frame_path(self, base_dir, variant, frame):
        return os.path.join(
            base_dir,
            "{}.{:04d}.{}".format(variant["baseName"], frame, variant["ext"]),
        )

    def _raw_frames_complete(self, variant):
        for frame in range(variant["frameStart"], variant["frameEnd"] + 1):
            path = self._frame_path(variant["renderDir"], variant, frame)
            if not os.path.isfile(path):
                return False
        return True

    def _cache_complete(self, variant):
        cache_dir = self._cache_dir(variant)
        for frame in range(variant["frameStart"], variant["frameEnd"] + 1):
            path = self._frame_path(cache_dir, variant, frame)
            if not os.path.isfile(path):
                return False
        return True

    def _cache_variant_frames(self, variant):
        # Already cached (by this pass or an earlier one) - nothing to do.
        if self._cache_complete(variant):
            return
        # Not currently present in the shared staging folder - either
        # not rendered yet, or already swept away by this variant's own
        # publish having integrated earlier. Either way, nothing we can
        # cache right now; a later pass may catch it if it's the one
        # whose own frames these are.
        if not self._raw_frames_complete(variant):
            return

        cache_dir = self._cache_dir(variant)
        os.makedirs(cache_dir, exist_ok=True)
        for frame in range(variant["frameStart"], variant["frameEnd"] + 1):
            src = self._frame_path(variant["renderDir"], variant, frame)
            dst = self._frame_path(cache_dir, variant, frame)
            if not os.path.isfile(dst):
                shutil.copy2(src, dst)

    def _cleanup_cache(self, render_dir):
        shutil.rmtree(
            os.path.join(render_dir, ".comparison_cache"), ignore_errors=True
        )

    # -- lock ----------------------------------------------------------

    def _claim_lock(self, lock_path):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            return False

    # -- video build -----------------------------------------------------

    def _build_video(self, comparison, output_path):
        from ayon_core.lib import get_ffmpeg_tool_args, run_subprocess

        variants = comparison["variants"]
        width = comparison["resolutionWidth"]
        height = comparison["resolutionHeight"]
        fps = comparison["fps"]

        count = len(variants)
        cols = math.ceil(math.sqrt(count))
        rows = math.ceil(count / cols)
        tile_w = width // cols
        tile_h = height // rows
        # Even dimensions avoid libx264 "width/height not divisible by 2".
        tile_w -= tile_w % 2
        tile_h -= tile_h % 2

        font_path = "C\\:/Windows/Fonts/arial.ttf"

        inputs = []
        filter_parts = []
        for index, variant in enumerate(variants):
            pattern = os.path.join(
                self._cache_dir(variant),
                "{}.%04d.{}".format(variant["baseName"], variant["ext"]),
            )
            inputs += [
                "-start_number", str(variant["frameStart"]),
                "-framerate", str(fps),
                "-i", pattern,
            ]
            label = variant["variant"].replace("'", r"\'").replace(":", r"\:")
            filter_parts.append(
                "[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                "pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                "drawtext=fontfile='{font}':text='{label}':x=10:"
                "y=h-th-10:fontsize=24:fontcolor=white:box=1:"
                "boxcolor=black@0.5:boxborderw=6[v{i}]".format(
                    i=index, w=tile_w, h=tile_h,
                    font=font_path, label=label,
                )
            )

        if count == 1:
            filter_complex = filter_parts[0].replace("[v0]", "[out]")
        else:
            layout_positions = []
            for index in range(count):
                row, col = divmod(index, cols)
                x = "0" if col == 0 else "+".join(["w0"] * col)
                y = "0" if row == 0 else "+".join(["h0"] * row)
                layout_positions.append("{}_{}".format(x, y))

            stack_inputs = "".join(
                "[v{}]".format(i) for i in range(count)
            )
            filter_complex = "{};{}xstack=inputs={}:layout={}[out]".format(
                ";".join(filter_parts),
                stack_inputs,
                count,
                "|".join(layout_positions),
            )

        # Force the final canvas back to the exact shot resolution -
        # cols/rows tile-size rounding can leave it a few pixels short.
        final_w = width - (width % 2)
        final_h = height - (height % 2)
        filter_complex += ";[out]scale={}:{}[final]".format(
            final_w, final_h)

        args = get_ffmpeg_tool_args(
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[final]",
            "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-crf", "18",
            "-movflags", "faststart",
            output_path,
        )
        self.log.info("Running ffmpeg comparison build: %s", " ".join(args))
        run_subprocess(args, logger=self.log)

    # -- kitsu delivery --------------------------------------------------

    def _upload_to_kitsu(self, context, comparison, output_path):
        """Post a single Kitsu comment listing every included variant,
        with the comparison video attached as its preview.

        Deliberately bypasses ayon-kitsu's generic CollectKitsuEntities/
        IntegrateKitsuNote/IntegrateKitsuReview chain (and doesn't
        create any AYON product/instance for the video at all) - going
        through those would both drag in the studio's generic farm
        comment template (which always includes a version number, since
        any farm-published sibling instance in the same context makes
        IntegrateKitsuNote treat this one as a farm publish too) and
        leave the video as a browsable-but-not-really-loadable product
        cluttering the AYON Loader. gazu is already authenticated at
        this point (ayon-kitsu's CollectKitsuLogin runs at
        CollectorOrder, well before this plugin's CollectorOrder+0.05).
        """
        task_entity = context.data.get("taskEntity")
        kitsu_id = (task_entity or {}).get("data", {}).get("kitsuId")
        if not kitsu_id:
            self.log.warning(
                "No Kitsu task linked for this context - skipping "
                "Kitsu upload of the comparison review."
            )
            return

        import gazu

        kitsu_task = gazu.task.get_task(kitsu_id)
        variant_names = [v["variant"] for v in comparison["variants"]]
        comment_text = "Rendered variants: {}".format(
            ", ".join(variant_names))

        kitsu_comment = gazu.task.add_comment(
            kitsu_task, kitsu_task["task_status_id"], comment=comment_text)
        gazu.task.add_preview(
            task=kitsu_task["id"],
            comment=kitsu_comment["id"],
            preview_file_path=output_path,
            normalize_movie=True,
        )
        self.log.info(
            "Uploaded comparison review to Kitsu task '%s': %s",
            kitsu_task["id"], output_path,
        )
