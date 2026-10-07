# やくみ組 3Dモデル v1.3.0

11体のBlenderモデル・GLB・自作テクスチャ・確認画像を配布します。わさび、ねぎ、からし、唐辛子、大根おろし、ゆず、サンショウ、しょうが、にんにくは原作画像を確認した版です。**みょうが・オクラは暫定版で、原作形状は未確認です。**

[全11体の一括ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-all-11-v1.3.0.zip) · [Releaseページ](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.3.0) · [SHA256一覧](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/SHA256SUMS.txt) · [検証記録](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/VALIDATION.json)

| キャラクター | 状態 | 個別ダウンロード |
|---|---|---|
| わさび | 原作画像照合版 | [わさび（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Wasabi-v1.3.0.zip) |
| ねぎ | 原作画像照合版 | [ねぎ（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Negi-v1.3.0.zip) |
| からし | 原作画像照合版 | [からし（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Mustard-v1.3.0.zip) |
| 唐辛子 | 原作画像照合版 | [唐辛子（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Chili-v1.3.0.zip) |
| 大根おろし | 原作画像照合版 | [大根おろし（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Daikon-v1.3.0.zip) |
| ゆず | 原作画像照合版 | [ゆず（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Yuzu-v1.3.0.zip) |
| サンショウ | 原作画像照合版 | [サンショウ（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Sansho-v1.3.0.zip) |
| しょうが | 原作画像照合版 | [しょうが（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Ginger-v1.3.0.zip) |
| にんにく | 原作画像照合版 | [にんにく（原作画像照合版）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Garlic-v1.3.0.zip) |
| みょうが | 暫定版・原作形状未確認 | [みょうが（暫定版・原作形状未確認）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Myoga-v1.3.0.zip) |
| オクラ | 暫定版・原作形状未確認 | [オクラ（暫定版・原作形状未確認）個別ZIP](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/download/v1.3.0/yakumigumi-Okra-v1.3.0.zip) |

## 使い方

1. ZIPを展開し、`characters/キャラクター名/model.blend` をBlenderで開きます。Blender 4.3.2で再読込を確認しています。テクスチャはモデルにパックしてあり、編集用PNGも同梱しています。
2. ポーズや動きはArmatureのPose Modeと既存Actionで操作します。各キャラクターの `README.md` にボーンと動作の説明があります。
3. `model.glb` は必要なリソースを内蔵したglTF 2.0ファイルです。GLBに対応するアプリで読み込めます。しょうが・にんにくは頂点色とPBR材質で塗りを表し、他の9体は画像テクスチャを埋め込んでいます。
4. `previews/` の画像、動画のある9体は `motion_1080p.mp4` で質感と動きを確認できます。動画は1080×1080・24fpsで、7体は3秒、しょうが・にんにくは4秒です。

Blenderの材質・照明・色管理で作った見た目と、GLBのPBR表示には差があります。GLBの色や質感は読み込むアプリの照明と色管理にも影響されます。外見の編集基準は `.blend` と同梱のBlenderレンダリングです。

## 主な仕様

- しょうが：原作の腕2本・脚2本を保持。`root`、`body`、`arm.L`、`arm.R`、`leg.L`、`leg.R` の6ボーンでFK動作を操作できます。
- にんにく：追加の手足を除いた本体と顔のモデル。15メッシュ、`root` と `body` の2ボーンで跳ね・傾きを操作できます。
- サンショウ：確認できた短い脚3本を保持。`root` と `body` の2ボーンで本体を揺らします。
- みょうが・オクラ：旧版のモデルとFKリグを収録する暫定版です。手足を含む形状の原作照合は未完了です。

みょうが・オクラのGLBには、Blenderでスキニングを評価したときに一部の法線の長さが1未満になる旧版の制約があります（最小約0.941692）。元GLBと公開GLBの9ポーズの位置・法線は一致し、すべて有限で法線の長さは0より大きいことを確認しています。公開用の整理による形状の変更はありません。

公開用コピーのモデル再読込、リグ・アニメーション、GLBの埋め込み画像、動画の映像データを検証しています。公開用メタデータ整理によって形状・材質・アニメーションや画像の画素は変更していません。検証範囲と各ファイルのSHA256は `VALIDATION.json`、`manifest.json`、`SHA256SUMS.txt` に記録しています。

## ライセンス

収録モデル・テクスチャ・プレビュー・動画は **CC0 1.0 Universal** です。商用利用・改変・再配布に利用できます。許可申請とクレジット表記は不要です。ライセンス全文は同梱の `LICENSE` を参照してください。

## 過去のRelease

- [v1.2.0：しょうが・手足のないにんにく](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.2.0)
- [v1.1.0：旧しょうが・にんにく](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.1.0)
- [v1.0.0：旧追加キャラクター9体](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.0.0)

過去のReleaseは保持しています。リポジトリの [既存ビューア](https://github.com/Cosm0rder/yakumigumi-3d-models/tree/main/viewer) は旧しょうが・にんにくの確認用です。v1.3.0の11体は、このReleaseの各ZIPに入っている `.blend` / GLBを使用してください。
