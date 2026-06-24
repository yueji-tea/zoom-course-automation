#!/usr/bin/env python3
"""Zoom会議を作成する CLI

使い方:
    # 5期セッションを今すぐ開始(インスタント会議)
    python3 ~/transcribe/_scripts/zoom_create_meeting.py 5ki "Day5 体質チェック振り返り"

    # 日時指定(JST)
    python3 ~/transcribe/_scripts/zoom_create_meeting.py 5ki "Day5 体質チェック" \\
        --at "2026-07-15 19:00"

    # 所要時間上書き(分)
    python3 ~/transcribe/_scripts/zoom_create_meeting.py kobetsu "ゆきこさん面談" --duration 90

    # 利用可能なテンプレ一覧
    python3 ~/transcribe/_scripts/zoom_create_meeting.py --list

挙動:
- テンプレに従ってZoom API でミーティング作成
- topic は「{prefix} {title}」形式(prefix が Discord 振り分けキーになる)
- URL/ID は標準出力 + pbcopy でクリップボードへ
- あなたのZoomデフォルト設定(待機室ON・参加時ミュート・参加時ビデオOFF・パスコードなし)を反映
"""
import os
import sys
import json
import base64
import argparse
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path.home() / "transcribe" / "_scripts"
ENV_PATH = SCRIPTS_DIR / ".env"
TEMPLATES_PATH = SCRIPTS_DIR / "zoom_meeting_templates.json"


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


def get_access_token(env):
    auth_b64 = base64.b64encode(
        f"{env['ZOOM_CLIENT_ID']}:{env['ZOOM_CLIENT_SECRET']}".encode()
    ).decode()
    data = urllib.parse.urlencode({
        "grant_type": "account_credentials",
        "account_id": env["ZOOM_ACCOUNT_ID"],
    }).encode()
    req = urllib.request.Request(
        "https://zoom.us/oauth/token",
        data=data,
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
    return body["access_token"], body.get("scope", "")


def create_meeting(token, body):
    req = urllib.request.Request(
        "https://api.zoom.us/v2/users/me/meetings",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err}")


def copy_to_clipboard(text):
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except Exception:
        return False


def list_templates(templates):
    print("\n=== 利用可能なテンプレート ===")
    for key, tpl in templates["templates"].items():
        prefix = tpl["topic_prefix"] or "(なし)"
        print(f"  {key:12s}  {prefix:10s} {tpl['duration']:3d}分  {tpl['description']}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("template", nargs="?", help="テンプレキー(5ki/dabuhapi/asacha/kobetsu/tsunagari/freeform)")
    parser.add_argument("title", nargs="?", help="ミーティング名(prefix の後ろ)")
    parser.add_argument("--at", help="日時 JST。例 '2026-07-15 19:00'。省略時はインスタント開始")
    parser.add_argument("--duration", type=int, help="所要時間(分)、テンプレ既定を上書き")
    parser.add_argument("--list", action="store_true", help="テンプレ一覧を表示")
    parser.add_argument("--no-copy", action="store_true", help="クリップボードコピーをスキップ")
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力(スクリプト連携用)")
    args = parser.parse_args()

    templates = load_templates()

    if args.list or not args.template:
        list_templates(templates)
        if not args.template:
            sys.exit(0)

    if args.template not in templates["templates"]:
        print(f"❌ 未定義のテンプレ: {args.template}")
        list_templates(templates)
        sys.exit(1)

    if not args.title:
        print("❌ ミーティング名(title)が必要")
        sys.exit(1)

    tpl = templates["templates"][args.template]
    defaults = templates["default_settings"]

    # topic 組み立て: 「{prefix} {title}」
    prefix = tpl["topic_prefix"]
    topic = f"{prefix} {args.title}".strip() if prefix else args.title

    duration = args.duration or tpl["duration"]

    # body 組み立て
    body = {
        "topic": topic,
        "duration": duration,
        "timezone": tpl["timezone"],
        "settings": {
            "host_video": defaults["host_video"],
            "participant_video": defaults["participant_video"],
            "mute_upon_entry": defaults["mute_upon_entry"],
            "waiting_room": defaults["waiting_room"],
            "join_before_host": defaults["join_before_host"],
            "meeting_authentication": defaults["meeting_authentication"],
            "approval_type": defaults["approval_type"],
            "audio": defaults["audio"],
            "auto_recording": tpl["auto_recording"],
        },
    }

    if args.at:
        # スケジュール会議 (type=2)
        body["type"] = 2
        # JST 解釈 → ISO8601(timezone付きで送ると確実)
        try:
            dt = datetime.strptime(args.at, "%Y-%m-%d %H:%M")
        except ValueError:
            print(f"❌ --at の形式が不正: '{args.at}' (例: '2026-07-15 19:00')")
            sys.exit(1)
        # timezone情報はbodyのtimezoneフィールドで指定するので、start_timeはローカル時刻
        body["start_time"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        # インスタント会議 (type=1)
        body["type"] = 1

    env = load_env()
    token, scope = get_access_token(env)

    # スコープ確認(meeting:write がなかったら早期エラー)
    if "meeting:write" not in scope:
        print(f"❌ Zoomトークンに meeting:write スコープがない")
        print(f"   現在のスコープ: {scope}")
        print(f"   Zoom Marketplace でスコープ追加 → Re-activate してください")
        sys.exit(1)

    try:
        result = create_meeting(token, body)
    except RuntimeError as e:
        print(f"❌ 作成失敗: {e}")
        sys.exit(1)

    join_url = result.get("join_url", "")
    meeting_id = result.get("id", "")
    formatted_id = format_meeting_id(meeting_id)
    start_time = result.get("start_time", "")
    is_instant = body["type"] == 1

    if args.json:
        out = {
            "template": args.template,
            "topic": topic,
            "duration": duration,
            "type": "instant" if is_instant else "scheduled",
            "start_time": start_time or "now",
            "join_url": join_url,
            "meeting_id": meeting_id,
            "meeting_id_formatted": formatted_id,
            "discord_target": tpl.get("discord_target"),
            "host_email": result.get("host_email", ""),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print()
        print(f"✅ Zoom会議作成完了")
        print(f"   テンプレ:    {args.template} ({tpl['description']})")
        print(f"   トピック:    {topic}")
        print(f"   日時:        {'今すぐ開始' if is_instant else start_time + ' JST'}")
        print(f"   所要時間:    {duration}分")
        print(f"   URL:         {join_url}")
        print(f"   ID:          {formatted_id}")
        print(f"   パスコード:  (なし・URLに埋め込み済み)")
        if tpl.get("discord_target"):
            print(f"   Discord告知先: {tpl['discord_target']}")
        print()

    if not args.no_copy and join_url:
        if copy_to_clipboard(join_url):
            print("📋 URLをクリップボードにコピー済み")


def format_meeting_id(mid):
    """123456789012 → 1234 5678 9012"""
    s = str(mid)
    if len(s) == 11:
        return f"{s[0:3]} {s[3:7]} {s[7:11]}"
    if len(s) == 10:
        return f"{s[0:3]} {s[3:6]} {s[6:10]}"
    if len(s) == 12:
        return f"{s[0:4]} {s[4:8]} {s[8:12]}"
    return s


if __name__ == "__main__":
    main()
