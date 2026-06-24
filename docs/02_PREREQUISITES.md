# 02. 必要な準備(Mac環境とアカウント)

## このセクションの目的

このパッケージを動かすために、**Macに必要なツールを入れる**作業をします。
あわせて、後のステップで使う **各種サービスのアカウント** を確認しておきます。

「ターミナル」というアプリを使いますが、コマンドはすべてコピペでOKです。

## 所要時間

30〜45分(各ツールのインストール時間込み)

## 前提

- macOS 12(Monterey)以降の Mac
- インターネット接続
- 管理者パスワード(自分のMacのパスワード)

---

## 用語の説明(先に1回だけ)

- **ターミナル**:文字でMacに命令するためのアプリ。`/Applications/Utilities/Terminal.app` にある
- **Homebrew(ホームブリュー)**:Mac用のソフト管理ツール。「Macのアプリストア(コマンド版)」
- **CLI(シーエルアイ)**:Command Line Interface の略。文字で操作するツールのこと
- **Python(パイソン)**:プログラミング言語。このパッケージはPythonで書かれている
- **git(ギット)**:ソースコードを管理するためのツール
- **API(エーピーアイ)**:アプリ同士が会話するための仕様

---

## 手順

### Step 1: ターミナルを開く

1. Finder の「アプリケーション」→「ユーティリティ」フォルダを開く
2. 「ターミナル.app」をダブルクリック
3. 黒い(または白い)文字だけの画面が出てくる

これが「ターミナル」です。今後はここにコマンドを貼り付けて Enter を押します。

「ターミナル」がよく分からない場合は、Spotlight(Macの右上の虫眼鏡マーク)で「ターミナル」と検索しても出てきます。

### Step 2: Homebrew をインストールする

ターミナルに以下のコマンドを **そのままコピペ** して Enter。

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

途中で「Password:」と聞かれたら、Mac のログインパスワードを入力(打っても画面に何も出ませんが、入力されています)。

5〜10分くらい待ちます。最後に「Installation successful!」と出ればOK。

### Step 3: Homebrew で必要なツールをまとめて入れる

以下をターミナルにコピペして Enter。

```bash
brew install python@3.11 git gh ffmpeg
```

入るもの:
- **python@3.11**:Python 本体(3.10以上ならOK、3.11推奨)
- **git**:後でこのパッケージをダウンロードするのに使う
- **gh**:GitHub の公式CLI(あると便利)
- **ffmpeg**:動画ファイル処理用

数分かかります。

### Step 4: インストールできたか確認する

それぞれが正しく入ったか確認します。1行ずつコピペして Enter。

```bash
python3 --version
```
→ `Python 3.11.x` のような表示が出ればOK(3.10以上ならOK)

```bash
git --version
```
→ `git version 2.xx.x` のような表示が出ればOK

```bash
gh --version
```
→ `gh version 2.xx.x` のような表示が出ればOK

```bash
ffmpeg -version
```
→ `ffmpeg version x.x.x` のような表示が出ればOK

### Step 5: (任意)gog CLI を入れる

Google Drive / Calendar / Docs などを操作したい場合は、gog CLI を入れておくと便利です。
(YouTube アップロードは別ツールでも可能なので、最初はスキップしてもOK)

```bash
brew install openclaw/gog/gog
```

入ったか確認:
```bash
gog --version
```

### Step 6: 必要なアカウントを確認する

このパッケージを使うには、以下のサービスのアカウントが必要です。
**今すぐ作る必要はありません**(後の各ドキュメントで案内します)。今は「持っているか」だけ確認してください。

| サービス | 必須? | 用途 | プラン |
|---|---|---|---|
| **Zoom** | ★必須 | Zoom会議の作成・クラウド録画 | **Pro以上**(クラウド録画機能のため) |
| **Google アカウント** | ★必須 | Drive / Calendar / YouTubeアップロード | 無料でOK |
| **Discord** | ◯推奨 | 告知・リマインダー投稿 | 無料 |
| **OpenRouter** | ★必須 | AIで録画要約を生成 | 従量課金(月$5程度) |
| **YouTube チャンネル** | ◯推奨 | 録画の限定公開アップ | 無料 |

⚠️ **Zoom は「Pro以上」が必須** です。無料プランだとクラウド録画ができないため、自動処理ができません。

### Step 7: 作業用フォルダの確認

このパッケージは `~/zoom-course-automation/` に置く想定です。
ターミナルで以下を実行して、フォルダの中身を確認しておきます。

```bash
ls ~/zoom-course-automation/
```

`docs` フォルダが見えていればOK(このドキュメントが入っているはずです)。

---

## 動作確認

### こうなっていればOK

以下のコマンドが、全てバージョン番号を返せばOK。

```bash
python3 --version && git --version && gh --version && ffmpeg -version | head -1
```

4つすべてバージョンが表示されれば、必要なツールが揃っています。

---

## トラブル時

### エラー: `command not found: brew`
**原因**: Homebrew のインストールが完了していない、またはパスが通っていない。

**解決方法**:
ターミナルで以下を実行(Apple Silicon Mac の場合):
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```
Intel Mac の場合は `/usr/local/bin/brew` に置き換える。

その後、ターミナルを一度閉じて開き直してください。

### エラー: `xcrun: error: invalid active developer path`
**原因**: Xcode Command Line Tools が入っていない。

**解決方法**:
```bash
xcode-select --install
```
ポップアップが出るので「インストール」を押して、5〜15分待つ。

### エラー: Homebrew のインストール中に「Permission denied」
**原因**: Mac のパスワード入力が必要。

**解決方法**: 「Password:」が出たら、自分のMacログインパスワードを入力する(画面には何も表示されないが、入力されている)。

### `python3` を実行すると「macOS版」が出てしまう
**原因**: Mac標準のPythonが優先されている。

**解決方法**:
バージョンが 3.10以上 ならそのまま使えます。3.9以下なら以下で Homebrew版を優先:
```bash
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

★ ここまで終わったら、次は [03_ZOOM_API_SETUP.md](03_ZOOM_API_SETUP.md) へ。
