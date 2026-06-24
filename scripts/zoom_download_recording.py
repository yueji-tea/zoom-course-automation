#!/usr/bin/env python3
"""Zoom録画ダウンロードテスト

使い方:
    # 最新の録画を1件DL
    python3 ~/transcribe/_scripts/zoom_download_recording.py --latest

    # トピックに含まれる文字列でフィルタしてDL
    python3 ~/transcribe/_scripts/zoom_download_recording.py --topic "朝茶会"

    # 全部リストアップして選ばせる(対話)
    python3 ~/transcribe/_scripts/zoom_download_recording.py --pick

保存先:
    ~/transcribe/zoom_recordings/YYYYMMDD_HHMMSS_<safe_topic>/
"""
import os
import sys
import re
import json
import base64
import argparse
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

OUTPUT_DIR = Path.home() / "transcribe" / "zoom_recordings"

# DL対象のファイル種別
VIDEO_FILE_TYPES = {"MP4", "M4A"}
TRANSCRIPT_FILE_TYPES = {"TRANSCRIPT", "CC"}  # VTT形式の文字起こし
CHAT_FILE_TYPES = {"CHAT"}  # チャットログ


def get_access_token():
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
        return json.loads(resp.read())["access_token"]


def list_recordings(token, days_back=30):
    today = datetime.now()
    from_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    url = (
        f"https://api.zoom.us/v2/users/me/recordings"
        f"?from={from_date}&to={to_date}&page_size=30"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read()).get("meetings", [])


def vtt_to_plain_text(vtt_path, txt_path):
    """ZoomのVTT(WebVTT)字幕ファイルをタイムスタンプ削除したプレーンテキストに変換"""
    lines_out = []
    last_text = None
    with open(vtt_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue
            if line.startswith("WEBVTT"):
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            # 連続する同じ字幕は1行にまとめる(Zoomは重複出力することがある)
            if line == last_text:
                continue
            lines_out.append(line)
            last_text = line
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")


def safe_topic(text):
    text = re.sub(r"[^\w぀-ゟ゠-ヿ一-鿿 -]", "", text)
    return text.strip().replace(" ", "_")[:60] or "no_topic"


def download_file(url, token, dest, expected_size=0):
    is_tty = sys.stdout.isatty()
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        downloaded = 0
        chunk = 1024 * 256
        next_milestone = 10  # 非TTYでは10%刻みで報告
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            f.write(buf)
            downloaded += len(buf)
            if expected_size:
                pct = downloaded / expected_size * 100
                mb = downloaded / 1024 / 1024
                total_mb = expected_size / 1024 / 1024
                if is_tty:
                    sys.stdout.write(f"\r    {pct:5.1f}%  {mb:.1f}/{total_mb:.1f}MB")
                    sys.stdout.flush()
                elif pct >= next_milestone:
                    print(f"    {pct:5.1f}%  {mb:.1f}/{total_mb:.1f}MB")
                    next_milestone += 10
    if expected_size and is_tty:
        sys.stdout.write("\n")


def download_meeting(meeting, token):
    topic = meeting.get("topic", "no_topic")
    start_time = meeting.get("start_time", "")
    files = meeting.get("recording_files", [])

    # JST 変換 (Zoomは UTC で返してくる)
    try:
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        dt_jst = dt + timedelta(hours=9)
        ts = dt_jst.strftime("%Y%m%d_%H%M%S")
    except Exception:
        ts = "unknown"

    dirname = f"{ts}_{safe_topic(topic)}"
    target_dir = OUTPUT_DIR / dirname
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📂 保存先: {target_dir}")
    print(f"📹 {topic}")
    print(f"   開催(JST): {ts}")

    metadata = {
        "topic": topic,
        "uuid": meeting.get("uuid"),
        "start_time_utc": start_time,
        "duration_min": meeting.get("duration"),
        "files": [],
    }

    for f in files:
        ftype = f.get("file_type")
        rtype = f.get("recording_type", "unknown")

        # 種別ごとに拡張子と取得判定
        if ftype in VIDEO_FILE_TYPES:
            ext = ftype.lower()
        elif ftype in TRANSCRIPT_FILE_TYPES:
            ext = "vtt"
        elif ftype in CHAT_FILE_TYPES:
            ext = "txt"
        else:
            print(f"   ⏭  スキップ: {rtype} [{ftype}]")
            continue

        fname = f"{rtype}.{ext}"
        dest = target_dir / fname
        size = f.get("file_size", 0)
        size_mb = size / 1024 / 1024

        if dest.exists() and dest.stat().st_size == size:
            print(f"   ✅ 既存(スキップ): {fname} ({size_mb:.1f}MB)")
            metadata["files"].append({"name": fname, "size": size, "skipped": True})
            continue

        print(f"   ⬇️  DL中: {fname} ({size_mb:.2f}MB)")
        download_file(f["download_url"], token, dest, size)
        metadata["files"].append({"name": fname, "size": size})

        # 文字起こしVTTをプレーンテキストにも変換
        if ftype in TRANSCRIPT_FILE_TYPES:
            txt_dest = target_dir / f"{rtype}.txt"
            try:
                vtt_to_plain_text(dest, txt_dest)
                print(f"   📝 プレーンテキスト化: {txt_dest.name}")
            except Exception as e:
                print(f"   ⚠️  VTT変換失敗: {e}")

    with open(target_dir / "_meta.json", "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return target_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest", action="store_true", help="最新1件をDL")
    parser.add_argument("--topic", type=str, help="トピックに含まれる文字列でフィルタ")
    parser.add_argument("--pick", action="store_true", help="対話的に選択")
    parser.add_argument("--days", type=int, default=30, help="検索期間(日)")
    args = parser.parse_args()

    if not (args.latest or args.topic or args.pick):
        parser.print_help()
        sys.exit(1)

    print("Step 1: 認証中...")
    token = get_access_token()
    print("  ✅ 認証成功\n")

    print(f"Step 2: 過去{args.days}日の録画取得中...")
    meetings = list_recordings(token, days_back=args.days)
    print(f"  ✅ {len(meetings)}件\n")

    if args.latest:
        targets = meetings[:1]
    elif args.topic:
        targets = [m for m in meetings if args.topic in m.get("topic", "")]
        print(f"  → トピックフィルタ「{args.topic}」で {len(targets)}件マッチ")
    elif args.pick:
        for i, m in enumerate(meetings):
            files = m.get("recording_files", [])
            total_mb = sum(
                f.get("file_size", 0) for f in files if f.get("file_type") in VIDEO_FILE_TYPES
            ) / 1024 / 1024
            print(f"  [{i}] {m.get('start_time')}  {m.get('topic')} ({total_mb:.1f}MB)")
        choice = input("\n番号を入力(複数はカンマ区切り、空Enterでキャンセル): ").strip()
        if not choice:
            print("キャンセル")
            sys.exit(0)
        idxs = [int(x) for x in choice.split(",")]
        targets = [meetings[i] for i in idxs]

    if not targets:
        print("⚠️  マッチする録画がありません")
        sys.exit(1)

    for m in targets:
        download_meeting(m, token)

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
