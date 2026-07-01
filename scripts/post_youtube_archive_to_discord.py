#!/usr/bin/env python3
"""YouTube限定公開アーカイブURLをDiscordへ案内投稿する。

使い方:
    python3 ~/transcribe/_scripts/post_youtube_archive_to_discord.py <録画ディレクトリ>

前提:
- <録画ディレクトリ>/_meta.json に youtube_url または youtube_video_id がある
- .env に投稿先Webhookを設定
- youtube_archive_discord_routes.json のルールで投稿先を振り分け

冪等性:
- _meta.json の youtube_discord_posts に投稿先別の投稿時刻を記録
- --force を付けると再投稿
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPTS_DIR.parent / "config"
ENV_PATH = SCRIPTS_DIR / ".env"
DISCORD_POST = SCRIPTS_DIR / "discord_post.sh"
ROUTES_PATH = CONFIG_DIR / "youtube_archive_discord_routes.json"


def load_env():
    env = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_meta(target_dir):
    meta_path = target_dir / "_meta.json"
    if not meta_path.exists():
        raise SystemExit(f"❌ _meta.json が見つかりません: {meta_path}")
    return meta_path, json.loads(meta_path.read_text(encoding="utf-8"))


def build_video_url(meta):
    if meta.get("youtube_url"):
        return meta["youtube_url"]
    if meta.get("youtube_video_id"):
        return f"https://www.youtube.com/watch?v={meta['youtube_video_id']}"
    raise SystemExit("❌ _meta.json に youtube_url / youtube_video_id がありません")


def load_routes(path=ROUTES_PATH):
    if not path.exists():
        return {"routes": [], "fallback_webhook_env": "DISCORD_WEBHOOK_YOUTUBE_ARCHIVE", "unmatched_policy": "fallback"}
    return json.loads(path.read_text(encoding="utf-8"))


def match_routes(target_dir, meta, routes_config):
    haystack = "\n".join(
        str(x)
        for x in [
            target_dir.name,
            meta.get("topic", ""),
            meta.get("title", ""),
            meta.get("zoom_topic", ""),
            meta.get("meeting_topic", ""),
        ]
        if x
    )
    matches = []
    for route in routes_config.get("routes", []):
        for pattern in route.get("patterns", []):
            if re.search(pattern, haystack, flags=re.IGNORECASE):
                matches.append((route, pattern))
                break
    return matches, haystack


def resolve_webhooks(env, target_dir, meta, route_name=None):
    routes_config = load_routes()
    if route_name:
        for route in routes_config.get("routes", []):
            if route.get("name") == route_name:
                webhook_env = route.get("webhook_env", "")
                return [(route, f"--route {route_name}", webhook_env, env.get(webhook_env, "").strip())]
        raise SystemExit(f"❌ 指定ルートが見つかりません: {route_name}")

    matches, haystack = match_routes(target_dir, meta, routes_config)
    if matches:
        resolved = []
        for route, matched_pattern in matches:
            webhook_env = route.get("webhook_env", "")
            resolved.append((route, matched_pattern, webhook_env, env.get(webhook_env, "").strip()))
        return resolved

    fallback_env = routes_config.get("fallback_webhook_env") or "DISCORD_WEBHOOK_YOUTUBE_ARCHIVE"
    if routes_config.get("unmatched_policy") == "fallback":
        return [({"name": "fallback"}, "fallback", fallback_env, env.get(fallback_env, "").strip())]

    raise SystemExit(
        "❌ 投稿先を自動判定できませんでした。\n"
        "youtube_archive_discord_routes.json に判定語を追加するか、--route で投稿先を指定してください。\n"
        f"判定対象:\n{haystack}"
    )


def read_summary_excerpt(target_dir, max_chars=360):
    summary_path = target_dir / "_summary.md"
    if not summary_path.exists():
        return ""
    text = summary_path.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    # 見出し記号がそのままDiscordに出ても読めるよう、軽く整える。
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        line = line.lstrip("-・ ")
        if line:
            lines.append(line)
        if sum(len(x) for x in lines) >= max_chars:
            break
    excerpt = "\n".join(lines).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rstrip() + "…"
    return excerpt


def build_message(target_dir, meta, video_url):
    title = meta.get("topic") or meta.get("title") or target_dir.name
    duration = meta.get("duration_min")
    duration_line = f"\n録画時間: 約{duration}分" if duration else ""
    excerpt = read_summary_excerpt(target_dir)
    excerpt_block = f"\n\n内容メモ:\n{excerpt}" if excerpt else ""

    return (
        "アーカイブ動画をアップしました。\n\n"
        f"タイトル: {title}{duration_line}\n"
        f"視聴URL:\n{video_url}"
        f"{excerpt_block}\n\n"
        "必要な方はこちらからご覧ください。"
    )


def post_to_discord(webhook, message, dry_run=False):
    if dry_run:
        print("=== DRY RUN: Discord投稿本文 ===")
        print(message)
        return
    # ★ Webhook URL は環境変数経由(argv 経由の ps 漏洩を防止)
    env = os.environ.copy()
    env["DISCORD_USERNAME"] = env.get("DISCORD_USERNAME", "ArchiveBot")
    env["DISCORD_WEBHOOK"] = webhook  # ← argv ではなく env に置く
    result = subprocess.run(
        [str(DISCORD_POST), message],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise SystemExit(
            "❌ Discord投稿に失敗しました\n"
            f"stdout: {result.stdout[:800]}\n"
            f"stderr: {result.stderr[:800]}"
        )


def posted_routes(meta):
    posts = meta.get("youtube_discord_posts")
    if isinstance(posts, dict):
        return posts
    legacy_route = meta.get("youtube_discord_route")
    legacy_at = meta.get("youtube_discord_posted_at")
    if legacy_route and legacy_at:
        return {legacy_route: {"posted_at": legacy_at, "webhook_env": meta.get("youtube_discord_webhook", "")}}
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recording_dir")
    parser.add_argument("--route", help="投稿先ルート名を手動指定。routes JSON で定義した name")
    parser.add_argument("--force", action="store_true", help="投稿済みでも再投稿する")
    parser.add_argument("--dry-run", action="store_true", help="投稿せず本文だけ表示")
    args = parser.parse_args()

    target_dir = Path(args.recording_dir).expanduser().resolve()
    if not target_dir.is_dir():
        raise SystemExit(f"❌ ディレクトリが見つかりません: {target_dir}")

    env = load_env()
    meta_path, meta = load_meta(target_dir)
    resolved_routes = resolve_webhooks(env, target_dir, meta, args.route)
    posts = posted_routes(meta)

    video_url = build_video_url(meta)
    message = build_message(target_dir, meta, video_url)
    posted_any = False

    for route, matched_pattern, webhook_env, webhook in resolved_routes:
        route_name = route.get("name", "-")
        if route_name in posts and not args.force:
            print(f"✅ Discord投稿済み(スキップ): {route_name} / {posts[route_name].get('posted_at')}")
            continue
        if not webhook:
            if args.dry_run:
                webhook = "dry-run"
            else:
                raise SystemExit(f"❌ .env に {webhook_env} が未設定です")

        print(f"投稿先ルート: {route_name}")
        print(f"判定: {matched_pattern}")
        print(f"Webhook環境変数: {webhook_env}")
        post_to_discord(webhook, message, dry_run=args.dry_run)
        posted_any = True

        if not args.dry_run:
            posts[route_name] = {
                "posted_at": datetime.now().isoformat(timespec="seconds"),
                "webhook_env": webhook_env,
                "matched_pattern": matched_pattern,
            }

    if not args.dry_run:
        meta["youtube_discord_posts"] = posts
        if posted_any:
            meta["youtube_discord_posted_at"] = datetime.now().isoformat(timespec="seconds")
            meta["youtube_discord_routes"] = list(posts.keys())
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        if posted_any:
            print("✅ Discord投稿完了")


if __name__ == "__main__":
    main()
