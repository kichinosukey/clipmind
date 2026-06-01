#!/usr/bin/env python3
"""
Summarizer module for YouTube transcripts.

- CLI usage:
    python summarizer.py summarize <file>
    python summarizer.py translate <file>

- Library usage (for pipeline.py):
    from clipmind.summarizer import summarize_text
    summary_text = summarize_text(text, mode="summarize")
"""

from openai import OpenAI
import os, sys, argparse
from clipmind.paths import load_project_dotenv
from clipmind.utils.log import log
from clipmind.utils.error import handle_error

# ==== .env読込 ====
load_project_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:1234/v1")
API_KEY = os.getenv("API_KEY", "not-needed")
MODEL = os.getenv("MODEL", "openai/gpt-oss-20b")

DEFAULT_SYSTEM_SUMMARIZE_PROMPT = """
You are a friend explaining a video you just watched to another adult over coffee.
Speak in plain everyday words and short sentences, with concrete examples when useful.
Avoid jargon; if a technical term is necessary, paraphrase it in everyday words in parentheses immediately after.
Do not be condescending or use "kid" framing — your reader is an adult who simply wants the cognitive load reduced.
Stay accurate: do not add any information that is not in the transcript.
Always follow the exact output format requested by the user. Headings are mandatory and must appear in the final output, even when merging partial summaries.
Use plain text only (no tables, no code blocks).
"""

DEFAULT_SYSTEM_TRANSLATE_PROMPT = """
You are a professional translator specializing in fluent, natural Japanese.
Respond only in Japanese unless a proper noun requires English.
"""

DEFAULT_USER_SUMMARIZE_PROMPT = """
Explain the following transcript in plain everyday words, as if telling a friend (an adult) what the video was about.
If a jargon term appears, paraphrase it in parentheses right after using it.

You MUST output using these EXACT headings, in this EXACT order. Do not omit any heading.
Do not collapse into free-form prose. Do not skip headings even if a section feels short — write the heading and a brief honest line under it.

What it's about:
<one plain sentence>

What they're saying:
- <2-3 plain sentences. If a technical term is needed, paraphrase it in parentheses.>
- ...

Notable Quotes:
- "<quote>" — <brief context in plain words>
- ...

So what?:
<1-3 sentences: what is actually new, surprising, or worth caring about here. If nothing stands out, say so honestly.>

Guidelines:
- Keep the flow roughly chronological
- Provide 5 to 7 items under "What they're saying"
- Quotes must be exact excerpts from the transcript and <= 20 words each
- If quotes are unclear due to transcription, omit them rather than invent
- Use plain text only (no tables, no code blocks)

Transcript:
{text}
""".strip()

DEFAULT_USER_TRANSLATE_PROMPT = """
Translate the following English summary into natural Japanese.
Respond only in Japanese. Do not include English words except proper nouns.

Summary:
{text}
""".strip()

PROMPTS = {
    "summarize": os.getenv("PROMPT_SUMMARIZE", DEFAULT_SYSTEM_SUMMARIZE_PROMPT),
    "translate": os.getenv("PROMPT_TRANSLATE", DEFAULT_SYSTEM_TRANSLATE_PROMPT),
}

USER_PROMPTS = {
    "summarize": os.getenv("USER_PROMPT_SUMMARIZE", DEFAULT_USER_SUMMARIZE_PROMPT),
    "translate": os.getenv("USER_PROMPT_TRANSLATE", DEFAULT_USER_TRANSLATE_PROMPT),
}


# ======================================================
#  ライブラリモード: パイプラインから直接呼ぶ用
# ======================================================
MAX_CHUNK_CHARS = 8000  # ~2000 tokens — safe for 4096 n_ctx with prompt overhead


def _call_llm(client: OpenAI, system_prompt: str, user_prompt: str) -> str:
    """Single LLM call. Raises on failure."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def _split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split text into chunks at paragraph boundaries."""
    paragraphs = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) + 1 > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para) + 1

    if current:
        chunks.append("\n".join(current))
    return chunks


def summarize_text(text: str, mode: str = "summarize") -> str:
    """
    Summarize or translate given text content.
    Long texts are automatically split into chunks and summarized,
    then merged into a final summary.

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

        if mode not in PROMPTS:
            raise ValueError(f"Unsupported mode: {mode}")

        system_prompt = PROMPTS[mode]
        user_prompt_template = USER_PROMPTS[mode]

        chunks = _split_text(text)
        log(f"[summarizer] text length={len(text)}, chunks={len(chunks)}")

        if len(chunks) <= 1:
            # Short text — single call
            try:
                user_prompt = user_prompt_template.format(text=text)
            except Exception:
                user_prompt = f"{user_prompt_template}\n\n{text}"

            output = _call_llm(client, system_prompt, user_prompt)
            log(f"[summarizer] output length={len(output)}")
            return output

        # Long text — summarize each chunk, then merge
        log(f"[summarizer] chunked mode: {len(chunks)} chunks")
        partial_summaries: list[str] = []
        for i, chunk in enumerate(chunks):
            log(f"[summarizer] processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            try:
                user_prompt = user_prompt_template.format(text=chunk)
            except Exception:
                user_prompt = f"{user_prompt_template}\n\n{chunk}"

            partial = _call_llm(client, system_prompt, user_prompt)
            partial_summaries.append(partial)

        # Merge partial summaries into a final summary
        merged_input = "\n\n---\n\n".join(partial_summaries)
        merge_prompt = (
            "Below are partial summaries of consecutive sections of the same transcript. "
            "Combine them into ONE coherent summary.\n\n"
            "You MUST use these EXACT headings in this EXACT order, just like the partial summaries:\n"
            "  What it's about:\n"
            "  What they're saying:\n"
            "  Notable Quotes:\n"
            "  So what?:\n\n"
            "Do not collapse into free-form prose. Do not omit any heading. "
            "Merge the bullets under 'What they're saying' (keep 5-7 total, chronological). "
            "Merge the quotes under 'Notable Quotes' (keep the strongest ones). "
            "Write a single 'What it's about' line and a single 'So what?' paragraph that span the whole transcript.\n\n"
            f"{merged_input}"
        )
        log(f"[summarizer] merging {len(partial_summaries)} partial summaries")
        output = _call_llm(client, system_prompt, merge_prompt)
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
    parser.add_argument(
        "mode", choices=["summarize", "translate"], help="Processing mode"
    )
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
