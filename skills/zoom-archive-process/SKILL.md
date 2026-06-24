---
name: zoom-archive-process
description: Zoomクラウド録画をフル自動処理する。「Zoom録画処理して」「録画アーカイブ進めて」「最近のZoom配信処理して」「昨日の○○の録画上げて」「Zoomパイプライン回して」「録画チェックして」「録画たまってるから処理して」など、過去のZoom会議録画の事後処理に関する発話で起動。録画一覧確認 → DL → 要約生成(Claude Haiku) → Google Drive バックアップ → YouTube限定公開アップロード → 該当Discordサーバーへのアーカイブ案内投稿、までを完全自動化。冪等性あり(処理済みは自動スキップ)、個別面談・コーチング・パーソナル系は YouTube自動除外。
---

# Zoom録画 フル自動処理パイプライン

ユーザーが過去のZoom録画を処理してほしい時、フル自動パイプラインを起動する。

## 自動処理する6ステップ

1. **DL** — Zoomクラウドから MP4(speaker_view + gallery_view) + 字幕(VTT→TXT) + チャットログを `~/transcribe/zoom_recordings/YYYYMMDD_HHMMSS_<topic>/` にダウンロード
2. **要約生成** — Claude Haiku 4.5 (OpenRouter経由) で `_summary.md` を生成(一言サマリー / 主な内容 / キーワード / 持ち帰りポイント)
3. **Drive バックアップ** — 「マイドライブ/Zoom録画/YYYYMMDD_<topic>/」配下にアップロード(動画+字幕+要約+メタ)
4. **YouTube限定公開アップ** — speaker_view を限定公開でアップロード。タイトルは「<トピック> (YYYY/MM/DD)」、説明文は要約全文、タグはキーワードから自動抽出
5. **Obsidian保存** — Vault の `文字起こし/Zoom/YYYYMMDD_HHMMSS_<topic>.md` に整形版を保存。frontmatter(動画リンク含む) + 要約 + 動画リンク3点(YouTube/Drive/ローカル)。CLAUDE.md「全文は保存しない」方針に従い、文字起こし全文は含めない
6. **Discord アーカイブ案内** — トピック名でルーティング → 該当アーカイブチャンネルに YouTube URL を投稿

## YouTube 自動除外パターン

以下キーワードがトピックに含まれる録画は YouTube アップをスキップ(Drive バックアップは実行):
- 個別面談 / 面談 / コーチング / パーソナル / 1on1 / 1-on-1 / 個別セッション / 個別相談

これらは「個別の機微情報を含む」想定で、外部公開を完全防止する運用ルール。

## 発話例とマッピング

| あなたの発話 | 実行内容 |
|---|---|
| 「録画処理して」「録画アーカイブ進めて」 | デフォルト(過去3日) |
| 「過去7日分の録画処理」「先週の録画やって」 | --since 7 |
| 「定例会の録画だけ処理」「○○コミュニティのだけ」 | --topic で絞る |
| 「録画チェックして」「未処理ある?」 | --dry-run で確認だけ |
| 「YouTubeに上げないで処理して」 | --no-youtube |
| 「Driveだけアップして」 | --no-youtube --no-discord |

## 実行手順

### Step 1: 発話から引数を抽出

- **対象期間**: 「過去○日」→ --since ○、「最近の」「最新の」→ デフォルト 3日
- **トピックフィルタ**: 「定例会だけ」「5期のだけ」等 → --topic <キーワード>(部分一致)
- **YouTubeスキップ**: 「YouTube上げないで」「Driveまでで」→ --no-youtube
- **Discord案内スキップ**: 「Discord告知しないで」→ --no-discord
- **要約スキップ**: 「要約は飛ばして」→ --no-summary
- **Driveスキップ**: 「Driveいらない」→ --no-drive
- **Obsidianスキップ**: 「Obsidianに保存しないで」→ --no-obsidian
- **ドライラン**: 「何が処理対象か見せて」「確認だけして」→ --dry-run

### Step 2: 録画一覧プレビュー(対象が多そうな時のみ)

`--since 7` 以上や明示の確認要求があれば、先に処理対象一覧を見せて OK もらってから本実行:

```bash
~/transcribe/_scripts/zoom-process <日数> --dry-run
```

### Step 3: スクリプト実行(caffeinate でスリープ防止)

```bash
caffeinate -i ~/transcribe/_scripts/zoom-process [<日数>] [オプション]
```

例:
```bash
# 過去3日 デフォルト
caffeinate -i ~/transcribe/_scripts/zoom-process

# 過去7日
caffeinate -i ~/transcribe/_scripts/zoom-process 7

# 定例会だけ
caffeinate -i ~/transcribe/_scripts/zoom-process --topic 定例会

# YouTube無しで Drive までで止める
caffeinate -i ~/transcribe/_scripts/zoom-process --no-youtube
```

大量の動画(2.5GB+)を含む場合は長時間ジョブになる(10分+)。バックグラウンド実行も可:
```bash
caffeinate -i ~/transcribe/_scripts/zoom-process & 
```

### Step 4: 結果報告

各録画について以下を集計して報告:

```
✅ パイプライン完了: 成功 N / 失敗 0

📹 ○○講座 第N回 ○○のテーマ(45分)
   ✅ DL / 要約 / Drive / YouTube / Discord案内

📹 ゆきこさん個別面談(60分)
   ✅ DL / 要約 / Drive
   🚫 YouTube除外(個別面談キーワード)

📹 月曜定例会(30分)
   ✅ 全段階既に処理済み(スキップ)

▼ 今回新規アップしたYouTube動画:
- ○○講座 Day5: https://www.youtube.com/watch?v=...
```

## 冪等性(★ 重要)

各録画ディレクトリの `_meta.json` でステップ別の処理済みフラグを管理:

- `downloaded_at` / video files の存在 → DLスキップ判定
- `_summary.md` の存在 (>200バイト) → 要約スキップ判定
- `drive_folder_id` → Driveスキップ判定
- `youtube_video_id` → YouTubeスキップ判定
- `obsidian_saved_at` → Obsidianスキップ判定
- `youtube_discord_posted_at` → Discord案内スキップ判定

何度実行しても、既に処理済みの段階は自動スキップ。途中で失敗した場合、次回実行で残りだけ処理される。

## 完全自動化(launchd)

毎日 7:30 HKT(=8:30 JST)に launchd cron で `zoom-process 3` 自動実行:
- 定例会(5:15-5:45 HKT)の録画準備完了後に処理
- caffeinate-i ラップ済みでスリープ防止
- ログ: `~/transcribe/_logs/zoom_pipeline_YYYYMMDD.log`

つまり、ユーザーが何もしなくても、未処理の録画は翌朝までに全部処理される。手動キックは「すぐ処理したい時」用。

## エラー時の対応

- **要約失敗(OpenRouter token超過)**: 動画が長すぎて OpenRouter 無料枠を超えた場合 → クレジット確認、必要なら追加チャージ案内
- **Drive 重複フォルダ**: 既存フォルダ自動再利用するので発生しないはず。万一発生したら手動削除案内
- **YouTube 認証失敗**: refresh_token 期限切れ等 → `youtube_oauth_setup.py` 再実行案内
- **Discord 403/401**: Webhook URL や Bot Token を `.env` 再確認

## 関連ファイル

- **オーケストレーター**: `~/transcribe/_scripts/zoom_pipeline.py`
- **ショートカット**: `~/transcribe/_scripts/zoom-process [日数]`
- **DL**: `~/transcribe/_scripts/zoom_download_recording.py`
- **要約**: `~/transcribe/_scripts/zoom_summarize_recording.py` (OpenRouter / Claude Haiku 4.5)
- **Drive UP**: `~/transcribe/_scripts/zoom_upload_to_drive.py` (冪等・重複フォルダ防止)
- **YouTube UP**: `~/transcribe/_scripts/zoom_upload_to_youtube.py` (限定公開)
- **Obsidian保存**: `~/transcribe/_scripts/zoom_save_to_obsidian.py` (Vault `文字起こし/Zoom/` 配下)
- **Discord案内**: `~/transcribe/_scripts/post_youtube_archive_to_discord.py` + `youtube_archive_discord_routes.json`
- **launchd cron**: `~/Library/LaunchAgents/com.ochinaoko.zoom.pipeline.plist`
- **ログ**: `~/transcribe/_logs/zoom_pipeline_YYYYMMDD.log`

## Drive の保存先

`マイドライブ/Zoom録画/` 配下、フォルダ名 `YYYYMMDD_<topic>` 形式(時刻は省略)。
フォルダ親ID: `1fs4wikaUV_buf337DMcbLKPxyFfm7vSZ`

## Obsidian の保存先

Vault: `/Users/ochinaoko/Library/Mobile Documents/com~apple~CloudDocs/★Obsidian_ユーザー`
保存先: `文字起こし/Zoom/YYYYMMDD_HHMMSS_<topic>.md`

中身:
- frontmatter (created / date / topic / duration / source=Zoom録画 / refined=true / tags=[zoom,整形済み] / youtube_url / drive_folder_url)
- 要約全文(_summary.md の中身)
- 動画リンク3点(YouTube限定公開URL / Drive フォルダURL / ローカル録画パス)

文字起こし全文は含めない(CLAUDE.md 運用ルール: あなたの好み)。生データが必要な場合は Drive 内の `audio_transcript.vtt` または `audio_transcript.txt` を参照。

★ 振り分け(将来予定):
- 現在は全録画一律 `文字起こし/Zoom/` に保存
- 将来、個別面談・コーチング系を `2_講座・コミュニティ/ビジネス伴走/{相手名}/` に、○○講座面談を `3_プロモ・企画/_2026○○講座個別面談/` に振り分ける拡張余地あり

## YouTube アーカイブ Discord ルーティング

`youtube_archive_discord_routes.json` で振り分け:
- トピック「○○講座」を含む → `DISCORD_WEBHOOK_CHA_YO_5KI_ARCHIVE`(○○講座アーカイブチャンネル)
- トピックコミュニティ用パターンを含む → `DISCORD_WEBHOOK_DABUHAPI`
- マッチしないトピック(個別面談・パーソナル等)→ 投稿スキップ(エラーにしない)

ルーティングを変えたい場合は `youtube_archive_discord_routes.json` を編集。

## メッセージのトーン

Discord 案内メッセージ(`post_youtube_archive_to_discord.py` 生成)はユーザー運用ルールに準拠:
- Markdown 太字 (`**`) 禁止(コピペ時の手間を避ける)
- 「アーカイブ動画をアップしました」「必要な方はこちらからご覧ください」など丁寧調

ユーザーから変更要望があれば `post_youtube_archive_to_discord.py` 内のテンプレを編集。
