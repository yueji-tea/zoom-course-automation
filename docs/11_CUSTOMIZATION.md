# 11. テンプレ・ルーティング・スキルのカスタマイズ

## このセクションの目的

このパッケージは「とりあえず動く初期値」で出荷されていますが、実際にあなたの講座・コミュニティで使うときには **自分のサービス名・チャンネル名・口調** に合わせて中身を書き換えると、運用がぐっと楽になります。

このセクションでは、よくカスタマイズしたい箇所を **設定ファイル別** にまとめます。最初は気になるところだけ触って、慣れてきたら少しずつ深い設定に進めばOKです。

## 所要時間

10〜60分(どこまでカスタマイズするかによる)

## 前提

- 基本セットアップ(`02`〜`10`)が完了している
- テキストエディタが使える(VS Code、メモ帳系アプリ、`nano` など何でもOK)

---

## 手順

### Step 1: Zoom 会議テンプレートを増やす

ファイル: `config/zoom_meeting_templates.json`

ここでは「○○塾用」「個別面談用」など、用途別に Zoom 会議のデフォルト設定を定義します。

たとえば「○○塾」という新しいシリーズを追加したい場合、以下のように書き加えます。

```json
{
  "templates": {
    "ooo_juku": {
      "topic_prefix": "○○塾",
      "duration": 120,
      "discord_webhook_env": "DISCORD_WEBHOOK_OOO_NOTIFY",
      "discord_role_mention": "@everyone"
    }
  },
  "default_settings": {
    "waiting_room": true,
    "mute_upon_entry": true,
    "auto_recording": "cloud"
  }
}
```

- `topic_prefix`: 会議タイトルの先頭につく文字列(例: 「○○塾 第3回」)
- `duration`: 会議の長さ(分)
- `discord_webhook_env`: 告知投稿先の Discord Webhook を、`.env` のどのキーから読むか
- `default_settings`: 全テンプレに共通で適用される基本設定(待機室・参加時ミュート・自動録画など)

⚠️ JSON は **カンマや括弧の閉じ忘れに敏感** です。編集後は https://jsonlint.com/ などに貼り付けて構文チェックすると安心です。

### Step 2: YouTube アーカイブの Discord 投稿先を振り分ける

ファイル: `config/youtube_archive_discord_routes.json`

「『○○塾』というトピック名を含む録画はAサーバーに、『朝茶部』ならBサーバーに」というように、YouTube アップ後の Discord 告知先を **トピック名のパターンで振り分け** ます。

```json
{
  "routes": [
    {
      "match": "○○塾",
      "match_type": "contains",
      "webhook_env": "DISCORD_WEBHOOK_OOO_ARCHIVE"
    },
    {
      "match": "^朝茶部.*",
      "match_type": "regex",
      "webhook_env": "DISCORD_WEBHOOK_ASACHA_ARCHIVE"
    }
  ],
  "default_webhook_env": "DISCORD_WEBHOOK_GENERAL_ARCHIVE"
}
```

- `match_type`: `contains`(部分一致)または `regex`(正規表現)
- 上から順にマッチをチェックし、どれにも当たらなければ `default_webhook_env` が使われる

### Step 3: Discord 告知メッセージの文面を変える

ファイル: `scripts/zoom_schedule_session.py`

「Zoom会議を作成したよ」と Discord に流す文面を変えたい場合は、このスクリプト内の `build_discord_message` 関数を編集します。

```python
def build_discord_message(topic, start_time, join_url):
    return (
        f"📣 {topic} のZoomを準備しました\n"
        f"開始時刻: {start_time}\n"
        f"参加URL: {join_url}"
    )
```

絵文字を変えたり、自分の口調(「○○のお時間です🌿」など)に整えるとブランドが立ちます。

### Step 4: 要約のプロンプト・トーンを変える

ファイル: `scripts/zoom_summarize_recording.py`

要約 AI の振る舞いを決めるのが、このスクリプト内の `SYSTEM_PROMPT` という変数です。

```python
SYSTEM_PROMPT = """
あなたは○○講座のアシスタントです。Zoom録画の文字起こしから、
受講生が後で振り返りやすい要約を作ってください。
- 3〜5個の要点を箇条書きで
- 専門用語は易しく言い換える
- 講師の口調(やわらかい敬語)に寄せる
"""
```

合わせて `.env` ファイルにある以下も埋めておくと、要約内で講座名・講師名が自然に使われます。

```
COURSE_NAME=○○講座
COURSE_HOST_NAME=山田太郎
```

### Step 5: Claude Code Skill の起動キーワードを増やす

ファイル: `skills/zoom-meeting-create/SKILL.md` および `skills/zoom-archive-process/SKILL.md`

それぞれの先頭にある `description:` フィールドに、Skill を発動させたいフレーズを追加します。

例(`zoom-meeting-create/SKILL.md`):

```yaml
---
description: ゆえじの講座Zoomを作成する。「Zoom作って」「○○塾のZoom用意」「個別面談のZoom」など、会議の事前準備に関する発話で起動。
---
```

ここに自分がよく言う言い回しを足すと、Claude Code がそのフレーズに反応して自動で Skill を起動してくれます。

### Step 6: YouTube 自動除外パターンを調整

ファイル: `scripts/zoom_pipeline.py`

個別面談やパーソナルコーチング系は YouTube にアップしたくない(公開したくない)ものです。これは以下の `YOUTUBE_EXCLUDE_PATTERNS` リストで制御されています。

```python
YOUTUBE_EXCLUDE_PATTERNS = [
    "個別面談",
    "パーソナル",
    "1on1",
    "コーチング",
]
```

自分のサービス名に合わせて追加・削除してください。ここにマッチしたトピック名の録画は、 **要約と Drive バックアップだけ実施し、YouTube アップロードはスキップ** されます。

### Step 7: アップロード対象の動画ファイルを変える

ファイル: `scripts/zoom_upload_to_youtube.py`

Zoom録画は複数の動画ファイル(共有画面のみ・ギャラリービュー・話者ビューなど)が生成されます。デフォルトでは一番見やすい組み合わせがアップロードされますが、`--video` オプションで明示的に指定もできます。

```bash
python3 scripts/zoom_upload_to_youtube.py --video shared_screen_with_gallery_view.mp4
```

選べる代表的なファイル名:

- `shared_screen_with_gallery_view.mp4`(画面共有+顔)
- `shared_screen.mp4`(画面共有のみ)
- `gallery_view.mp4`(顔のみ)
- `active_speaker.mp4`(発言者のみ)

### Step 8: launchd 実行時刻を変える

`10_LAUNCHD_SETUP.md` で設定した plist の `Hour` / `Minute` を編集して、いったん unload → load し直します。

```bash
launchctl unload ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
# (エディタで時刻を変更して保存)
launchctl load ~/Library/LaunchAgents/com.YOURNAME.zoom.pipeline.plist
```

---

## 動作確認

### こうなっていればOK

- 編集した設定ファイル(JSON)が、`python3 -c "import json; json.load(open('config/zoom_meeting_templates.json'))"` でエラーなく読める
- 編集した Python スクリプトが、`python3 -m py_compile scripts/zoom_pipeline.py` でエラーなくコンパイルできる
- 手動でパイプラインを発火 → 期待通り(新テンプレが使われる/新ルートに投稿される/新文面で流れる)
- launchd を再 load した後、`launchctl list | grep zoom.pipeline` で行が表示される

---

## トラブル時

### エラー: `json.decoder.JSONDecodeError`
**原因**: JSON ファイルの構文ミス(カンマ漏れ、括弧閉じ忘れ、末尾カンマなど)。
**解決方法**: https://jsonlint.com/ に内容を貼り付けて、エラー行を修正。

### Python スクリプト編集後にパイプラインが落ちる
**原因**: インデント(字下げ)の崩れ、文字列のクォート忘れなど。
**解決方法**:
```bash
python3 -m py_compile scripts/zoom_pipeline.py
```
でエラー行を特定。元のバックアップ(編集前にコピーしておく癖をつけましょう)に戻すのも有効。

### Skill のキーワードを追加したのに反応しない
**原因**: Claude Code の Skill 一覧キャッシュが古い。
**解決方法**: Claude Code を一度終了して再起動。または新しい会話を開始する。

### Discord 告知が違うサーバーに飛んだ
**原因**: `youtube_archive_discord_routes.json` のマッチパターンが上から順に評価されるため、意図しないルートに当たっている。
**解決方法**: より具体的なパターンを上に、ゆるいパターンを下に並べ替える。

### 「○○ のWebhook URL が見つかりません」エラー
**原因**: `webhook_env` で指定した環境変数名が `.env` に存在しない、または値が空。
**解決方法**: `.env` を開いて、該当キー(例: `DISCORD_WEBHOOK_OOO_NOTIFY=...`)を追記して保存。

---

★ ここまで終わったら、次は [12_TROUBLESHOOTING.md](12_TROUBLESHOOTING.md) へ。
