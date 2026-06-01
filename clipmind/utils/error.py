# utils/error.py
import sys
import traceback
from clipmind.utils.log import log

def handle_error(message: str, exc: Exception | None = None, exit_code: int = 1) -> None:
    """
    共通エラーハンドラ。
    - メッセージを標準化して表示
    - 例外があれば詳細も出力
    - 終了コード指定可
    """
    log(f"❌ {message}", "ERROR")
    if exc:
        log(f"Details: {exc}", "ERROR")
        traceback.print_exc(file=sys.stderr)
    sys.exit(exit_code)

