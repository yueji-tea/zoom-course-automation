# zoom-course-automation

オンライン講座を運営している人のための、Zoom配信フル自動化パッケージ。

「Zoom会議作って」「録画処理して」とAIアシスタント(Claude Code)に話しかけるだけで、以下が全部自動で進む:

```
[ Zoom会議作成 ]
     ↓
   ・ Discord 該当サーバーに@everyone告知投稿
   ・ Discord「イベント」タブにスケジュール登録
   ・ 5分前リマインダーを自動予約(launchd で時間が来たら自動送信)
   ・ Googleカレンダーに予定追加

[ 配信終了後(録画完了したら) ]
     ↓
   ・ Zoom録画を自動ダウンロード
   ・ Claude Haiku で要約生成(主な内容/キーワード/持ち帰りポイント)
   ・ Google Drive にバックアップ
   ・ YouTube に限定公開アップロード
   ・ Obsidian Vault に整形版を保存
   ・ Discord アーカイブチャンネルに視聴URL投稿
```

毎日朝7:30に launchd cron が自動実行するので、放っとけば翌朝までに全部処理される。

---

## こんな人に役立つ

- ★ オンライン講座運営者(Zoom配信 → 録画 → YouTubeアップロードを毎回手作業でやってる)
- ★ コーチ・カウンセラー・コミュニティ運営者(定例会の告知・リマインドを自動化したい)
- ★ 受講生に動画アーカイブを共有したい
- ★ 録画動画の要約を Obsidian に整理しておきたい
- ★ Claude Code を使ってる、もしくはこれから使ってみたい

---

## 何が含まれているか

| 種類 | 数 | 説明 |
|---|---|---|
| Python スクリプト | 12本 | Zoom作成、録画処理、要約、Drive/YouTube/Obsidian保存、Discord投稿 |
| Claude Code Skill | 2本 | チャットで「Zoom作って」「録画処理して」と言うだけで起動 |
| launchd plist テンプレ | 2本 | 毎朝自動実行、リマインダー毎分実行 |
| 設定テンプレ JSON | 2本 | 講座テンプレ、Discord 投稿ルーティング |
| セットアップガイド(日本語) | 12本 | API取得手順を1ステップずつ |
| セットアップウィザード | 1本 | 対話で `.env` を生成 |

---

## 必要なもの

### Mac環境
- macOS 12 以降
- Python 3.10 以降
- Homebrew
- git, gh CLI(GitHub操作)
- gog CLI(Google Workspace操作、任意)
- Claude Code(Skill 利用時)

### サービスアカウント
- Zoom Pro 以上(クラウド録画必須)
- Google アカウント(Drive / Calendar / YouTube)
- Discord アカウント + サーバー管理権限
- OpenRouter アカウント(月数十円〜数百円)
- (任意)Obsidian(ローカル無料)

詳細は [docs/02_PREREQUISITES.md](docs/02_PREREQUISITES.md) を参照。

---

## クイックスタート(15分)

```bash
# 1. クローン
git clone https://github.com/yueji-tea/zoom-course-automation.git
cd zoom-course-automation

# 2. 対話セットアップ(.env を自動生成)
bash setup.sh

# 3. 設定テンプレをコピーして編集
cp config/zoom_meeting_templates.example.json config/zoom_meeting_templates.json
cp config/youtube_archive_discord_routes.example.json config/youtube_archive_discord_routes.json

# 4. YouTube OAuth 認証(1回だけ)
python3 scripts/youtube_oauth_setup.py

# 5. 動作確認
python3 scripts/zoom_list_recordings.py 7

# 6. Claude Code Skill 有効化(任意)
mkdir -p ~/.claude/skills
cp -r skills/zoom-meeting-create ~/.claude/skills/
cp -r skills/zoom-archive-process ~/.claude/skills/

# 7. launchd 自動実行設定(任意)
# launchd/ 配下の .template ファイルを編集して ~/Library/LaunchAgents/ にコピー
# 詳細は docs/10_LAUNCHD_SETUP.md
```

各 API キーの取得手順は docs/ 配下に1ステップずつ書いてある。

---

## セットアップガイド(順番に読むと迷わない)

1. [01_OVERVIEW.md](docs/01_OVERVIEW.md) — このパッケージは何?何ができる?
2. [02_PREREQUISITES.md](docs/02_PREREQUISITES.md) — 必要な準備
3. [03_ZOOM_API_SETUP.md](docs/03_ZOOM_API_SETUP.md) — Zoom Server-to-Server OAuth
4. [04_OPENROUTER_SETUP.md](docs/04_OPENROUTER_SETUP.md) — OpenRouter APIキー
5. [05_DISCORD_BOT_SETUP.md](docs/05_DISCORD_BOT_SETUP.md) — Discord Bot 作成
6. [06_DISCORD_WEBHOOK_SETUP.md](docs/06_DISCORD_WEBHOOK_SETUP.md) — Discord Webhook 取得
7. [07_GOOGLE_OAUTH_SETUP.md](docs/07_GOOGLE_OAUTH_SETUP.md) — Google Cloud + gog CLI
8. [08_YOUTUBE_API_SETUP.md](docs/08_YOUTUBE_API_SETUP.md) — YouTube API + OAuth
9. [09_OBSIDIAN_SETUP.md](docs/09_OBSIDIAN_SETUP.md) — Obsidian Vault 連携(任意)
10. [10_LAUNCHD_SETUP.md](docs/10_LAUNCHD_SETUP.md) — 毎朝自動実行
11. [11_CUSTOMIZATION.md](docs/11_CUSTOMIZATION.md) — テンプレ・ルーティングのカスタマイズ
12. [12_TROUBLESHOOTING.md](docs/12_TROUBLESHOOTING.md) — トラブル時

---

## 使い方の例

### Claude Code 経由(推奨)

ターミナルで Claude Code を起動して、自然言語で頼む:

```
「明日19:00から○○講座 第5回 ○○振り返りのZoom作って」
```

→ Skill `zoom-meeting-create` が起動 → Zoom作成 → Discord告知 → カレンダー登録 → リマインダー予約 まで自動。

```
「録画処理して」
```

→ Skill `zoom-archive-process` が起動 → 未処理の Zoom 録画を全部処理。

### 直接 CLI で

```bash
# Zoom会議作成 + 告知 + リマインダー予約 + カレンダー登録
python3 scripts/zoom_schedule_session.py course1 "第5回 ○○振り返り" --at "2026-07-15 19:00"

# 録画処理(過去3日分)
bash scripts/zoom-process

# 録画処理(過去7日)
bash scripts/zoom-process 7

# 特定トピックだけ処理
bash scripts/zoom-process --topic 朝茶会

# YouTube アップロード抑制
bash scripts/zoom-process --no-youtube
```

### 完全自動運用(launchd)

launchd plist を `~/Library/LaunchAgents/` に登録すれば、毎朝7:30に自動実行される。詳細は [docs/10_LAUNCHD_SETUP.md](docs/10_LAUNCHD_SETUP.md) を参照。

---

## カスタマイズ

- **会議テンプレートを追加・編集**: `config/zoom_meeting_templates.json`
- **Discord 投稿ルーティング**: `config/youtube_archive_discord_routes.json`
- **要約のトーン・専門用語**: `scripts/zoom_summarize_recording.py` の `SYSTEM_PROMPT`
- **告知メッセージの文面**: `scripts/zoom_schedule_session.py` の `build_discord_message`
- **YouTube アップ除外パターン**: `scripts/zoom_pipeline.py` の `YOUTUBE_EXCLUDE_PATTERNS`
- **Skill の起動キーワード**: `skills/*/SKILL.md` の `description`

詳細は [docs/11_CUSTOMIZATION.md](docs/11_CUSTOMIZATION.md)。

---

## トラブル時

- 「Zoom 401」「OpenRouter 402」「Discord 403」「YouTube アップ失敗」など、よくあるエラーの対処方法を [docs/12_TROUBLESHOOTING.md](docs/12_TROUBLESHOOTING.md) に集約

---

## アーキテクチャ(技術者向け)

- **言語**: Python 3 標準ライブラリのみ(urllib, argparse, json 等)、外部依存なし
- **AI**: OpenRouter 経由で Claude Haiku 4.5(またはAnthropic公式API直接)
- **環境変数管理**: `.env` ファイル(`.gitignore` で除外)
- **冪等性**: 各録画ディレクトリ `_meta.json` で処理済みフラグ管理。再実行で重複処理しない
- **タイムゾーン**: ISO 8601 UTC で内部保持、表示時に JST 変換
- **スリープ対策**: launchd 実行は `caffeinate -i` でラップ

---

## ライセンス

[MIT](LICENSE) — 商用利用OK、改変OK、再配布OK、無保証。

---

## クレジット

Created by ゆえじ(@oyueji_tea)2026年6月、Claude Code との共同開発。

このパッケージは、ゆえじが自身のお茶講座運営(「茶養講座」)の手作業を自動化するために構築したものを汎用化したものです。同じように講座運営を頑張ってる方の役に立てば嬉しいです。

---

## 関連リンク

- Claude Code: https://claude.com/claude-code
- Zoom Marketplace: https://marketplace.zoom.us/develop/create
- OpenRouter: https://openrouter.ai/
- Discord Developer Portal: https://discord.com/developers/applications
- Google Cloud Console: https://console.cloud.google.com/
- Obsidian: https://obsidian.md/
