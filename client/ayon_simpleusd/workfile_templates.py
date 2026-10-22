# -*- coding: utf-8 -*-
"""Build a Simple USD workfile template into new, unsaved Houdini scenes.

Reuses ayon-houdini's HoudiniTemplateBuilder (placeholders, path resolving,
first version save) and only swaps where the template profiles come from:
'project_settings/simple-usd/workfile_templates' instead of
'project_settings/houdini/templated_workfile_build'. Each profile can point
at a template shipped in this addon's 'templates' dir or at a custom path.

Profiles are shared with Blender (blender_workfile_templates.py): bundled
templates are named '{host}_{name}.{ext}' and each host picks its own file,
custom paths are only used by the host their extension belongs to.
"""
import os
import re
import logging

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates")

# Scene file extensions per host - decides which template a host can open.
HOST_EXTENSIONS = {
    "houdini": (".hip", ".hipnc", ".hiplc"),
    "blender": (".blend",),
}

# Custom template paths can use {SIMPLEUSD_TEMPLATES} in every host - the
# Houdini prelaunch hook sets it too, but not the Blender launch.
os.environ.setdefault("SIMPLEUSD_TEMPLATES", TEMPLATES_DIR)

log = logging.getLogger(__name__)


def _find_included_template(name, host_name):
    """Return the bundled '{host_name}_{name}[_v###].{ext}' template, or ''.

    The version suffix is optional - with several versions the highest one
    wins, so bumping a template doesn't need a settings change.
    """
    extensions = HOST_EXTENSIONS.get(host_name, ())
    pattern = re.compile(
        rf"^{re.escape(f'{host_name}_{name}')}(?:_v(?P<version>\d+))?$",
        re.IGNORECASE,
    )
    candidates = []
    for filename in os.listdir(TEMPLATES_DIR):
        stem, ext = os.path.splitext(filename)
        if ext.lower() not in extensions:
            continue
        match = pattern.match(stem)
        if not match:
            continue
        version = int(match.group("version") or 0)
        # Same version in several formats: keep HOST_EXTENSIONS order.
        candidates.append(
            (version, -extensions.index(ext.lower()), filename))
    if not candidates:
        return ""
    return os.path.join(TEMPLATES_DIR, max(candidates)[2])


def get_template_profiles(project_settings, host_name):
    """Simple USD workfile template profiles usable by `host_name`.

    Each returned profile has 'path' set to the template for this host.
    Profiles without a template for this host (no bundled
    '{host_name}_{name}' file, or a custom path of another host's file
    type) are left out, so they never match.
    """
    settings = (
        project_settings
        .get("simple-usd", {})
        .get("workfile_templates", {})
    )
    if not settings.get("enabled"):
        return []

    extensions = HOST_EXTENSIONS.get(host_name, ())
    profiles = []
    for profile in settings.get("profiles", []):
        template = profile.get("template") or {}
        if template.get("source") == "custom":
            path = template.get("custom") or ""
            # No extension (e.g. still a template key) - let it through.
            ext = os.path.splitext(path)[1].lower()
            if ext and ext not in extensions:
                continue
        else:
            included = template.get("included") or ""
            path = (
                _find_included_template(included, host_name)
                if included else ""
            )
            if not path:
                continue
        profile = dict(profile)
        profile["path"] = path
        profiles.append(profile)
    return profiles


def _get_builder_class():
    from ayon_houdini.api.workfile_template_builder import (
        HoudiniTemplateBuilder,
    )

    class SimpleUSDTemplateBuilder(HoudiniTemplateBuilder):
        def _get_build_profiles(self):
            return get_template_profiles(self.project_settings, "houdini")

        def houdini_profile_matches(self):
            """Whether ayon-houdini's own templated workfile build has a
            profile for this context (it builds that one itself)."""
            from ayon_core.lib import filter_profiles

            folder_entity = self.current_folder_entity
            filter_data = {
                "task_types": self.current_task_type,
                "task_names": self.current_task_name,
                "folder_types": (
                    folder_entity["folderType"] if folder_entity else None),
                "folder_paths": self.current_folder_path,
            }
            houdini_profiles = super()._get_build_profiles()
            return bool(houdini_profiles) and bool(
                filter_profiles(houdini_profiles, filter_data))

    return SimpleUSDTemplateBuilder


def build_on_new():
    import hou
    from ayon_core.pipeline import registered_host
    from ayon_core.pipeline.workfile.workfile_template_builder import (
        TemplateProfileNotFound,
        TemplateNotFound,
        TemplateLoadFailed,
    )

    if hou.hipFile.isLoadingHipFile():
        return

    host = registered_host()
    if host is None:
        return

    builder = _get_builder_class()(host)
    if builder.houdini_profile_matches():
        log.info(
            "Houdini 'Templated Workfile Build' profile matches this "
            "context, skipping Simple USD workfile template.")
        return

    try:
        builder.build_template(workfile_creation_enabled=True)
    except TemplateProfileNotFound:
        pass
    except (TemplateNotFound, TemplateLoadFailed) as exc:
        log.warning("Simple USD workfile template: %s", exc)


def _on_new():
    import hou
    import hdefereval

    # AfterClear also fires right before a file is opened.
    if hou.hipFile.isLoadingHipFile():
        return
    hdefereval.executeDeferred(build_on_new)


def register_callbacks():
    import hdefereval
    from ayon_core.lib import register_event_callback

    # File > New / Workfiles tool emit "new" (Houdini AfterClear).
    register_event_callback("new", _on_new)
    # The first launch doesn't emit "new" - and ayon-houdini's host isn't
    # installed yet (its pythonrc runs after ours), so defer.
    hdefereval.executeDeferred(build_on_new)
