# 03. Zoom API アプリの作成(Server-to-Server OAuth)

## このセクションの目的

Zoom が提供している「API(=外部からZoomを操作するための仕組み)」を、このパッケージから使えるようにします。

具体的には、Zoom の「App Marketplace」というサイトで **Server-to-Server OAuth アプリ** という小さなアプリを1つ作って、そこから出てくる **3つの認証情報**(Account ID / Client ID / Client Secret)をコピーします。

このアプリのおかげで、パッケージが Zoom会議を勝手に作ったり、録画を勝手にダウンロードしたりできるようになります。

## 所要時間

15〜20分

## 前提

- **Zoom Pro 以上**のアカウント(クラウド録画機能が使えるプラン)
- そのアカウントの **管理者権限**(自分1人で使っているアカウントなら通常は管理者)
- 02_PREREQUISITES.md が完了している

---

## 用語の説明

- **Server-to-Server OAuth(サーバー間OAuth)**: 人が毎回ログインしなくても、プログラムが自動でZoomにアクセスできる仕組み。ユーザー認証画面が出ない、サーバー(=自分のMac)から直接Zoomを操作するための方式
- **Scope(スコープ)**: 「このアプリには何を許可するか」の権限リスト。録画を読めるけど削除はできない、など細かく設定する
- **Account ID / Client ID / Client Secret**: Zoom がアプリに発行する3つの認証情報。これでこのアプリだけが本物だと証明できる(★ 他人に見せない)

---

## 手順

### Step 1: Zoom App Marketplace にアクセス

ブラウザで以下を開きます。

```
https://marketplace.zoom.us/develop/create
```

Zoom にログイン中のアカウントで開いてください(普段使っている Zoom のアカウント)。

### Step 2: 「Server-to-Server OAuth」を選ぶ

画面にいくつかのアプリタイプが並んでいます。

1. 「**Server-to-Server OAuth**」のカードを探す
2. その下の「**Create**」ボタンをクリック

⚠️ 他の「OAuth」「Webhook Only」「Meeting SDK」などとは違うので、必ず「Server-to-Server OAuth」を選んでください。

### Step 3: App Name を入力

ポップアップが出るので、好きな名前を入れます。例:

```
zoom-course-automation
```

または

```
講座運営自動化(ゆえじ)
```

日本語でもOK。あとから自分で見て分かる名前にしてください。
入力したら「**Create**」をクリック。

### Step 4: 認証情報をコピーする(★ 超重要)

作成が完了すると、左メニューに「**App Credentials**」という項目が現れます。クリックすると以下が表示されます。

- **Account ID**(例: `abc123XYZ...`)
- **Client ID**(例: `aBc1DeFg...`)
- **Client Secret**(例: `xYz9876...`)— ★ デフォルトでは伏せ字。「Copy」ボタンか「目のアイコン」で表示できる

⚠️ **この3つは絶対に他人に見せない、SNS等に貼らない**(=自分のZoomアカウントが乗っ取られます)

3つとも、Macの「メモ」アプリなどに一時的にコピペしておきます。
あとで `.env` という設定ファイルに貼ります。

### Step 5: Information タブを埋める

左メニューの「**Information**」をクリック。

必須項目を埋めます(全部 **自分用** なので適当でOK):

- **Short description**: `Course automation tool`
- **Long description**: `For my own course management automation.`
- **Company Name**: 自分の名前または屋号
- **Name** / **Email**: 自分の名前・メールアドレス

「Continue」または「Save」を押す。

### Step 6: Feature タブ(★ 通常は何もしない)

左メニュー「**Feature**」をクリック。

このパッケージでは Webhook(Zoomから自動通知を受ける機能)は不要なので、**何も触らずに次へ**進んでOK。

### Step 7: Scopes タブで権限を追加する(★ 一番重要)

左メニュー「**Scopes**」をクリック。

「**Add Scopes**」というボタンをクリックして、以下の **6つの権限** を1つずつ追加します。

検索ボックスに以下を貼ると見つけやすいです。

| Scope名 | これで何ができる? |
|---|---|
| `cloud_recording:read:list_user_recordings:admin` | 録画の一覧を取得できる |
| `cloud_recording:read:recording:admin` | 録画ファイルの詳細を取得・ダウンロードできる |
| `user:read:user:admin` | ユーザー情報を取得できる |
| `meeting:write:meeting:admin` | Zoom会議を新規作成できる |
| `meeting:update:meeting:admin` | Zoom会議を編集できる |
| `meeting:delete:meeting:admin` | Zoom会議を削除できる |

#### 追加手順
1. 「Add Scopes」をクリック
2. 検索窓に scope 名(例: `cloud_recording:read:list_user_recordings:admin`)をペースト、または部分検索(例: `list_user_recordings`)
3. 左のチェックボックスにチェック
4. 右下の「Done」をクリック

これを6個ぶん繰り返します。

最後に画面下の「**Continue**」または「**Save**」を押す。

⚠️ Scope に `:admin` が付くものを選んでください。`:master` が付く別の選択肢もありますが、こちらは通常使いません。

### Step 8: Activation でアプリを有効化する

左メニュー「**Activation**」をクリック。

「**Activate your app**」という青いボタンをクリック。

「Activated」という緑のチェックマークが出れば、Zoom側の作業は完了です。

### Step 9: 取得した3つの値を .env ファイルに貼る

パッケージのルートフォルダ(`~/zoom-course-automation/`)に `.env` というファイルを作って、Step 4 でコピーした3つを貼ります。

ターミナルで以下のコマンドを実行(初回作成の場合):

```bash
cd ~/zoom-course-automation/
cp .env.example .env
```

`.env.example` が無い場合は、新規で作ります:

```bash
cd ~/zoom-course-automation/
touch .env
open -e .env
```

(`open -e .env` でテキストエディタが開きます)

開いたファイルに以下を追記します(★ 値の部分を自分のものに置き換える):

```
ZOOM_ACCOUNT_ID=ここにAccount IDを貼る
ZOOM_CLIENT_ID=ここにClient IDを貼る
ZOOM_CLIENT_SECRET=ここにClient Secretを貼る
```

保存(Command + S)して閉じる。

⚠️ `.env` ファイルは絶対に GitHub などにアップしないでください(パッケージの `.gitignore` で除外されているはずですが念のため)。

---

## 動作確認

### こうなっていればOK

1. Zoom App Marketplace の左上に、自分のアプリ名(例: `zoom-course-automation`)が表示される
2. 「Activation」タブが緑のチェックで「Activated」になっている
3. `.env` ファイルに ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET の3行が入っている

ターミナルで以下を打って、3行があるか確認(値は伏字で表示):

```bash
grep -E '^ZOOM_' ~/zoom-course-automation/.env | sed 's/=.*/=***/'
```

→ こんな表示になればOK:
```
ZOOM_ACCOUNT_ID=***
ZOOM_CLIENT_ID=***
ZOOM_CLIENT_SECRET=***
```

---

## トラブル時

### エラー: 「Server-to-Server OAuth」の選択肢が表示されない
**原因**: Zoom アカウントが「Pro以上」でない、または管理者権限がない。

**解決方法**:
- Zoom Web ポータル(zoom.us)にログイン →「アカウント管理」→「アカウントプロファイル」でプラン確認
- Pro未満なら、Pro以上にアップグレードする(クラウド録画機能も込みなのでこのパッケージには必須)
- 自分が管理者でない場合は、アカウント管理者に依頼する

### エラー: Scope を追加しようとすると「Permission denied」
**原因**: ロール権限が不足している。

**解決方法**:
管理者にロール権限の付与を依頼してください。
自分のアカウントなら、Zoom ポータルの「アカウント管理」→「ロール管理」で確認できます。

### エラー: Activate ボタンを押しても「Information を埋めて」と出る
**原因**: Step 5 の必須項目が未入力。

**解決方法**:
「Information」タブに戻って、Short description / Long description / Company Name / Name / Email をすべて埋めてから再度 Activate を試す。

### Client Secret を失くした / 漏らした疑い
**原因**: Client Secret を誤って他人に共有した、または見失った。

**解決方法**:
1. App Credentials タブで「**Regenerate**(再生成)」ボタンをクリック
2. 新しい Client Secret が発行される
3. ⚠️ 古い Secret は無効化されるので、`.env` ファイルも新しい値で書き換える

---

★ ここまで終わったら、次は [04_OPENROUTER_SETUP.md](04_OPENROUTER_SETUP.md) へ。
