#!/usr/bin/env python3
"""
clipmind Native Messaging Host

Chrome拡張からNative Messagingプロトコルでメッセージを受信し、
clipmind_runner.py をdetachedサブプロセスとして起動する。

stdlibのみ使用するためsystem pythonで動作する。
"""
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from clipmind.paths import NATIVE_RUNNER_SCRIPT, PROJECT_ROOT, STATUS_DIR, VENV_PYTHON


def read_message():
    """stdin から Native Messaging プロトコルのメッセージを読む。"""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) != 4:
        return None
    length = struct.unpack("<I", raw_length)[0]
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode("utf-8"))


def send_message(msg):
    """stdout に Native Messaging プロトコルのメッセージを書く。"""
    encoded = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def _handle_get_config():
    """設定済みのデスティネーション一覧を返す。

    venv pythonで.envを読み取り、webhook URLが設定済みのデスティネーションを判定する。
    """
    config_script = str(Path(__file__).resolve().parent / "clipmind_config.py")
    venv_python = str(VENV_PYTHON)

    if not os.path.exists(venv_python):
        send_message({"destinations": ["discord", "slack"]})
        return

    try:
        result = subprocess.run(
            [venv_python, config_script],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            send_message(data)
        else:
            send_message({"destinations": ["discord", "slack"]})
    except Exception:
        send_message({"destinations": ["discord", "slack"]})


def main():
    msg = read_message()
    if msg is None:
        send_message({"status": "error", "error": "No message received"})
        return

    action = msg.get("action", "summarize")

    # get_config: 設定済みデスティネーションを返す
    if action == "get_config":
        _handle_get_config()
        return

    url = msg.get("url", "")
    if not url:
        send_message({"status": "error", "error": "No URL provided"})
        return

    destinations = msg.get("destinations", ["discord"])

    # ジョブID生成
    job_id = hashlib.md5(f"{url}:{time.time()}".encode()).hexdigest()[:12]

    # ステータスディレクトリ
    status_dir = str(STATUS_DIR)
    os.makedirs(status_dir, exist_ok=True)
    status_file = os.path.join(status_dir, f"{job_id}.json")
    log_file = os.path.join(status_dir, f"{job_id}.log")

    # 初期ステータス書き込み
    with open(status_file, "w") as f:
        json.dump({"status": "starting", "url": url, "job_id": job_id}, f)

    # clipmind_runner.py を detached subprocess で起動
    runner = str(NATIVE_RUNNER_SCRIPT)
    venv_python = str(VENV_PYTHON)

    if not os.path.exists(venv_python):
        send_message({
            "status": "error",
            "error": f"venv python not found: {venv_python}",
        })
        return

    dests_arg = ",".join(destinations)

    with open(log_file, "w") as lf:
        subprocess.Popen(
            [venv_python, runner, url, status_file, dests_arg],
            stdout=lf,
            stderr=lf,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(PROJECT_ROOT),
        )

    send_message({"status": "started", "job_id": job_id})


if __name__ == "__main__":
    main()
