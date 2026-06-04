#!/usr/bin/env python3
"""
clipmind Pipeline Runner

clipmind_host.py から detached subprocess として起動される。
venv の python で実行され、clipmind パッケージをインポートして
run_pipeline() を呼び出す。

完了・エラー時に macOS ネイティブ通知を表示する。
"""
import os
import subprocess
import sys
import traceback
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from clipmind.config import load_runtime_config
from clipmind.jobs import JobStatusStore
from clipmind.paths import JOBS_DIR, PROJECT_ROOT
from clipmind.secrets import redact_secrets


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


def main():
    if len(sys.argv) < 3:
        print("Usage: clipmind_runner.py <youtube_url> <job_id> [destinations]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    job_id = sys.argv[2]
    destinations = sys.argv[3].split(",") if len(sys.argv) > 3 else ["discord"]

    os.chdir(str(PROJECT_ROOT))
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    # PATH に homebrew 等のパスを追加 (yt-dlp, ffmpeg 用)
    extra_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    current_path = os.environ.get("PATH", "")
    for p in extra_paths:
        if p not in current_path:
            current_path = p + ":" + current_path
    os.environ["PATH"] = current_path

    try:
        from clipmind.pipeline import run_pipeline

        config = load_runtime_config()
        reporter = JobStatusStore(
            JOBS_DIR, job_id=job_id, source_url=url, secrets=config.secrets
        )
        result = run_pipeline(
            url, config=config, reporter=reporter, destinations=destinations
        )
        title = result.get("title", "Unknown") if result else "Unknown"
        notify("clipmind - 完了", f"要約が完了しました: {title[:50]}")

    except Exception as e:
        tb = traceback.format_exc()
        secrets = config.secrets if "config" in locals() else []
        print(redact_secrets(tb, secrets), file=sys.stderr)
        notify("clipmind - エラー", f"エラー: {redact_secrets(str(e), secrets)[:50]}")


if __name__ == "__main__":
    main()
