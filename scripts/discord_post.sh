#!/bin/bash
# ===========================================
# Discord Webhook 汎用投稿スクリプト
# 引数:
#   $1 = Webhook URL（必須）
#   $2 = 投稿テキスト（必須、または stdin から読む）
# 環境変数:
#   DISCORD_USERNAME = 表示名（任意）
# 戻り値: 0=成功, 1=失敗
#
# 例:
#   discord_post.sh "$DISCORD_WEBHOOK_MEMO" "今日のメモ"
#   echo "長文" | discord_post.sh "$DISCORD_WEBHOOK_MEMO"
# ===========================================

set -u

WEBHOOK="${1:-}"
MESSAGE="${2:-}"

LOG_DIR="$HOME/transcribe/_logs"
LOG_FILE="$LOG_DIR/discord_$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

if [ -z "$WEBHOOK" ]; then
    log "ERROR: Webhook URL が空"
    echo "Usage: discord_post.sh <webhook_url> <message>" >&2
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
    http_code=$(curl -s -o /tmp/discord_post_resp.$$ -w "%{http_code}" \
        -H "Content-Type: application/json; charset=utf-8" \
        -X POST \
        -d "$payload" \
        "$WEBHOOK")

    if [ "$http_code" = "204" ] || [ "$http_code" = "200" ]; then
        log "投稿成功 (${#chunk}文字)"
        rm -f /tmp/discord_post_resp.$$
        return 0
    else
        log "投稿失敗 HTTP=$http_code body=$(cat /tmp/discord_post_resp.$$ 2>/dev/null)"
        rm -f /tmp/discord_post_resp.$$
        return 1
    fi
}

# 2000文字以下ならそのまま
if [ "${#MESSAGE}" -le 1900 ]; then
    post_chunk "$MESSAGE"
    exit $?
fi

# 1900文字ごとに分割（改行優先で切る）
log "メッセージが長い (${#MESSAGE}文字) ため分割投稿"
python3 - "$MESSAGE" <<'PYEOF' | while IFS= read -r chunk_b64; do
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
    chunk=$(echo "$chunk_b64" | base64 -d)
    post_chunk "$chunk" || exit 1
    sleep 1  # rate limit対策
done
