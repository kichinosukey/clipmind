# utils/log.py
import sys
import datetime

def log(message: str, level: str = "INFO") -> None:
    """統一的なログ出力（stderr）"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", file=sys.stderr, flush=True)

