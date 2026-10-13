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
import datetime

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
        comparison["artist"] = data.get("user", "")

        variants = comparison["variants"]
        render_dir = variants[0]["renderDir"]
        lock_path = os.path.join(
            render_dir, ".comparison_{}.lock".format(comparison["versionStr"])
        )
        # Check before doing any caching work at all - otherwise a pass
        # that runs *after* a successful build+cleanup (a retry, a late
        # sibling job, an RR resubmission) would recreate
        # .comparison_cache/<variant>/ for whatever frames still happen
        # to be sitting in the render dir, only to then discover the
        # lock already exists and bail - leaving that partial cache dir
        # behind uncleaned.
        if os.path.isfile(lock_path):
            self.log.debug(
                "Comparison review already built (or in progress) for "
                "this version - skipping."
            )
            return

        for variant in variants:
            self._cache_variant_frames(variant)

        if not all(self._cache_complete(variant) for variant in variants):
            self.log.debug(
                "Not all comparison review variants have finished "
                "rendering yet - skipping for now."
            )
            return

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
        try:
            self._build_video(comparison, output_path)
            self._upload_to_ayon(context, comparison, output_path)
            self._set_ayon_review_status(context)
            self._upload_to_kitsu(context, comparison, output_path)
            self._cleanup_cache(render_dir)
        except Exception:
            # Don't fail the render product's own publish over a broken
            # comparison review - but do release the lock so a later
            # republish pass can retry, instead of leaving every future
            # pass silently skipping forever ("already built by another
            # variant's publish job") because of one stale lock file
            # left behind by this crash. Deliberately leave
            # .comparison_cache in place - a retry needs it and cleanup
            # only ever runs after a full success.
            self.log.error(
                "Failed to build/upload the Simple USD comparison "
                "review - a later republish pass will retry.",
                exc_info=True
            )
            try:
                os.remove(lock_path)
            except OSError:
                pass
            # ffmpeg's "-y" creates/truncates the output file up front,
            # so a mid-build failure can leave a 0-byte/partial mp4
            # behind that looks like a broken deliverable - clear it so
            # it isn't mistaken for one.
            try:
                os.remove(output_path)
            except OSError:
                pass

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

    # -- burn-in text -----------------------------------------------------

    def _escape_drawtext(self, text):
        return str(text).replace("'", r"\'").replace(":", r"\:")

    def _drawtext_style(self, text, x, y, font_path, escape=True):
        # escape=False is for text that is itself already valid drawtext
        # syntax (e.g. a "%{eif\:...\:d}" dynamic frame-number
        # expression) - running it through _escape_drawtext would also
        # escape the colons that expression syntax requires, breaking it.
        if escape:
            text = self._escape_drawtext(text)
        return (
            "fontfile='{font}':text='{text}':x={x}:y={y}:fontsize=24:"
            "fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=6".format(
                font=font_path, text=text, x=x, y=y,
            )
        )

    # -- colorspace conversion ---------------------------------------------

    # Standard ACEScg (AP1, D60) -> linear Rec.709/sRGB primaries (D65,
    # Bradford-adapted) 3x3 matrix - a well-known published constant (the
    # same one used by e.g. Unreal/Filament's ACES emulation), used here
    # as an ffmpeg `colorchannelmixer` matrix since oiiotool/OCIO aren't
    # available on this farm (see _ffmpeg_supports_color_management).
    _ACESCG_TO_REC709_MATRIX = (
        "rr=1.70505:rg=-0.62179:rb=-0.08326:"
        "gr=-0.13026:gg=1.14080:gb=-0.01055:"
        "br=-0.02400:bg=-0.12897:bb=1.15297"
    )

    def _ffmpeg_supports_color_management(self):
        """Whether this ffmpeg build has the `zscale`/`tonemap` filters
        needed for the ACEScg-to-sRGB approximation below.

        `zscale` requires libzimg and isn't guaranteed present in every
        ffmpeg build, so this is checked (and cached) once per plugin
        instance rather than assumed.
        """
        cached = getattr(self, "_color_management_supported", None)
        if cached is not None:
            return cached

        from ayon_core.lib import get_ffmpeg_tool_args, run_subprocess

        try:
            args = get_ffmpeg_tool_args("ffmpeg", "-hide_banner", "-filters")
            output = run_subprocess(args, logger=self.log)
        except Exception:
            output = ""

        supported = "zscale" in output and "tonemap" in output
        if not supported:
            self.log.warning(
                "This ffmpeg build is missing the 'zscale'/'tonemap' "
                "filters - comparison review frames will be burned in "
                "without the ACEScg-to-sRGB color conversion."
            )
        self._color_management_supported = supported
        return supported

    def _color_management_filter_chain(self):
        """ffmpeg filter chain approximating Houdini's default viewport
        transform ("sRGB - Display, ACES 1.0 - SDR Video") for ACEScg
        renders: primaries matrix -> linear tag -> filmic (Hable)
        highlight rolloff -> sRGB gamma encode.

        This is an approximation, not the literal ACES 1.0 RRT+ODT curve
        (ffmpeg's built-in `tonemap` filter has no literal "aces" curve) -
        chosen over a true OCIO transform because oiiotool isn't
        available on this farm.
        """
        return (
            "format=gbrpf32le,"
            "colorchannelmixer={matrix},"
            # Raw EXR frames carry no colorspace tags (primaries/matrix/
            # transfer all come in "unspecified") - without this, the
            # zscale below has no known source to convert *from* and
            # fails with "no path between colorspaces". This first
            # zscale doesn't convert anything (the *in* options match
            # the target) - it just stamps the frame as what it actually
            # already is post-colorchannelmixer: linear light, Rec.709
            # primaries. Note zscale's input-side options are suffixed
            # ("transferin"/"primariesin"/"matrixin"), not prefixed with
            # "in_" - the prefixed form doesn't exist and errors with
            # "Option not found".
            "zscale=transferin=linear:primariesin=bt709:matrixin=bt709:"
            "transfer=linear:primaries=bt709:matrix=bt709,"
            "tonemap=hable,"
            "zscale=transfer=iec61966-2-1,"
            "format=yuv420p,"
        ).format(matrix=self._ACESCG_TO_REC709_MATRIX)

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
        color_managed = self._ffmpeg_supports_color_management()

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
            color_chain = (
                self._color_management_filter_chain() if color_managed else ""
            )
            filter_parts.append(
                "[{i}:v]{color_chain}"
                "scale={w}:{h}:force_original_aspect_ratio=decrease,"
                "pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                "drawtext={style}[v{i}]".format(
                    i=index, w=tile_w, h=tile_h, color_chain=color_chain,
                    style=self._drawtext_style(
                        variant["variant"], "(w-tw)/2", "10", font_path
                    ),
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

        # Burn the shared (non per-variant) fields once onto the whole
        # combined canvas - they're the same for every tile since this
        # is all one shot/publish. Only "variant" (above) differs per
        # tile, so it stays burned individually on each one.
        frame_start = variants[0]["frameStart"]
        frame_end = variants[0]["frameEnd"]
        # "n" is drawtext's own per-output-frame counter (0-based, one
        # tick per encoded frame of the combined stream) - offsetting it
        # by frame_start turns it into the actual current source frame
        # number, updating live as the video plays rather than showing a
        # single static frame count for the whole clip.
        current_frame_expr = "%{{eif\\:n+{}\\:d}}".format(frame_start)
        frame_text = "{} ({}-{})".format(
            current_frame_expr, frame_start, frame_end)
        overlay_fields = [
            (datetime.date.today().isoformat(), "10", "10", True),
            (comparison.get("versionStr", ""), "w-tw-10", "10", True),
            (comparison.get("artist", ""), "10", "h-th-10", True),
            (
                "{} / {}".format(
                    comparison.get("sequence", ""), comparison.get("shot", "")
                ).strip(" /"),
                "(w-tw)/2", "h-th-10", True,
            ),
            (frame_text, "w-tw-10", "h-th-10", False),
        ]

        current_label = "final"
        overlay_parts = []
        for index, (text, x, y, escape) in enumerate(overlay_fields):
            next_label = "burn{}".format(index)
            overlay_parts.append(
                "[{cur}]drawtext={style}[{nxt}]".format(
                    cur=current_label,
                    style=self._drawtext_style(
                        text, x, y, font_path, escape=escape),
                    nxt=next_label,
                )
            )
            current_label = next_label
        filter_complex += ";" + ";".join(overlay_parts)

        args = get_ffmpeg_tool_args(
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[{}]".format(current_label),
            "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-crf", "18",
            "-movflags", "faststart",
            output_path,
        )
        self.log.info("Running ffmpeg comparison build: %s", " ".join(args))
        run_subprocess(args, logger=self.log)

    # -- AYON delivery -----------------------------------------------------

    def _upload_to_ayon(self, context, comparison, output_path):
        """Attach the comparison video as a "webreview"-tagged
        representation on whichever variant instance(s) are present in
        *this* farm job's own context.

        Each variant publishes as its own independent farm job/process,
        so by the time this runs (on whichever variant's pass finds
        every variant's frames cached), sibling variants have typically
        already published in their own, now-gone, processes - only this
        job's own instance(s) are available here to attach to. The
        representation then rides through this same process's own
        later Extract/Integrate plugins untouched: ayon-core's
        IntegrateAsset only ever drops representations tagged "delete",
        and IntegrateAYONReview uploads any "webreview"-tagged
        representation via ayon_api.upload_reviewable() once IntegrateAsset
        has copied it into the publish location. This is what lets
        ShotGrid's AYON-side sync (which reacts to AYON reviewables/
        versions, not to a direct client push) pick this up.

        Matched via "productName", not "simpleusdBaseName" - this
        studio's RR publish-job creator builds each farm job's instance
        data through ayon-core's create_skeleton_instance(), which only
        carries over a fixed set of keys (productName among them) and
        drops arbitrary custom fields like simpleusdBaseName entirely.
        """
        product_names = {v["productName"] for v in comparison["variants"]}
        matches = [
            instance for instance in context
            if instance.data.get("productName") in product_names
        ]
        if not matches:
            self.log.warning(
                "No instance in this farm job's context matches any "
                "comparison review variant - nothing to attach the "
                "AYON reviewable to in this process."
            )
            return

        for instance in matches:
            representations = instance.data.setdefault("representations", [])
            representations.append({
                "name": "comparisonreview",
                "ext": "mp4",
                "files": os.path.basename(output_path),
                "stagingDir": os.path.dirname(output_path),
                "outputName": "Comparison Review",
                # Not tagged "review" - that would trigger ExtractReview's
                # ffmpeg transcode pass, unneeded since _build_video already
                # produced the final, color-managed, burned-in mp4.
                "tags": ["webreview"],
            })
            self.log.info(
                "Attached comparison review as an AYON reviewable on "
                "product '%s'.", instance.data.get("productName"),
            )

    def _set_ayon_review_status(self, context):
        """Move the linked task on to the configured AYON review status
        now that the comparison review has actually been built and
        attached - the definitive "farm job is done" signal.

        Deliberately done here, directly, rather than left to
        integrate_simpleusd_ayon_review_status.py: that plugin is
        restricted away from usdrenderPackage/farm instances entirely
        (see its own docstring) specifically because relying on it for
        this would race against/be indistinguishable from unrelated
        review-tagged publishes (e.g. the workfile) landing in the same
        or an adjacent publish.
        """
        settings = context.data["project_settings"].get("simple-usd", {})
        status_name = settings.get("ayon_review_status", {}).get(
            "status_name")
        if not status_name:
            return

        task_entity = context.data.get("taskEntity")
        task_id = (task_entity or {}).get("id")
        if not task_id:
            self.log.debug(
                "No linked task - skipping AYON review status update."
            )
            return

        import ayon_api

        project_name = context.data["projectName"]
        try:
            ayon_api.update_task(project_name, task_id, status=status_name)
        except Exception:
            self.log.error(
                "Failed to set AYON review status.", exc_info=True)
        else:
            self.log.info("Set task status to '%s'.", status_name)

    # -- kitsu delivery --------------------------------------------------

    def _upload_to_kitsu(self, context, comparison, output_path):
        """Post a single Kitsu comment listing every included variant,
        with the comparison video attached as its preview.

        Deliberately bypasses ayon-kitsu's generic CollectKitsuEntities/
        IntegrateKitsuNote/IntegrateKitsuReview chain - going through
        those would drag in the studio's generic farm comment template
        (which always includes a version number, since any
        farm-published sibling instance in the same context makes
        IntegrateKitsuNote treat this one as a farm publish too).
        Kept as a parallel, best-effort delivery path alongside
        _upload_to_ayon() above - gazu is already authenticated at this
        point (ayon-kitsu's CollectKitsuLogin runs at CollectorOrder,
        well before this plugin's CollectorOrder+0.05) and this simply
        no-ops whenever no Kitsu task is linked.
        """
        task_entity = context.data.get("taskEntity")

        from ayon_simpleusd.kitsu_lib import (
            get_kitsu_task_id, is_kitsu_enabled, post_kitsu_status_comment)

        project_name = context.data["projectName"]
        if not is_kitsu_enabled(project_name):
            return

        kitsu_id = get_kitsu_task_id(task_entity)
        if not kitsu_id:
            self.log.warning(
                "No Kitsu task linked for this context - skipping "
                "Kitsu upload of the comparison review."
            )
            return

        variant_names = [v["variant"] for v in comparison["variants"]]
        comment_text = "Rendered variants: {}".format(
            ", ".join(variant_names))

        kitsu_comment = post_kitsu_status_comment(
            project_name, kitsu_id, comment_text, log=self.log)
        if not kitsu_comment:
            return

        import gazu

        gazu.task.add_preview(
            task=kitsu_id,
            comment=kitsu_comment["id"],
            preview_file_path=output_path,
            normalize_movie=True,
            revision=comparison.get("version"),
        )
        self.log.info(
            "Uploaded comparison review to Kitsu task '%s': %s",
            kitsu_id, output_path,
        )
