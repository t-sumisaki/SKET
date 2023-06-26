# Blender から FBX を出力するときのルール

## Mesh と Armature の設定

- Armature は 0.01 倍にする必要がある

FBX を UnrealEngine にインポートするとき、UnrealEngine 側で 100 倍されるため
Armature は 0.01 倍にする必要がある

- 同じ Skeleton を使った AnimSequence を再生するだけなら問題はない
- 物理シミュレーション（揺れもの、ラグドール、布）を行う場合、不具合が起こる可能性がある
- AnimSequence をリターゲットする場合、スケールの違いにより、うまくリターゲットができない場合がある

### Animation 対応

- Action のスケールを Armature に合わせる必要がある

Armature のスケールを 0.01 倍する関係上、Translation を 100 倍で作成しなければならない  
あとから Armature のスケールを 0.01 すると、Translation も 0.01 倍されるため、Action が破綻する

## 命名に関する規則

### Armature

- Blender から FBX を出力するとき、Armature の名前は `Armature` でなければならない

FBX を UnrealEngine にインポートするとき、FBX が Blender から出力されていると認識した場合
UnrealEngine は `Armature` と名前のついたノードをノード階層からスキップするようになっている

Armature に `Armature` 以外の名前がついている場合、 Armature を取り除くことができず
Armature が Root として扱われる

### Object(Bone、Mesh)

- 同一名称のオブジェクト（Bone、Mesh）が存在する場合、Warning が発生し、命名重複の回避が行われる

FBX を UnrealEngine にインポートするとき、Node 名が重複している場合、Warning が発生する
同時に、どちらかの名前を変更して問題の解決が行われる

このとき、Bone 名が変更されると、AnimSequence の方に問題が出てくる可能性があるため、事前の解決が必要
