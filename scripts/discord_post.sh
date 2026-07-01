#!/bin/bash
# ===========================================
# Discord Webhook 汎用投稿スクリプト
#
# 使い方:
#   DISCORD_WEBHOOK=xxx discord_post.sh "投稿テキスト"
#   DISCORD_WEBHOOK=xxx echo "長文" | discord_post.sh
#   discord_post.sh --webhook-env DISCORD_WEBHOOK_MEMO "テキスト"
#
# セキュリティ:
#   - Webhook URL は環境変数 DISCORD_WEBHOOK 経由(argv には載せない → ps 漏洩防止)
#   - 一時ファイルは mktemp で予測不可能なパス(symlink attack 防止)
#
# 環境変数:
#   DISCORD_WEBHOOK = Webhook URL(必須)
#   DISCORD_USERNAME = 表示名(任意)
# 戻り値: 0=成功, 1=失敗
# ===========================================

set -u

# --webhook-env <VAR_NAME> オプションで別の環境変数から webhook を読める
if [ "${1:-}" = "--webhook-env" ] && [ -n "${2:-}" ]; then
    WEBHOOK="${!2:-}"
    shift 2
else
    WEBHOOK="${DISCORD_WEBHOOK:-}"
fi

MESSAGE="${1:-}"

LOG_DIR="${LOG_DIR:-$HOME/transcribe/_logs}"
LOG_FILE="$LOG_DIR/discord_$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

if [ -z "$WEBHOOK" ]; then
    log "ERROR: DISCORD_WEBHOOK 環境変数が未設定"
    echo "Usage: DISCORD_WEBHOOK=<url> discord_post.sh <message>" >&2
    echo "  または: discord_post.sh --webhook-env DISCORD_WEBHOOK_XXX <message>" >&2
    exit 1
fi

# 引数になければ stdin から読む
if [ -z "$MESSAGE" ]; then
    MESSAGE=$(cat)
fi

if [ -z "$MESSAGE" ]; then
    log "ERROR: メッセージが空"
    exit 1
fi

USERNAME="${DISCORD_USERNAME:-CourseBot}"

# ★ 予測不可能な一時ファイル(symlink attack 防止)
RESP_FILE=$(mktemp -t discord_post_resp.XXXXXXXX)
trap 'rm -f "$RESP_FILE"' EXIT

# Discord の1メッセージ上限は2000文字。超えたら分割投稿。
post_chunk() {
    local chunk="$1"
    local payload
    payload=$(python3 -c '
import json, sys
content = sys.argv[1]
username = sys.argv[2]
print(json.dumps({"content": content, "username": username}, ensure_ascii=False))
' "$chunk" "$USERNAME")

    local http_code
    http_code=$(curl -s -o "$RESP_FILE" -w "%{http_code}" \
        -H "Content-Type: application/json; charset=utf-8" \
        -H "User-Agent: Mozilla/5.0 (Macintosh; AppleWebKit) DiscordPostBot/1.0" \
        -X POST \
        --data-binary "$payload" \
        "$WEBHOOK")

    if [ "$http_code" = "204" ] || [ "$http_code" = "200" ]; then
        log "投稿成功 (${#chunk}文字)"
        return 0
    else
        log "投稿失敗 HTTP=$http_code body=$(cat "$RESP_FILE" 2>/dev/null | head -c 300)"
        return 1
    fi
}

# 2000文字以下ならそのまま
if [ "${#MESSAGE}" -le 1900 ]; then
    post_chunk "$MESSAGE"
    exit $?
fi

# 1900文字ごとに分割(改行優先で切る)
# ★ pipe subshell の exit 1 が親に伝播しないバグを修正: 全チャンクを配列に読んでからループ
log "メッセージが長い (${#MESSAGE}文字) ため分割投稿"

chunks_file=$(mktemp -t discord_chunks.XXXXXXXX)
trap 'rm -f "$RESP_FILE" "$chunks_file"' EXIT

python3 - "$MESSAGE" > "$chunks_file" <<'PYEOF'
import sys, base64
text = sys.argv[1]
max_len = 1900
i = 0
while i < len(text):
    end = min(i + max_len, len(text))
    if end < len(text):
        nl = text.rfind('\n', i, end)
        if nl > i + max_len // 2:
            end = nl + 1
    chunk = text[i:end]
    print(base64.b64encode(chunk.encode('utf-8')).decode('ascii'))
    i = end
PYEOF

# 親プロセスでループ → post_chunk 失敗時に確実に exit 1
exit_code=0
while IFS= read -r chunk_b64; do
    chunk=$(echo "$chunk_b64" | base64 -d)
    if ! post_chunk "$chunk"; then
        exit_code=1
        break
    fi
    sleep 1  # rate limit対策
done < "$chunks_file"

exit $exit_code
