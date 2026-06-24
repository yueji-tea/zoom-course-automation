#!/usr/bin/env python3
"""discord_reminders_pending.json の予約済みリマインダーを実行

挙動:
- discord_reminders_pending.json を読み、fire_at_jst が現在時刻以下のものを送信
- 送信成功したエントリは削除
- 失敗エントリは残す(次回リトライ)
- launchd で毎分起動する想定
"""
import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))

SCRIPTS_DIR = Path.home() / "transcribe" / "_scripts"
ENV_PATH = SCRIPTS_DIR / ".env"
PENDING_REMINDERS_PATH = SCRIPTS_DIR / "discord_reminders_pending.json"
LOG_DIR = Path.home() / "transcribe" / "_logs"


def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"discord_reminder_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a") as f:
        f.write(line + "\n")


def build_reminder_message(reminder):
    """リマインドメッセージ(@everyone 必須)"""
    lines = [
        "@everyone",
        f"🟢 この後{reminder['start_hhmm']}から",
        f"{reminder['topic']} を開始します",
        "",
        "▼ ご参加はこちらから",
        reminder["join_url"],
        f"ミーティングID: {reminder['meeting_id_formatted']}",
        "",
        "▼ ご案内",
        "",
        "ぜひご参加ください",
    ]
    note = reminder.get("note", "")
    if note:
        lines.append("")
        lines.append(note)
    return "\n".join(lines)


def post_to_discord(webhook_url, message):
    body = json.dumps({
        "content": message,
        "allowed_mentions": {"parse": ["everyone"]},
    }).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; AppleWebKit) YuejiZoomBot/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    if not PENDING_REMINDERS_PATH.exists():
        return  # 何もない、サイレント終了
    items = json.loads(PENDING_REMINDERS_PATH.read_text(encoding="utf-8"))
    if not items:
        return

    env = load_env()
    now_utc = datetime.now(timezone.utc)
    remaining = []
    fired = 0
    for r in items:
        try:
            # 新形式 fire_at_utc を優先、旧形式 fire_at_jst もサポート
            if "fire_at_utc" in r:
                fire_at = datetime.fromisoformat(r["fire_at_utc"])
            elif "fire_at_jst" in r:
                # 旧形式: naive datetime を JST として解釈
                fire_at = datetime.strptime(r["fire_at_jst"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
            else:
                log(f"❌ 不正なエントリ(時刻フィールドなし)削除: {r}")
                continue
        except Exception as e:
            log(f"❌ 不正なエントリ削除: {e} / {r}")
            continue

        if fire_at > now_utc:
            # まだ時刻が来てない
            remaining.append(r)
            continue

        # 送信実行
        webhook = env.get(r["webhook_env"], "")
        if not webhook:
            log(f"❌ {r['webhook_env']} が .env にない、エントリ残す: {r['topic']}")
            remaining.append(r)
            continue

        try:
            msg = build_reminder_message(r)
            status = post_to_discord(webhook, msg)
            log(f"✅ リマインド送信: {r['topic']} ({r['channel_label']}, HTTP {status})")
            fired += 1
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            log(f"❌ Discord送信失敗 HTTP {e.code}: {r['topic']} / {err_body}")
            remaining.append(r)  # リトライ用に残す
        except Exception as e:
            log(f"❌ Discord送信失敗: {r['topic']} / {e}")
            remaining.append(r)

    PENDING_REMINDERS_PATH.write_text(
        json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if fired:
        log(f"完了: {fired}件送信 / {len(remaining)}件保留")


if __name__ == "__main__":
    main()
