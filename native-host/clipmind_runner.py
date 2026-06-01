#!/usr/bin/env python3
"""
clipmind Pipeline Runner

clipmind_host.py から detached subprocess として起動される。
venv の python で実行され、clipmind パッケージをインポートして
run_pipeline() を呼び出す。

完了・エラー時に macOS ネイティブ通知を表示する。
"""
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from clipmind.paths import PROJECT_ROOT, load_project_dotenv


def notify(title, message):
    """macOS ネイティブ通知を表示する。"""
    script = f'display notification "{message}" with title "{title}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def update_status(status_file, data):
    """ステータスファイルを更新する。"""
    try:
        with open(status_file, "w") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def main():
    if len(sys.argv) < 3:
        print("Usage: clipmind_runner.py <youtube_url> <status_file> [destinations]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    status_file = sys.argv[2]
    destinations = sys.argv[3].split(",") if len(sys.argv) > 3 else ["discord"]

    # プロジェクトルートに移動 (.env の load_dotenv() が動くように)
    os.chdir(str(PROJECT_ROOT))
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    load_project_dotenv()

    # PATH に homebrew 等のパスを追加 (yt-dlp, ffmpeg 用)
    extra_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    current_path = os.environ.get("PATH", "")
    for p in extra_paths:
        if p not in current_path:
            current_path = p + ":" + current_path
    os.environ["PATH"] = current_path

    update_status(status_file, {"status": "running", "url": url})

    try:
        from clipmind.pipeline import run_pipeline

        result = run_pipeline(url, destinations=destinations)
        title = result.get("title", "Unknown") if result else "Unknown"
        delivery = result.get("delivery_results", {}) if result else {}

        update_status(status_file, {
            "status": "completed",
            "url": url,
            "title": title,
            "delivery_results": delivery,
        })
        notify("clipmind - 完了", f"要約が完了しました: {title[:50]}")

    except SystemExit:
        update_status(status_file, {
            "status": "error",
            "url": url,
            "error": "Pipeline exited with error",
        })
        notify("clipmind - エラー", "パイプラインの実行に失敗しました")

    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        update_status(status_file, {
            "status": "error",
            "url": url,
            "error": str(e),
        })
        notify("clipmind - エラー", f"エラー: {str(e)[:50]}")


if __name__ == "__main__":
    main()
