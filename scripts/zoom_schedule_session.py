#!/usr/bin/env python3
"""Zoom会議作成 + Discord告知 + Googleカレンダー登録 の統合ワークフロー

使い方:
    # 今すぐ開始(インスタント)+ Discord告知
    python3 ~/transcribe/_scripts/zoom_schedule_session.py 5ki "Day5 体質チェック"

    # スケジュール会議 + Discord + カレンダー登録
    python3 ~/transcribe/_scripts/zoom_schedule_session.py 5ki "Day5 体質チェック" \\
        --at "2026-07-15 19:00"

    # 自由文を Discord に追記
    python3 ~/transcribe/_scripts/zoom_schedule_session.py 5ki "Day5 ..." \\
        --at "2026-07-15 19:00" \\
        --note "持ち物:お茶ノートとお気に入りのお茶"

    # スキップオプション
    --no-discord    Discord告知をスキップ
    --no-calendar   カレンダー登録をスキップ

挙動:
1. Zoom会議作成(zoom_create_meeting.py 経由)
2. テンプレに webhook 設定あれば Discord告知投稿(@everyone 付き)
3. スケジュール会議なら指定の Googleカレンダーに登録(--no-calendar で無効化)
"""
import os
import sys
import json
import argparse
import subprocess
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))

SCRIPTS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPTS_DIR.parent / "config"
ENV_PATH = SCRIPTS_DIR / ".env"
TEMPLATES_PATH = CONFIG_DIR / "zoom_meeting_templates.json"
PENDING_REMINDERS_PATH = SCRIPTS_DIR / "discord_reminders_pending.json"
def _load_env_value(key, default=""):
    """ENV_PATH から1つのキー値を読む(モジュール初期化用)"""
    if not ENV_PATH.exists():
        return default
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    return default

GOG_ACCOUNT = os.environ.get("GOG_ACCOUNT") or _load_env_value("GOG_ACCOUNT", "")
REMINDER_MINUTES_BEFORE = 5  # 開始の何分前にリマインド送信するか


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


def load_templates():
    with open(TEMPLATES_PATH, encoding="utf-8") as f:
        return json.load(f)


def create_zoom_meeting(template_key, title, at, duration):
    """zoom_create_meeting.py を呼んで JSON 取得"""
    args = ["python3", str(SCRIPTS_DIR / "zoom_create_meeting.py"),
            template_key, title, "--json", "--no-copy"]
    if at:
        args.extend(["--at", at])
    if duration:
        args.extend(["--duration", str(duration)])
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Zoom作成失敗:\n{result.stdout}\n{result.stderr}")
    # 出力から JSON 行を抜き出す(末尾に「📋 URLをクリップボードに...」等あり得る)
    lines = result.stdout.strip().splitlines()
    json_text = ""
    in_json = False
    for line in lines:
        if line.startswith("{"):
            in_json = True
        if in_json:
            json_text += line + "\n"
        if line.startswith("}"):
            in_json = False
    return json.loads(json_text)


def create_discord_event(bot_token, guild_id, name, description, start_dt_jst, duration, location):
    """Discord Scheduled Event 作成。EXTERNAL タイプ(Zoom等の外部URL用)
    Returns: 作成したイベント情報
    """
    end_dt_jst = start_dt_jst + timedelta(minutes=duration)
    start_utc = start_dt_jst.astimezone(timezone.utc)
    end_utc = end_dt_jst.astimezone(timezone.utc)
    body = json.dumps({
        "name": name[:100],  # Discord制限100文字
        "description": description[:1000],
        "scheduled_start_time": start_utc.isoformat().replace("+00:00", "Z"),
        "scheduled_end_time": end_utc.isoformat().replace("+00:00", "Z"),
        "privacy_level": 2,  # GUILD_ONLY
        "entity_type": 3,  # EXTERNAL
        "entity_metadata": {"location": location[:100]},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/guilds/{guild_id}/scheduled-events",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (yuejibot, 1.0)",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def post_to_discord(webhook_url, message):
    """Discord Webhook に投稿(Cloudflareブロック回避でUA明示)"""
    body = json.dumps({
        "content": message,
        "allowed_mentions": {"parse": ["everyone"]},  # @everyone を有効化
    }).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; AppleWebKit) YuejiZoomBot/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def build_discord_message(template_key, title, topic, join_url, meeting_id_formatted,
                          start_time_jst, duration, is_instant, note):
    """事前告知のDiscordメッセージを組み立て(@everyone 必須)"""
    lines = ["@everyone", ""]
    if is_instant:
        lines.append(f"🟢 ただいまから {topic} を開始します")
        lines.append("")
        lines.append("ぜひご参加ください")
    else:
        lines.append(f"📢 {topic} のお知らせ")
        lines.append("")
        # 「2026/07/15 (水) 日本時間19:00 (90分)」形式
        lines.append(f"📅 日時: {start_time_jst} ({duration}分)")

    lines.append("")
    lines.append(f"▼ ご参加はこちらから")
    lines.append(f"{join_url}")
    lines.append(f"ミーティングID: {meeting_id_formatted}")

    if note:
        lines.append("")
        lines.append("▼ ご案内")
        lines.append(note)

    return "\n".join(lines)


def build_reminder_message(topic, join_url, meeting_id_formatted, start_hhmm, note):
    """開始5分前のリマインドメッセージ(@everyone 必須)"""
    lines = [
        "@everyone",
        f"🟢 この後{start_hhmm}から",
        f"{topic} を開始します",
        "",
        "▼ ご参加はこちらから",
        join_url,
        f"ミーティングID: {meeting_id_formatted}",
        "",
        "▼ ご案内",
        "",
        "ぜひご参加ください",
    ]
    if note:
        lines.append("")
        lines.append(note)
    return "\n".join(lines)


def create_calendar_event(env, template_key, topic, join_url, start_dt_jst, duration, description_extra):
    """指定のGoogleカレンダーに予定追加(.envのGCAL_TARGET_CALENDAR)"""
    cal_id = env.get("GCAL_TARGET_CALENDAR", "")
    if not cal_id:
        raise RuntimeError("GCAL_TARGET_CALENDAR が .env にない")

    end_dt = start_dt_jst + timedelta(minutes=duration)
    # gog の RFC3339 形式: 2026-07-15T19:00:00+09:00
    from_str = start_dt_jst.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    to_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S+09:00")

    description_lines = [
        f"テンプレ: {template_key}",
        "",
        f"Zoom URL: {join_url}",
    ]
    if description_extra:
        description_lines.append("")
        description_lines.append(description_extra)
    description = "\n".join(description_lines)

    args = [
        "gog", "-a", GOG_ACCOUNT, "calendar", "create", cal_id,
        "--summary", topic,
        "--from", from_str,
        "--to", to_str,
        "--start-timezone", "Asia/Tokyo",
        "--end-timezone", "Asia/Tokyo",
        "--description", description,
        "--location", join_url,
        "-j",
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"カレンダー登録失敗:\n{result.stderr}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}
    if "result" in data:
        data = data["result"]
    return data


def append_pending_reminder(reminder):
    """discord_reminders_pending.json に追記"""
    if PENDING_REMINDERS_PATH.exists():
        items = json.loads(PENDING_REMINDERS_PATH.read_text(encoding="utf-8"))
    else:
        items = []
    items.append(reminder)
    PENDING_REMINDERS_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def format_jst(iso_str):
    """ISO 8601 → 'YYYY/MM/DD (曜) 日本時間HH:MM' 形式"""
    if not iso_str or iso_str == "now":
        return "今すぐ"
    try:
        if iso_str.endswith("Z"):
            dt_utc = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            dt = dt_utc + timedelta(hours=9)
        else:
            dt = datetime.fromisoformat(iso_str)
    except Exception:
        return iso_str
    yobi = ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]
    return dt.strftime(f"%Y/%m/%d ({yobi}) 日本時間%H:%M")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("template", help="テンプレキー(5ki/dabuhapi/asacha/kobetsu/tsunagari/freeform)")
    parser.add_argument("title", help="ミーティング名(prefixの後ろ)")
    parser.add_argument("--at", help="日時 JST。例 '2026-07-15 19:00'。省略時はインスタント")
    parser.add_argument("--duration", type=int, help="所要時間(分)、テンプレ既定を上書き")
    parser.add_argument("--note", default="", help="Discord告知の補足テキスト")
    parser.add_argument("--no-discord", action="store_true", help="Discord告知をスキップ")
    parser.add_argument("--no-calendar", action="store_true", help="カレンダー登録をスキップ")
    args = parser.parse_args()

    env = load_env()
    templates = load_templates()
    if args.template not in templates["templates"]:
        print(f"❌ 未定義テンプレ: {args.template}")
        sys.exit(1)
    tpl = templates["templates"][args.template]

    # Step 1: Zoom 作成
    print(f"=== Step 1: Zoom会議作成 ===")
    zoom = create_zoom_meeting(args.template, args.title, args.at, args.duration)
    print(f"  ✅ {zoom['topic']}")
    print(f"     URL: {zoom['join_url']}")
    print(f"     ID:  {zoom['meeting_id_formatted']}")

    is_instant = zoom["type"] == "instant"
    duration = zoom["duration"]
    start_time_iso = zoom.get("start_time", "")

    # Step 2: Discord 告知
    print(f"\n=== Step 2: Discord告知 ===")
    discord_webhook_env_key = tpl.get("discord_webhook_env")
    if args.no_discord:
        # スキップでも、本来送る予定だったメッセージは表示してプレビュー
        if discord_webhook_env_key:
            channel_label = tpl.get("discord_channel_label", "(no label)")
            start_time_jst_str = format_jst(start_time_iso)
            preview_msg = build_discord_message(
                args.template, args.title, zoom["topic"],
                zoom["join_url"], zoom["meeting_id_formatted"],
                start_time_jst_str, duration, is_instant, args.note,
            )
            print(f"  ⏭  --no-discord でスキップ")
            print(f"  📋 送る予定だった内容(プレビュー、{channel_label} 宛):")
            print(f"  ─── メッセージ内容 ───")
            for line in preview_msg.splitlines():
                print(f"  {line}")
            print(f"  ──────────────────")
        else:
            print(f"  ⏭  --no-discord でスキップ")
    elif not discord_webhook_env_key:
        print(f"  ⏭  テンプレに告知先なし(個別/朝茶会等)")
    else:
        webhook = env.get(discord_webhook_env_key, "")
        if not webhook:
            print(f"  ❌ {discord_webhook_env_key} が .env にない")
        else:
            start_time_jst_str = format_jst(start_time_iso)
            msg = build_discord_message(
                args.template, args.title, zoom["topic"],
                zoom["join_url"], zoom["meeting_id_formatted"],
                start_time_jst_str, duration, is_instant, args.note,
            )
            try:
                status = post_to_discord(webhook, msg)
                channel_label = tpl.get("discord_channel_label", "(no label)")
                print(f"  ✅ {channel_label} に投稿(HTTP {status})")
                print(f"  ─── メッセージ内容 ───")
                for line in msg.splitlines():
                    print(f"  {line}")
                print(f"  ──────────────────")
            except Exception as e:
                print(f"  ❌ Discord投稿失敗: {e}")

    # Step 2.3: Discord Scheduled Event 作成(スケジュール会議で告知先ありの場合のみ)
    print(f"\n=== Step 2.3: Discord Event 作成 ===")
    guild_id = tpl.get("discord_guild_id")
    bot_token = env.get("DISCORD_BOT_TOKEN", "")
    if args.no_discord:
        print(f"  ⏭  --no-discord でスキップ")
    elif is_instant:
        print(f"  ⏭  インスタント会議のためEvent不要")
    elif not guild_id:
        print(f"  ⏭  テンプレに guild_id なし")
    elif not bot_token:
        print(f"  ⏭  DISCORD_BOT_TOKEN なし")
    else:
        try:
            dt_jst = datetime.strptime(args.at, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
            event_description = f"Zoom URL: {zoom['join_url']}\nミーティングID: {zoom['meeting_id_formatted']}"
            if args.note:
                event_description += f"\n\n▼ ご案内\n{args.note}"
            event = create_discord_event(
                bot_token, guild_id, zoom["topic"], event_description,
                dt_jst, duration, zoom["join_url"],
            )
            print(f"  ✅ Event作成: {event.get('id')}")
            print(f"     名前: {event.get('name')}")
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            print(f"  ❌ Event作成失敗 HTTP {e.code}: {err[:300]}")
        except Exception as e:
            print(f"  ❌ Event作成失敗: {e}")

    # Step 2.5: リマインダー予約(スケジュール会議で告知先ありの場合のみ)
    print(f"\n=== Step 2.5: リマインダー予約 ===")
    if args.no_discord:
        print(f"  ⏭  --no-discord なのでリマインダー予約もスキップ")
    elif is_instant:
        print(f"  ⏭  インスタント会議のためリマインダー不要")
    elif not discord_webhook_env_key:
        print(f"  ⏭  告知先テンプレなし(リマインダーも不要)")
    else:
        try:
            # args.at は JST として明示的に解釈
            dt_jst = datetime.strptime(args.at, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
            fire_at_jst = dt_jst - timedelta(minutes=REMINDER_MINUTES_BEFORE)
            # UTC に変換して保存(tz意識した比較に統一)
            fire_at_utc = fire_at_jst.astimezone(timezone.utc)
            now_utc = datetime.now(timezone.utc)
            if fire_at_utc <= now_utc:
                print(f"  ⚠️  リマインド時刻({fire_at_jst.strftime('%H:%M JST')})が既に過去なのでスキップ")
            else:
                reminder = {
                    "fire_at_utc": fire_at_utc.isoformat(),
                    "fire_at_jst_display": fire_at_jst.strftime("%Y-%m-%d %H:%M JST"),
                    "webhook_env": discord_webhook_env_key,
                    "channel_label": tpl.get("discord_channel_label", ""),
                    "topic": zoom["topic"],
                    "join_url": zoom["join_url"],
                    "meeting_id_formatted": zoom["meeting_id_formatted"],
                    "start_hhmm": dt_jst.strftime("%H:%M"),
                    "note": args.note,
                    "added_at_utc": now_utc.isoformat(),
                }
                append_pending_reminder(reminder)
                print(f"  ✅ {fire_at_jst.strftime('%Y-%m-%d %H:%M JST')} に送信予約")
                print(f"     送信先: {reminder['channel_label']}")
        except Exception as e:
            print(f"  ❌ リマインダー予約失敗: {e}")

    # Step 3: カレンダー登録(スケジュール会議のみ)
    print(f"\n=== Step 3: Googleカレンダー登録 ===")
    if args.no_calendar:
        print(f"  ⏭  --no-calendar でスキップ")
    elif is_instant:
        print(f"  ⏭  インスタント会議のため登録不要")
    else:
        try:
            dt_jst = datetime.strptime(args.at, "%Y-%m-%d %H:%M")
            cal_event = create_calendar_event(
                env, args.template, zoom["topic"], zoom["join_url"],
                dt_jst, duration, args.note,
            )
            event_id = cal_event.get("event", {}).get("id") or cal_event.get("id") or "?"
            html_link = cal_event.get("event", {}).get("htmlLink") or cal_event.get("htmlLink") or ""
            print(f"  ✅ 指定カレンダーに登録: {event_id}")
            if html_link:
                print(f"     {html_link}")
        except Exception as e:
            print(f"  ❌ カレンダー登録失敗: {e}")

    # サマリー
    print(f"\n=== サマリー ===")
    print(f"  Zoom URL:      {zoom['join_url']}")
    print(f"  ミーティングID: {zoom['meeting_id_formatted']}")
    if not is_instant:
        print(f"  開催日時:      {format_jst(start_time_iso)}")


if __name__ == "__main__":
    main()
