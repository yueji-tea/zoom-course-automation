# 09. Obsidian Vault 連携(任意・スキップ可)

## このセクションの目的

Obsidian(オブシディアン)は無料のローカル・マークダウンノートアプリです。「Vault(ヴォルト)」と呼ばれるノート保管フォルダの中に、Zoom 録画から自動生成された要約テキストを毎回自動保存できるようにします。

Obsidian を使っていない方、または「とりあえず Google Drive と YouTube だけ自動化できればOK」という方は **このセクションは丸ごとスキップして大丈夫です**。スキップする場合は、パイプラインを実行するときに `--no-obsidian` オプションを付けるだけで Obsidian 関連の処理を完全に飛ばせます。

## 所要時間

10〜15分(Obsidian未インストールの場合は +10分)

## 前提

- macOS で Obsidian がインストール済み(未インストールならこの後の手順でDLします)
- このパッケージの `.env` ファイルが用意できている(`02_INSTALL.md` まで完了済み)

---

## 手順

### Step 1: Obsidian をインストール(持っていない人だけ)

すでに Obsidian を使っている方は Step 2 へ進んでください。

1. ブラウザで https://obsidian.md/ を開く
2. 右上の「Download」ボタンをクリック
3. 「Mac (Universal)」をクリックして `.dmg` ファイルをダウンロード
4. ダウンロードした `.dmg` をダブルクリックで開く
5. Obsidian のアイコンを「Applications」フォルダにドラッグ&ドロップ
6. Launchpad または Finder のアプリケーションフォルダから Obsidian を起動

初回起動時、「Create new vault(新しい Vault を作る)」または「Open folder as vault(既存フォルダを Vault として開く)」を選ぶ画面が出ます。新規の方は「Create new vault」を選び、Vault の名前(例: `MyVault`)と保存場所を指定してください。

### Step 2: Vault のフルパスを確認

Vault のフルパス(=Mac のどこにあるかの住所)を調べます。

1. Obsidian を起動
2. 画面左下の Vault 名(または画面左上のフォルダアイコン)を **右クリック**
3. メニューから **「Show in Finder」** または **「Reveal in Finder」** をクリック
4. Finder で Vault のフォルダが開く
5. Finder のメニューバー → 「表示」 → 「パスバーを表示」を有効化
6. ウィンドウ下部に表示されるパスを確認(例: `/Users/yamada/Documents/MyVault`)

もしくは、Vault フォルダを **右クリック → 「情報を見る」** で表示される「場所:」欄をコピーすると確実です。

> 💡 **iCloud Drive 上に Vault を置いている方へ**
> iCloud と同期している Vault でも問題なく動作します。その場合のパスは次のような形になります。
> `/Users/YOU/Library/Mobile Documents/com~apple~CloudDocs/MyVault`
> このパスをそのまま `.env` に貼ってください。

### Step 3: `.env` ファイルに Vault パスを記入

`.env` ファイルをテキストエディタ(VS Code、メモ帳系アプリ、`nano` など)で開き、以下の2行を追加または編集します。

```
OBSIDIAN_VAULT_PATH=/Users/YOU/Documents/MyVault
OBSIDIAN_ZOOM_SUBDIR=Transcripts/Zoom
```

- `OBSIDIAN_VAULT_PATH`: Step 2 で調べた Vault のフルパスをそのまま貼る
- `OBSIDIAN_ZOOM_SUBDIR`: Vault の中のどのサブフォルダに保存するか(省略するとデフォルトで `Transcripts/Zoom` が使われます)

サブフォルダは事前に作っておかなくてもOKです(スクリプトが自動で作成します)。

⚠️ パスにスペースや日本語が含まれていてもそのまま貼ってOK。クォート( `"` )で囲む必要はありません。

### Step 4: 保存して閉じる

`.env` ファイルを保存して閉じます。

---

## 動作確認

以下のコマンドをターミナルで実行します(`<録画ディレクトリ>` は Zoom録画が入っているフォルダのパスに置き換えてください)。

```bash
cd /Users/YOU/zoom-course-automation
python3 scripts/zoom_save_to_obsidian.py <録画ディレクトリ>
```

### こうなっていればOK

- ターミナルに「Saved to: /Users/YOU/Documents/MyVault/Transcripts/Zoom/YYYYMMDD_xxx.md」のような行が表示される
- Obsidian を開いて、左サイドバーの `Transcripts/Zoom/` フォルダに新しいノートが追加されている
- ノートを開くと、Zoom録画の要約・参加者・所要時間などが整形されて入っている

---

## トラブル時

### エラー: `OBSIDIAN_VAULT_PATH is not set`
**原因**: `.env` ファイルに `OBSIDIAN_VAULT_PATH` の行がない、または値が空になっている。
**解決方法**: `.env` を開いて Step 3 の通り Vault のフルパスを記入。保存後、もう一度コマンドを実行する。

### エラー: `No such file or directory: '/Users/.../MyVault'`
**原因**: `.env` に書いた Vault パスが間違っている(タイポ、Vault を移動した、など)。
**解決方法**: Step 2 をもう一度実行して正しいパスを確認し、`.env` を修正する。

### Obsidian でノートが表示されない
**原因**: Obsidian アプリが古い情報をキャッシュしている。
**解決方法**: Obsidian を一度終了して再起動。または、左サイドバーのフォルダを右クリック → 「Refresh」。

### iCloud 同期中で保存が反映されない
**原因**: iCloud Drive 上の Vault は、別の Mac との同期に時間がかかることがある。
**解決方法**: 数分待つ。急ぐ場合は Finder で Vault フォルダを開いて「今すぐダウンロード」を実行。

### Obsidian を使わないので連携を完全にオフにしたい
`.env` の `OBSIDIAN_VAULT_PATH` を空のままにし、パイプライン実行時に `--no-obsidian` オプションを付けると Obsidian 処理は完全にスキップされます。例:
```bash
python3 scripts/zoom_pipeline.py --no-obsidian
```

---

★ ここまで終わったら、次は [10_LAUNCHD_SETUP.md](10_LAUNCHD_SETUP.md) へ。
