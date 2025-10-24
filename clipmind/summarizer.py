#!/usr/bin/env python3
"""
Summarizer module for YouTube transcripts.

- CLI usage:
    python summarizer.py summarize <file>
    python summarizer.py translate <file>

- Library usage (for pipeline.py):
    from yt_full.summarizer import summarize_text
    summary_text = summarize_text(text, mode="summarize")
"""

from openai import OpenAI
from dotenv import load_dotenv
import os, sys, argparse
from clipmind.utils.log import log
from clipmind.utils.error import handle_error

# ==== .env読込 ====
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:1234/v1")
API_KEY = os.getenv("API_KEY", "not-needed")
MODEL = os.getenv("MODEL", "openai/gpt-oss-20b")

PROMPTS = {
    "summarize": """
You are an expert in summarizing university lectures.
The following transcript comes from a YouTube lecture video.

Goal: Clearly summarize the overall structure and key arguments of the lecture.

Output format:
1. Overview – one paragraph describing the lecture's theme and purpose
2. Main Points (5-10 items)
   - For each item: include the main idea and short supporting example or note (if any)
3. Key Messages – the lecturer’s emphasized takeaways or conclusions
4. Learning Points – what the audience should understand or remember after watching

Guidelines:
- Preserve the logical order and structure of explanation
- Keep concrete examples only when they clarify key ideas
- Briefly explain technical terms in simple language (e.g., “cohort = a group born in the same period”)
""",
    "translate": """
You are a professional translator who translates English into natural Japanese.
Please ensure the output is fluent and natural, not literal.
"""
}


# ======================================================
#  ライブラリモード: パイプラインから直接呼ぶ用
# ======================================================
def summarize_text(text: str, mode: str = "summarize") -> str:
    """
    Summarize or translate given text content.

    Args:
        text (str): English transcript or summary text.
        mode (str): Either "summarize" or "translate". Default "summarize".

    Returns:
        str: Generated summary or translation.
    """
    if not text.strip():
        raise ValueError("Input text is empty.")

    try:
        client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        log(f"[summarizer] mode={mode}, model={MODEL}")

        system_prompt = PROMPTS[mode]
        user_prompt = (
            f"Summarize the following English text:\n\n{text}"
            if mode == "summarize"
            else f"Translate the following English summary into Japanese:\n\n{text}"
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        output = response.choices[0].message.content.strip()
        log(f"[summarizer] output length={len(output)}")
        return output

    except Exception as e:
        handle_error("summarize_text() failed", e)


# ======================================================
#  CLIモード: ファイルを直接処理する用
# ======================================================
def main():
    parser = argparse.ArgumentParser(
        description="Summarize or translate text files using OpenAI-compatible API"
    )
    parser.add_argument("mode", choices=["summarize", "translate"], help="Processing mode")
    parser.add_argument("file", help="Path to the input text file")
    args = parser.parse_args()

    log(f"mode={args.mode}")
    log(f"input file={args.file}")
    log(f"BASE_URL={BASE_URL}")
    log(f"MODEL={MODEL}")

    if not os.path.exists(args.file):
        handle_error(f"File not found: {args.file}")

    # ==== 出力ファイル名 ====
    out_path = (
        args.file.replace(".txt", "_summary.txt")
        if args.mode == "summarize"
        else args.file.replace("_summary.txt", "_summary_ja.txt")
    )

    # ==== ファイル読み込み ====
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read().strip()
        log(f"file read success, length={len(text)}")
    except Exception as e:
        handle_error("Failed to read input file", e)

    if not text:
        handle_error("Input file is empty")

    # ==== モデル実行 ====
    output_text = summarize_text(text, args.mode)

    # ==== 出力 ====
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output_text)
        log(f"Output written to {out_path}")
    except Exception as e:
        handle_error("Failed to write output file", e)

    log("Processing finished successfully")


if __name__ == "__main__":
    main()

