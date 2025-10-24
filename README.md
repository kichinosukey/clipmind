# 🎬 ClipMind

> YouTube → Whisper → LLM → Discord  
> 自動で動画要約を生成して投稿する軽量パイプライン

ClipMind は、YouTube 動画から音声を抽出し、  
Whisper.cpp による文字起こし → LLM による要約 → Discord 投稿  
までを一括で処理するオープンソースツールです。

---

## ✨ 特徴

- 🎥 YouTube URL ひとつで完結  
- 🧠 Whisper.cpp + OpenAI互換APIを使用（ローカル or クラウド）  
- 💬 自動で英語→日本語要約  
- 🔗 Discord Webhook 連携  
- ⚙️ Alfred / cron / RSS トリガー対応  

---

## 📁 出力例

```
~/clipmind/data/
└── Stanford/
    └── Steve Jobs_ 2005 Stanford Commencement Address/
        ├── Steve Jobs_ 2005 Stanford Commencement Address.wav
        ├── Steve Jobs_ 2005 Stanford Commencement Address.txt
        ├── Steve Jobs_ 2005 Stanford Commencement Address_summary.txt
        ├── Steve Jobs_ 2005 Stanford Commencement Address_summary_ja.txt
        └── metadata.json
```

---

## 🧩 依存ツール

| ツール | 説明 | インストール例 |
|--------|------|----------------|
| **yt-dlp** | YouTube音声ダウンロード | `brew install yt-dlp` |
| **ffmpeg** | 音声抽出用 | `brew install ffmpeg` |
| **whisper.cpp** | 音声文字起こし | [GitHub – whisper.cpp](https://github.com/ggerganov/whisper.cpp) |
| **Python 3.10+** | 本ツール実行用 | `brew install python` |

---

## ⚙️ セットアップ

### 1. リポジトリを取得
```bash
git clone https://github.com/<yourname>/clipmind.git
cd clipmind
```

### 2. 仮想環境構築
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Whisper.cpp の準備
```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
./models/download-ggml-model.sh base.en  # 英語モデルをダウンロード
```

### 4. `.env` の設定
`.env.example` をコピーして編集します：

```bash
cp .env.example .env
```

```ini
# OpenAI互換API（OllamaやLocalAIにも対応）
BASE_URL=http://localhost:1234/v1
API_KEY=not-needed
MODEL=openai/gpt-oss-20b

# Discord Webhook（投稿先）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/XXXXXXXXX/XXXXXXXXX

# 出力先
OUTROOT=~/clipmind/data
```

---

## 🚀 実行方法

### 1. CLIから実行
```bash
python -m clipmind.pipeline "https://www.youtube.com/watch?v=UF8uR6Z6KLc"
```

### 2. Alfred Workflowから
以下のような Run Script を設定：

```bash
#!/bin/zsh
set -euo pipefail

URL="${1:-}"
[[ -z "$URL" ]] && osascript -e 'display notification "URLが空です" with title "ClipMind"' && exit 1

: "${CLIPMIND_HOME:=$HOME/clipmind}"
cd "$CLIPMIND_HOME"
source "$CLIPMIND_HOME/.venv/bin/activate"

python -m clipmind.pipeline "$URL" > /tmp/clipmind.log 2>&1
osascript -e 'display notification "処理が完了しました" with title "ClipMind"'
```

---

## 🧠 動作イメージ

1. YouTubeのURLを入力（CLI or Alfred）  
2. Whisper.cpp が文字起こしを実行  
3. LLM（ローカル or API）が英語要約と日本語要約を生成  
4. Discordに要約を自動投稿  

---

## 📦 requirements.txt

```
openai>=1.0.0
python-dotenv>=1.0.0
requests>=2.31.0
yt-dlp>=2024.3.10
```

---

## 🪪 License

MIT License  
(c) 2025 ClipMind Contributors

---

## 🤝 貢献方法

Pull Request・Issue・フィードバック歓迎！  
特に以下の貢献ポイントがあります：

- ローカルLLM対応の改善（Ollama / LM Studio）  
- Whisperモデル自動ダウンロード  
- RSSやGitHub Actionsとの連携  

---

## 🧩 開発メモ

- すべてのログは `/tmp/clipmind.log` に出力されます。  
- 出力ディレクトリは `.env` の `OUTROOT` で変更可能。  
- Discord 投稿を無効にしたい場合は `.env` で `DISCORD_WEBHOOK_URL` を空欄に。

---

🧠 **ClipMind**  
_“Summarize the world’s knowledge, one clip at a time.”_
