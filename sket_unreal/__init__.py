bl_info = {
    "name": "SKET: SkeletalMesh Export Tool for Unreal Engine",
    "author": "T_Sumisaki",
    "version": (1, 1, 0),
    "blender": (3, 2, 0),
    "location": "File > Import-Export",
    "description": "FBX Exporter for Unreal Engine",
    "category": "Import-Export",
}

import bpy

if "bpy" in locals():
    import importlib

    if "sket_fbx_export" in locals():
        importlib.reload(sket_fbx_export)

    if "sket_delete_action" in locals():
        importlib.reload(sket_delete_action)

    if "export_fbx_init" in locals():
        importlib.reload(export_fbx_init)


from . import sket_delete_action, sket_fbx_export
from .fbx_export import export_fbx_init

def register():
    
    if "bpy" in locals():
        import importlib

        if "sket_fbx_export" in locals():
            importlib.reload(sket_fbx_export)

        if "sket_delete_action" in locals():
            importlib.reload(sket_delete_action)

        if "export_fbx_init" in locals():
            importlib.reload(export_fbx_init)

    export_fbx_init.register()
    sket_delete_action.register()
    sket_fbx_export.register()


def unregister():
    export_fbx_init.unregister()
    sket_fbx_export.unregister()
    sket_delete_action.unregsiter()
