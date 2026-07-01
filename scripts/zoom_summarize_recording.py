#!/usr/bin/env python3
"""Zoom録画の文字起こしから「会員サイト掲載用」の動画要約を生成

使い方:
    python3 ~/transcribe/_scripts/zoom_summarize_recording.py <録画ディレクトリ>

例:
    python3 ~/transcribe/_scripts/zoom_summarize_recording.py \\
        ~/transcribe/zoom_recordings/20260622_061515_月曜朝茶会_日本時間615-645

入力: <録画ディレクトリ>/audio_transcript.txt
出力: <録画ディレクトリ>/_summary.md

ANTHROPIC_API_KEY が ~/transcribe/_scripts/.env にある前提。
"""
import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path


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


ENV_PATH = Path(__file__).resolve().parent / ".env"
env = load_env(ENV_PATH)

# API選択: ANTHROPIC_API_KEY があれば直 / なければ OPENROUTER_API_KEY 経由
ANTHROPIC_KEY = env.get("ANTHROPIC_API_KEY", "").strip()
OPENROUTER_KEY = env.get("OPENROUTER_API_KEY", "").strip()

if ANTHROPIC_KEY:
    PROVIDER = "anthropic"
    API_URL = "https://api.anthropic.com/v1/messages"
    MODEL = "claude-haiku-4-5"
elif OPENROUTER_KEY:
    PROVIDER = "openrouter"
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "anthropic/claude-haiku-4.5"
else:
    PROVIDER = None

_COURSE_NAME = os.environ.get("COURSE_NAME") or env.get("COURSE_NAME", "オンライン講座")
_HOST_NAME = os.environ.get("COURSE_HOST_NAME") or env.get("COURSE_HOST_NAME", "")
SYSTEM_PROMPT = f"""あなたは {_COURSE_NAME}{(f" (主宰: {_HOST_NAME})" if _HOST_NAME else "")} の運営アシスタントです。
受講者向けに、Zoom録画アーカイブの「視聴前に見る要約」を書きます。

目的:
- 受講者が「見る/見ない」を判断できる
- 後から特定の話題を検索できる
- 復習のとっかかりになる

絶対ルール:
- Markdown太字 (**) は使わない(コピペ用途のため)
- 「」 や ★ 等で代替する
- 講師の話す内容を淡々と整理する。感想や評価は書かない
- 朝の挨拶・雑談は省く
- 文字起こしの誤認識(短い断片・重複)は文脈から正しく解釈する
- お茶用語・中医学用語(気血水・五行・体質名等)は正確に拾う"""

USER_TEMPLATE = """以下はZoomセッション「{topic}」の文字起こしです(発言者: ラベル付き)。
これを以下のフォーマットで要約してください。

# {topic}

## 一言サマリー
(1-2行でこのセッションの中身を伝える)

## 主な内容
- (時系列に5-8個の箇条書き。各項目は「ばってん呼吸法 ─ 椅子に座って手をX字にして開閉する」のように具体的に書く)

## キーワード
(講座用語・お茶用語・中医学用語・体質ワードを横並びで。コンマ区切り)

## 持ち帰りポイント
1. (受講者が「これだけは覚えて帰りたい」要点)
2.
3.
(3〜5個)

---

【文字起こし】

{transcript}
"""


def summarize(transcript: str, topic: str) -> str:
    if PROVIDER is None:
        return "(ANTHROPIC_API_KEY / OPENROUTER_API_KEY のどちらも未設定)"

    user_msg = USER_TEMPLATE.format(topic=topic, transcript=transcript)

    if PROVIDER == "anthropic":
        body = {
            "model": MODEL,
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        }
        headers = {
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    else:  # openrouter (OpenAI互換)
        body = {
            "model": MODEL,
            "max_tokens": 2000,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://transcribe.local",
            "X-Title": "ChayouZoomSummarizer",
        }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
            if PROVIDER == "anthropic":
                return data["content"][0]["text"]
            else:
                return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return f"(API エラー HTTP {e.code}: {err_body})"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target_dir = Path(sys.argv[1]).expanduser().resolve()
    if not target_dir.is_dir():
        print(f"❌ ディレクトリが見つからない: {target_dir}")
        sys.exit(1)

    transcript_path = target_dir / "audio_transcript.txt"
    if not transcript_path.exists():
        print(f"❌ audio_transcript.txt が見つからない: {transcript_path}")
        sys.exit(1)

    transcript = transcript_path.read_text(encoding="utf-8")
    if not transcript.strip():
        print(f"❌ 文字起こしが空")
        sys.exit(1)

    # トピックはディレクトリ名から推定 (YYYYMMDD_HHMMSS_<topic>)
    parts = target_dir.name.split("_", 2)
    topic = parts[2] if len(parts) >= 3 else target_dir.name

    print(f"📝 要約生成中: {topic}")
    print(f"   API: {PROVIDER}  /  Model: {MODEL}")
    print(f"   文字起こし: {len(transcript)}文字")

    summary = summarize(transcript, topic)

    out_path = target_dir / "_summary.md"
    out_path.write_text(summary + "\n", encoding="utf-8")
    print(f"✅ 保存: {out_path}")
    print()
    print("=" * 60)
    print(summary)


if __name__ == "__main__":
    main()
