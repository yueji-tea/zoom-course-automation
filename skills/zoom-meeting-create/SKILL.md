---
name: zoom-meeting-create
description: あなたの講座・面談・コミュニティ等のZoom会議を作成する。「Zoom作って」「○期セッション設定」「コミュニティMTG作って」「定例会のZoom用意」「○○さんの個別面談のZoom作って」「イベントのZoom」など、会議の事前準備に関するすべての発話で起動。Zoom作成と同時に、該当するDiscordサーバーへの@everyone告知投稿、Discord Eventsへの登録、5分前自動リマインダーの予約、指定のGoogleカレンダー(.env GCAL_TARGET_CALENDAR)への予定追加までを一括で実行する。
---

# Zoom会議作成 + 告知連動 統合フロー

ユーザーがZoom会議の準備を依頼してきた時、テンプレートに基づいて会議を作成し、関連する告知・カレンダー・リマインダーまで一括で処理する。

## 利用可能なテンプレート

| キー | 用途 | デフォルト時間 | Discord告知先 |
|---|---|---|---|
| `5ki` | 講座シリーズ(例: 5期講座) | 90分 | (あなたの講座Discordサーバー) |
| `dabuhapi` | コミュニティMTG | 60分 | (あなたのコミュニティDiscordサーバー) |
| `asacha` | 月曜定例会 | 30分 | なし(告知不要) |
| `kobetsu` | 個別面談・コーチング | 60分 | なし(YouTube自動除外対象) |
| `tsunagari` | イベント | 180分 | なし |
| `freeform` | 自由形式 | 60分 | なし |

## 発話例とマッピング

| あなたの発話 | テンプレ | タイトル例 |
|---|---|---|
| 「明日19:00から5期Day5のZoom作って、体質チェック振り返り」 | 5ki | "Day5 体質チェック振り返り" |
| 「○○コミュニティ週次MTGのZoom、明日21:00から」 | dabuhapi | "週次MTG" |
| 「明日定例会のZoom用意して」 | asacha | "" (空でOK) |
| 「ゆきこさんの個別面談Zoom作って、今週金曜14:00から」 | kobetsu | "ゆきこさん" |
| 「イベントのZoom、7月15日13:00から3時間」 | tsunagari | "" (空でOK) |

## 実行手順

### Step 1: 発話から引数を抽出

あなたの発話を解析して以下を抽出:

- **テンプレキー**: 「5期」「○○講座」→ `5ki` / 「○○コミュニティ」→ `dabuhapi` / 「定例会」→ `asacha` / 「個別面談」「コーチング」「○○さんの面談」→ `kobetsu` / 「イベント」→ `tsunagari` / 該当なし→ `freeform`
- **タイトル**: 会議の具体的な内容(例: "Day5 体質チェック振り返り")。テンプレに既に prefix が含まれるので、prefix を除いた部分のみ
- **日時**: 「明日19:00」「今週金曜14:00」「今すぐ」等を YYYY-MM-DD HH:MM (JST) 形式に変換。「今すぐ」「すぐに」「これから」などはインスタント会議(--at 省略)
- **所要時間**: ユーザーが「90分」「2時間」と指定した場合のみ --duration で渡す(なければテンプレ既定)
- **補足メモ**: 「持ち物○○」「事前に○○読んでおいて」等の参加者向け案内文(あれば --note で渡す)

### Step 2: 実行前確認(★必須)

すべての引数を抽出したら、実行前に必ず以下フォーマットでユーザーに確認:

```
これで Zoom 作成します:

▼ テンプレ: 5ki (○○講座、デフォルト90分)
▼ タイトル: Day5 体質チェック振り返り
▼ 日時: 2026-07-15 19:00 JST (90分)
▼ 補足メモ: ノートと対象テーマをご用意ください

連動して実行する:
- Discord告知 → (あなたの講座Discordサーバー)(@everyone)
- Discord Event 登録(イベントタブ)
- 5分前リマインダー予約 → 18:55 JST
- Googleカレンダー登録 → ユーザーSKD

このまま実行していい?
```

ユーザーが「OK」「進めて」等の返答をしたら Step 3 へ。修正要望があれば抽出し直し。

### Step 3: スクリプト実行

```bash
python3 ~/transcribe/_scripts/zoom_schedule_session.py <template> "<title>" \
    --at "<YYYY-MM-DD HH:MM>" \
    [--duration <分>] \
    [--note "<補足>"]
```

例:
```bash
python3 ~/transcribe/_scripts/zoom_schedule_session.py 5ki "Day5 体質チェック振り返り" \
    --at "2026-07-15 19:00" \
    --note "ノートと対象テーマをご用意ください"
```

### Step 4: 結果報告

実行結果から以下を抽出して整形報告:
- Zoom URL / ミーティングID
- Discord告知の投稿先と内容(プレビュー)
- Discord Event ID
- リマインダー予約時刻
- Googleカレンダーの登録結果と URL

報告フォーマット例:
```
✅ Zoom作成完了

▼ Zoom URL: https://us06web.zoom.us/j/...
▼ ミーティングID: ... ... ...
▼ 開催: 2026/07/15 (火) 日本時間19:00 (90分)

連動処理:
- ✅ Discord告知投稿 → (あなたの講座Discordサーバー)
- ✅ Discord Event登録 (イベントタブ)
- ✅ 5分前リマインダー予約 → 18:55 JST 自動送信
- ✅ Googleカレンダー登録 → ユーザーSKD
```

## エラー時の対応

- **「日時が過去」エラー**: ユーザーに「日時が過去ですが、本当に作っていい?」と確認
- **「テンプレキー未定義」**: 一覧を提示してどれにするか確認
- **Discord 403 エラー**: Webhook URL や Bot Token を `.env` 再確認
- **Zoom API 401 エラー**: トークン期限切れ等、Zoom Marketplace で Re-activate 必要を案内

## インスタント会議の特例

「今すぐ」「これから」等のインスタント開始の場合:
- `--at` を省略 → type=1 (インスタント) で作成
- Discord Event 作成はスキップされる(インスタントは Event 不可)
- リマインダー予約もスキップされる(5分前は既に過去)
- カレンダー登録もスキップされる
- Discord告知は「ただいまから○○を開始します」形式に変わる(スクリプトが自動判定)

## 関連ファイル

- 統合スクリプト: `~/transcribe/_scripts/zoom_schedule_session.py`
- 単独Zoom作成: `~/transcribe/_scripts/zoom_create_meeting.py` (内部呼び出し)
- テンプレ定義: `~/transcribe/_scripts/zoom_meeting_templates.json`
- 環境変数: `~/transcribe/_scripts/.env` (ZOOM/DISCORD/GCAL 系)
- リマインダーキュー: `~/transcribe/_scripts/discord_reminders_pending.json`
- リマインダー実行: launchd `com.ochinaoko.discord.reminder.runner` (毎分起動)

## 補足

- あなたのZoomデフォルト設定(待機室ON・参加時ミュート・参加時ビデオOFF・パスコードなし)は templates JSON の default_settings で全テンプレ共通適用
- 時刻表記は常に JST(日本時間)
- @everyone 通知が告知メッセージとリマインダーの両方に入る(ユーザー確認済み運用ルール)
- メッセージから Markdown 太字 (`**`) は禁止(コピペ時の手間を避ける、ユーザー運用ルール)
