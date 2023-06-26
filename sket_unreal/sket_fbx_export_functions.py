import bpy

from typing import List, Any


from .sket_common import (
    # Constants
    SKET_EXPORT_OBJ_SUFFIX,
    SKET_EXPORT_WORK_OBJ_SUFFIX,
    SKET_EXPORT_DUMMYMESH_NAME,
    SKET_NAME_ARMATURE,
    # Functions
    is_object_hidden,
    set_active_object,
    set_hidden_object,
    is_mesh,
    is_armature,
    is_empty,
    get_object_relation_depth,
)


def create_copy_objects(armature_name: str, no_armature_mode=False, force_dummy_mesh=False) -> List[str]:
    copy_armature_name = armature_name + SKET_EXPORT_OBJ_SUFFIX

    list_stored_actions = [action.name for action in bpy.data.actions]
    if no_armature_mode:
        list_char_objects = [obj.name for obj in bpy.context.selected_objects]
    else:
        list_char_objects = get_skeletalmesh_objects(armature_name, force_dummy_mesh)

    list_copy_objects: List[str] = []

    set_active_object(armature_name)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")

    for obj_name in list_char_objects:
        set_hidden_object(bpy.data.objects[obj_name], hidden=False)
        selectable_state = bpy.data.objects[obj_name].hide_select
        bpy.data.objects[obj_name].hide_select = False

        bpy.context.evaluated_depsgraph_get().update()
        set_active_object(obj_name)

        bpy.ops.object.mode_set(mode="OBJECT")

        # Duplicate and rename
        current_obj_in_scene = [o.name for o in bpy.data.objects]
        bpy.ops.object.duplicate(linked=False, mode="TRANSLATION")

        for o in bpy.data.objects:
            if o.name not in current_obj_in_scene:
                set_hidden_object(o, hidden=False)
                set_active_object(o.name)

        # Set duplicated object name
        copy_object_name = obj_name + SKET_EXPORT_OBJ_SUFFIX

        bpy.context.active_object.name = copy_object_name

        bpy.ops.object.select_all(action="DESELECT")

        # Restore selectable state
        bpy.data.objects[obj_name].hide_select = selectable_state

        # add to list
        list_copy_objects.append(copy_object_name)

    if no_armature_mode:
        # Reparent duplicate objects
        for obj_name in list_copy_objects:
            copy_obj = bpy.data.objects[obj_name]
            if copy_obj.parent is not None:
                reparent_name = copy_obj.parent.name + SKET_EXPORT_OBJ_SUFFIX
                copy_obj_mat = copy_obj.matrix_world.copy()
                copy_obj.parent = bpy.data.objects[reparent_name]
                copy_obj.matrix_world = copy_obj_mat

    else:
        # Reparent meshes to armature
        for obj_name in list_copy_objects:
            copy_obj = bpy.data.objects[obj_name]
            if is_mesh(copy_obj):
                copy_obj_mat = copy_obj.matrix_world.copy()
                copy_obj.parent = bpy.data.objects[copy_armature_name]
                copy_obj.matrix_world = copy_obj_mat

        # Reset armature target object
        for obj_name in list_copy_objects:
            copy_obj = bpy.data.objects[obj_name]
            if is_mesh(copy_obj):
                if len(copy_obj.modifiers) > 0:
                    for mod in copy_obj.modifiers:
                        if is_armature(mod):
                            if mod.object is not None:
                                if mod.object.name == armature_name:
                                    mod.object = bpy.data.objects[copy_armature_name]

    for action in bpy.data.actions:
        if not action.name in list_stored_actions:
            bpy.data.actions.remove(action, do_unlink=True)

    return list_copy_objects


def delete_copy_objects(list_target_objects):
    arm_data = None
    for obj_name in list_target_objects:
        if obj_name in bpy.data.objects:
            obj = bpy.data.objects[obj_name]

            if is_armature(obj):
                arm_data = bpy.data.armatures.get(obj.data.name)


            try:
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.armatures.remove(arm_data, do_unlink=True)
            except:
                pass

    for mesh in bpy.data.meshes:
        if SKET_EXPORT_DUMMYMESH_NAME in mesh.name:
            bpy.data.meshes.remove(mesh, do_unlink=True)


def rename_objects_for_export(list_target_objects : List[str], fix_duplicated_name=False):

    # Bone名の一覧を取得
    # チェックはLowerCaseに統一して行う
    bones = [bone.name.lower() for bone in bpy.data.armatures[0].bones]

    print(f"bones: {bones}")

    renamed_obj = []

    # 対象となるObjectのオリジナルを一時的に別名にして退避する
    for obj_name in list_target_objects:
        origin_obj_name = obj_name.replace(SKET_EXPORT_OBJ_SUFFIX, "")
        if bpy.data.objects.get(origin_obj_name):
            bpy.data.objects[origin_obj_name].name = origin_obj_name + SKET_EXPORT_WORK_OBJ_SUFFIX

            # 参照で取る
            obj = bpy.data.objects[obj_name]

            # HACK: Armature名はUnrealEngine側で決まっているので、Armature名は固定値とする
            if is_armature(obj):
                obj.name = SKET_NAME_ARMATURE
            else:
                obj.name = origin_obj_name
            
            if fix_duplicated_name:
                print(f"check duplicated: {obj.name}")
                if is_mesh(obj) and obj.name.lower() in bones:
                    print(f"rename duplicated: {obj.name}")
                    obj.name = obj.name + "_mesh"

                    renamed_obj.append(obj.name)

    list_target_objects.extend(renamed_obj)


def revert_object_name(list_target_objects):
    # 退避したオリジナルのObjectをもとに戻す
    for obj_name in list_target_objects:
        origin_obj_name = obj_name.replace(SKET_EXPORT_OBJ_SUFFIX, "")
        base_obj_name = origin_obj_name + SKET_EXPORT_WORK_OBJ_SUFFIX

        if bpy.data.objects.get(origin_obj_name):
            bpy.data.objects[origin_obj_name].name = obj_name

        if bpy.data.objects.get(base_obj_name):
            bpy.data.objects[base_obj_name].name = origin_obj_name


def get_skeletalmesh_objects(armature_name: str, force_dummy_mesh=False) -> List[str]:
    """SkeletalMesh用のオブジェクト名を取得する"""
    skl_objects = []

    #
    skl_objects.append(armature_name)

    if not force_dummy_mesh:
        for obj in bpy.data.objects:
            # Meshであり、非表示でないもの
            print("obj name:", obj.name, is_mesh(obj), is_object_hidden(obj))
            if is_mesh(obj) and not is_object_hidden(obj):
                print("check mods: ", len(obj.modifiers))
                for mod in obj.modifiers:
                    print("mod:", mod.name, mod.type)
                    if is_armature(mod) and mod.show_viewport:
                        if mod.object is not None:
                            if mod.object.name == armature_name:
                                print("found obj:", obj.name)
                                skl_objects.append(obj.name)
                                break

    if len(skl_objects) == 1:
        dummy_obj = _create_dummy_mesh()
        new_mod = dummy_obj.modifiers.new(type="ARMATURE", name="rig")
        new_mod.object = bpy.data.objects[armature_name]
        skl_objects.append(dummy_obj.name)

    print("SkeletalMesh Objects:", skl_objects)
    return skl_objects


def _create_dummy_mesh(name=SKET_EXPORT_DUMMYMESH_NAME):
    """ダミーメッシュ情報を作成する"""

    # Create dummy mesh
    dummy_mesh = bpy.data.meshes.new(name)
    dummy_obj = bpy.data.objects.new(name, dummy_mesh)
    # Link to collection
    bpy.context.scene.collection.objects.link(dummy_obj)

    return dummy_obj


def apply_scale_x100(armature_name: str):
    """スケール100倍を適用する"""

    scene = bpy.context.scene
    rig_arm = bpy.data.objects[armature_name + SKET_EXPORT_OBJ_SUFFIX]

    meshes = []

    for obj in bpy.data.objects:
        if is_mesh(obj):
            if len(obj.modifiers) > 0:
                for mod in obj.modifiers:
                    if is_armature(mod):
                        if mod.object == rig_arm:
                            meshes.append(obj)

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")

    set_active_object(rig_arm.name)
    rig_arm.scale *= 100
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.evaluated_depsgraph_get().update()

    rig_arm.scale *= 0.01
    bpy.ops.object.select_all(action="DESELECT")

    for mesh in meshes:
        set_active_object(mesh.name)

    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.evaluated_depsgraph_get().update()

    bpy.ops.object.select_all(action="DESELECT")


def apply_scale_x100_no_armature(target_meshes):
    """スケール100倍を適用する"""
    relation = []

    # FIX: create relation list
    for mesh in target_meshes:
        mesh_obj = bpy.data.objects[mesh]
        relation.append(
            {
                "name": mesh_obj.name,
                "parent_name": mesh_obj.parent.name if mesh_obj.parent is not None else "",
                "depth": get_object_relation_depth(mesh_obj),
            }
        )

    for mesh in [x["name"] for x in sorted(relation, key=lambda i: i["depth"], reverse=True)]:
        mesh_obj = bpy.data.objects[mesh]

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")

        set_active_object(mesh_obj.name)
        # to x100
        mesh_obj.scale *= 100
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        mesh_obj.scale *= 0.01
        bpy.context.evaluated_depsgraph_get().update()


def apply_action_scale_x100(list_target_actions):
    for action_name in list_target_actions:
        action = bpy.data.actions[action_name]
        for fcurve in action.fcurves:
            if "location" in fcurve.data_path:
                for point in fcurve.keyframe_points:
                    point.co[1] *= 100
                    point.handle_left[1] *= 100
                    point.handle_right[1] *= 100


def revert_action_scale_x100(list_target_actions):
    for action_name in list_target_actions:
        action = bpy.data.actions[action_name]
        for fcurve in action.fcurves:
            if "location" in fcurve.data_path:
                for point in fcurve.keyframe_points:
                    point.co[1] *= 0.01
                    point.handle_left[1] *= 0.01
                    point.handle_right[1] *= 0.01


def revert_scale_x100(armature_name):
    """Revert armature scales"""

    rig_arm = bpy.data.objects[armature_name + SKET_EXPORT_OBJ_SUFFIX]

    meshes = []

    for obj in bpy.data.objects:
        if is_mesh(obj):
            if len(obj.modifiers) > 0:
                for mod in obj.modifiers:
                    if mod.type == "ARMATURE":
                        if mod.object == rig_arm:
                            meshes.append(obj)

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")

    set_active_object(rig_arm.name)
    rig_arm.scale *= 100

    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.ops.object.select_all(action="DESELECT")

    for mesh in meshes:
        set_active_object(mesh.name)
        mesh.scale *= 0.01

    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bpy.ops.object.select_all(action="DESELECT")

    # TODO revert animation curves

def insert_root_bone(armature_name: str):

    print(armature_name)

    print([arm.name for arm in bpy.data.armatures])
    print([obj.name for obj in bpy.data.objects if is_armature(obj)])

    # TODO: 汎用的に使える関数にする
    arm_name = armature_name + SKET_EXPORT_OBJ_SUFFIX

    arm_obj = bpy.data.objects[arm_name]
    set_active_object(arm_obj.name)
    bpy.ops.object.mode_set(mode="EDIT", toggle=False)


    arm = bpy.data.armatures[arm_obj.data.name]
    c_root = [bone for bone in arm.bones if bone.parent is None]

    if len(c_root) != 1:
        return
    
    c_root = c_root[0]

    ebs = arm.edit_bones

    eb = ebs.new("root")
    eb.head = (0, 0, 0)
    eb.tail = (0, 1, 0)

    ebs[c_root.name].parent = eb

    bpy.ops.object.mode_set(mode="OBJECT", toggle=False)




