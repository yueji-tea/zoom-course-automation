#!/usr/bin/env python3
"""Zoom録画ディレクトリを Google Drive にアップロード

使い方:
    # ルート直下に新規フォルダ作って上げる
    python3 ~/transcribe/_scripts/zoom_upload_to_drive.py <録画ディレクトリ>

    # 親フォルダIDを指定して上げる
    python3 ~/transcribe/_scripts/zoom_upload_to_drive.py <録画ディレクトリ> --parent <ID>

例:
    python3 ~/transcribe/_scripts/zoom_upload_to_drive.py \\
        ~/transcribe/zoom_recordings/20260622_061515_月曜朝茶会_日本時間615-645 \\
        --parent 1aAv_xxxxxx

挙動:
- ローカル名 YYYYMMDD_HHMMSS_<topic> → Drive名 YYYYMMDD_<topic> に変換
- ★ 親フォルダ内に同名のDriveフォルダがあれば再利用(重複作成しない)
- ★ 同名ファイルが既にあって、サイズも同じならスキップ
- ★ 同名ファイルがあって、サイズが違えば古いのを削除して新規アップ
- 動画(MP4)・字幕(VTT/TXT)・要約(MD)・メタ情報(JSON)を全部アップ
- 失敗時は2回までリトライ
"""
import os
import re
import sys
import json
import argparse
import subprocess
from pathlib import Path

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

# 拡張子 → MIME タイプ
MIME_MAP = {
    ".mp4": "video/mp4",
    ".m4a": "audio/mp4",
    ".vtt": "text/vtt",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
}


def gog_run(args, capture=True):
    """gog コマンドを実行"""
    cmd = ["gog", "-a", GOG_ACCOUNT] + args
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gog failed:\n  cmd: {' '.join(cmd)}\n  stderr: {result.stderr}")
    return result.stdout.strip()


def _extract_id(data):
    """gog のレスポンスから id を取り出す(複数の構造に対応)"""
    if "result" in data:
        data = data["result"]
    for key in ("folder", "file", "upload"):
        if key in data and isinstance(data[key], dict) and "id" in data[key]:
            return data[key]["id"]
    return data.get("id")


def list_children(parent_id, mime_type_filter=None):
    """親フォルダ内のファイル/フォルダ一覧を取得
    Returns: [{"id": ..., "name": ..., "size": ..., "mimeType": ...}, ...]
    """
    args = ["drive", "ls", "--parent", parent_id, "-j"]
    try:
        out = gog_run(args)
    except RuntimeError:
        return []
    data = json.loads(out)
    if "result" in data:
        data = data["result"]
    files = data.get("files", [])
    if mime_type_filter:
        files = [f for f in files if f.get("mimeType") == mime_type_filter]
    return files


def find_folder(name, parent_id):
    """親フォルダ内の同名フォルダを探す。なければNone"""
    folders = list_children(parent_id, mime_type_filter="application/vnd.google-apps.folder")
    for f in folders:
        if f.get("name") == name:
            return f.get("id")
    return None


def find_file(name, parent_id):
    """親フォルダ内の同名ファイルを探す(フォルダ除外)。なければNone
    Returns: {"id": ..., "size": int} or None"""
    children = list_children(parent_id)
    for f in children:
        if f.get("name") == name and f.get("mimeType") != "application/vnd.google-apps.folder":
            size = f.get("size")
            if isinstance(size, str):
                size = int(size) if size.isdigit() else 0
            return {"id": f.get("id"), "size": size or 0}
    return None


def delete_file(file_id):
    """Driveのファイル/フォルダをゴミ箱へ"""
    gog_run(["drive", "delete", file_id, "-y"])


def mkdir(name, parent_id=None):
    """Driveフォルダ作成。既に同名フォルダがあれば再利用。フォルダIDを返す"""
    # 既存チェック(parent_id がある場合のみ。ルートでは検索ロジック未対応)
    if parent_id:
        existing = find_folder(name, parent_id)
        if existing:
            return existing  # 既存を再利用
    args = ["drive", "mkdir", name, "-j"]
    if parent_id:
        args.extend(["--parent", parent_id])
    out = gog_run(args)
    return _extract_id(json.loads(out))


def upload(local_path, parent_id, mime_type=None, max_retries=2):
    """ファイルをDriveにアップロード。失敗時はリトライ"""
    args = ["drive", "upload", str(local_path), "--parent", parent_id, "-j"]
    if mime_type:
        args.extend(["--mime-type", mime_type])
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            out = gog_run(args)
            return _extract_id(json.loads(out))
        except RuntimeError as e:
            last_err = e
            if attempt < max_retries:
                import time
                time.sleep(15 * (attempt + 1))  # 15s, 30s
                continue
            raise last_err


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recording_dir", help="ローカルの録画ディレクトリ")
    parser.add_argument("--parent", help="Drive親フォルダID(省略時は Drive ルート直下)")
    parser.add_argument("--skip-video", action="store_true",
                        help="動画(MP4)はスキップ(字幕と要約だけ上げる)")
    args = parser.parse_args()

    target = Path(args.recording_dir).expanduser().resolve()
    if not target.is_dir():
        print(f"❌ ディレクトリが見つからない: {target}")
        sys.exit(1)

    # ローカル名 YYYYMMDD_HHMMSS_<topic> → Drive名 YYYYMMDD_<topic>
    # (時刻を省いて読みやすく)
    m = re.match(r"^(\d{8})_\d{6}_(.+)$", target.name)
    folder_name = f"{m.group(1)}_{m.group(2)}" if m else target.name

    print(f"📂 ローカル: {target}")
    print(f"📛 Driveフォルダ名: {folder_name}")
    if args.parent:
        print(f"📁 親フォルダID: {args.parent}")
    else:
        print(f"📁 親フォルダ: Driveルート")
    print()

    # Driveに同名フォルダを作成 or 既存利用
    print("Step 1: Driveフォルダ確認/作成中...")
    drive_folder_id = mkdir(folder_name, parent_id=args.parent)
    print(f"  ✅ {drive_folder_id}")
    print(f"     URL: https://drive.google.com/drive/folders/{drive_folder_id}\n")

    # ファイル一覧
    local_files = sorted([f for f in target.iterdir() if f.is_file()])
    print(f"Step 2: {len(local_files)}個のローカルファイルを確認/アップロード中...")

    uploaded = []
    skipped_same = []  # 既存(同サイズ)でスキップ
    replaced = []  # 既存(サイズ違い)で置き換え
    failed = []

    for f in local_files:
        ext = f.suffix.lower()
        size_bytes = f.stat().st_size
        size_mb = size_bytes / 1024 / 1024

        if args.skip_video and ext in {".mp4", ".m4a"}:
            print(f"  ⏭  指定スキップ: {f.name} ({size_mb:.1f}MB)")
            continue

        # 既存ファイル確認
        existing = find_file(f.name, drive_folder_id)
        if existing:
            if existing["size"] == size_bytes:
                print(f"  ✅ 既存(同サイズ)スキップ: {f.name} ({size_mb:.1f}MB)")
                skipped_same.append(f.name)
                continue
            else:
                # サイズ違い → 古いの削除して新規アップ
                print(f"  🔁 置き換え: {f.name} (Drive {existing['size']/1024/1024:.1f}MB → ローカル {size_mb:.1f}MB)")
                try:
                    delete_file(existing["id"])
                except Exception as e:
                    print(f"     ⚠️  古い版削除失敗(続行): {e}")

        # 新規 or 置き換えアップロード
        mime = MIME_MAP.get(ext)
        print(f"  ⬆️  UP中: {f.name} ({size_mb:.1f}MB)")
        try:
            file_id = upload(f, drive_folder_id, mime)
            print(f"     ✅ {file_id}")
            if existing:
                replaced.append(f.name)
            else:
                uploaded.append(f.name)
        except Exception as e:
            print(f"     ❌ 失敗: {str(e)[:200]}")
            failed.append(f.name)

    print()
    print(f"=== サマリー ===")
    print(f"  ⬆️  新規アップ:   {len(uploaded)}個")
    print(f"  🔁 置き換え:    {len(replaced)}個")
    print(f"  ✅ 既存スキップ: {len(skipped_same)}個")
    if failed:
        print(f"  ❌ 失敗:        {len(failed)}個 ─ {', '.join(failed)}")
    print(f"\nDriveフォルダ:")
    print(f"  https://drive.google.com/drive/folders/{drive_folder_id}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
