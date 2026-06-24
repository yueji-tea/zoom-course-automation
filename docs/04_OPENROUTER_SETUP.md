# 04. OpenRouter のアカウント作成と APIキー取得

## このセクションの目的

このパッケージは、Zoom録画の中身を **AI(Claude など)で自動要約** します。
そのAIに話しかけるために、**OpenRouter** という中継サービスのアカウントとAPIキーを用意します。

OpenRouter を使う理由:
- Claude / GPT / Gemini など複数のAIモデルを **1つのAPIキー** で使い分けられる
- 料金は **使った分だけ**(月固定費なし)
- 動画1本の要約は **だいたい数円〜数十円**

なお、Anthropic 公式API を直接使うこともできます(末尾に説明あり)。

## 所要時間

10〜15分

## 前提

- メールアドレス(Googleアカウントでログインもできる)
- クレジットカードまたはデビットカード(チャージ用、最低$5から)
- 03_ZOOM_API_SETUP.md が完了している

---

## 用語の説明

- **API キー**: アプリが「OpenRouter にアクセスするための鍵」。長い文字列。★ 絶対に他人に見せない
- **クレジット**: OpenRouter内の前払い残高。チャージしておくと、AIを使うたびに少しずつ減る
- **モデル**: AIの種類(Claude Sonnet 4 / GPT-4o / Gemini Pro など)
- **トークン**: AIが文章を扱う最小単位。料金計算の基準

---

## OpenRouter とは(もう少し詳しく)

OpenRouter は「**いろんなAI企業のAPIを1か所にまとめた中継サービス**」です。

例:
- 普通は Claude を使うには Anthropic と契約、GPT を使うには OpenAI と契約…と別々に契約が必要
- OpenRouter なら、1つのアカウント+1つのAPIキーで全部使える
- このパッケージでも、用途によって違うモデルを呼び分けています(要約は安いモデル、難しい判断は高いモデル、など)

代わりに OpenRouter が **+5%程度の手数料** を取ります。
「いろんなモデルを試したい」「契約を分けたくない」人にはおすすめ。
「Claude しか使わない、最安にしたい」人は Anthropic 公式API でもOK(末尾参照)。

---

## 手順

### Step 1: OpenRouter にアクセス

ブラウザで以下を開きます。

```
https://openrouter.ai/
```

### Step 2: 新規アカウント作成

1. 右上の「**Sign In**」をクリック
2. 「**Sign in with Google**」または「Sign in with GitHub」を選ぶ(おすすめ:Google)
3. Googleアカウントで認証する
4. 利用規約に同意して登録完了

普段使っているGoogleアカウントでOKです。

### Step 3: クレジットをチャージする

1. 画面右上の自分のアイコン → 「**Credits**」をクリック
   または直接 https://openrouter.ai/credits を開く
2. 「**Add Credits**」ボタンをクリック
3. チャージ金額を選ぶ(最低$5から)
   - 初回は **$5** で十分です(動画数十本ぶんの要約ができます)
4. 「**Pay with Card**」でクレジットカード情報を入力
5. 決済完了

⚠️ 「Auto Top-Up(自動チャージ)」は、最初はオフのままにすることをおすすめします。残高を確認しながら使うほうが安心です。

### Step 4: API キーを作成する

1. 画面右上の自分のアイコン → 「**Keys**」をクリック
   または直接 https://openrouter.ai/keys を開く
2. 「**Create Key**」ボタンをクリック
3. 「Name」に分かりやすい名前を入れる(例: `zoom-course-automation`)
4. 「Credit limit(クレジット制限)」は空欄でOK(設定すると、そのキーで使える上限を縛れる)
5. 「**Create**」をクリック

### Step 5: APIキーをコピーする(★ 一度しか表示されない)

⚠️ **★ APIキーは作成直後の画面でしか表示されません**(セキュリティのため)。

`sk-or-v1-xxxxxxxxxxxxxxxxxxxxx...` のような長い文字列が表示されたら、**すぐにコピー**して、Macの「メモ」アプリなどに一時的に貼ってください。

もし閉じてしまった場合は、もう一度「Create Key」して新しいキーを作り直してください(古いキーは削除でOK)。

### Step 6: APIキーを .env ファイルに貼る

ターミナルで以下を実行:

```bash
cd ~/zoom-course-automation/
open -e .env
```

開いた `.env` ファイルに以下を追記(★ 値は自分のキーに置き換える):

```
OPENROUTER_API_KEY=sk-or-v1-ここに貼る
```

03 で書いた `ZOOM_xxx` の下に追加すればOK。
保存(Command + S)して閉じる。

最終的に `.env` はこんな感じになっているはず:

```
ZOOM_ACCOUNT_ID=...
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
OPENROUTER_API_KEY=sk-or-v1-...
```

---

## 月の使用量目安(参考)

このパッケージの主な用途別のコスト感:

| 処理 | 1回あたり | 月20回 |
|---|---|---|
| 60分の録画を要約 | $0.05〜$0.20 | $1〜$4 |
| 90分の録画を要約 | $0.10〜$0.30 | $2〜$6 |

→ 月数十円〜数百円(500円弱)で収まるケースが多いです。

残高は OpenRouter の Credits ページでいつでも確認できます。

---

## 代替案: Anthropic 公式API を直接使う

「Claude しか使わない」「OpenRouterの+5%手数料が気になる」場合は、Anthropic 公式API を直接使えます。

### Anthropic 公式 API のメリット
- OpenRouter手数料(5%)がかからない
- 公式なので最新モデルが最速で使える

### Anthropic 公式 API のデメリット
- Claude 以外のモデル(GPT, Gemini)は使えない
- 別途 Anthropic Console での契約が必要

### 切り替え方法
1. https://console.anthropic.com/ で登録
2. 「API Keys」で新規キー作成($5以上の前払いが必要)
3. `.env` に追加:
```
ANTHROPIC_API_KEY=sk-ant-...
```
4. パッケージ側の設定で「Anthropic を使う」を有効化(該当ドキュメントで案内予定)

★ OpenRouter と Anthropic 公式、両方の `*_API_KEY` を `.env` に入れておいて、設定で切り替えることも可能です。

---

## 動作確認

### こうなっていればOK

1. OpenRouter の Credits ページに「$5.00」(またはチャージした金額)が表示されている
2. Keys ページに作ったAPIキーが一覧に出ている(「Created」日付が今日になっている)
3. `.env` ファイルに `OPENROUTER_API_KEY=sk-or-v1-...` が入っている

ターミナルで確認:

```bash
grep -E '^OPENROUTER_API_KEY' ~/zoom-course-automation/.env | sed 's/=.*/=***/'
```

→ `OPENROUTER_API_KEY=***` と出ればOK。

### APIキーの疎通テスト(任意)

ターミナルで以下を実行すると、OpenRouter にアクセスできるか確認できます(★ `your-key` は自分のキーに置き換える):

```bash
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer your-key" | head -20
```

→ JSONでモデル一覧が返ってくればOK。
→ `401 Unauthorized` が出る場合は、キーが間違っている可能性があります。

---

## トラブル時

### エラー: APIキー作成時に「Insufficient credits」
**原因**: クレジットが$0 のままで、キーを使う前段階で弾かれている可能性。

**解決方法**:
Step 3 の手順でまず$5チャージする → そのあとキー作成。

### エラー: クレジットカードが弾かれる
**原因**: 海外決済が止められているカード、または3Dセキュア未対応。

**解決方法**:
- カード会社に「OpenRouter からの決済を許可してほしい」と連絡
- 別のカード(Visa / Mastercard 推奨)で試す
- どうしてもダメな場合は Anthropic 公式API(末尾の代替案)を検討

### エラー: 「Rate limit exceeded」
**原因**: 短時間に大量のリクエストを送って、OpenRouter側で制限がかかった。

**解決方法**:
1〜2分待ってから再実行する。
それでも続く場合は、無料枠ではなく Credits が残っているか確認。

### APIキーを失くした / 漏らした疑い
**原因**: キーを誤って他人に共有した、SNS等に貼ってしまった。

**解決方法**:
1. すぐに OpenRouter の Keys ページで該当キーの「**Delete**」ボタンを押して無効化
2. 新しいキーを「Create Key」で作る
3. `.env` ファイルの値を新しいキーに置き換える

### `.env` ファイルが見つからない / 開けない
**原因**: ファイル名の先頭が `.` なので Finder では「隠しファイル」扱い。

**解決方法**:
ターミナルから開く:
```bash
open -e ~/zoom-course-automation/.env
```
Finder で見えるようにするには、Finder で `Command + Shift + .` を押す(隠しファイル表示の切り替え)。

---

★ ここまで終わったら、次は [05_DISCORD_BOT_SETUP.md](05_DISCORD_BOT_SETUP.md) へ。
