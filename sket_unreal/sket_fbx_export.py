from typing import List, Any
import bpy
from bpy.types import AnyType, Context, UILayout
from bpy_extras.io_utils import ExportHelper
from .sket_common import (
    # constants
    SKET_TOOL_CATEGORY,
    SKET_E_MODE_EXPORT_ANIM_ALL,
    SKET_E_MODE_EXPORT_ANIM_SELECT,
    SKET_E_MODE_EXPORT_ANIM_NONE,
    SKET_TAG_EXPORT,
    SKET_TAG_ACTION_EXCLUDE,
    # functions
    is_armature,
    is_mesh,
    is_empty,
    set_active_object,
    select_objects,
    partial_matched,
    is_exclude_action,
)

from .sket_fbx_export_functions import (
    apply_scale_x100,
    apply_scale_x100_no_armature,
    apply_action_scale_x100,
    create_copy_objects,
    delete_copy_objects,
    rename_objects_for_export,
    revert_object_name,
    revert_action_scale_x100,
    insert_root_bone,
)

import pathlib


class SKETExportPropertyMixin:
    # DeformBoneのみ出力
    use_armature_deform_only: bpy.props.BoolProperty(
        name="Deform Armature Only",
        description="If True, export only deform (weight-painted) armature",
        default=False,
    )

    # 出力スケール
    global_scale: bpy.props.FloatProperty(name="Global Scale", default=1.0, description="Global scale applied")

    # スムージング種別
    mesh_smooth_type: bpy.props.EnumProperty(
        name="Smoothing",
        items=(
            ("OFF", "Normals Only", "Export only normals"),
            ("FACE", "Face", "Write face smoothing"),
            ("EDGE", "Edge", "Write edge smoothing"),
        ),
        description="Export smoothing information (prefer 'Normal Only' option if your target importer understand split normals)",
        default="FACE",
    )

    # PrimaryAxis
    bone_axis_primary_export: bpy.props.EnumProperty(
        name="Primary Bone Axis",
        items=(
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ),
        default="Z",
    )

    # SecondaryAxis
    bone_axis_secondary_export: bpy.props.EnumProperty(
        name="Secondary Bone Axis",
        items=(
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ),
        default="X",
    )

    # アニメーション出力種別
    mode_export_animations: bpy.props.EnumProperty(
        name="Export animation mode",
        items=(
            (SKET_E_MODE_EXPORT_ANIM_ALL, "All animation export", ""),
            (SKET_E_MODE_EXPORT_ANIM_SELECT, "Select export animation", ""),
            (
                SKET_E_MODE_EXPORT_ANIM_NONE,
                "No animation export (Armature only)",
                "",
            ),
        ),
        default=SKET_E_MODE_EXPORT_ANIM_ALL,
    )

    # アニメーション毎にファイルを分けて出力するか
    mode_export_separate_each_anims: bpy.props.BoolProperty(
        name="Separate File For Each Animation",
        description="Output a separate file for each animation",
        default=False,
    )

    # Meshを出力せず、Animationのみで出力するか
    mode_export_animation_only: bpy.props.BoolProperty(
        name="Export Animation Only", description="Output animation without skin mesh", default=False
    )

    mode_auto_fix_duplicated_name: bpy.props.BoolProperty(
        name="Auto Fix Duplicated Name",
        description="Fix duplicated object name automatically (mesh <-> bone)",
        default=True,
    )

    mode_auto_insert_rootbone: bpy.props.BoolProperty(
        name="Auto Insert Root Bone", description="Insert root bone automatically", default=False
    )


class SKET_PT_export_fbx_panel(bpy.types.Panel):
    """
    FBXExport用のパネルを作成
    """

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = SKET_TOOL_CATEGORY
    bl_label = "SKET: Export FBX"
    bl_idname = "SKET_PT_export_fbx_panel"

    def draw(self, context):
        layout = self.layout
        self.draw_command_section(context, layout)

    def draw_command_section(self, context, parent):
        col = parent.column(align=True)
        col.operator(SKET_OT_export_fbx.bl_idname, text="Export FBX")


class SKETExportSubPanel:
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "SKET_OT_export_fbx"


class SKET_PT_export_mesh(bpy.types.Panel, SKETExportSubPanel):
    bl_label = "Mesh"

    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = not operator.mode_export_animation_only

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(operator, "global_scale", text="Global Scale")  # global scale
        col.prop(operator, "mesh_smooth_type", text="Smoothing Group")  # smooth type
        col.prop(operator, "use_armature_deform_only")  # deform armature only


class SKET_PT_export_mesh_axis(bpy.types.Panel, SKETExportSubPanel):
    bl_label = "Axes"
    bl_parent_id = "SKET_PT_export_mesh"

    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = not operator.mode_export_animation_only

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(operator, "bone_axis_primary_export", text="Primary")
        col.prop(operator, "bone_axis_secondary_export", text="Secondary")


class SKET_PT_export_mesh_options(bpy.types.Panel, SKETExportSubPanel):
    bl_label = "Options"
    bl_parent_id = "SKET_PT_export_mesh"

    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator

        layout.active = not operator.mode_export_animation_only

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(operator, "mode_auto_fix_duplicated_name")
        col.prop(operator, "mode_auto_insert_rootbone")


class SKET_PT_export_mode(bpy.types.Panel, SKETExportSubPanel):
    bl_label = "Mode"

    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator

        col = layout.column(align=True)
        col.prop(operator, "mode_export_animation_only")


class SKET_PT_export_actions(bpy.types.Panel, SKETExportSubPanel):
    bl_label = "Animations"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        sfile = context.space_data
        operator = sfile.active_operator
        keyword = operator.action_filter

        col = layout.column(align=True)
        col.active = operator.mode_export_animations in (SKET_E_MODE_EXPORT_ANIM_ALL, SKET_E_MODE_EXPORT_ANIM_SELECT)
        col.prop(operator, "mode_export_separate_each_anims", text="Separate FBX each actions")

        col = layout.column(align=True)
        col.prop(
            operator,
            "mode_export_animations",
            text="Export Mode",
        )

        if operator.mode_export_animations == SKET_E_MODE_EXPORT_ANIM_SELECT:
            op_row = layout.row(align=True)
            select_all_op = op_row.operator(SKET_OT_set_export_all_actions.bl_idname, text="Select All")
            select_all_op.action_filter = keyword

            unselect_all_op = op_row.operator(SKET_OT_set_notexport_all_actions.bl_idname, text="Unselect All")
            unselect_all_op.action_filter = keyword

            if len(bpy.data.actions) > 0:
                row = layout.row()
                row.template_list("SKET_UL_export_actions", "", bpy.data, "actions", operator, "action_index")

            else:
                # Actionが存在しない場合はラベルのみ
                layout.row(align=True).label(text="No actions to export")


class SKET_UL_export_actions(bpy.types.UIList):
    bl_label = ""

    def draw_item(
        self,
        context: Context | None,
        layout: UILayout,
        data: AnyType | None,
        item: AnyType | None,
        icon_type: int | None,
        active_data: AnyType,
        active_property: str,
        index: Any | None = 0,
        flt_flag: Any | None = 0,
    ):
        act = item
        icon_type = "CHECKBOX_HLT" if act.sket_export_action else "CHECKBOX_DEHLT"

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=act.name)
            layout.prop(act, "sket_export_action", icon_only=True, emboss=False, icon=icon_type)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=act.name)

    def draw_filter(self, context: Context | None, layout: UILayout):
        sfile = context.space_data
        operator = sfile.active_operator

        col = layout.column(align=True)
        row = col.row(align=True)

        row.prop(operator, "action_filter", text="", icon="FILTER")

    def filter_items(self, context: Context | None, data: AnyType | None, property: str | Any):
        acts = getattr(data, property)
        helper_funcs = bpy.types.UI_UL_list

        flt_flags = []
        flt_neworder = []

        sfile = context.space_data
        operator = sfile.active_operator

        if operator.action_filter:
            flt_flags = helper_funcs.filter_items_by_name(
                operator.action_filter, self.bitflag_filter_item, acts, "name"
            )

        if not flt_flags:
            flt_flags = [self.bitflag_filter_item] * len(acts)

        return flt_flags, flt_neworder


class SKET_OT_export_fbx(bpy.types.Operator, ExportHelper, SKETExportPropertyMixin):
    bl_idname = "sket.export_fbx"
    bl_label = "SKET: Export FBX"

    filename_ext = ".fbx"
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={"HIDDEN"})

    action_filter: bpy.props.StringProperty(name="Filter", default="", options={"TEXTEDIT_UPDATE"})

    action_index: bpy.props.IntProperty(default=0)

    def draw(self, context):
        pass

    # def invoke(self, context, event):
    #     context.window_manager.fileselect_add(self)
    #     return {"RUNNING_MODAL"}

    def execute(self, context):
        # 実行前のデータを保存
        self.save_units = context.scene.unit_settings.scale_length
        self.save_unit_type = context.scene.unit_settings.system
        self.save_auto_key = context.scene.tool_settings.use_keyframe_insert_auto
        self.save_collection_vis = [c.hide_viewport for c in bpy.data.collections]

        self.current_selection = None
        self.arm_scale = None
        self.char_objects = None

        self.actions_units_changed = []
        self.actions_x100_changed = []
        self.actions_pushed_changed = []

        self.armature_name = ""
        self.armature_add_name = ""
        self.message_final = ""
        self.non_armature_actions = []
        self.shape_keys_data = {}

        target_armature_name = ""
        list_target_objects = []
        list_target_actions = []

        no_armature_mode = False

        mode_skeleton_only = self.mode_export_animation_only
        mode_fix_duplicated_name = self.mode_auto_fix_duplicated_name

        mode_insert_rootbone = self.mode_auto_insert_rootbone

        try:
            # Initial checks

            # Is target armature selected?
            if bpy.context.active_object is None:
                self.report({"ERROR"}, "Select the armature to export")
                return {"FINISHED"}

            self.current_selection = [
                bpy.context.active_object.name,
                [i.name for i in bpy.context.selected_objects],
            ]

            # Set the armature as active object (if any)
            if not is_armature(bpy.context.active_object):
                for obj in bpy.context.selected_objects:
                    if is_armature(obj):
                        set_active_object(obj.name)
                        break

            if not is_armature(bpy.context.active_object):
                # TODO Need Implemetnt NO ARMATURE mode
                no_armature_mode = True
                print("NO ARMATURE MODE")

                selected_parent = [obj for obj in bpy.context.selected_objects if obj.parent is None]

                if len(selected_parent) == 0:
                    self.report(
                        {"ERROR"},
                        "No root object detected. Plase select target object(s) structure include root.",
                    )
                    return {"FINISHED"}

                if len(selected_parent) > 1:
                    self.report(
                        {"ERROR"},
                        "Multi root object detected. Please select single structure.",
                    )
                    return {"FINISHED"}

                target_armature_name = selected_parent[0].name

            # Set main target armature name
            target_armature_name = bpy.context.active_object.name

            # Disable auto-keyframe
            context.scene.tool_settings.use_keyframe_insert_auto = False

            # Create copy objects
            list_target_objects = create_copy_objects(target_armature_name, no_armature_mode, mode_skeleton_only)
            list_target_actions = [a.name for a in bpy.data.actions]

            if mode_insert_rootbone:
                insert_root_bone(target_armature_name)

            if no_armature_mode:
                apply_scale_x100_no_armature(list_target_objects)
            else:
                apply_scale_x100(target_armature_name)

            apply_action_scale_x100(list_target_actions)

            # Select exportable only
            select_objects(list_target_objects)
            rename_objects_for_export(list_target_objects, mode_fix_duplicated_name)

            object_types = {"EMPTY", "ARMATURE", "MESH"}

            if mode_skeleton_only:
                object_types = object_types - {"MESH"}

            
            export_actions = []

            if self.mode_export_animations == "ALL":
                export_actions = [act.name for act in bpy.data.actions]
            if self.mode_export_animations == "SELECT":
                export_actions = [act.name for act in bpy.data.actions if act.sket_export_action]

            if self.mode_export_separate_each_anims:
                basefilepath = pathlib.Path(self.filepath)

                for export_act in export_actions:
                    filepath = basefilepath.parent / f"{basefilepath.stem}_{export_act}{basefilepath.suffix}"

                    print(f"Export file: {filepath}")

                    # Actionに出力用のタグを設定する
                    for act in bpy.data.actions:
                        if act.name == export_act:
                            act[SKET_TAG_EXPORT] = True
                            print(f"Set Export Target:{act.name}")
                        else:
                            act[SKET_TAG_EXPORT] = False
                            print(f"Set no export target:{act.name}")

                    bpy.ops.sket_export_scene.fbx(
                        filepath=str(filepath),
                        use_selection=True,
                        # TODO DEBUG
                        global_scale=self.global_scale,
                        use_mesh_modifiers=True,
                        use_armature_deform_only=self.use_armature_deform_only,
                        add_leaf_bones=False,
                        apply_unit_scale=True,
                        # TODO debug
                        # humanoid_actions=context.scene.sket_export_h_actions,
                        # TODO debug
                        # bake_anim_simplify_factor=context.scene.sket_simplify_fac,
                        mesh_smooth_type=self.mesh_smooth_type,
                        primary_bone_axis=self.bone_axis_primary_export,
                        secondary_bone_axis=self.bone_axis_secondary_export,
                        # TODO debug
                        # shape_keys_baked_data=str(self.shape_keys_data)
                        object_types=object_types,
                    )

            else:
                # Actionに出力用のタグを設定する
                for act in bpy.data.actions:
                    if act.name in export_actions:
                        act[SKET_TAG_EXPORT] = True
                    else:
                        act[SKET_TAG_EXPORT] = False

                bpy.ops.sket_export_scene.fbx(
                    filepath=self.filepath,
                    use_selection=True,
                    # TODO DEBUG
                    global_scale=self.global_scale,
                    use_mesh_modifiers=True,
                    use_armature_deform_only=self.use_armature_deform_only,
                    add_leaf_bones=False,
                    apply_unit_scale=True,
                    # TODO debug
                    # humanoid_actions=context.scene.sket_export_h_actions,
                    # TODO debug
                    # bake_anim_simplify_factor=context.scene.sket_simplify_fac,
                    mesh_smooth_type=self.mesh_smooth_type,
                    primary_bone_axis=self.bone_axis_primary_export,
                    secondary_bone_axis=self.bone_axis_secondary_export,
                    # TODO debug
                    # shape_keys_baked_data=str(self.shape_keys_data)
                )

        finally:
            # 出力用のタグは削除しておく
            for act in bpy.data.actions:
                if SKET_TAG_EXPORT in act.keys():
                    del act[SKET_TAG_EXPORT]

            revert_object_name(list_target_objects)
            revert_action_scale_x100(list_target_actions)

            delete_copy_objects(list_target_objects)

            # 設定値を戻す
            context.scene.unit_settings.scale_length = self.save_units
            context.scene.unit_settings.system = self.save_unit_type
            context.scene.tool_settings.use_keyframe_insert_auto = self.save_auto_key

            # Collectionの表示を戻す
            for i, vis in enumerate(self.save_collection_vis):
                bpy.data.collections[i].hide_viewport = vis

            # 選択状態を戻す
            set_active_object(self.current_selection[0])
            for obj in self.current_selection[1]:
                bpy.data.objects[obj].select_set(True)

            bpy.context.evaluated_depsgraph_get().update()

        self.report({"INFO"}, "SKET: Export success")
        return {"FINISHED"}


class SKET_OT_set_action_data_tag(bpy.types.Operator):
    bl_idname = "sket.set_action_data_tag"
    bl_label = "SKET set action data tag"

    action_name: bpy.props.StringProperty(default="")
    tag: bpy.props.StringProperty(default="")

    mode: bpy.props.EnumProperty(
        items=(("ADD", "Add", "Add tag"), ("REMOVE", "Remove", "Remove tag"), ("TOGGLE", "Toggle", "Toggle tag")),
        default="TOGGLE",
    )

    def execute(self, context):
        global_undo = context.preferences.edit.use_global_undo

        try:
            context.preferences.edit.use_global_undo = False

            if self.action_name != "":
                act = bpy.data.actions.get(self.action_name)

                print(f"ActionName={self.action_name}, Tag={self.tag}, Mode={self.mode}")

                if act:
                    if self.mode == "ADD":
                        act[self.tag] = True

                    if self.mode == "REMOVE":
                        if self.tag in act.keys():
                            del act[self.tag]

                    if self.mode == "TOGGLE":
                        if self.tag in act.keys():
                            act[self.tag] = not act[self.tag]
                        else:
                            act[self.tag] = True

        finally:
            context.preferences.edit.use_global_undo = global_undo

        return {"FINISHED"}


class SKET_OT_set_export_all_actions(bpy.types.Operator):
    bl_idname = "sket.set_export_all_actions"
    bl_label = "Select All"
    bl_description = "Set to export all (or filtered) actions"

    action_filter: bpy.props.StringProperty(default="")

    def execute(self, context):
        flt_flags = []
        helper_funcs = bpy.types.UI_UL_list
        acts = bpy.data.actions

        if self.action_filter:
            flt_flags = helper_funcs.filter_items_by_name(self.action_filter, 1, acts, "name")
        if not flt_flags:
            flt_flags = [1] * len(acts)

        for act, flg in zip(bpy.data.actions, flt_flags):
            if flg:
                act.sket_export_action = True

        return {"FINISHED"}


class SKET_OT_set_notexport_all_actions(bpy.types.Operator):
    bl_idname = "sket.set_notexport_all_actions"
    bl_label = "Unselect All"
    bl_description = "Set to not export all (or filtered) actions"

    action_filter: bpy.props.StringProperty(default="")

    def execute(self, context):
        flt_flags = []
        helper_funcs = bpy.types.UI_UL_list
        acts = bpy.data.actions

        if self.action_filter:
            flt_flags = helper_funcs.filter_items_by_name(self.action_filter, 1, acts, "name")
        if not flt_flags:
            flt_flags = [1] * len(acts)

        for act, flg in zip(bpy.data.actions, flt_flags):
            if flg:
                act.sket_export_action = False

        return {"FINISHED"}


classes = (
    SKET_PT_export_fbx_panel,
    SKET_PT_export_mode,
    SKET_PT_export_mesh,
    SKET_PT_export_mesh_axis,
    SKET_PT_export_mesh_options,
    SKET_PT_export_actions,
    SKET_OT_export_fbx,
    SKET_OT_set_export_all_actions,
    SKET_OT_set_notexport_all_actions,
    SKET_OT_set_action_data_tag,
    SKET_UL_export_actions,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Action.sket_export_action = bpy.props.BoolProperty(
        name="Export Action", description="Export animation when export fbx", default=True
    )


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Action.sket_export_action
