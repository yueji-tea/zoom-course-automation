# 12. よくあるトラブルと解決方法

## このセクションの目的

このパッケージを使っていて「エラーが出た」「思った通りに動かない」というときの **症状別チェックリスト** です。

エラーメッセージの一部や、起きている現象に当てはまる項目を探して、書かれている解決方法を上から順に試してみてください。「自分一人ではどうにもならない」と感じたら、エラーメッセージ全文と該当のログファイルを添えて開発元に連絡すると話が早いです。

## 所要時間

症状による(5分〜30分)

## 前提

- 該当する処理(Zoom 録画処理、Discord 投稿、launchd 自動実行 など)を一度は実行してみている
- エラーメッセージ・ログを確認できる状態

---

## 手順

### Step 1: まずはログを見る

ほとんどの問題は **ログを見ると原因がわかります**。以下のフォルダのファイルを開いてみてください。

```
/Users/YOU/zoom-course-automation/_logs/
```

主なログファイル:

- `zoom_pipeline.log`(標準出力)
- `zoom_pipeline.err`(エラー出力)
- `discord_reminder.log`(リマインダー関連)

最新のエラー行を確認したい場合:

```bash
tail -50 _logs/zoom_pipeline.err
```

### Step 2: 症状別に下のリストから該当箇所を探す

下にまとめた「トラブル時」セクションから、自分の症状に当てはまるものを見つけてください。

---

## 動作確認

### こうなっていればOK

- ログにエラーが出ていない
- 該当の処理が最後まで走り、Discord 投稿・YouTube アップ・Drive 保存などが期待通り完了している
- 同じエラーが再現しない

---

## トラブル時

### エラー: Zoom 401 Unauthorized

**症状**: Zoom API 呼び出しで「401 Unauthorized」が返ってくる。録画一覧が取れない、ダウンロードできない。
**原因**: Zoom OAuth トークンの期限切れ、または Zoom Marketplace 側で Re-activate が必要になっている。
**解決方法**:
1. ブラウザで https://marketplace.zoom.us/ にアクセス
2. 「Manage」 → 自分の Server-to-Server OAuth アプリを選択
3. 「Activation」タブで Re-activate ボタンを押す
4. 必要なら Client Secret を再生成し、新しい値を `.env` の `ZOOM_CLIENT_SECRET` に貼り直す

---

### エラー: OpenRouter 402 Payment Required

**症状**: 要約生成時に「402 Payment Required」「insufficient credits」のような表示。
**原因**: OpenRouter(要約に使う AI ルーター)の無料枠を使い切った、またはクレジット残高が0。
**解決方法**:
1. https://openrouter.ai/settings/credits にアクセス
2. 残高を確認し、必要に応じて少額(US$5〜10程度)をチャージ
3. しばらく待ってから(課金反映まで数分)もう一度実行

---

### エラー: Discord 403 / 401

**症状**: Discord 投稿が「403 Forbidden」または「401 Unauthorized」で失敗。
**原因**: Webhook URL が削除済み・無効化されている、または Bot Token の期限切れ。
**解決方法**:
1. Discord サーバー設定 → 連携サービス → Webhook を再生成
2. 新しい URL を `.env` の該当キー(例: `DISCORD_WEBHOOK_ASACHA`)に貼り直す
3. 再実行

---

### エラー: Discord 403 (Cloudflare 1010 "The owner of this website has banned your access")

**症状**: Webhook を叩いたら HTML の Cloudflare ブロックページが返ってくる。エラーコード 1010。
**原因**: HTTP リクエストの User-Agent が空、または Cloudflare に弾かれるパターンになっている。
**解決方法**: 該当スクリプト内のリクエスト送信箇所で、ヘッダに以下のような User-Agent を明示する。

```python
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}
```

---

### エラー: YouTube アップロード失敗

**症状**: YouTube アップロード処理が「quotaExceeded」「authentication failed」などで止まる。
**原因の候補**:
1. 1日のクォータ超過(YouTube Data API は1日あたり概ね6本程度のアップロードで上限に達する)
2. OAuth 認証が切れている
3. アップロード先 YouTube アカウントと、認証に使った Google アカウントが食い違っている

**解決方法**:
- クォータ超過なら翌日まで待つ(リセットは太平洋時間 0:00)
- 認証切れなら以下を実行して再認証:
  ```bash
  python3 scripts/youtube_oauth_setup.py
  ```
- アカウント不一致なら、ブラウザでログインしている Google アカウントが目的のチャンネルの所有者になっているか確認

---

### エラー: Google Drive 403 insufficientPermissions

**症状**: Drive アップロードで「403 insufficientPermissions」が出る。
**原因**: 認可スコープが `drive.readonly`(読み取り専用)になっていて、書き込みできない。
**解決方法**: `--drive-scope file` を明示して再認証する。

```bash
gog auth add YOUR_EMAIL --services drive --drive-scope file
```

⚠️ 単に `--services drive` だけで再認証すると readonly に戻ってしまうので、必ず `--drive-scope file` をつけること。

---

### トラブル: launchd が実行されない

**症状**: 設定した時刻になっても処理が走らない、ログも作られない。
**原因の候補**:
1. plist の中のパス(スクリプト/ログ/Python)が間違っている
2. `launchctl load` がそもそも行われていない
3. その時刻に Mac がスリープ中だった
4. plist の XML 構文エラー

**解決方法**:
- 登録確認:
  ```bash
  launchctl list | grep zoom.pipeline
  ```
- 手動発火でテスト:
  ```bash
  launchctl kickstart -k gui/$(id -u)/com.YOURNAME.zoom.pipeline
  ```
- 手動発火なら動く場合は時刻設定 or スリープが原因。`10_LAUNCHD_SETUP.md` の注意書きを再確認。
- 手動発火でも動かない場合は plist のパスが間違っているのでエディタで再確認。

---

### トラブル: リマインダーが時間通りに飛ばない

**症状**: Discord に出るリマインダーが指定時刻からずれて投稿される、または来ない。
**原因の候補**:
- スケジュール定義のタイムゾーンが UTC で保存されており、ローカル時刻と食い違っている
- Mac のシステム時刻自体がずれている

**解決方法**:
- リマインダー定義(`config/discord_reminders.json` 等)のタイムゾーン指定を確認。 UTC で保存している場合は、ローカル時刻に換算してから設定する
- Mac の「システム設定 → 一般 → 日付と時刻」で「日付と時刻を自動的に設定」がオンになっているか確認

---

### トラブル: 要約が「分析できません」になる

**症状**: 要約結果に「内容を分析できませんでした」のようなメッセージしか入っていない。
**原因の候補**:
1. 動画が極端に短い(1分未満)
2. Zoom 側で文字起こし(Audio Transcript)が生成されていない
3. 録音言語と AI が想定している言語が大きく食い違っている

**解決方法**:
- Zoom Web ポータル → 設定 → 録画 → 「音声トランスクリプト」がオンになっているか確認
- 短い録画はそもそも要約対象外として割り切る
- 該当録画のフォルダに `.vtt` や `.txt` の文字起こしファイルが入っているか手動で確認

---

### トラブル: Drive アップで重複フォルダができる

**症状**: 同じ会議の保存フォルダが Google Drive 上に2つできる。
**原因**: 通常は冪等性(同名フォルダを再利用)が効いていますが、フォルダ名の前後にスペースが入っていたり、年月の桁数が違ったりすると別物として扱われます。
**解決方法**: `zoom_upload_to_drive.py` は同名フォルダを再利用する作りなので、それでも重複した場合は手動で Drive 上の片方を削除してOKです。中身を移してから古い方を削除すると安全。

---

### エラー: `○○ が .env にない` / `KeyError: '○○'`

**症状**: スクリプト実行直後に「○○ が `.env` に設定されていません」などのメッセージで停止する。
**原因**: 必要な環境変数(API キー、Webhook URL 等)が `.env` に書かれていないか、値が空。
**解決方法**:
1. `.env` をエディタで開く
2. エラーメッセージに出ているキー(例: `OPENROUTER_API_KEY`)が存在するか確認
3. 存在しなければ追加、値が空ならセットする
4. 保存して再実行(ターミナルを開き直すか、`source .env` を実行)

---

### その他、原因が特定できないとき

1. `_logs/` 配下の最新ログを最後まで読む(エラーは最後の数十行に出ていることが多い)
2. 同じ症状を **手動で1ステップずつ** 再現してみる(`zoom_pipeline.py` をいきなり叩かず、`zoom_download_recording.py` → `zoom_summarize_recording.py` … と個別に動かす)
3. 直前に何を変更したか思い出す(`.env` を触った? plist を編集した? Mac を再起動した?)
4. それでも解決しない場合は、エラーメッセージ全文 + ログの該当行 + 試したことを添えて開発元に相談する

---

★ READMEに戻る → [README](../README.md)
