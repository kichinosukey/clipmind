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

from clipmind.paths import JOBS_DIR, NATIVE_RUNNER_SCRIPT, PROJECT_ROOT, VENV_PYTHON


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


def main():
    msg = read_message()
    if msg is None:
        send_message({"status": "error", "error": "No message received"})
        return

    url = msg.get("url", "")
    if not url:
        send_message({"status": "error", "error": "No URL provided"})
        return

    destinations = msg.get("destinations", ["discord"])

    # ジョブID生成
    job_id = hashlib.md5(f"{url}:{time.time()}".encode()).hexdigest()[:12]

    # ステータスディレクトリ
    status_dir = str(JOBS_DIR)
    os.makedirs(status_dir, exist_ok=True)
    log_file = os.path.join(status_dir, f"{job_id}.log")

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
            [venv_python, runner, url, job_id, dests_arg],
            stdout=lf,
            stderr=lf,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(PROJECT_ROOT),
        )

    send_message({"status": "started", "job_id": job_id})


if __name__ == "__main__":
    main()
