# -*- coding: utf-8 -*-
"""Build a Simple USD workfile template into new, unsaved Blender scenes.

Blender counterpart of workfile_templates.py: reuses ayon-blender's
BlenderTemplateBuilder (opens the template as the new scene, placeholders,
first version save) with the profiles from
'project_settings/simple-usd/workfile_templates', resolved to the
'blender_{name}.blend' templates.

Registered from SimpleUSDAddon.on_host_install - Blender has no pythonrc
this addon could hook into.
"""
import logging

from ayon_simpleusd.workfile_templates import get_template_profiles

log = logging.getLogger(__name__)

# True while a template is being opened - read_homefile fires load_post,
# which ayon-blender emits as another "new" event.
_building = False


def _get_builder_class():
    from ayon_blender.api.workfile_template_builder import (
        BlenderTemplateBuilder,
    )

    class SimpleUSDBlenderTemplateBuilder(BlenderTemplateBuilder):
        def _get_build_profiles(self):
            return get_template_profiles(self.project_settings, "blender")

        def blender_profile_matches(self):
            """Whether ayon-blender's own templated workfile build has a
            profile for this context (it builds that one itself)."""
            from ayon_core.lib import filter_profiles

            try:
                blender_profiles = super()._get_build_profiles()
            except (KeyError, TypeError):
                return False

            folder_entity = self.current_folder_entity
            filter_data = {
                "task_types": self.current_task_type,
                "task_names": self.current_task_name,
                "folder_types": (
                    folder_entity["folderType"] if folder_entity else None),
                "folder_paths": self.current_folder_path,
            }
            return bool(blender_profiles) and bool(
                filter_profiles(blender_profiles, filter_data))

    return SimpleUSDBlenderTemplateBuilder


def build_on_new():
    import bpy
    from ayon_core.pipeline import registered_host
    from ayon_core.pipeline.workfile.workfile_template_builder import (
        TemplateProfileNotFound,
        TemplateNotFound,
        TemplateLoadFailed,
    )

    global _building

    # Only build into a new scene, never into an opened file.
    if bpy.data.filepath:
        return

    host = registered_host()
    if host is None:
        return

    builder = _get_builder_class()(host)
    if builder.blender_profile_matches():
        log.info(
            "Blender 'Templated Workfile Build' profile matches this "
            "context, skipping Simple USD workfile template.")
        return

    try:
        preset = builder.get_template_preset()
        if not preset.profile or not preset.has_valid_path():
            return
        _building = True
        builder.create_first_workfile_version(preset)
    except TemplateProfileNotFound:
        pass
    except (TemplateNotFound, TemplateLoadFailed) as exc:
        log.warning("Simple USD workfile template: %s", exc)
    finally:
        _building = False


def _build_timer():
    import bpy

    # Wait until Blender's startup / file load has settled.
    if not bpy.context.window_manager or not bpy.context.scene:
        return 0.1
    try:
        build_on_new()
    except Exception:
        log.warning(
            "Failed to build Simple USD workfile template.", exc_info=True)
    return None


def _schedule_build(*args):
    import bpy

    if _building:
        return
    # One pending build at a time - launch and "new" can both request one.
    if not bpy.app.timers.is_registered(_build_timer):
        bpy.app.timers.register(_build_timer, first_interval=0.1)


def register_callbacks():
    import bpy
    from ayon_core.lib import register_event_callback

    if bpy.app.background:
        return

    # File > New / Workfiles tool emit "new" (Blender load_post without a
    # filepath).
    register_event_callback("new", _schedule_build)
    # The launch scene doesn't emit "new".
    _schedule_build()
