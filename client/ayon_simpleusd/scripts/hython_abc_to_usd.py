# -*- coding: utf-8 -*-
"""Convert an Alembic into a SimpleUSD model layer - run with hython.

Launched headless from Blender's "SimpleUSD Model (via Houdini)" publish
(see ayon_simpleusd/houdini_conversion.py). Rebuilds what an artist would
do by hand in Houdini: a SimpleUSD Alembic Loader HDA pointing at the
.abc, written out by a usd_rop with the same settings the SimpleUSD Asset
creator (plugins/create/houdini/create_usd_asset.py) puts on its node.

Exits non-zero on any failure, after saving the scene to --debug-hip so
the conversion can be inspected in Houdini.
"""
import argparse
import os
import sys
import traceback

import hou

ALEMBIC_LOADER_TYPE = "LennartHaak::SimpleUSD_Alembic_Loader"


def _version_key(node_type_name):
    """Sort key for "namespace::name::1.4" style versioned type names."""
    version = node_type_name.rsplit("::", 1)[-1]
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return ()


def get_alembic_loader_type():
    """Return the highest installed version of the Alembic Loader HDA."""
    type_names = [
        name for name in hou.lopNodeTypeCategory().nodeTypes()
        if name.startswith(ALEMBIC_LOADER_TYPE + "::")
    ]
    if not type_names:
        raise RuntimeError(
            "HDA '{}' is not installed - is ayon_simpleusd/startup on "
            "HOUDINI_PATH?".format(ALEMBIC_LOADER_TYPE))
    return max(type_names, key=_version_key)


def check_usd_python():
    """Fail with the real cause if Houdini's USD Python modules don't
    import - otherwise the usd_rop silently lacks its output processor
    parms and fails later with a misleading 'Invalid parameter name'."""
    try:
        import loputils  # noqa: F401 - imports Houdini's pxr
    except ImportError as exc:
        pxr_location = ""
        pxr_module = sys.modules.get("pxr")
        if pxr_module is not None:
            pxr_location = " ('pxr' was loaded from {})".format(
                os.path.dirname(getattr(pxr_module, "__file__", "") or ""))
        raise RuntimeError(
            "Houdini's USD Python modules failed to import{} - another "
            "application's 'pxr' is probably on PYTHONPATH. ({})".format(
                pxr_location, exc))


def convert(abc_path, output_path):
    check_usd_python()
    if not os.path.isfile(abc_path):
        raise RuntimeError("Alembic file not found: {}".format(abc_path))
    if not os.environ.get("ASSET"):
        raise RuntimeError("$ASSET is not set - the published layer would "
                           "have no default prim.")

    stage = hou.node("/stage")

    loader = stage.createNode(get_alembic_loader_type(), "alembic_loader")
    loader.parm("fileName").set(abc_path.replace("\\", "/"))
    print("Using {} ({})".format(loader.path(), loader.type().name()))

    rop = stage.createNode("usd_rop", "simpleusd_model")
    rop.setParms({
        "loppath": loader.path(),
        "lopoutput": output_path.replace("\\", "/"),
        "savestyle": "flattenstage",
        "defaultprim": "$ASSET",
        "enableoutputprocessor_simplerelativepaths": False,
    })

    rop.render()

    errors = list(loader.errors()) + list(rop.errors())
    if errors:
        raise RuntimeError("\n".join(errors))
    if not os.path.isfile(output_path):
        raise RuntimeError(
            "USD ROP finished but wrote no file: {}".format(output_path))
    print("Wrote {}".format(output_path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--abc", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--debug-hip", required=True)
    args = parser.parse_args()

    try:
        convert(args.abc, args.output)
    except Exception:
        traceback.print_exc()
        try:
            hou.hipFile.save(args.debug_hip.replace("\\", "/"))
            print("Saved debug scene: {}".format(args.debug_hip))
        except Exception:
            traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
