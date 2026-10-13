# -*- coding: utf-8 -*-
"""Shared helpers for posting Kitsu status/comment updates directly via
gazu, bypassing ayon-kitsu's generic CollectKitsuFamily/IntegrateKitsuNote
pipeline.

That pipeline only fires for review/farm-targeted instances (see
strip_render_kitsu_family.py and build_simpleusd_comparison_review.py for
the full explanation), so Simple USD's own products - which are always
either local Houdini publishes or don't carry a "review" family - talk to
Kitsu directly instead.
"""
from ayon_core.settings import get_project_settings


def get_kitsu_task_id(task_entity):
    """Return the linked Kitsu task id for an AYON task entity, if any."""
    return (task_entity or {}).get("data", {}).get("kitsuId")


def is_kitsu_enabled(project_name):
    """Whether Simple USD's own Kitsu status/comment integration is
    enabled (see SimpleUSDSettings.kitsu.enabled in server/settings.py).
    """
    settings = get_project_settings(project_name)
    return settings.get("simple-usd", {}).get("kitsu", {}).get(
        "enabled", True)


def get_kitsu_review_status_shortname(project_name):
    """Configured Kitsu status short name to set on part/root/review
    publish comments (see SimpleUSDSettings.kitsu.review_status_shortname
    in server/settings.py). Empty string means: post the comment without
    changing status.
    """
    settings = get_project_settings(project_name)
    return settings.get("simple-usd", {}).get("kitsu", {}).get(
        "review_status_shortname", "REV")


def post_kitsu_status_comment(
        project_name, kitsu_task_id, comment_text, log=None):
    """Post a comment to a Kitsu task, moving it to the configured status.

    add_comment()'s status argument is what actually changes the task's
    status - passing its own current status back is a no-op.

    Returns:
        dict or None: The created Kitsu comment, or None if the task
            couldn't be found.
    """
    import gazu

    kitsu_task = gazu.task.get_task(kitsu_task_id)
    if not kitsu_task:
        if log:
            log.warning("Kitsu task '%s' not found.", kitsu_task_id)
        return None

    note_status = kitsu_task["task_status_id"]
    status_shortname = get_kitsu_review_status_shortname(project_name)
    if status_shortname:
        kitsu_status = gazu.task.get_task_status_by_short_name(
            status_shortname.strip())
        if kitsu_status:
            note_status = kitsu_status["id"]
        elif log:
            log.warning(
                "Cannot find Kitsu status '%s' - leaving task status "
                "unchanged.", status_shortname)

    return gazu.task.add_comment(
        kitsu_task, note_status, comment=comment_text)
