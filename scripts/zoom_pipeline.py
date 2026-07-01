#!/usr/bin/env python3
"""Zoom録画フルパイプライン

挙動:
1. 過去N日のZoom録画を取得
2. 各録画について順次:
   - DL (まだなら)
   - 要約生成 (_summary.md がまだなら)
   - Drive アップロード (drive_folder_id 未記録なら)
   - YouTube アップロード (youtube_video_id 未記録、かつ除外パターンに当たらないなら)
   - Obsidian 保存 (obsidian_saved_at 未記録なら、文字起こし/Zoom/ 配下)
   - YouTube URL を Discord へ案内投稿 (youtube_discord_posted_at 未記録なら)
3. すべて冪等。何度実行してもOK。

使い方:
    # 過去3日の録画を全部処理(launchd向け)
    python3 ~/transcribe/_scripts/zoom_pipeline.py

    # 過去7日を処理
    python3 ~/transcribe/_scripts/zoom_pipeline.py --since 7

    # トピック指定
    python3 ~/transcribe/_scripts/zoom_pipeline.py --topic 朝茶会

    # 段階スキップ
    python3 ~/transcribe/_scripts/zoom_pipeline.py --no-youtube --no-drive
    python3 ~/transcribe/_scripts/zoom_pipeline.py --no-discord

    # 何が起こるか確認だけ
    python3 ~/transcribe/_scripts/zoom_pipeline.py --dry-run

YouTube除外パターン(Drive バックアップは残す):
    個別面談 / コーチング / パーソナル / 1on1 / 面談 を含むトピック
"""
import os
import sys
import json
import re
import argparse
import subprocess
import urllib.request
import urllib.parse
import base64
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPTS_DIR.parent / "config"
RECORDINGS_DIR = Path.home() / "transcribe" / "zoom_recordings"
LOG_DIR = Path.home() / "transcribe" / "_logs"
ENV_PATH = SCRIPTS_DIR / ".env"

# YouTube アップを除外するトピックパターン(部分一致、case insensitive)
YOUTUBE_EXCLUDE_PATTERNS = [
    "個別面談", "コーチング", "パーソナル", "1on1", "1-on-1",
    "面談", "個別セッション", "個別相談",
]

# Drive フォルダ
DRIVE_PARENT_FOLDER = ""  # main() 内で env から読む


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


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"zoom_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a") as f:
        f.write(line + "\n")


def get_zoom_token(env):
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
        return json.loads(resp.read())["access_token"]


def list_recordings(token, days_back):
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


def safe_topic_for_dirname(text):
    text = re.sub(r"[^\w぀-ゟ゠-ヿ一-鿿 -]", "", text)
    return text.strip().replace(" ", "_")[:60] or "no_topic"


def get_local_dir(meeting):
    """ミーティングのローカル保存先パスを返す(存在チェックはしない)"""
    topic = meeting.get("topic", "no_topic")
    start_time = meeting.get("start_time", "")
    try:
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        dt_jst = dt + timedelta(hours=9)
        ts = dt_jst.strftime("%Y%m%d_%H%M%S")
    except Exception:
        ts = "unknown"
    return RECORDINGS_DIR / f"{ts}_{safe_topic_for_dirname(topic)}"


def load_meta(local_dir):
    meta_path = local_dir / "_meta.json"
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def save_meta(local_dir, meta):
    meta_path = local_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def is_youtube_excluded(topic):
    """このトピックは YouTube アップから除外?"""
    return any(p.lower() in topic.lower() for p in YOUTUBE_EXCLUDE_PATTERNS)


def run_script(args, dry_run=False):
    """サブプロセスでスクリプト実行。失敗時は例外。"""
    if dry_run:
        log(f"    [DRY-RUN] would run: {' '.join(map(str, args))}")
        return ""
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed (code {result.returncode}):\n  {' '.join(map(str, args))}\n"
            f"  stderr: {result.stderr[:500]}"
        )
    return result.stdout


def process_meeting(meeting, args, env):
    """1つのミーティングについて、全段階を順次処理"""
    topic = meeting.get("topic", "no_topic")
    uuid = meeting.get("uuid", "")
    local_dir = get_local_dir(meeting)
    meta = load_meta(local_dir)

    log(f"")
    log(f"📹 {topic}")
    log(f"   保存先: {local_dir.name}")

    # Step 1: DL
    video_file = local_dir / "shared_screen_with_speaker_view.mp4"
    transcript_txt = local_dir / "audio_transcript.txt"
    if video_file.exists() and transcript_txt.exists():
        log(f"   ✅ DL済み(スキップ)")
    else:
        log(f"   ⬇️  DL中...")
        # トピックの最初の20文字でフィルタ(全角の括弧等を避ける)
        topic_filter = re.sub(r"[（）()【】「」\s].*", "", topic)[:20] or topic[:20]
        run_script([
            "python3", str(SCRIPTS_DIR / "zoom_download_recording.py"),
            "--topic", topic_filter,
            "--days", str(args.since),
        ], dry_run=args.dry_run)
        log(f"   ✅ DL完了")

    # Step 2: 要約生成
    summary_file = local_dir / "_summary.md"
    if args.no_summary:
        log(f"   ⏭  要約スキップ(--no-summary)")
    elif summary_file.exists() and summary_file.stat().st_size > 200:
        log(f"   ✅ 要約済み(スキップ)")
    else:
        log(f"   📝 要約生成中...")
        run_script([
            "python3", str(SCRIPTS_DIR / "zoom_summarize_recording.py"),
            str(local_dir),
        ], dry_run=args.dry_run)
        log(f"   ✅ 要約完了")

    # Step 3: Drive UP
    if args.no_drive:
        log(f"   ⏭  Driveスキップ(--no-drive)")
    elif meta.get("drive_folder_id"):
        log(f"   ✅ Drive済み(スキップ)")
    else:
        log(f"   ⬆️  Drive UP中...")
        out = run_script([
            "python3", str(SCRIPTS_DIR / "zoom_upload_to_drive.py"),
            str(local_dir),
            "--parent", DRIVE_PARENT_FOLDER,
        ], dry_run=args.dry_run)
        if not args.dry_run:
            # 出力から folder ID を抽出 (URL末尾)
            m = re.search(r"https://drive\.google\.com/drive/folders/([A-Za-z0-9_-]+)", out)
            if m:
                meta = load_meta(local_dir)
                meta["drive_folder_id"] = m.group(1)
                save_meta(local_dir, meta)
        log(f"   ✅ Drive完了")

    # Step 4: YouTube UP
    youtube_ready_for_discord = False
    if args.no_youtube:
        log(f"   ⏭  YouTubeスキップ(--no-youtube)")
    elif is_youtube_excluded(topic):
        log(f"   🚫 YouTube除外パターン該当(個別/面談/コーチング系)")
    elif meta.get("youtube_video_id"):
        log(f"   ✅ YouTube済み(スキップ): {meta['youtube_video_id']}")
        youtube_ready_for_discord = True
    else:
        if not video_file.exists() and not args.dry_run:
            log(f"   ⚠️  動画ファイルなし、YouTubeスキップ", "WARN")
        else:
            log(f"   ⬆️  YouTube UP中...")
            out = run_script([
                "python3", str(SCRIPTS_DIR / "zoom_upload_to_youtube.py"),
                str(local_dir),
            ], dry_run=args.dry_run)
            if not args.dry_run:
                meta = load_meta(local_dir)  # スクリプトが追記済み
                vid = meta.get("youtube_video_id", "?")
                log(f"   ✅ YouTube完了: {vid}")
                youtube_ready_for_discord = True

    # Step 4.5: Obsidian保存(要約整形版)
    if args.no_obsidian:
        log(f"   ⏭  Obsidianスキップ(--no-obsidian)")
    else:
        meta = load_meta(local_dir)
        if meta.get("obsidian_saved_at"):
            log(f"   ✅ Obsidian済み(スキップ): {meta['obsidian_saved_at']}")
        elif not (local_dir / "_summary.md").exists():
            log(f"   ⏭  Obsidianスキップ(_summary.mdなし)")
        else:
            log(f"   📓 Obsidian保存中...")
            run_script([
                "python3", str(SCRIPTS_DIR / "zoom_save_to_obsidian.py"),
                str(local_dir),
            ], dry_run=args.dry_run)
            if not args.dry_run:
                meta = load_meta(local_dir)
                log(f"   ✅ Obsidian完了: {meta.get('obsidian_path', '-')}")

    # Step 5: Discord案内投稿
    if args.no_discord:
        log(f"   ⏭  Discord案内スキップ(--no-discord)")
    elif youtube_ready_for_discord:
        meta = load_meta(local_dir)
        if meta.get("youtube_discord_posted_at"):
            log(f"   ✅ Discord案内済み(スキップ): {meta['youtube_discord_posted_at']}")
        else:
            log(f"   📣 Discord案内投稿中...")
            run_script([
                "python3", str(SCRIPTS_DIR / "post_youtube_archive_to_discord.py"),
                str(local_dir),
            ], dry_run=args.dry_run)
            if not args.dry_run:
                meta = load_meta(local_dir)
                log(f"   ✅ Discord案内完了: {meta.get('youtube_discord_posted_at', '-')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=int, default=3, help="過去N日(デフォルト:3)")
    parser.add_argument("--topic", type=str, help="トピックフィルタ(部分一致)")
    parser.add_argument("--no-summary", action="store_true")
    parser.add_argument("--no-drive", action="store_true")
    parser.add_argument("--no-youtube", action="store_true")
    parser.add_argument("--no-discord", action="store_true")
    parser.add_argument("--no-obsidian", action="store_true", help="Obsidian保存をスキップ")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log("=" * 60)
    log("Zoom録画パイプライン 開始")
    log(f"  対象期間: 過去{args.since}日")
    if args.topic:
        log(f"  トピックフィルタ: {args.topic}")
    if args.dry_run:
        log(f"  ★ DRY-RUN モード")
    log("=" * 60)

    env = load_env()

    global DRIVE_PARENT_FOLDER
    DRIVE_PARENT_FOLDER = env.get("DRIVE_PARENT_FOLDER", "")
    if not DRIVE_PARENT_FOLDER and not args.no_drive:
        log("⚠️  .env に DRIVE_PARENT_FOLDER がない → --no-drive をつけて実行 or .env に追記", "WARN")
        sys.exit(1)

    log("Zoom録画一覧取得中...")
    token = get_zoom_token(env)
    meetings = list_recordings(token, args.since)
    log(f"  {len(meetings)}件取得")

    if args.topic:
        meetings = [m for m in meetings if args.topic in m.get("topic", "")]
        log(f"  フィルタ後: {len(meetings)}件")

    if not meetings:
        log("処理対象なし、終了")
        return

    success = 0
    failures = 0
    for m in meetings:
        try:
            process_meeting(m, args, env)
            success += 1
        except Exception as e:
            failures += 1
            log(f"   ❌ エラー: {e}", "ERROR")

    log("")
    log("=" * 60)
    log(f"完了: 成功 {success} / 失敗 {failures}")
    log("=" * 60)

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
