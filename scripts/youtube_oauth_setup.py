#!/usr/bin/env python3
"""YouTube OAuth 初回セットアップ(1回だけ実行)

使い方:
    python3 ~/transcribe/_scripts/youtube_oauth_setup.py

挙動:
- ブラウザが開く → Google ログインして「許可」をクリック
- リフレッシュトークンを取得して .env の YOUTUBE_REFRESH_TOKEN に保存
- 以降は zoom_upload_to_youtube.py が自動で access token を更新できる

前提:
- .env に OAuth クライアント情報(YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET)が必要
  (gog の credentials.json から取得した値)
"""
import os
import sys
import json
import time
import urllib.parse
import urllib.request
import webbrowser
import socket
import http.server
import threading
from pathlib import Path

ENV_PATH = Path.home() / "transcribe" / "_scripts" / ".env"

# YouTube アップロードに必要なスコープ
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


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


def append_or_update_env(env_path, key, value):
    """既存の .env の同名キーを上書き、なければ追記"""
    lines = []
    found = False
    with open(env_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(f"{key}="):
                lines.append(f"{key}={value}\n")
                found = True
            else:
                lines.append(line)
    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """OAuth リダイレクト先(localhost:PORT/callback)を受け取る"""
    received_code = None
    received_error = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            CallbackHandler.received_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<h1>認証成功</h1><p>このタブは閉じてOKです。</p>".encode("utf-8")
            )
        elif "error" in params:
            CallbackHandler.received_error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<h1>エラー</h1><p>{params['error'][0]}</p>".encode("utf-8")
            )

    def log_message(self, *args, **kwargs):
        pass  # サーバーログ抑制


def main():
    env = load_env(ENV_PATH)

    client_id = env.get("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = env.get("YOUTUBE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("❌ YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET が .env にない")
        print("   .env に以下を追加:")
        print("   YOUTUBE_CLIENT_ID=<gog の client_id>")
        print("   YOUTUBE_CLIENT_SECRET=<gog の client_secret>")
        sys.exit(1)

    if env.get("YOUTUBE_REFRESH_TOKEN", "").strip():
        print("⚠️  YOUTUBE_REFRESH_TOKEN が既に設定されてる。")
        choice = input("    上書きする? [y/N]: ").strip().lower()
        if choice != "y":
            print("中止")
            sys.exit(0)

    port = find_free_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # 必ず refresh_token を返してもらう
    }
    auth_url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(auth_params)

    print(f"\n🌐 ブラウザが開きます。Google アカウントで「許可」を押してください。")
    print(f"   開かない場合は以下を手動で開く:\n   {auth_url}\n")

    server = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    webbrowser.open(auth_url)

    # コールバック待ち(最大5分)
    deadline = time.time() + 300
    while time.time() < deadline:
        if CallbackHandler.received_code or CallbackHandler.received_error:
            break
        time.sleep(0.5)

    server.shutdown()

    if CallbackHandler.received_error:
        print(f"❌ 認証エラー: {CallbackHandler.received_error}")
        sys.exit(1)
    if not CallbackHandler.received_code:
        print(f"❌ タイムアウト(5分)")
        sys.exit(1)

    code = CallbackHandler.received_code
    print(f"✅ 認証コード取得")

    # コード → refresh_token 交換
    token_data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read())

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print(f"❌ refresh_token が取れなかった: {tokens}")
        sys.exit(1)

    append_or_update_env(ENV_PATH, "YOUTUBE_REFRESH_TOKEN", refresh_token)
    print(f"✅ YOUTUBE_REFRESH_TOKEN を .env に保存(長さ:{len(refresh_token)})")
    print(f"   有効期限:基本的に永続(ユーザーが認証を取り消すまで)")
    print(f"\n以降は zoom_upload_to_youtube.py で動画アップロードできます。")


if __name__ == "__main__":
    main()
