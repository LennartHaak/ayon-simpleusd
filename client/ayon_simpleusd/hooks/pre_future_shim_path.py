# -*- coding: utf-8 -*-
"""Prelaunch hook working around a Houdini 22 startup crash.

AYON's vendored `future` package (from its dependency package zip) is
built for older Python and unconditionally does `import imp` inside
`future.standard_library`, a module removed in Python 3.12+. Houdini
22 ships Python 3.13, and Houdini's own internal bootstrap
(`houpythonportion/__utils__.py`) does
`from future import standard_library; standard_library.install_aliases()`
during `import hou`. Because AYON puts its dependency zip on
PYTHONPATH ahead of anything else, that import resolves to the broken
copy and raises ModuleNotFoundError - which reproducibly segfaults
Houdini's native code when it later needs a working Python evaluation
context to build its main menu bar (SI_XMLMenuItemFilter::evalExpression).

`vendor/future_shim` vendors a current, unmodified `future`/`past`
(PyPI `future` 1.0.0) install, which guards that import
(`if sys.version_info >= (3, 6): import importlib as imp`). Prepending
it to PYTHONPATH ahead of AYON's broken copy fixes `import hou`
without touching AYON's cached dependency package.
"""
import os

from ayon_applications import PreLaunchHook, LaunchTypes

ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUTURE_SHIM_DIR = os.path.join(ADDON_ROOT, "vendor", "future_shim")


class AddFutureShimPath(PreLaunchHook):
    """Prepend a working `future`/`past` install to PYTHONPATH."""

    app_groups = {"houdini"}
    launch_types = {LaunchTypes.local, LaunchTypes.farm_render}
    order = 0

    def execute(self):
        env = self.launch_context.env
        old_python_path = env.get("PYTHONPATH") or ""
        parts = [FUTURE_SHIM_DIR]
        for path in old_python_path.split(os.pathsep):
            if path and path not in parts:
                parts.append(path)
        env["PYTHONPATH"] = os.pathsep.join(parts)
        self.log.debug(
            "Prepended future/past shim to PYTHONPATH: %s",
            FUTURE_SHIM_DIR)
