# Blender-Addon: SkeletalMesh Export Tool for Unreal Engine (SKET)

## About

- UnrealEngine 用の SkeletalMesh を出力するための Blender アドオン
- UnrealEngine 向けに出力する際に必要な、Armature の Scale 修正や Animation の Scale 修正を出力時に自動的に行う

## Support Versions

- Blender 3.2 以降

## インストール方法

### リリースから

- [Releases](https://github.com/t-sumisaki/SKET/Releases) から `sket_unreal_vx.x.x.zip` を取得する
- Blender のアドオン設定で、取得した zip ファイルをアドオンとしてインストールする

### ソースから

- リポジトリをダウンロードする
- `sket_unreal` フォルダを zip 圧縮する
- Blender のアドオン設定で、作成した zip ファイルをアドオンとしてインストールする

## 機能

- [x] FBX 出力 (v1.0.0)
- [x] Action(AnimSequence)の選択出力 (v1.1.0)
- [x] Action ごとの FBX 出力 (v1.1.0)
- [x] Animation のみの出力 (v1.1.0)
- [x] Armature 名の自動修正 (v1.1.0)
- [x] Bone と Mesh の名前重複の自動修正 (v1.2.0)
- [x] 出力時に原点に RootBone を挿入する機能 (v1.2.0)
- [x] スクリプトによる出力対応 (v1.3.0)
- [ ] Blender のビルトイン Exporter のオプション項目対応の修正 (~~v1.3.0~~ 未定)
- [ ] `Import Meshes in Bone Hierarchy` オプションへの対応機能の修正 (~~v1.3.0~~ 未定)
- [ ] SkeletalMesh Validation
