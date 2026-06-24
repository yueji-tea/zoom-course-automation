# 10. launchd で毎朝自動実行のセットアップ

## このセクションの目的

launchd(ローンチディー)は、macOS に最初から入っている純正のタスクスケジューラです(他のOSでいう cron や Windows のタスクスケジューラに相当します)。

これを設定すると、**毎朝決まった時刻に Zoom録画パイプラインが自動で走る** ようになります。あなたが「録画チェックして」と毎日打ち込まなくても、Mac が起動していれば勝手に処理してくれます。

## 所要時間

15〜20分

## 前提

- `02_INSTALL.md`〜`08_DISCORD.md` までのセットアップが完了している
- 手動で `python3 scripts/zoom_pipeline.py` を一度走らせて、エラーなく動くことを確認済み
- Mac のユーザー名がわかる(わからなくても下の手順で調べます)

---

## 手順

### Step 1: 自分の Mac のユーザー名を確認

ターミナルを開いて以下を実行します。

```bash
whoami
```

表示された文字列(例: `yamada`)があなたのユーザー名です。以降の手順で `YOURNAME` と書かれている箇所はすべてこの名前に置き換えてください。

### Step 2: テンプレートをコピー

このパッケージに同梱されている plist テンプレートを、macOS が自動実行ジョブを読み込むフォルダ(`~/Library/LaunchAgents/`)にコピーします。

```bash
cd /Users/YOU/zoom-course-automation
cp launchd/com.YOURNAME.zoom.pipeline.plist.template ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
```

⚠️ ファイル名の `YOURNAME` の部分は Step 1 で調べた自分のユーザー名に置き換えてください(例: `com.yamada.zoom.pipeline.plist`)。

### Step 3: plist ファイルをエディタで開いて編集

コピーしたファイルをテキストエディタで開きます。Finder で `~/Library/LaunchAgents/` フォルダを開く方法は以下:

1. Finder のメニューバー → 「移動」 → 「フォルダへ移動...」(または `Cmd + Shift + G`)
2. `~/Library/LaunchAgents` と入力 → Enter
3. コピーした `com.YOURNAME.zoom.pipeline.plist` を右クリック → 「このアプリケーションで開く」 → テキストエディット(または VS Code 等)

中の以下の項目を **すべて自分の環境に合わせて置換** します。

| 置換対象 | 置換後の内容 | 例 |
|---|---|---|
| `YOURNAME` | Step 1 で調べたユーザー名 | `yamada` |
| `YOUR_SCRIPTS_DIR` | スクリプト配置先のフルパス | `/Users/yamada/zoom-course-automation/scripts` |
| `YOUR_LOG_DIR` | ログ保存先のフルパス | `/Users/yamada/zoom-course-automation/_logs` |

ログ保存先フォルダが存在しない場合は、先に作成しておきます。

```bash
mkdir -p /Users/YOU/zoom-course-automation/_logs
```

### Step 4: 実行時刻を決める(任意)

plist の中に以下のような部分があります。

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>30</integer>
</dict>
```

- `Hour`: 24時間表記の「時」(0〜23)
- `Minute`: 「分」(0〜59)

上の例は「毎朝 8:30 に実行」の意味です。自分の好きな時刻に変更してください(例: 朝9時なら `Hour=9, Minute=0`)。

編集が終わったら **必ず保存** します(`Cmd + S`)。

### Step 5: launchd に登録(=毎日動くようにする)

ターミナルで以下を実行します。

```bash
launchctl load ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
```

エラーが何も表示されなければ登録成功です。

### Step 6: 登録されたことを確認

```bash
launchctl list | grep zoom.pipeline
```

`com.YOURNAME.zoom.pipeline` のような行が表示されればOK。

### Step 7: Discord リマインダー機能を使う人だけ追加で登録

リマインダー機能(`08_DISCORD.md`)も自動実行したい場合は、同じ手順で `com.YOURNAME.discord.reminder.runner.plist` も登録します。

```bash
cp launchd/com.YOURNAME.discord.reminder.runner.plist.template ~/Library/LaunchAgents/com.YOURNAME.discord.reminder.runner.plist
# エディタで YOURNAME などを置換して保存
launchctl load ~/Library/LaunchAgents/com.YOURNAME.discord.reminder.runner.plist
```

### Step 8: 手動でテスト発火(本運用前に必ず1回)

⚠️ 慣れないうちは、いきなり翌朝まで待つのではなく、まず **手動で1回発火させて動作確認** してください。

```bash
launchctl kickstart -k gui/$(id -u)/com.YOURNAME.zoom.pipeline
```

`-k` は「もし実行中ならkillして即再起動」の意味です。発火後、ログを確認します。

```bash
tail -f /Users/YOU/zoom-course-automation/_logs/zoom_pipeline.log
```

(`Ctrl + C` で抜けられます)

---

## 動作確認

### こうなっていればOK

- `launchctl list | grep zoom.pipeline` で行が表示される
- Step 8 の手動発火後、`_logs/zoom_pipeline.log` に処理ログが書き出される
- ログの末尾が「Pipeline finished」「Done」などで終わっている(途中でエラー停止していない)
- Discord の告知チャンネル等に投稿が来ている(該当する場合)
- 翌朝、指定した時刻に自動で同じ処理が走る

---

## トラブル時

### エラー: `Load failed: 5: Input/output error`
**原因**: plist の XML が壊れている(タグの閉じ忘れ、文字化け、置換ミスなど)。
**解決方法**: plist ファイルをもう一度開いて、`YOURNAME` などの置換漏れがないか、タグが閉じているか確認。修正後、いったん `unload` してから再度 `load` する。

```bash
launchctl unload ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
launchctl load ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
```

### エラー: `Bootstrap failed: 5: Input/output error`
**原因**: 同じ名前のジョブがすでに登録されている。
**解決方法**: 先に `unload` してから再度 `load` する(上のコマンドと同じ)。

### 時刻になっても動かない
**原因の候補**:
1. plist の Hour/Minute が間違っている
2. plist のスクリプトパス(`YOUR_SCRIPTS_DIR`)が違う
3. Python のパスが違う(`/usr/bin/python3` 等のフルパスになっているか)
4. その時刻に Mac がスリープ中だった
5. `launchctl load` を忘れている

**解決方法**:
- `launchctl list | grep zoom.pipeline` で登録されているか確認
- `_logs/zoom_pipeline.log` および `_logs/zoom_pipeline.err`(stderr)を確認
- 手動発火(`launchctl kickstart`)で動くなら時刻設定の問題

> 💡 **スリープについて**: Mac がスリープ中だと launchd は発火しません。ただしこのパッケージのスクリプトは `caffeinate` でラップされているので、 **実行が始まってからスリープに入ってしまう** ことは防げます。朝の処理を確実に走らせたい人は「システム設定 → ロック画面 → ディスプレイがオフのときコンピュータを自動でスリープさせない」もチェックしておくと安心です。

### ログファイルが空 or 作られない
**原因**: `YOUR_LOG_DIR` で指定したフォルダが存在しない、または書き込み権限がない。
**解決方法**: `mkdir -p /Users/YOU/zoom-course-automation/_logs` で作成。

### 手動発火コマンドの `$(id -u)` がよくわからない
これは「あなたのユーザーID(数字)」に自動で置き換わるシェルの書き方です。そのままコピペでOK。心配な人は `id -u` を単独で実行すると数字(例: `501`)が出るので、それを `gui/501/com.YOURNAME...` のように手で書いてもOKです。

### 解除したい(自動実行を止めたい)
```bash
launchctl unload ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
```

完全に削除する場合は、その後 plist ファイル自体を削除してください。

```bash
rm ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
```

---

★ ここまで終わったら、次は [11_CUSTOMIZATION.md](11_CUSTOMIZATION.md) へ。
