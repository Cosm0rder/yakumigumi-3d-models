しょうがちゃん・にんにく用 Three.js r180 viewer

モデルは v1.1.0 Release のZIPから展開してください。
https://github.com/Cosm0rder/yakumigumi-3d-models/releases/tag/v1.1.0

このリポジトリを Code → Download ZIP で取得して展開します。
viewer フォルダーで次を実行し、ブラウザーで http://127.0.0.1:8000/ を開きます。
python -m http.server 8000 --bind 127.0.0.1

「展開したモデルのGLBを選択」で Ginger_rigged.glb または Garlic_rigged.glb を指定します。
ファイルはブラウザー内で読み、外部へアップロードしません。
SHA256はGLTFLoaderが読む同じバイト列から計算し、検証結果に表示します。

手足のポーズ・再生/停止・正面/斜め/側面・ドラッグ回転・スクロール距離を操作できます。
縦横比に応じて全身を収めるカメラ距離を更新し、手動ズームの相対倍率は維持します。
腕・脚は支配ウェイトを持つ頂点の実変形を左右それぞれ検査します。
塗装はCOLOR_0頂点色で、画像mapが0件なのは仕様です。全メッシュの色データと材質使用を検査します。
GLBの既存サンプルはBlender frame1/7/13 → 1/12,7/12,13/12秒に対応します。
Three.jsのclip durationは2.083333秒です。独自動作は2秒分、MP4は厳密2秒です。
材質はPBR近似、にんにくの顔ドライバーはBlender限定で、.blendを外観の基準とします。

この追加viewerは既存のモデルRelease ZIPを置き換えません。
独自viewerコードはCC0。vendor内Three.jsはMIT（vendor/THREE_LICENSE.txt）。
