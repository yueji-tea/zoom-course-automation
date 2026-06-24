# 08. YouTube Data API のセットアップ

## このセクションの目的

このパッケージは、Zoomで録画された講座動画を **YouTube に限定公開でアップロード** して、そのURLをDiscordチャンネルにアーカイブ案内として投稿します。

「限定公開」とは、URLを知っている人だけが視聴できる公開方法です。検索結果には出ず、チャンネル一覧にも出ません。受講生だけにDiscord経由でURLを共有する運用に適しています。

このセクションでは、YouTubeへ動画アップロードするためのOAuth認証を行います。前のセクション(07)で作成したGoogle Cloudプロジェクトを流用するので、ゼロから作り直す必要はありません。

## 所要時間

約15分

## 前提

- [07_GOOGLE_OAUTH_SETUP.md](07_GOOGLE_OAUTH_SETUP.md) を完了していること
- 動画をアップロードしたい YouTube チャンネルがあること(個人チャンネルでもブランドアカウントでもOK)
- ⚠️ **重要**: YouTubeを運用しているチャンネルが、 07で認証したGoogleアカウントに紐づいていること
  - 確認方法: ブラウザでYouTubeにログイン → 右上のアイコン → 「アカウントを切り替える」で対象チャンネルが表示されるか確認

## 手順

### Step 1: YouTube Data API v3 が有効か確認

07 で既に有効化していますが、念のため確認します。

ブラウザで Google Cloud Console を開く:

```
https://console.cloud.google.com/
```

左メニュー「**APIとサービス**」 → 「**有効なAPI とサービス**」をクリック。

リストの中に「**YouTube Data API v3**」があればOK。なければ「**APIとサービス**」 → 「**ライブラリ**」から検索して「**有効にする**」を押してください。

### Step 2: 07 で作ったOAuthクライアントの情報を確認

左メニュー「**APIとサービス**」 → 「**認証情報**」を開きます。

「**OAuth 2.0 クライアント ID**」のセクションに、07 で作った「デスクトップ アプリ」が表示されているはずです。

右側の編集ボタン(鉛筆アイコン)、または名前をクリックして開くと、以下が表示されます:

- **クライアント ID** (例 `1234567890-abcdefg.apps.googleusercontent.com`)
- **クライアント シークレット** (例 `GOCSPX-xxxxxxxxxxxx`)

これら2つをコピーします。

### Step 3: `.env` ファイルに YouTube用キーを貼る

zoom-course-automation のフォルダにある `.env` を開いて、以下を追加(または既存の行を編集):

```
YOUTUBE_CLIENT_ID=ここにクライアントIDを貼る
YOUTUBE_CLIENT_SECRET=ここにクライアントシークレットを貼る
```

例:

```
YOUTUBE_CLIENT_ID=1234567890-abcdefg.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx
```

⚠️ この値は 07 で確認したものと同じです。YouTube用に別のOAuthクライアントを作る必要はありません。

ファイルを保存して閉じます。

### Step 4: refresh token を取得するスクリプトを実行

ターミナルで zoom-course-automation のフォルダに移動して、以下を実行します。

```
cd /Users/ochinaoko/zoom-course-automation
python3 scripts/youtube_oauth_setup.py
```

スクリプトが実行されると:

1. ターミナルに認証URLが表示される(自動的にブラウザが開く場合もあり)
2. ブラウザでGoogleログイン画面 → **YouTubeを運用しているアカウント** を選択
   - ⚠️ ここで別アカウントを選ぶと、別チャンネルにアップロードされてしまうので注意
3. 「**このアプリは Google で確認されていません**」 → 「**詳細**」 → 「**[アプリ名]に移動**」
4. 権限の一覧 → 「**続行**」「**許可**」
5. ブラウザに認証完了画面 → ターミナルに自動で戻る
6. スクリプトが `.env` に **`YOUTUBE_REFRESH_TOKEN=...`** を自動で書き込む

ターミナルに「Refresh token saved to .env」のようなメッセージが出れば成功です。

### Step 5: アップロードの動作確認(任意)

実際にテストアップロードしたい場合(短いダミー動画で確認):

```
python3 scripts/zoom_upload_to_youtube.py /path/to/test_video.mp4 --title "テストアップロード" --description "動作確認用"
```

- デフォルトは **限定公開(unlisted)** でアップロード
- アップロード完了後、動画のYouTube URLが表示される
- ブラウザでそのURLを開き、視聴できればOK
- 終わったら YouTube Studio から削除して大丈夫

### 公開設定の変更(参考)

デフォルトは限定公開ですが、必要に応じて変更可能:

- `--public` を付ければ完全公開
- `--private` を付ければ非公開(本人のみ視聴可)

実運用では基本的に **限定公開のまま** にして、Discord経由でURLを共有する運用を推奨します。

## 動作確認

### こうなっていればOK

- Google Cloud Console の「有効なAPI」一覧に YouTube Data API v3 が含まれる
- `.env` ファイルに以下3つが入っている:
  - `YOUTUBE_CLIENT_ID=...`
  - `YOUTUBE_CLIENT_SECRET=...`
  - `YOUTUBE_REFRESH_TOKEN=...` (Step 4で自動付与)
- テストアップロード(任意)を実行すると、YouTube Studio に動画が表示される

## アップロード上限(クォータ)について

YouTube Data API v3 には1日あたりの上限(クォータ)があります。デフォルトでは:

- **1日あたり 10,000 ユニット**
- 1動画アップロード = 約 1,600 ユニット
- → 1日に約 **6本** までアップロード可能

個人運用や少人数の講座運営なら十分です。

もし1日に7本以上アップロードしたい場合は、Google Cloud Console の「**APIとサービス**」 → 「**クォータ**」から増枠申請ができます(無料、利用目的を書いて送信、数日で承認されることが多いです)。

## トラブル時

### エラー: `Channel not found` / `noLinkedYouTubeAccount`

**原因**: 認証したGoogleアカウントに、YouTubeチャンネルが紐づいていない。あるいは別アカウントで認証してしまった。

**解決方法**:

1. ブラウザで https://www.youtube.com にアクセス
2. 右上のアイコン → 「アカウントを切り替える」で、対象チャンネルが「(自分の名前)のチャンネル」として表示されているか確認
3. 表示されていない場合は、ブラウザを一度ログアウトして、正しいGoogleアカウントだけでログイン → YouTubeを開いてチャンネルを作成
4. もう一度 Step 4 を実行して、 **正しいアカウント** を選択

### エラー: `unauthorized_client` または「アプリが確認されていません」で進めない

**原因**: 「**詳細**」リンクが見えていない、またはアカウントがテストユーザーに登録されていない。

**解決方法**:
- 警告画面の左下「**詳細**」をクリックすると、「**(アプリ名)(安全ではないページ)に移動**」のリンクが表示されます
- それでも進めない場合は、07の OAuth同意画面 → テストユーザーに、ログイン中のアカウントが含まれているか確認

### エラー: `quotaExceeded` / `dailyLimitExceeded`

**原因**: 1日のクォータ上限(10,000ユニット = 約6アップロード)に達した。

**解決方法**:
- 翌日(UTC基準でリセット = 日本時間9:00頃)まで待つ
- 急ぐ場合は Google Cloud Console → APIとサービス → クォータ から増枠申請

### エラー: `youtube_oauth_setup.py` を実行したら「No module named ...」

**原因**: 必要なPythonパッケージが未インストール。

**解決方法**: ターミナルで以下を実行:

```
cd /Users/ochinaoko/zoom-course-automation
pip3 install -r requirements.txt
```

### refresh token が `.env` に書き込まれない

**原因**: スクリプトの権限不足、または `.env` のパスが違う。

**解決方法**: スクリプトの実行ディレクトリが zoom-course-automation のフォルダ直下になっているか確認。ターミナルに表示された refresh token の文字列を、手動で `.env` の `YOUTUBE_REFRESH_TOKEN=` に貼ってもOKです。

### 動画はアップロードされたが、「処理中」のまま再生できない

**原因**: YouTube側の動画変換(エンコード)に時間がかかっている(動画の長さ・解像度による)。

**解決方法**: これはエラーではありません。アップロードは成功しています。1時間の講座動画なら処理に10〜30分かかることがあります。YouTube Studio から状況を確認できます。

---

★ ここまで終わったら、次は [09_OBSIDIAN_SETUP.md](09_OBSIDIAN_SETUP.md) へ。
