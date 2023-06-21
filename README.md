# SKET: SkeletalMesh Export Tool for Unreal Engine

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

- [x] FBX 出力
- [ ] SkeletalMesh Validation
- [x] Action(AnimSequence)の選択出力
- [x] Action ごとの FBX 出力
- [x] Animation のみの出力
