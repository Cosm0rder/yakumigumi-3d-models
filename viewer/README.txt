しょうがちゃん・にんにく用 Three.js r180 viewer

モデルは v1.2.0 Release のZIPから展開してください。旧v1.1.0のGLBも対応profileを保持しています。
https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.2.0
旧版: https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.1.0

このリポジトリを Code → Download ZIP で取得して展開します。
viewer フォルダーで次を実行し、ブラウザーで http://127.0.0.1:8000/ を開きます。
python -m http.server 8000 --bind 127.0.0.1

「展開したモデルのGLBを選択」で Ginger_rigged.glb または v1.2.0の Garlic_body_motion.glb を指定します。
旧v1.1.0の Garlic_rigged.glb も読み込めます。SHA256で版を識別し、対応する操作へ切り替えます。
ファイルはブラウザー内で読み、外部へアップロードしません。
SHA256はGLTFLoaderが読む同じバイト列から計算し、検証結果に表示します。
配布GLBのSHA256に一致したprofileだけで動作検証します。未知・改変GLBを既存profileで合格にはしません。

休止・2種類の動作・再生/停止・正面/斜め/側面・ドラッグ回転・スクロール距離を操作できます。
縦横比に応じて全身を収めるカメラ距離を更新し、手動ズームの相対倍率は維持します。

v1.2.0のにんにくは追加手足を削除し、root/bodyの2ボーンで跳ね・傾きを動かします。
24 fps・4秒。休止frame0/0秒、跳ねframe12/0.5秒、傾きframe36/1.5秒です。
ボタンも「跳ね」「傾き」へ切り替わります。跳ねはrootの上移動0.075、傾きはbodyの8度回転を測り、実変形頂点の移動と手足nodeの不存在を検査します。
しょうがちゃんと旧v1.1.0のにんにくは6ボーンの手足FKです。
腕・脚は支配ウェイトを持つ頂点の実変形を左右それぞれ検査し、旧版と同じ16項目を保持しています。
旧サンプルはBlender frame1/7/13 → 1/12,7/12,13/12秒、Three.jsのclip durationは2.083333秒です。

塗装はCOLOR_0頂点色で、画像mapが0件なのは仕様です。全メッシュの色データと材質使用を検査します。
材質はPBR近似、にんにくの顔ドライバーはBlender限定で、.blendを外観の基準とします。

この追加viewerは既存のモデルRelease ZIPを置き換えません。
独自viewerコードはCC0。vendor内Three.jsはMIT（vendor/THREE_LICENSE.txt）。
