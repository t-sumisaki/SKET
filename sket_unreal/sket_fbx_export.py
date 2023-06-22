from typing import List
import bpy
from bpy.types import Context
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
)

import pathlib


def get_export_actions(context) -> List[str]:
    export_actions = []

    if context.scene.sket_mode_export_animations == SKET_E_MODE_EXPORT_ANIM_NONE:
        return export_actions

    for act in bpy.data.actions:
        if context.scene.sket_mode_export_animations == SKET_E_MODE_EXPORT_ANIM_SELECT:
            if SKET_TAG_ACTION_EXCLUDE in act.keys() and act[SKET_TAG_ACTION_EXCLUDE] == True:
                continue

        export_actions.append(act.name)

    return export_actions


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
        col.operator(SKET_OT_open_export_fbx_dialog.bl_idname, text="Export FBX")


class SKET_OT_open_export_fbx_dialog(bpy.types.Operator, ExportHelper):
    bl_idname = "sket.open_export_fbx_dialog"
    bl_label = "SKET: Export FBX"
    bl_description = "Open Export FBX Dialog"

    filename_ext = ".fbx"
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={"HIDDEN"})

    def draw(self, context):
        layout = self.layout

        self.draw_mode_section(context, layout)

        self.draw_mesh_option_section(context, layout)
        self.draw_animation_section(context, layout)

    def draw_mode_section(self, context, parent):
        box = parent.box()
        box.label(text="Mode:")
        box.column(align=True).prop(context.scene, "sket_mode_export_animation_only")

    def draw_mesh_option_section(self, context, parent):
        if not context.scene.sket_mode_export_animation_only:
            box = parent.box()
            box.label(text="Mesh:")

            # global scale
            box.column(align=True).prop(context.scene, "sket_global_scale")
            # smooth type
            box.column(align=True).prop(context.scene, "sket_mesh_smooth_type")
            # deform armature only
            box.column(align=True).prop(context.scene, "sket_use_armature_deform_only")

            # axis
            axis = box.column(align=True)
            axis.label(text="Bone Axes:")
            axis.prop(context.scene, "sket_bone_axis_primary_export")
            axis.prop(context.scene, "sket_bone_axis_secondary_export")

            exp = box.column(align=True)
            exp.label(text="Experimental:")
            exp.prop(context.scene, "sket_mode_auto_fix_duplicated_name")

    def draw_animation_section(self, context, parent):
        box = parent.box()
        box.label(text="Animations:")

        # export animation
        anim_mode = box.column(align=True)
        anim_mode.label(text="Export Mode:")
        anim_mode.prop(context.scene, "sket_mode_export_animations", text="")

        if context.scene.sket_mode_export_animations == SKET_E_MODE_EXPORT_ANIM_SELECT:
            col = box.column(align=True)

            if len(bpy.data.actions) > 0:
                # Actionを選択する用のボタンを作成
                for act in bpy.data.actions:
                    act_row = col.row(align=True)
                    act_row.label(text=act.name)

                    checkbox = "CHECKBOX_HLT"

                    if SKET_TAG_ACTION_EXCLUDE in act.keys() and act[SKET_TAG_ACTION_EXCLUDE] == True:
                        checkbox = "CHECKBOX_DEHLT"

                    _op = act_row.operator(SKET_OT_set_action_data_tag.bl_idname, text="", icon=checkbox)
                    _op.action_name = act.name
                    _op.tag = SKET_TAG_ACTION_EXCLUDE
                    _op.mode = "TOGGLE"

            else:
                # Actionが存在しない場合はラベルのみ
                col.row(align=True).label(text="No actions to export")

        if context.scene.sket_mode_export_animations in (SKET_E_MODE_EXPORT_ANIM_ALL, SKET_E_MODE_EXPORT_ANIM_SELECT):
            col = box.column(align=True)
            col.prop(context.scene, "sket_mode_export_separate_each_anims", text="Separate FBX each actions")

    def execute(self, context):
        return SKET_OT_export_fbx.execute(self, context)


class SKET_OT_export_fbx(bpy.types.Operator):
    bl_idname = "sket.export_fbx"
    bl_label = "SKET: Export FBX"

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

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

        mode_skeleton_only = context.scene.sket_mode_export_animation_only
        mode_fix_duplicated_name = context.scene.sket_mode_auto_fix_duplicated_name

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

            export_files = []

            if context.scene.sket_mode_export_separate_each_anims:
                basefilepath = pathlib.Path(self.filepath)

                for export_act in get_export_actions(context):
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
                        global_scale=context.scene.sket_global_scale,
                        use_mesh_modifiers=True,
                        use_armature_deform_only=context.scene.sket_use_armature_deform_only,
                        add_leaf_bones=False,
                        apply_unit_scale=True,
                        # TODO debug
                        # humanoid_actions=context.scene.sket_export_h_actions,
                        # TODO debug
                        # bake_anim_simplify_factor=context.scene.sket_simplify_fac,
                        mesh_smooth_type=context.scene.sket_mesh_smooth_type,
                        primary_bone_axis=context.scene.sket_bone_axis_primary_export,
                        secondary_bone_axis=context.scene.sket_bone_axis_secondary_export,
                        # TODO debug
                        # shape_keys_baked_data=str(self.shape_keys_data)
                        object_types=object_types,
                    )

            else:
                # Actionに出力用のタグを設定する

                export_actions = get_export_actions(context)

                for act in bpy.data.actions:
                    if act.name in export_actions:
                        act[SKET_TAG_EXPORT] = True
                    else:
                        act[SKET_TAG_EXPORT] = False

                bpy.ops.sket_export_scene.fbx(
                    filepath=self.filepath,
                    use_selection=True,
                    # TODO DEBUG
                    global_scale=context.scene.sket_global_scale,
                    use_mesh_modifiers=True,
                    use_armature_deform_only=context.scene.sket_use_armature_deform_only,
                    add_leaf_bones=False,
                    apply_unit_scale=True,
                    # TODO debug
                    # humanoid_actions=context.scene.sket_export_h_actions,
                    # TODO debug
                    # bake_anim_simplify_factor=context.scene.sket_simplify_fac,
                    mesh_smooth_type=context.scene.sket_mesh_smooth_type,
                    primary_bone_axis=context.scene.sket_bone_axis_primary_export,
                    secondary_bone_axis=context.scene.sket_bone_axis_secondary_export,
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

                print(f"{self.tag}={act[self.tag]}")

        finally:
            context.preferences.edit.use_global_undo = global_undo

        return {"FINISHED"}


class SKET_OT_set_exclude_action(bpy.types.Operator):
    bl_idname = "sket.set_exclude_action"
    bl_label = "SKET set exclude action"

    bl_description = "set exclude action"

    action_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        global_undo = context.preferences.edit.use_global_undo

        try:
            context.preferences.edit.use_global_undo = False

            if self.action_name != "":
                act = bpy.data.actions.get(self.action_name)

                if act:
                    act[SKET_TAG_ACTION_EXCLUDE] = True

        finally:
            context.preferences.edit.use_global_undo = global_undo

        return {"FINISHED"}


class SKET_OT_unselect_action(bpy.types.Operator):
    bl_idname = "sket.unselect_action"
    bl_label = "SKET unselect action"

    bl_description = "Unselect Action"

    action_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        global_undo = context.preferences.edit.use_global_undo

        try:
            context.preferences.edit.use_global_undo = False

            if self.action_name != "":
                act = bpy.data.actions.get(self.action_name)

                if act:
                    act[SKET_TAG_ACTION_EXCLUDE] = False

        finally:
            context.preferences.edit.use_global_undo = global_undo

        return {"FINISHED"}


classes = (
    SKET_PT_export_fbx_panel,
    SKET_OT_open_export_fbx_dialog,
    SKET_OT_export_fbx,
    SKET_OT_set_exclude_action,
    SKET_OT_unselect_action,
    SKET_OT_set_action_data_tag,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # DeformBoneのみ出力
    bpy.types.Scene.sket_use_armature_deform_only = bpy.props.BoolProperty(
        name="Deform Armature Only",
        description="If True, export only deform (weight-painted) armature",
        default=False,
    )

    # 出力スケール
    bpy.types.Scene.sket_global_scale = bpy.props.FloatProperty(
        name="Global Scale", default=1.0, description="Global scale applied"
    )

    # スムージング種別
    bpy.types.Scene.sket_mesh_smooth_type = bpy.props.EnumProperty(
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
    bpy.types.Scene.sket_bone_axis_primary_export = bpy.props.EnumProperty(
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
    bpy.types.Scene.sket_bone_axis_secondary_export = bpy.props.EnumProperty(
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
    bpy.types.Scene.sket_mode_export_animations = bpy.props.EnumProperty(
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
    bpy.types.Scene.sket_mode_export_separate_each_anims = bpy.props.BoolProperty(
        name="Separate File For Each Animation",
        description="Output a separate file for each animation",
        default=False,
    )

    # Meshを出力せず、Animationのみで出力するか
    bpy.types.Scene.sket_mode_export_animation_only = bpy.props.BoolProperty(
        name="Export Animation Only", description="Output animation without skin mesh", default=False
    )

    bpy.types.Scene.sket_mode_auto_fix_duplicated_name = bpy.props.BoolProperty(
        name="Auto Fix Duplicated Name", description="Auto fix duplicated object name (mesh <-> bone)", default=True
    )


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.sket_use_armature_deform_only
    del bpy.types.Scene.sket_global_scale
    del bpy.types.Scene.sket_mesh_smooth_type
    del bpy.types.Scene.sket_bone_axis_primary_export
    del bpy.types.Scene.sket_bone_axis_secondary_export
    del bpy.types.Scene.sket_mode_export_animations
    del bpy.types.Scene.sket_mode_export_animation_only
    del bpy.types.Scene.sket_mode_export_separate_each_anims
