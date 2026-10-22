# -*- coding: utf-8 -*-
"""Run the headless Houdini Alembic -> USD conversion from another host.

Used by the Blender "SimpleUSD Model (via Houdini)" publish
(plugins/publish/blender/extract_simpleusd_houdini_usd.py). hython is
launched with the same AYON environment a farm render of that Houdini
variant would get - so this addon's prelaunch hooks put the HDAs on
HOUDINI_PATH (hooks/pre_houdini_startup_path.py) and set $ASSET
(hooks/pre_asset_env.py) exactly like an interactive Houdini launch.
"""
import os
import platform
import subprocess
import sys

from ayon_core.lib import find_executable

SIMPLEUSD_ADDON_ROOT = os.path.dirname(os.path.abspath(__file__))
HYTHON_SCRIPT = os.path.join(
    SIMPLEUSD_ADDON_ROOT, "scripts", "hython_abc_to_usd.py")


class HoudiniConversionError(Exception):
    """Conversion failed - message is artist-facing, `output` is the
    captured hython log (if hython got to run at all)."""

    def __init__(self, message, output=""):
        super().__init__(message)
        self.output = output


def get_houdini_application(app_name=None):
    """Return the configured Houdini application variant, or the latest
    one with an existing executable when `app_name` is empty."""
    from ayon_applications import ApplicationManager

    manager = ApplicationManager()
    if app_name:
        app = manager.applications.get(app_name)
        if app is None:
            raise HoudiniConversionError(
                "Houdini application '{}' is not configured in AYON's "
                "Applications settings.".format(app_name))
        return app

    app = manager.find_latest_available_variant_for_group("houdini")
    if app is None:
        raise HoudiniConversionError(
            "No Houdini application with an existing executable is "
            "configured in AYON's Applications settings.")
    return app


def get_hython_path(app):
    """hython lives next to the Houdini executable in its bin dir."""
    executable = app.find_executable()
    if not executable:
        raise HoudiniConversionError(
            "No executable found for '{}'.".format(app.full_name))
    houdini_path = find_executable(executable.executable_path)
    if not houdini_path:
        raise HoudiniConversionError(
            "No executable found for '{}'.".format(app.full_name))

    hython_name = "hython.exe" if platform.system() == "Windows" else "hython"
    hython_path = os.path.join(os.path.dirname(houdini_path), hython_name)
    if not os.path.isfile(hython_path):
        raise HoudiniConversionError(
            "hython not found next to '{}'.".format(houdini_path))
    return hython_path


def _normalize(path):
    return os.path.normcase(os.path.normpath(path))


def _is_under(path, roots):
    return any(
        path == root or path.startswith(root + os.sep) for root in roots)


def _get_base_environment():
    """This process's environment without what ayon-blender's launch added
    for Blender itself, so it doesn't leak into hython.

    Drops BLENDER_* vars, the ayon_blender startup scripts dir and - added
    by ayon-blender's pre_pyside_install hook - the calling interpreter's
    own stdlib/site-packages. Those hold Blender's own `pxr`, which hython
    would otherwise import instead of Houdini's (DLL load failed).
    """
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("BLENDER_", "AYON_BLENDER_"))
    }
    env.pop("PYTHONHOME", None)

    host_python_roots = {_normalize(sys.prefix), _normalize(sys.base_prefix)}
    python_path = []
    for path in env.get("PYTHONPATH", "").split(os.pathsep):
        if not path:
            continue
        normalized = _normalize(path)
        if "ayon_blender" in normalized.split(os.sep):
            continue
        if _is_under(normalized, host_python_roots):
            continue
        python_path.append(path)
    env["PYTHONPATH"] = os.pathsep.join(python_path)
    return env


def get_houdini_environment(project_name, folder_path, task_name, app):
    from ayon_applications import LaunchTypes
    from ayon_applications.utils import get_app_environments_for_context

    # farm_render: the headless launch type this addon's prelaunch hooks
    # (HOUDINI_PATH startup dir, $ASSET) already run for, while
    # local-only hooks (last workfile, workfile templates) are skipped.
    return get_app_environments_for_context(
        project_name,
        folder_path,
        task_name,
        app.full_name,
        launch_type=LaunchTypes.farm_render,
        env=_get_base_environment(),
    )


def run_abc_to_usd(
    project_name,
    folder_path,
    task_name,
    abc_path,
    usd_path,
    debug_hip_path,
    app_name=None,
    timeout=600,
    log=None,
):
    """Convert `abc_path` to `usd_path` through the SimpleUSD Alembic
    Loader HDA in a headless Houdini. Returns the captured hython log."""
    app = get_houdini_application(app_name)
    hython_path = get_hython_path(app)
    env = get_houdini_environment(project_name, folder_path, task_name, app)

    args = [
        hython_path, HYTHON_SCRIPT,
        "--abc", abc_path,
        "--output", usd_path,
        "--debug-hip", debug_hip_path,
    ]
    if log:
        log.info("Converting with %s (%s)", app.full_name, hython_path)
        log.debug("Command: %s", subprocess.list2cmdline(args))

    kwargs = {}
    if platform.system() == "Windows":
        # Don't flash a console window over the host application.
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            args,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            **kwargs
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        raise HoudiniConversionError(
            "Houdini conversion timed out after {}s.".format(timeout),
            output)

    if log:
        log.debug("hython output:\n%s", result.stdout)
    if result.returncode != 0 or not os.path.isfile(usd_path):
        raise HoudiniConversionError(
            "Houdini conversion failed (exit code {}).".format(
                result.returncode),
            result.stdout)
    return result.stdout
