# 07. Google Cloud + gog CLI のセットアップ

## このセクションの目的

このパッケージは Google Workspace(Googleドライブ・Googleカレンダー・YouTubeなど)とやり取りします。やり取りするために、Googleに対して「このパソコンからのアクセスを許可します」という登録(OAuth=オーオース)を行う必要があります。

具体的には:

- Google Cloud(クラウド)にプロジェクトを作成
- Drive / Calendar / YouTube などの API(機能)を「使えるようにします」と有効化
- 「デスクトップ アプリ」用のID(client_id / client_secret)を発行
- `gog` という便利なCLI(コマンドラインツール)で、上記IDを使って実際にログイン

これが終わると、ターミナルから1行のコマンドで Drive のファイル一覧や Calendar 予定を読み書きできるようになります。

## 所要時間

約30〜40分(Googleの画面操作が多めです。途中でコーヒーを淹れるくらいの気持ちで)

## 前提

- Googleアカウントを持っていること(YouTube/Drive/Calendar を運用しているアカウント)
- Homebrew(ホームブルー)がMacにインストール済みであること
  - 確認方法: ターミナルで `brew --version` と打ってバージョンが出ればOK
  - 入っていなければ: https://brew.sh/index_ja からインストール

## 手順

### Step 1: Google Cloud Console にアクセス

ブラウザで以下を開きます。

```
https://console.cloud.google.com/
```

普段使うGoogleアカウントでログイン。

初回ログインだと「無料トライアル」のバナーが出ることがありますが、このパッケージで使うAPIは無料枠内に収まるので、登録不要です(右上の「×」または「あとで」で閉じて大丈夫)。

### Step 2: 新規プロジェクトを作成

画面上部の青いバー、左寄りにある「プロジェクトを選択」(または既存プロジェクト名)のドロップダウンをクリックします。

ポップアップ右上の「**新しいプロジェクト**」をクリック。

- **プロジェクト名**: 任意(例 `zoom-automation`、`講座運営` など)
- **場所**: 「組織なし」のままでOK
- 「**作成**」ボタンをクリック

数十秒待つと、画面右上の通知に「プロジェクトを作成しました」と出ます。通知の「プロジェクトを選択」をクリック、または再度ドロップダウンから今作ったプロジェクトを選びます。

### Step 3: 使うAPIを「有効にする」

左サイドメニュー(「ハンバーガーアイコン ☰」 → メニュー展開)から「**APIとサービス**」 → 「**ライブラリ**」を開きます。

検索ボックスで以下を1つずつ検索 → クリック → 「**有効にする**」ボタン:

1. **Google Drive API**
2. **Google Calendar API**
3. **YouTube Data API v3**(これは次のセクション 08 でも使います)

それぞれ有効化後、左上の「←」で戻って次のAPIを検索、を繰り返します。

⚠️ 「**請求先アカウントを設定してください**」と出ても、上記APIは無料枠で動くため設定不要です。出てきても「キャンセル」でOK。

### Step 4: OAuth同意画面の設定

左メニュー「**APIとサービス**」 → 「**OAuth同意画面**」をクリック。

「**User Type**」の選択:

- 「**外部**」を選択(個人Googleアカウントの場合はこちら)
- 「**作成**」をクリック

次に「アプリ情報」を入力:

- **アプリ名**: 任意(例 `zoom-automation`)
- **ユーザーサポートメール**: 自分のメールアドレスを選択
- **アプリのロゴ**: 不要(スキップ)
- **アプリのドメイン**: すべて空欄でOK
- **承認済みドメイン**: 空欄でOK
- **デベロッパーの連絡先情報**: 自分のメールアドレスを入力
- 「**保存して次へ**」

次の「スコープ」画面:

- ここでは何も追加せず、そのまま「**保存して次へ**」(実際の権限は後述の `gog auth add` 時に求めます)

次の「テストユーザー」画面:

- 「**+ ADD USERS**」または「**+ ユーザーを追加**」をクリック
- 自分のメールアドレスを入力 → 「**追加**」
- ⚠️ ここに登録したメールアドレスでないとログインできません。 **YouTube/Driveを運用しているアカウントのメール** を必ず入れてください。
- 「**保存して次へ**」

「概要」画面が出たら「**ダッシュボードに戻る**」。

⚠️ 「**公開ステータス: テスト**」のままでOK。 一般公開しないので Google の審査は不要です(テストユーザー登録だけで自分は使えます)。

### Step 5: OAuth クライアントID を作成

左メニュー「**APIとサービス**」 → 「**認証情報**」をクリック。

上部の「**+ 認証情報を作成**」 → 「**OAuth クライアント ID**」を選択。

- **アプリケーションの種類**: 「**デスクトップ アプリ**」を選択
- **名前**: 任意(例 `gog-cli-desktop`)
- 「**作成**」

ポップアップに **クライアントID** と **クライアントシークレット** が表示されます。

「**JSON をダウンロード**」ボタンで、認証情報のJSONファイルをダウンロードして、安全な場所に保管しておくこともできます(任意・推奨)。

⚠️ クライアントシークレットは秘密情報。SNSやGitHubに貼らないこと。

(なお、デスクトップアプリ用のOAuthはユーザーがブラウザでログインして初めて有効になるため、シークレットが万一漏れても直接ログインされる種類のものではありませんが、それでも公開はしないでください。)

### Step 6: gog CLI をインストール

ターミナルを開いて、以下を実行します。

```
brew install openclaw/gogcli/gogcli
```

(インストール先のtap指定が変わっている場合は、公式リポジトリ https://github.com/openclaw/gogcli の README を参照してください)

インストールが終わったら、確認:

```
gog --version
```

バージョン番号が表示されればOK。

### Step 7: gog でGoogleアカウントを認証

以下のコマンドを実行します。 `YOUR_EMAIL` の部分は、Step 4 でテストユーザーに登録した自分のメールアドレスに置き換えてください。

```
gog auth add YOUR_EMAIL --services drive,calendar,docs,sheets,gmail,tasks,youtube --drive-scope file --extra-scopes https://www.googleapis.com/auth/youtube.upload
```

例:

```
gog auth add YOUR_EMAIL@gmail.com --services drive,calendar,docs,sheets,gmail,tasks,youtube --drive-scope file --extra-scopes https://www.googleapis.com/auth/youtube.upload
```

このコマンドが実行されると:

1. ターミナル経由で **ブラウザが自動で開く**
2. Googleのログイン画面 → 自分のアカウントを選択
3. 「**このアプリは Google で確認されていません**」という警告画面が出る
   - 「**詳細**」をクリック → 「**[アプリ名](安全ではないページ)に移動**」をクリック
   - これは自分で作ったアプリだから出る警告で、自分のアカウントなので問題ありません
4. アクセスを求める権限の一覧が表示される → 「**続行**」(または「**許可**」)
5. ブラウザに「**Authentication successful**(認証成功)」のページが出る
6. ターミナルに戻ると、`Successfully added account` のようなメッセージが表示される

これでgog経由でGoogleサービスを操作できるようになりました。

### Step 8: 動作確認 + カレンダーID取得

ターミナルで以下を実行(YOUR_EMAILは自分のメールに置き換え):

```
gog -a YOUR_EMAIL calendar calendars
```

自分が持っているカレンダーの一覧が表示されます。

```
ID                                               | NAME
YOUR_EMAIL@gmail.com                            | (デフォルトのカレンダー名)
xxxxxxxxxxxxxxxxxxx@group.calendar.google.com    | 講座スケジュール
...
```

このパッケージで予定を追加したい「対象のカレンダー」のIDをコピーします。

- メインの予定なら自分のメールアドレスがそのままID
- 専用カレンダー(例「ゆえじSKD」のような独立カレンダー)を作っている場合は、`xxxx@group.calendar.google.com` 形式のID

`.env` ファイルに貼ります:

```
GCAL_TARGET_CALENDAR=ここにカレンダーIDを貼る
```

### Step 9: Drive 動作確認(任意)

念のため Drive アクセスも確認しておきましょう。

```
gog -a YOUR_EMAIL drive ls --max 5
```

最近のDriveファイル5件が表示されればOK。

## 動作確認

### こうなっていればOK

- Google Cloud Console のダッシュボードに、自分が作ったプロジェクトが表示されている
- 「APIとサービス」 → 「有効なAPI」に Drive API / Calendar API / YouTube Data API v3 が出ている
- 「認証情報」に作成したOAuthクライアント(デスクトップアプリ)がリストされている
- ターミナルで `gog -a YOUR_EMAIL calendar calendars` を実行するとカレンダー一覧が出る
- `.env` の `GCAL_TARGET_CALENDAR=` の右側にカレンダーIDが入っている

## トラブル時

### エラー: `access_denied` または「アクセスがブロックされました」

**原因**: Step 4のテストユーザーに、ログインしているメールアドレスが登録されていない。

**解決方法**: Google Cloud Console → OAuth同意画面 → テストユーザーの欄に、ログインしているGoogleアカウントのメールアドレスが入っているか確認。入っていなければ追加して、もう一度 `gog auth add` を実行してください。

### エラー: 「このアプリは Google で確認されていません」が怖い

**原因**: 一般公開していない自作アプリにアクセスする際の標準的な警告。

**解決方法**: 自分で作ったアプリで、自分のアカウントでログインしているので問題ありません。「詳細」→「移動」で進んでください。第三者に使わせるアプリを作る場合だけGoogle審査が必要です。

### エラー: `403 PERMISSION_DENIED` / `insufficientPermissions`

**原因**: 認証時に必要なスコープ(権限)が含まれていない。特に YouTube アップロードや Drive 書き込みでよく起きる。

**解決方法**: Step 7のコマンドを `--drive-scope file` および `--extra-scopes https://www.googleapis.com/auth/youtube.upload` 付きで実行し直してください。`--drive-scope file` がないと Drive は読み取り専用になります。

```
gog auth add YOUR_EMAIL --services drive,calendar,docs,sheets,gmail,tasks,youtube --drive-scope file --extra-scopes https://www.googleapis.com/auth/youtube.upload
```

### エラー: `brew install openclaw/gogcli/gogcli` で「Error: No formula found for ...」

**原因**: tap(リポジトリ)が変わったか、URLが違う。

**解決方法**: https://github.com/openclaw/gogcli の README を確認し、最新のインストールコマンドを使ってください。または `brew tap openclaw/gogcli` を先に実行してから `brew install gogcli` を試す。

### gog コマンドが「command not found」

**原因**: Homebrew のbinパスが通っていない、またはインストール直後でシェルがパスを再読み込みしていない。

**解決方法**: ターミナルを一度閉じてから開き直してみてください。それでもダメなら:

```
which brew
brew --prefix
```

を実行して、表示されたパス + `/bin` を `$PATH` に追加してください。M1/M2 Mac の場合は `/opt/homebrew/bin` のことが多いです。

### APIの「請求先アカウント設定」を求められる

**原因**: 一部APIで請求アカウント紐付けを要求してくる。

**解決方法**: このパッケージで使う Drive / Calendar / YouTube Data API v3 は **無料枠** で利用できます。「請求先必須」と出るAPIは別物なので、対象APIを再確認してください。万が一クレジットカード登録を促されても、無料枠だけ使う限り課金はされません(不安なら登録しないでスキップ)。

---

★ ここまで終わったら、次は [08_YOUTUBE_API_SETUP.md](08_YOUTUBE_API_SETUP.md) へ。
