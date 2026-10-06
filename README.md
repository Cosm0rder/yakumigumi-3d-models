# やくみ組 3Dモデル

ねぎ・わさび・からし・ゆず・唐辛子・みょうが・オクラ・大根おろし・サンショウの、手足を動かせる3Dモデルです。原画の輪郭と表情を参照し、厚みのある編集可能なメッシュと、新しい色鉛筆風の塗装を制作しました。

**モデル・材質・リグ・オリジナル動作・制作スクリプトはCC0です。商用利用、改変、再配布を許可します。クレジット表記は任意です。** 同梱Three.jsのコードはMITライセンスです。

## ダウンロード

[v1.0.0 配布ファイル](https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.0.0) のZIPを展開してください。各モデルのBlenderファイル、GLB、テクスチャ、短い動作確認MP4、プレビュー、操作説明、制作コードと検証結果を同梱しています。

| フォルダー | キャラクター |
|---|---|
| `batch-01-negi-wasabi-mustard` | ねぎ・わさび・からし |
| `batch-02-yuzu-chili-myoga` | ゆず・唐辛子・みょうが |
| `batch-03-okra-daikon-sansho` | オクラ・大根おろし・サンショウ |

## プレビュー

独自モデルのプレビューです。1枚目は最終GLB3体のThree.js全身表示、2・3枚目はBlenderでの手足なし・休止・腕・脚・GLB再読込の比較です。

![ねぎ・わさび・からし](batch1-preview.png)

![ゆず・唐辛子・みょうが](batch2-preview.png)

![オクラ・大根おろし・サンショウ](batch3-preview.png)

## Blenderで使う

1. 各バッチの `models/*_rigged.blend` をBlender 4.3.2以降で開きます。
2. リグを選びPose Modeに切り替えます。`arm.L` / `arm.R` が腕、`leg.L` / `leg.R` が脚です。`body` と `root` は全体を動かすために使います。
3. 同梱の `*_FK_motion_check` を再生すると手足の動きを確認できます。自分の動作を作るときは、このActionを複製するか新しいActionへ切り替えてください。

追加した短い手足は別Collectionです。Collectionを非表示にすると、原画に近い手足なしの形を確認できます。からしのキャップと中身、オクラの薄切り、大根おろしのおろし板も別オブジェクトです。細かな操作は各バッチの `docs/RIG_USAGE.md` を参照してください。

## Three.jsで使う

GLBにはメッシュ、テクスチャ、6ジョイントのスキンと動作を格納しています。ZIPの展開先でローカルサーバーを起動し、`viewer/` を開くと1体ずつ読み込み・回転・再生・動作検証できます。

```sh
python -m http.server 8000 --bind 127.0.0.1
```

ブラウザーで `http://127.0.0.1:8000/viewer/` を開いてください。Three.jsのGLTFLoaderは骨名の `.` を取り除くため、JavaScript側では `armL` / `armR` / `legL` / `legR` になります。

## 制作と検証

各生成スクリプトは数式と制御点から形状を作り、固定seedのノイズから塗装を作ります。原画の画像ファイルや既存モデルを読み込みません。Blenderの新しいプロセスでモデルを開き直し、ウェイト、手足の変形、テクスチャ、GLBの再読込を確認しました。Three.jsでも最終GLB9体の休止・腕・脚を実行検証し、読込バイト列のSHA256を配布ファイルと照合しました。モデル別結果は配布の `runtime_validation.json` にあります。詳しい検証範囲と可動範囲は [VALIDATION.md](VALIDATION.md) と各バッチの検証JSONを参照してください。

外観の基準は同梱の `.blend` とそのレンダーです。GLBのPBR材質は光源や表示エンジンによって色・陰影が変わります。操作は6本のFKコントロールで、サンショウの尾は `body` に追従します。

このリポジトリには制作スクリプトを掲載し、完成モデル一式をRelease ZIPとして配布します。再生成する例：

```sh
blender --factory-startup --background --threads 2 --python 01_create_models.py -- --out batch-01-negi-wasabi-mustard --audit local-audit
```

生成したデータは新規に作った追加キャラクターのモデルです。既存のしょうが・にんにくの完成モデルは、この配布には含めていません。
