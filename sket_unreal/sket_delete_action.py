import bpy

from . import sket_common


class SKET_PT_delete_action(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = sket_common.SKET_TOOL_CATEGORY
    bl_label = "SKET: Delete Action"
    bl_idname = "SKET_PT_delete_action"

    def draw(self, context):
        layout = self.layout

        layout.label(text="Action list:")
        layout.prop(context.scene, "sket_delete_action_filter", text="", icon="FILTER")

        col = layout.column(align=True)

        if len(bpy.data.actions) > 0:
            keyword = context.scene.sket_delete_action_filter
            for action in bpy.data.actions:

                if keyword != "" and not sket_common.partial_matched(keyword, action.name):
                    continue

                _row = col.row(align=True)
                _row.label(text=action.name)
                _op = _row.operator(SKET_OT_delete_action.bl_idname, text="", icon="TRASH")
                _op.action_name = action.name
        else:
            _row = col.row(align=True)
            _row.label(text="No actions")


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


classes = (SKET_PT_delete_action, SKET_OT_delete_action)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.sket_delete_action_filter = bpy.props.StringProperty(name="Filter", default="", options={"TEXTEDIT_UPDATE"})


def unregsiter():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.sket_delete_action_filter
