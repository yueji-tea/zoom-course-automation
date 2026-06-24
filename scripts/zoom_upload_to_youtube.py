#!/usr/bin/env python3
"""Zoom録画ディレクトリの動画をYouTubeに限定公開でアップロード

使い方:
    python3 ~/transcribe/_scripts/zoom_upload_to_youtube.py <録画ディレクトリ>

    # オプション
    --public     公開設定を「公開」に(デフォルト:限定公開 unlisted)
    --private    公開設定を「非公開」に
    --video <ファイル名>  どのMP4を上げるか指定(デフォルト:speaker_view)

例:
    python3 ~/transcribe/_scripts/zoom_upload_to_youtube.py \\
        ~/transcribe/zoom_recordings/20260622_061515_月曜朝茶会_日本時間615-645

挙動:
- speaker_view の MP4 をアップロード(デフォルト)
- タイトル:「{元のZoomトピック} ({YYYY/MM/DD})」
- 説明:_summary.md の中身
- 限定公開(URL知ってる人だけ視聴可能)
- 結果として動画URLとIDを返す
- _meta.json に youtube_video_id を追記
"""
import os
import sys
import json
import re
import argparse
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ENV_PATH = Path.home() / "transcribe" / "_scripts" / ".env"

# YouTubeカテゴリ ID 22 = People & Blogs
DEFAULT_CATEGORY = "22"
# DEFAULT_TAGS は .env の YOUTUBE_DEFAULT_TAGS (カンマ区切り) から読む
DEFAULT_TAGS = [t.strip() for t in os.environ.get("YOUTUBE_DEFAULT_TAGS", "").split(",") if t.strip()] or ["講座", "アーカイブ"]


def load_env(env_path):
    env = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_access_token(env):
    """refresh_token を使って access_token を取得"""
    body = urllib.parse.urlencode({
        "client_id": env["YOUTUBE_CLIENT_ID"],
        "client_secret": env["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": env["YOUTUBE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def parse_dirname_for_meta(dirname):
    """ディレクトリ名から日付とトピックを抽出
    例: 20260622_061515_月曜朝茶会_日本時間615-645
    返り値: (datetime, topic_str)
    """
    m = re.match(r"^(\d{8})_(\d{6})_(.+)$", dirname)
    if not m:
        return None, dirname
    ymd, hms, topic = m.groups()
    try:
        dt = datetime.strptime(ymd + hms, "%Y%m%d%H%M%S")
    except ValueError:
        dt = None
    topic = topic.replace("_", " ")
    return dt, topic


def build_title(target_dir, video_meta):
    """タイトル生成: 「{トピック} (YYYY/MM/DD)」"""
    dt, topic = parse_dirname_for_meta(target_dir.name)
    # _meta.json があればトピックはそっち優先
    if video_meta.get("topic"):
        topic = video_meta["topic"]
    date_str = dt.strftime("%Y/%m/%d") if dt else ""
    if date_str:
        return f"{topic} ({date_str})"
    return topic


def build_description(target_dir, video_meta):
    """説明文生成: _summary.md の中身 + 元情報"""
    summary_path = target_dir / "_summary.md"
    if summary_path.exists():
        body = summary_path.read_text(encoding="utf-8").strip()
    else:
        body = "(要約なし)"

    dt, _ = parse_dirname_for_meta(target_dir.name)
    footer = "\n\n---\n"
    if dt:
        footer += f"開催日: {dt.strftime('%Y年%m月%d日 %H:%M')} (JST)\n"
    duration = video_meta.get("duration_min")
    if duration:
        footer += f"録画時間: {duration}分\n"

    return body + footer


def extract_tags_from_summary(summary_text):
    """要約のキーワード行からタグを抽出"""
    m = re.search(r"##\s*キーワード\s*\n([^\n#]+)", summary_text)
    if not m:
        return DEFAULT_TAGS
    tag_line = m.group(1).strip()
    tags = re.split(r"[、,\s]+", tag_line)
    tags = [t.strip() for t in tags if t.strip() and len(t.strip()) <= 30]
    # YouTube は全タグ計500字以内に
    final = list(DEFAULT_TAGS)
    total = sum(len(t) for t in final)
    for t in tags:
        if t in final:
            continue
        if total + len(t) > 480:
            break
        final.append(t)
        total += len(t)
    return final


def resumable_upload(access_token, video_path, metadata):
    """YouTube Resumable Upload(2段階)"""
    file_size = video_path.stat().st_size

    # Phase 1: メタデータPOSTでアップロードURL取得
    body = json.dumps(metadata).encode("utf-8")
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/mp4",
        },
    )
    with urllib.request.urlopen(req) as resp:
        upload_url = resp.headers["Location"]

    print(f"  ✅ アップロードURL取得")

    # Phase 2: 実ファイルをPUTで送信
    print(f"  ⬆️  動画アップ中({file_size / 1024 / 1024:.1f}MB)...")
    with open(video_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(
        upload_url,
        data=data,
        method="PUT",
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(file_size),
        },
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recording_dir")
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--video", default="shared_screen_with_speaker_view.mp4",
                        help="アップロードするMP4ファイル名")
    args = parser.parse_args()

    target = Path(args.recording_dir).expanduser().resolve()
    if not target.is_dir():
        print(f"❌ ディレクトリが見つからない: {target}")
        sys.exit(1)

    video_path = target / args.video
    if not video_path.exists():
        print(f"❌ 動画が見つからない: {video_path}")
        sys.exit(1)

    # メタ情報読み込み
    meta_path = target / "_meta.json"
    video_meta = {}
    if meta_path.exists():
        video_meta = json.loads(meta_path.read_text(encoding="utf-8"))

    env = load_env(ENV_PATH)
    for key in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
        if not env.get(key, "").strip():
            print(f"❌ .env に {key} が無い。先に youtube_oauth_setup.py を実行")
            sys.exit(1)

    # プライバシー設定
    if args.public:
        privacy = "public"
    elif args.private:
        privacy = "private"
    else:
        privacy = "unlisted"

    title = build_title(target, video_meta)
    description = build_description(target, video_meta)
    summary_text = (target / "_summary.md").read_text(encoding="utf-8") if (target / "_summary.md").exists() else ""
    tags = extract_tags_from_summary(summary_text)

    print("=== YouTube アップロード ===")
    print(f"📂 動画: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f}MB)")
    print(f"🎬 タイトル: {title}")
    print(f"🔒 公開設定: {privacy}")
    print(f"🏷  タグ: {', '.join(tags)}")
    print(f"📝 説明文: {len(description)}文字")
    print()

    # アクセストークン取得
    print("Step 1: アクセストークン取得中...")
    access_token = get_access_token(env)
    print(f"  ✅ 取得成功\n")

    # アップロード
    metadata = {
        "snippet": {
            "title": title[:100],  # YouTube制限100文字
            "description": description[:5000],  # YouTube制限5000文字
            "tags": tags,
            "categoryId": DEFAULT_CATEGORY,
            "defaultLanguage": "ja",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"Step 2: アップロード実行")
    try:
        result = resumable_upload(access_token, video_path, metadata)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ HTTP {e.code}: {body}")
        sys.exit(1)

    video_id = result["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    print(f"\n✅ アップロード完了")
    print(f"   動画ID: {video_id}")
    print(f"   URL:    {video_url}")

    # _meta.json に追記
    video_meta["youtube_video_id"] = video_id
    video_meta["youtube_url"] = video_url
    video_meta["youtube_privacy"] = privacy
    meta_path.write_text(json.dumps(video_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   メタ情報を {meta_path.name} に追記")


if __name__ == "__main__":
    main()
