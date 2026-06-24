# zoom-course-automation

オンライン講座を運営している人のための、Zoom配信フル自動化パッケージ。

「Zoom会議作って」「録画処理して」とAIアシスタント(Claude Code)に話しかけるだけで、以下が全部自動で進む:

```
[ Zoom会議作成 ]
     ↓
   ・ 受講者向けチャットアプリ(Discord等)に @everyone 告知投稿
   ・ チャットの「イベント」タブにスケジュール登録
   ・ 5分前リマインダーを自動予約(launchd で時間が来たら自動送信)
   ・ Googleカレンダーに予定追加

[ 配信終了後(録画完了したら) ]
     ↓
   ・ Zoom録画を自動ダウンロード
   ・ Claude Haiku で要約生成(主な内容/キーワード/持ち帰りポイント)
   ・ Google Drive にバックアップ
   ・ YouTube に限定公開アップロード
   ・ Obsidian Vault に整形版を保存
   ・ チャットアーカイブチャンネルに視聴URL投稿
```

毎日朝7:30に launchd cron が自動実行するので、放っとけば翌朝までに全部処理される。

---

## ⚡ クイックスタート(★ ターミナル操作ほぼナシで OK ★)

このパッケージは **「AI に頼むだけ」のセットアップ方式** を採用しています。
ターミナルでコマンドを覚える必要はありません。

### Step 0:Claude Code を持ってない方

★ Claude Code は Anthropic 社が無料提供する CLI ツール。AIアシスタント(Claude)とターミナルで会話できる。

▼ 公式インストールガイド: https://docs.claude.com/claude-code

▼ Mac の場合(Homebrew で簡単インストール):
```bash
brew install --cask claude-code
```

▼ インストール後、ターミナルで `claude` と打てば起動

★ 詳しいインストール手順: 公式ガイド or 「Claude Code インストール方法」で検索

### Step 1:Claude Code を起動

1. Mac で「ターミナル」アプリを開く(⌘+Space → "terminal" で検索)
2. `claude` と打ってエンター

### Step 2:[SETUP_PROMPT.md](SETUP_PROMPT.md) のプロンプトをコピペ

1. [SETUP_PROMPT.md](SETUP_PROMPT.md) を開く
2. 中の "コピー専用プロンプト"(\`\`\`で囲まれた長文)を全部コピー
3. Claude Code に貼り付け → エンター

### Step 3:あとは対話で進める

AI が以下を1つずつガイドしてくれます:

- 必要な API キーの取得手順(Zoom / OpenRouter / Discord / YouTube 等)
- 取得した値の `.env` への書き込み(これは自動)
- あなたの講座構造に合わせたテンプレ JSON 生成
- Claude Code Skill の配置
- 完全自動運用(launchd)のセットアップ
- 動作確認テスト
- 完了後のカスタマイズ相談

途中で「わからない」「これスキップしたい」と言えば、AI が柔軟に対応。
分からないところは聞き直せばOK。

---

## こんな人に役立つ

- ★ オンライン講座運営者(Zoom配信 → 録画 → YouTubeアップロードを毎回手作業でやってる)
- ★ コーチ・カウンセラー・コミュニティ運営者(定例会の告知・リマインドを自動化したい)
- ★ 受講生に動画アーカイブを共有したい
- ★ 録画動画の要約を Obsidian に整理しておきたい
- ★ Claude Code を使ってる、もしくはこれから使ってみたい
- ★ ターミナル操作は苦手だけど、AI に「お願いするだけ」で動く仕組みは欲しい

---

## 何が含まれているか

| 種類 | 数 | 説明 |
|---|---|---|
| Python スクリプト | 12本 | Zoom作成、録画処理、要約、Drive/YouTube/Obsidian保存、Discord投稿 |
| Claude Code Skill | 2本 | チャットで「Zoom作って」「録画処理して」と言うだけで起動 |
| セットアッププロンプト | 1本 | コピペするだけで AI がセットアップを伴走 |
| launchd plist テンプレ | 2本 | 毎朝自動実行、リマインダー毎分実行 |
| 設定テンプレ JSON | 2本 | 講座テンプレ、Discord 投稿ルーティング |
| セットアップガイド(日本語) | 12本 | API取得手順の詳細解説(困った時の参照用) |
| セットアップウィザード | 1本 | 代替手段:対話シェルスクリプトで .env 生成 |

---

## 必要なもの

### Mac環境
- macOS 12 以降
- Python 3.10 以降
- Homebrew
- git, gh CLI(GitHub操作)
- ★ Claude Code(これがメイン)

### サービスアカウント
- Zoom Pro 以上(クラウド録画必須)
- Google アカウント(Drive / Calendar / YouTube)
- 受講者向けチャット(Discord 推奨、Slack/LINE/Chatwork も拡張可)
- OpenRouter アカウント(月数十円〜数百円)
- (任意)Obsidian(ローカル無料)

詳細は [docs/02_PREREQUISITES.md](docs/02_PREREQUISITES.md) を参照。

---

## 使い方の例

### Claude Code 経由(推奨・通常運用)

セットアップ完了後、ターミナルで Claude Code を起動して、自然言語で頼む:

```
「明日19:00から○○講座 第5回 ○○振り返りのZoom作って」
```

→ Skill `zoom-meeting-create` が起動 → Zoom作成 → Discord告知 → カレンダー登録 → リマインダー予約 まで自動。

```
「録画処理して」
```

→ Skill `zoom-archive-process` が起動 → 未処理の Zoom 録画を全部処理。

### 完全自動運用(launchd)

launchd plist を `~/Library/LaunchAgents/` に登録すれば、毎朝7:30に自動実行される。詳細は [docs/10_LAUNCHD_SETUP.md](docs/10_LAUNCHD_SETUP.md) を参照。

### CLI で直接

慣れた人向け:

```bash
python3 scripts/zoom_schedule_session.py course1 "第5回 ○○振り返り" --at "2026-07-15 19:00"
bash scripts/zoom-process
```

---

## セットアップガイド(困った時・詳細を見たい時)

セットアッププロンプトで進めてれば各 docs は基本見なくて OK ですが、詰まった時の参照用:

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

## カスタマイズ

Claude Code に「○○をカスタマイズしたい」と相談するだけ:

- 「要約のトーンをもっとフランクに」
- 「Discord 告知メッセージの文面を変えたい」
- 「○○講座のテンプレを追加したい」
- 「特定キーワードを YouTube 自動除外に追加」
- 「Slack 連携に切り替えたい」
- 「launchd の時刻を朝6時に変えたい」

→ AI が該当ファイルを編集してくれる。

詳細は [docs/11_CUSTOMIZATION.md](docs/11_CUSTOMIZATION.md)。

---

## トラブル時

- 「Zoom 401」「OpenRouter 402」「Discord 403」「YouTube アップ失敗」など、よくあるエラーの対処方法を [docs/12_TROUBLESHOOTING.md](docs/12_TROUBLESHOOTING.md) に集約
- それでも詰まったら Claude Code に「○○のエラーが出た」と相談 → 一緒にデバッグ

---

## アーキテクチャ(技術者向け)

- **言語**: Python 3 標準ライブラリのみ(urllib, argparse, json 等)、外部依存なし
- **AI**: OpenRouter 経由で Claude Haiku 4.5(またはAnthropic公式API直接)
- **環境変数管理**: `.env` ファイル(`.gitignore` で除外)
- **冪等性**: 各録画ディレクトリ `_meta.json` で処理済みフラグ管理。再実行で重複処理しない
- **タイムゾーン**: ISO 8601 UTC で内部保持、表示時に JST 変換
- **スリープ対策**: launchd 実行は `caffeinate -i` でラップ

---

## 代替セットアップ手段(技術者向け)

Claude Code を使わず、自分でセットアップしたい場合:

```bash
git clone https://github.com/yueji-tea/zoom-course-automation.git
cd zoom-course-automation
bash setup.sh   # 対話的に .env を生成
cp config/zoom_meeting_templates.example.json config/zoom_meeting_templates.json
cp config/youtube_archive_discord_routes.example.json config/youtube_archive_discord_routes.json
python3 scripts/youtube_oauth_setup.py
```

その他のステップは docs/ の各ファイルを順に読んで進めてください。

---

## ライセンス

[MIT](LICENSE) — 商用利用OK、改変OK、再配布OK、無保証。

---

## クレジット

Created by 越智ゆえじ(@ueji-tea)2026年6月、Claude Code との共同開発。

このパッケージは、ゆえじが自身のオンライン講座運営(「中国茶ライフスタイル実践講座」)の手作業を自動化するために構築したものを汎用化したものです。同じように講座運営をがんばってる方の役に立てば嬉しいです。

インスタグラム
https://www.instagram.com/yueji_chanko/?hl=ja

---

## 関連リンク

- Claude Code: https://docs.claude.com/claude-code
- Zoom Marketplace: https://marketplace.zoom.us/develop/create
- OpenRouter: https://openrouter.ai/
- Discord Developer Portal: https://discord.com/developers/applications
- Google Cloud Console: https://console.cloud.google.com/
- Obsidian: https://obsidian.md/
