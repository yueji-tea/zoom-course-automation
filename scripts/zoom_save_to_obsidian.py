#!/usr/bin/env python3
"""Zoom録画の要約整形版をObsidianに保存

使い方:
    python3 ~/transcribe/_scripts/zoom_save_to_obsidian.py <録画ディレクトリ>

挙動:
- <録画ディレクトリ>/_summary.md を読む
- <録画ディレクトリ>/_meta.json から動画情報取得
- 保存先: 文字起こし/Zoom/YYYYMMDD_HHMMSS_<topic>.md
- frontmatter + 要約 + 動画リンク3点 (Zoom / Drive / YouTube)
- _meta.json に obsidian_saved_at と obsidian_path を追記

CLAUDE.mdルール:
- 文字起こし全文は保存しない(ユーザー設定可)
- Markdown太字 ** は本文に使わない
"""
import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path

def load_env(env_path=ENV_PATH):
    env = {}
    if not env_path.exists():
        return env
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_ENV_CACHE = load_env()


def _env_or_dotenv(key, default=""):
    """os.environ を優先、なければ .env から読む"""
    v = os.environ.get(key)
    if v:
        return v
    return _ENV_CACHE.get(key, default)


OBSIDIAN_VAULT = Path(_env_or_dotenv("OBSIDIAN_VAULT_PATH")).expanduser() if _env_or_dotenv("OBSIDIAN_VAULT_PATH") else None
OBSIDIAN_ZOOM_DIR = None  # main内で OBSIDIAN_VAULT 確認後に設定


def load_meta(local_dir):
    p = local_dir / "_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_meta(local_dir, meta):
    p = local_dir / "_meta.json"
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_dirname(name):
    """YYYYMMDD_HHMMSS_<topic> → (date_str, time_str, topic)"""
    m = re.match(r"^(\d{8})_(\d{6})_(.+)$", name)
    if not m:
        return None, None, name
    return m.group(1), m.group(2), m.group(3)


def build_obsidian_filename(local_dir_name, topic_clean):
    """Obsidian保存用ファイル名: YYYYMMDD_HHMMSS_<topic_clean>.md"""
    date_str, time_str, _ = parse_dirname(local_dir_name)
    if not date_str:
        return f"{local_dir_name}.md"
    # Obsidian filename 用の sanitize(/ や : を避ける)
    safe = re.sub(r'[/\\:*?"<>|]', "_", topic_clean)[:80]
    return f"{date_str}_{time_str}_{safe}.md"


def build_obsidian_body(local_dir, meta, summary_md):
    """Obsidian保存用の本文を組み立て"""
    topic = meta.get("topic", "Zoom録画")
    date_str, time_str, _ = parse_dirname(local_dir.name)
    duration = meta.get("duration_min", "")

    # 開催日時(JST 表記)
    started_at = ""
    if date_str and time_str:
        try:
            dt = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
            started_at = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass

    # 動画関連リンク
    zoom_id = str(meta.get("uuid", ""))
    drive_id = meta.get("drive_folder_id", "")
    yt_url = meta.get("youtube_url", "")
    drive_url = f"https://drive.google.com/drive/folders/{drive_id}" if drive_id else ""

    # frontmatter
    front = ["---"]
    front.append(f"created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if started_at:
        front.append(f"date: {started_at}")
    front.append(f"topic: {topic}")
    if duration:
        front.append(f"duration_min: {duration}")
    front.append("source: Zoom録画")
    front.append("refined: true")
    front.append("tags:")
    front.append("  - zoom")
    front.append("  - 整形済み")
    if yt_url:
        front.append(f"youtube_url: {yt_url}")
    if drive_url:
        front.append(f"drive_folder_url: {drive_url}")
    front.append("---")

    # 本文
    body = []
    body.append(f"# {topic}")
    body.append("")
    if started_at:
        body.append(f"開催: {started_at} JST" + (f" ({duration}分)" if duration else ""))
        body.append("")
    body.append(summary_md.strip())
    body.append("")
    body.append("---")
    body.append("")
    body.append("## 動画リンク")
    body.append("")
    if yt_url:
        body.append(f"- YouTube(限定公開): {yt_url}")
    if drive_url:
        body.append(f"- Google Drive バックアップ: {drive_url}")
    body.append(f"- ローカル録画ディレクトリ: `{local_dir}`")
    body.append("")

    return "\n".join(front) + "\n\n" + "\n".join(body) + "\n"


def main():
    if OBSIDIAN_VAULT is None:
        print("❌ OBSIDIAN_VAULT_PATH が .env にない。Obsidian Vault のフルパスを設定してください")
        print("   例: OBSIDIAN_VAULT_PATH=$HOME/Documents/MyObsidianVault")
        sys.exit(1)
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    local_dir = Path(sys.argv[1]).expanduser().resolve()
    if not local_dir.is_dir():
        print(f"❌ ディレクトリが見つからない: {local_dir}")
        sys.exit(1)

    summary_path = local_dir / "_summary.md"
    if not summary_path.exists():
        print(f"❌ _summary.md がない、先に要約生成してください: {summary_path}")
        sys.exit(1)

    summary_md = summary_path.read_text(encoding="utf-8")
    meta = load_meta(local_dir)
    topic = meta.get("topic", local_dir.name)

    # 保存先決定
    global OBSIDIAN_ZOOM_DIR
    OBSIDIAN_ZOOM_DIR = OBSIDIAN_VAULT / _env_or_dotenv("OBSIDIAN_ZOOM_SUBDIR", "Transcripts/Zoom")
    OBSIDIAN_ZOOM_DIR.mkdir(parents=True, exist_ok=True)
    out_filename = build_obsidian_filename(local_dir.name, topic)
    out_path = OBSIDIAN_ZOOM_DIR / out_filename

    # 本文組み立て
    body = build_obsidian_body(local_dir, meta, summary_md)
    out_path.write_text(body, encoding="utf-8")

    print(f"✅ Obsidian保存完了")
    print(f"   {out_path}")

    # _meta.json に記録
    meta["obsidian_saved_at"] = datetime.now().isoformat()
    meta["obsidian_path"] = str(out_path)
    save_meta(local_dir, meta)
    print(f"   _meta.json に obsidian_saved_at 追記")


if __name__ == "__main__":
    main()
