from typing import Any, List
import bpy
from bpy.types import AnyType, Context, UILayout

from . import sket_common


class SKET_PT_delete_action(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = sket_common.SKET_TOOL_CATEGORY
    bl_label = "SKET: Delete Action"
    bl_idname = "SKET_PT_delete_action"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.template_list("SKET_UL_delete_actions", "", bpy.data, "actions", context.scene, "sket_delete_action_index")


class SKET_UL_delete_actions(bpy.types.UIList):
    def draw_item(
        self,
        context: Context | None,
        layout: UILayout,
        data: AnyType | None,
        item: AnyType | None,
        icon: int | None,
        active_data: AnyType,
        active_property: str,
        index: Any | None = 0,
        flt_flag: Any | None = 0,
    ):
        act = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=act.name)
            _op = layout.operator(SKET_OT_delete_action.bl_idname, text="", icon="TRASH")
            _op.action_name = act.name
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=act.name)


class SKET_OT_delete_action(bpy.types.Operator):
    """delete action"""

    bl_idname = "sket.delete_action"
    bl_label = "The action will be permanently removed from the scene, ok?"
    bl_options = {"UNDO"}

    action_name: bpy.props.StringProperty(default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if not self.action_name:
            self.report({"ERROR"}, "Delete action name is not defined")
            return {"FINISHED"}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            if bpy.data.actions.get(self.action_name):
                bpy.data.actions.remove(bpy.data.actions[self.action_name])
                self.report({"INFO"}, "Action [" + self.action_name + "] deleted")

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {"FINISHED"}


classes = (SKET_PT_delete_action, SKET_OT_delete_action, SKET_UL_delete_actions)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.sket_delete_action_index = bpy.props.IntProperty(default=-1)


def unregsiter():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.sket_delete_action_index
