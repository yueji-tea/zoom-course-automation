#!/usr/bin/env python3
"""Zoom Server-to-Server OAuth - 録画一覧テスト

使い方:
    python3 ~/transcribe/_scripts/zoom_list_recordings.py [日数]

例:
    python3 ~/transcribe/_scripts/zoom_list_recordings.py 30
    (過去30日分の録画を一覧表示)
"""
import os
import sys
import json
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path


def load_env(env_path):
    env = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV_PATH = Path.home() / "transcribe" / "_scripts" / ".env"
env = load_env(ENV_PATH)

ACCOUNT_ID = env["ZOOM_ACCOUNT_ID"]
CLIENT_ID = env["ZOOM_CLIENT_ID"]
CLIENT_SECRET = env["ZOOM_CLIENT_SECRET"]


def get_access_token():
    """Server-to-Server OAuth でアクセストークンを取得"""
    url = "https://zoom.us/oauth/token"
    data = urllib.parse.urlencode({
        "grant_type": "account_credentials",
        "account_id": ACCOUNT_ID,
    }).encode()

    auth_b64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def list_recordings(token, days_back=30):
    """自分のクラウド録画一覧を取得(最大30件/ページ)"""
    today = datetime.now()
    from_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    url = (
        f"https://api.zoom.us/v2/users/me/recordings"
        f"?from={from_date}&to={to_date}&page_size=30"
    )
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    print("=== Zoom API テスト ===\n")

    print("Step 1: アクセストークン取得中...")
    try:
        token_data = get_access_token()
        token = token_data["access_token"]
        print(f"  ✅ トークン取得成功")
        print(f"     有効期限: {token_data.get('expires_in')}秒")
        scope = token_data.get("scope", "")
        print(f"     スコープ: {scope}\n")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ❌ トークン取得失敗: HTTP {e.code}")
        print(f"     {body}")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ トークン取得失敗: {e}")
        sys.exit(1)

    print(f"Step 2: 過去{days}日の録画一覧取得中...")
    try:
        result = list_recordings(token, days_back=days)
        meetings = result.get("meetings", [])
        print(f"  ✅ {len(meetings)}件のミーティング録画あり\n")

        for m in meetings:
            topic = m.get("topic", "(no topic)")
            start = m.get("start_time", "")
            files = m.get("recording_files", [])
            duration = m.get("duration", 0)

            print(f"  📹 {topic}")
            print(f"     開催: {start}  ({duration}分)")
            print(f"     録画ファイル: {len(files)}個")
            for f in files:
                size_mb = f.get("file_size", 0) / 1024 / 1024
                ftype = f.get("file_type", "?")
                rtype = f.get("recording_type", "?")
                print(f"       - {rtype} [{ftype}] {size_mb:.1f}MB")
            print()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ❌ 録画取得失敗: HTTP {e.code}")
        print(f"     {body}")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ 録画取得失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
