import os
import re
import hou

from ayon_core.pipeline import AYON_CONTAINER_ID
from ayon_houdini.api import plugin, lib
from ayon_houdini.api.lib import move_node_to_viewport


def get_current_context():
    """Return the current network context (network editor pwd) or fallback to /stage."""
    try:
        for tab in hou.ui.paneTabs():
            try:
                if tab.type() == hou.paneTabType.NetworkEditor:
                    pwd = tab.pwd()
                    if isinstance(pwd, hou.Node):
                        return pwd
            except Exception:
                continue
    except Exception:
        pass

    # Fallback to /stage or /obj
    return hou.node("/stage") or hou.node("/obj")

class MaterialXImageLoader(plugin.HoudiniLoader):
    """Load images as MaterialX texture inputs in the stage context."""

    product_types = {
        "imagesequence",
        "review",
        "render",
        "plate",
        "image",
        "online",
    }
    label = "Load Image (MaterialX)"
    representations = {"*"}
    order = -8
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):
        """Load image as MaterialX texture."""
        path = self.filepath_from_context(context)
        path = self.format_path(path, representation=context["representation"])

        parent = get_current_context()
        namespace = namespace or context["folder"]["name"]
        node_name = f"{namespace}_{name}" if namespace else name

        image_node_candidates = [
            "mtlximport",
            "mtlximage",
            "mtlxtexture",
            "texture",
            "material",
        ]

        node = None
        for ntype in image_node_candidates:
            try:
                node = parent.createNode(ntype, node_name=node_name)
                move_node_to_viewport(node)
                break
            except Exception:
                pass

        if node is None:
            raise RuntimeError(
                "Could not create a MaterialX image node: no valid node type found."
            )

        parms = {"file": path}
        parms.update(self.get_colorspace_parms(context["representation"]))

        filtered_parms = {k: v for k, v in parms.items() if node.parm(k) is not None}
        if filtered_parms:
            node.setParms(filtered_parms)

        lib.imprint(node, {
            "schema": "ayon:container-3.0",
            "id": AYON_CONTAINER_ID,
            "name": node_name,
            "namespace": namespace,
            "loader": self.__class__.__name__,
            "representation": context["representation"]["id"],
        })

        return node

    def update(self, container, context):
        """Update the file path and colorspace of an existing MaterialX image."""
        node = container["node"]
        repre_entity = context["representation"]

        file_path = self.filepath_from_context(context)
        file_path = self.format_path(file_path, repre_entity)

        parms = {
            "file": file_path,
            "representation": repre_entity["id"],
        }
        parms.update(self.get_colorspace_parms(repre_entity))

        filtered_parms = {k: v for k, v in parms.items() if node.parm(k) is not None}
        if filtered_parms:
            node.setParms(filtered_parms)

    def remove(self, container):
        """Remove the MaterialX image node and clean up empty parents."""
        node = container["node"]
        parent = node.parent()
        node.destroy()

        if not parent.children():
            grandparent = parent.parent()
            parent.destroy()
            if grandparent and not grandparent.children():
                grandparent.destroy()

    @staticmethod
    def format_path(path, representation):
        """Format file path for single image or sequence, with UDIM support."""
        ext = os.path.splitext(path)[-1]

        is_sequence = bool(representation["context"].get("frame"))
        if is_sequence:
            folder, filename = os.path.split(path)
            filename = re.sub(
                rf"(.*)\.([\d]+){re.escape(ext)}$",
                rf"\1.$F4{ext}",
                filename
            )
            path = os.path.join(folder, filename)

        path = os.path.normpath(path).replace("\\", "/")
        
        # Replace UDIM tile with <UDIM> token (e.g., name.1001.exr -> name.<UDIM>.exr)
        path = re.sub(r'([._])(1\d{3})(?=[._v]|$)', r"\1<UDIM>", path)

        return path

    def get_colorspace_parms(self, representation: dict) -> dict:
        """Return colorspace parameters if available in representation."""
        major, _, _ = hou.applicationVersion()
        if major < 20:
            return {}

        data = representation.get("data", {}).get("colorspaceData", {})
        colorspace = data.get("colorspace")
        return {"colorspace": colorspace} if colorspace else {}

    def switch(self, container, representation):
        self.update(container, representation)
