# 06. Discord Webhook のセットアップ

## このセクションの目的

Discord Webhook(ウェブフック)とは、特定のチャンネルにメッセージを投稿するための専用URLのことです。このURLにメッセージを送信するだけで、Discord に投稿できます。

このパッケージでは Webhook を使って:

- 講座開催前の **告知メッセージ**(「今夜20時から○○講座です」)
- 5分前の **リマインダー**
- 録画終了後の **YouTube限定公開URLのアーカイブ案内**

を自動で投稿します。

前のセクションで作った Bot はイベントタブ(Scheduled Event)を作るためのもの、Webhook はチャンネルへのメッセージ投稿のためのもの、と役割が違います。両方使います。

## 所要時間

約10分(チャンネル1つあたり3分程度。複数チャンネル用意するなら時間が増えます)

## 前提

- [05_DISCORD_BOT_SETUP.md](05_DISCORD_BOT_SETUP.md) でBotの招待が終わっていること(同じサーバーで作業します)
- 投稿したいDiscordチャンネルがすでに用意されていること(まだなら先にDiscordで作成してください)
- そのチャンネルでチャンネル設定を変更できる権限(管理者・モデレーター等)を持っていること

## 手順

### Step 1: 投稿したいチャンネルを開く

Discordアプリ(またはブラウザ版)で、メッセージを投稿させたいチャンネル(例:`#お知らせ`、`#アーカイブ`)を開きます。

### Step 2: チャンネル設定を開く

チャンネル名の右側にある **歯車アイコン(⚙️)**「チャンネルの編集」をクリックします。

(チャンネル名を右クリック →「チャンネルの編集」でもOK)

### Step 3: 連携サービス → ウェブフック

左サイドメニューから「**連携サービス**」をクリックします。

「**ウェブフック**」のセクションがあるので、「**ウェブフックを作成**」ボタンをクリックします。

### Step 4: Webhook の名前・アイコンを設定

新しい Webhook が作成され、設定画面が開きます。

- **名前**: 何でもOKですが、後で見て分かるように名前をつけます(例:`Course Notify`、`講座お知らせ`、`Archive Bot` など)
- **アイコン**: 任意で画像をアップロードできます(なくてもOK、Discordの初期アイコンになります)
- **チャンネル**: 投稿先のチャンネルになっているか念のため確認

### Step 5: ウェブフックURLをコピー

設定画面の下にある「**ウェブフックURLをコピー**」ボタン(青色)をクリックします。

クリップボードにURLがコピーされます(`https://discord.com/api/webhooks/...` で始まる長いURL)。

「**変更を保存する**」ボタンを忘れずに押してください。

⚠️ **このURLは秘密情報です。** このURLを知っている人は誰でもそのチャンネルにメッセージを投稿できてしまいます。
- SNSや公開リポジトリ(GitHubなど)に絶対に貼らないこと
- 漏れた場合はDiscordの同じ画面から「**ウェブフックを削除**」して作り直すこと

### Step 6: `.env` ファイルに貼る

zoom-course-automation のフォルダにある `.env` を開いて、用途ごとに対応するキーに貼ります。

```
# 講座の事前告知用
DISCORD_WEBHOOK_COURSE_NOTIFY=https://discord.com/api/webhooks/xxxxxx/xxxxxxxxxx

# 講座のアーカイブ案内用(録画後のYouTube URL投稿)
DISCORD_WEBHOOK_COURSE_ARCHIVE=https://discord.com/api/webhooks/xxxxxx/xxxxxxxxxx

# コミュニティの告知用
DISCORD_WEBHOOK_COMMUNITY_NOTIFY=https://discord.com/api/webhooks/xxxxxx/xxxxxxxxxx

# コミュニティのアーカイブ案内用
DISCORD_WEBHOOK_COMMUNITY_ARCHIVE=https://discord.com/api/webhooks/xxxxxx/xxxxxxxxxx
```

### Step 7: 必要なだけWebhookを増やす

このパッケージは「.envに書いたWebhookキー名を、テンプレートJSONから自由に参照する」設計になっているため、上記4つに限らず、必要に応じてキーを追加できます。

例:

```
DISCORD_WEBHOOK_VIP_NOTIFY=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_TAIWAN_TEAM=https://discord.com/api/webhooks/...
```

キー名は自分で決めて構いません。後でテンプレJSONで「このイベントは VIP_NOTIFY に投稿する」のように指定します。

### Step 8: 投稿先チャンネルを使い分けたい場合

「告知は #お知らせ チャンネル」「アーカイブは #アーカイブ チャンネル」のように分けたい場合は、それぞれのチャンネルでStep 1〜5を繰り返して、別々のWebhookを作成します。それぞれ別のキー名(例 `DISCORD_WEBHOOK_COURSE_NOTIFY` と `DISCORD_WEBHOOK_COURSE_ARCHIVE`)で `.env` に追加します。

## 動作確認

### こうなっていればOK

- Discordで該当チャンネルの「歯車 → 連携サービス → ウェブフック」を開くと、作った Webhook がリスト表示されている
- `.env` ファイルに `DISCORD_WEBHOOK_XXX=https://discord.com/api/webhooks/...` の形式で値が入っている
- 簡易テスト(任意): ターミナルで以下を実行して、Discordチャンネルに「テスト」と投稿されればOK

```
curl -H "Content-Type: application/json" \
     -X POST \
     -d '{"content":"テスト投稿です"}' \
     "貼ったWebhook URL"
```

(`貼ったWebhook URL` の部分は、`.env`に貼ったURLそのままに置き換えてください)

## トラブル時

### エラー: `401 Unauthorized` または `Invalid Webhook Token`

**原因**: WebhookのURLが間違っている、またはURLが古い(削除済み)。

**解決方法**: Discordのチャンネル設定→連携サービス→ウェブフックを開き、対象のWebhookがまだ存在するか確認。あれば「ウェブフックURLをコピー」をもう一度押して `.env` に貼り直してください。なければStep 3から作り直してください。

### エラー: `404 Not Found`

**原因**: Webhook URLの一部が欠けている。または Webhook が削除されている。

**解決方法**: `.env` ファイルでURLが途中で切れていないか確認。改行が混ざっていたり、末尾にスペースが入っていると失敗します。1行に収まっているかチェック。

### Webhook を作成するボタンがグレーアウトしている

**原因**: そのチャンネルで「ウェブフックの管理」権限がない。

**解決方法**: サーバー管理者に頼んで、自分のロールに「ウェブフックの管理」権限を付けてもらうか、管理者にWebhookを作ってもらってURLを共有してもらいます。

### 投稿はされるが、絵文字や日本語が文字化けする

**原因**: ほとんどの場合は問題ありませんが、curlでテスト投稿する際にシェルのエスケープで起きることがあります。

**解決方法**: 実運用ではこのパッケージのPythonスクリプトが正しくJSONエンコードして送信するため、文字化けは起きません。テストで気になる場合は、Pythonスクリプト経由で動作確認してください。

---

★ ここまで終わったら、次は [07_GOOGLE_OAUTH_SETUP.md](07_GOOGLE_OAUTH_SETUP.md) へ。
