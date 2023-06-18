import bpy

from typing import List

SKET_TOOL_CATEGORY = "SKET"


SKET_PROP_EXPORT_ANIM = "sket_export_anim"

SKET_E_MODE_EXPORT_ANIM_ALL = "ALL"
SKET_E_MODE_EXPORT_ANIM_SELECT = "SELECT"
SKET_E_MODE_EXPORT_ANIM_NONE = "NONE"

# Constants
SKET_EXPORT_OBJ_SUFFIX = "_sket_object"
SKET_EXPORT_WORK_OBJ_SUFFIX = "_sket_w_object"
SKET_EXPORT_DUMMYMESH_NAME = "sket_mesh_dummy"


def select_objects(obj_names):
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")

    for obj_name in obj_names:
        set_active_object(obj_name)


def set_active_object(obj_name):
    """オブジェクトをアクティブ常態にする"""
    bpy.context.view_layer.objects.active = bpy.data.objects[obj_name]
    bpy.data.objects[obj_name].select_set(state=True)


def set_hidden_object(obj, hidden=True):
    """オブジェクトの非表示状態を設定する"""
    obj.hide_set(hidden)
    obj.hide_viewport = hidden


def is_object_hidden(obj):
    if obj is not None:
        if obj.hide_get() or obj.hide_viewport:
            return True

    return False


def is_mesh(obj):
    return obj is not None and obj.type == "MESH"


def is_armature(obj):
    return obj is not None and obj.type == "ARMATURE"


def is_empty(obj):
    return obj is not None and obj.type == "EMPTY"


def get_object_relation_depth(obj, level=0) -> int:
    """オブジェクトの深さを取得する"""
    if obj is None:
        return -1

    if obj.parent is None:
        return level

    return get_object_relation_depth(obj.parent, level + 1)
