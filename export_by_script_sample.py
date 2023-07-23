import bpy
import pathlib


# 外部からの呼び出し方法については以下を確認
# https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html


if __name__ == "__main__":

    # 出力FBXパスを作成
    p = pathlib.Path(bpy.data.filepath)
    output_path = p.with_suffix(".fbx")


    # アニメーションを指定して出力する場合
    # sket_export_actionにTrueを設定し、mode_export_animations="SELECT" を指定する
    export_actions = ["Idle"]    
    for act in bpy.data.actions:
        act.sket_export_action = act.name in export_actions

    bpy.ops.sket.export_fbx(filepath=str(output_path), mode_export_animations="SELECT", mode_export_separate_each_anims=True)
    
    print("exported:", output_path)

    
    