# 🎬 ClipMind

> YouTube → Whisper → LLM → Discord  
> 自動で動画要約を生成して投稿する軽量パイプライン

ClipMind は、YouTube 動画から音声を抽出し、  
Whisper.cpp による文字起こし → LLM による要約 → Discord 投稿  
までを一括で処理するオープンソースツールです。

---

## 📥 インストール（macOS）

clone から一通り入れる bootstrap インストーラ（`curl | bash`）:

```bash
curl -fsSL https://raw.githubusercontent.com/kichinosukey/clipmind/main/install.sh | bash
```

または:

```bash
wget -qO- https://raw.githubusercontent.com/kichinosukey/clipmind/main/install.sh | bash
```

既定ではリポジトリを `~/.local/share/clipmind` に clone し、venv 作成・`pip install`・`~/.local/bin` へのラッパー配置まで行います。Chrome 拡張・Whisper・`.env` の API 設定はインストール後に必要です（完了時に案内が表示されます）。

| 環境変数 | 既定値 | 意味 |
|----------|--------|------|
| `CLIPMIND_HOME` | `~/.local/share/clipmind` | clone 先 |
| `CLIPMIND_REPO_URL` | `https://github.com/kichinosukey/clipmind.git` | clone URL |
| `CLIPMIND_BRANCH` | `main` | ブランチ |
| `CLIPMIND_INSTALL_DIR` | `~/.local/bin` | ラッパー配置先 |

**アンインストール**（ラッパー削除。clone 本体は既定で残す）:

```bash
curl -fsSL https://raw.githubusercontent.com/kichinosukey/clipmind/main/uninstall.sh | bash
```

clone ごと削除する場合: `CLIPMIND_REMOVE_REPO=1` を付けて実行。

すでに手動で clone 済みの場合は、リポジトリ直下で `./install.sh` を実行しても同じです。PATH ラッパーだけ更新したいときは `./scripts/install-local.sh` のみで構いません。

---

## ✨ 特徴

- 🎥 YouTube URL ひとつで完結  
- 🧠 Whisper.cpp + OpenAI互換APIを使用（ローカル or クラウド）  
- 💬 自動で英語→日本語要約  
- 🔗 Discord Webhook 連携  
- ⚙️ Alfred / cron / RSS トリガー対応
- 🌐 Chrome拡張で右クリックから即実行

---

## 📁 出力例

```
~/clipmind-data/
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
git clone https://github.com/kichinosukey/clipmind.git
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
OUTROOT=~/clipmind-data
```

### 5. （任意）`~/.local/bin` にコマンドを置く

どのディレクトリからでも `clipmind-run` / `clipmind-repair` を使う場合:

```bash
./scripts/install-local.sh
```

PATH に `~/.local/bin` が無い場合は、表示される `export PATH=...` を `~/.zshrc` 等に追加してください。

- **別 Mac へ初めて入れる場合** → 下記 [他マシン向けクイックスタート](#他マシン向けクイックスタート) が最短です。
- **アンインストール** → `./scripts/uninstall-local.sh`（`~/.local/bin` のラッパーのみ削除。clone 本体・Chrome 連携は残ります）

---

## 🖥 他マシン向けクイックスタート

別の Mac で使う場合の最短手順です。

**A. 1 行インストール（推奨）** — 上記 [インストール（macOS）](#-インストールmacos) の `curl | bash` を実行し、表示される Next steps に従います。

**B. 手動 clone** — clone 先は任意です（`install-local.sh` が実際のパスを記録します）。

```bash
git clone https://github.com/kichinosukey/clipmind.git
cd clipmind
./install.sh
# または ./scripts/install-local.sh のみ（venv 済みのとき）

brew install yt-dlp ffmpeg
# Whisper.cpp は「Whisper.cpp の準備」を参照

# Chrome: chrome-extension/ を unpacked 読み込み → Extension ID をコピー
clipmind-repair <extension-id>

cd /tmp && clipmind-run "https://www.youtube.com/watch?v=jNQXAC9IVRw"
```

| 依存 | 管理方法 | ClipMind |
|------|----------|----------|
| yt-dlp | Homebrew | 鮮度チェック・失敗時 `brew upgrade` リトライ（`clipmind-repair` で確認） |
| ffmpeg | Homebrew | README / brew install のみ |
| whisper-cli | 手動ビルド・`.env` | パスは `WHISPER_BIN` / `WHISPER_MODEL` |

リポジトリを移動したら、移動先で `./scripts/install-local.sh` を再実行し、続けて `clipmind-repair`（Extension ID が変わった場合は引数付き）を実行してください。

---

## 📍 `~/.local/bin` インストール（詳細）

| スクリプト | 作用 |
|-----------|------|
| `scripts/install-local.sh` | install 実行時の **clone 絶対パス** を `CLIPMIND_HOME` としてラッパーに記録し、`~/.local/bin/clipmind-run` と `clipmind-repair` を配置 |
| `scripts/uninstall-local.sh` | 上記 2 つのラッパーのみ削除 |

ラッパーはリポジトリ内の `clipmind-run` / `clipmind-repair` を `exec` します（`.venv` と `.env` は clone 先を参照）。

```bash
# インストール（リポジトリ直下で）
./scripts/install-local.sh

# 確認
which clipmind-run   # → ~/.local/bin/clipmind-run
clipmind-repair      # yt-dlp health 等を表示

# ラッパーのみ削除
./scripts/uninstall-local.sh
```

> **注意:** Chrome Native Messaging の manifest や Alfred ワークフローは `uninstall-local.sh` では削除しません。完全に外す場合は manifest ファイルを手動で削除し、Alfred 側はワークフローを無効化してください。

---

## 📂 リポジトリ構成（主要部分）

```
clipmind/                    # clone 先（curl インストール時は ~/.local/share/clipmind が既定）
├── install.sh               # bootstrap（clone / venv / install-local）
├── uninstall.sh             # ラッパー削除（任意で clone 削除）
├── clipmind-run             # リポジトリ内ランチャー（pipeline）
├── clipmind-repair          # Chrome NM / Alfred 修復
├── clipmind/                # Python パッケージ
├── scripts/
│   ├── install-local.sh     # ~/.local/bin へラッパーのみ
│   └── uninstall-local.sh   # ラッパーのみ削除
├── chrome-extension/        # Chrome 拡張（unpacked 読み込み）
├── native-host/             # Native Messaging Host
├── .env                     # 設定（要作成）
└── .venv/                   # Python 仮想環境
```

---

## 🚀 実行方法

### 1. CLIから実行

リポジトリ直下:

```bash
./clipmind-run "https://www.youtube.com/watch?v=UF8uR6Z6KLc"
```

`./scripts/install-local.sh` 済みなら、どのディレクトリからでも:

```bash
clipmind-run "https://www.youtube.com/watch?v=UF8uR6Z6KLc"
```

### 2. Alfred Workflowから

`./scripts/install-local.sh` のあと `clipmind-repair` を一度実行すると、ClipMind 用 Alfred ワークフローのスクリプトが **その時点の clone パス** に更新されます。手動で書く場合は、次のように **PATH 上の `clipmind-run`** を呼び出します（固定の home パスは不要）:

```bash
#!/bin/zsh
set -euo pipefail

URL="${1:-}"
[[ -z "$URL" ]] && osascript -e 'display notification "URLが空です" with title "ClipMind"' && exit 1

if ! command -v clipmind-run >/dev/null 2>&1; then
  osascript -e 'display notification "clipmind-run が PATH にありません。install-local.sh を実行してください" with title "ClipMind"'
  exit 1
fi

clipmind-run "$URL" > /tmp/clipmind.log 2>&1
osascript -e 'display notification "処理が完了しました" with title "ClipMind"'
```
### Alfred Workflow（macOS専用）

ワンクリックで実行したい場合は、こちらから最新の **Alfred Workflow リリース** をダウンロードしてください 👇
👉 [ClipMind リリースページ（GitHub）](https://github.com/kichinosukey/clipmind/releases)

インストール後、Alfredで次のように入力します：

### 3. Chrome拡張から（macOS専用）

YouTubeページ上で右クリック → 「clipmindで要約」を選ぶだけでパイプラインを実行できます。
CLIやAlfredを開く必要がなく、ブラウザだけで完結します。

詳しいセットアップは [Chrome拡張セットアップ](#-chrome-拡張機能) を参照してください。

---

## 🌐 Chrome 拡張機能

### 概要

Chrome拡張機能を使うと、YouTube動画のページで **右クリック →「clipmindで要約」** を選択するだけで、ローカルのclipmindパイプラインが起動します。

処理の流れ:

```
YouTubeページで右クリック
  → Chrome拡張 (background.js)
  → Chrome Native Messaging
  → clipmind_host.py (URLを受信、runnerを起動)
  → clipmind_runner.py (run_pipeline 実行)
  → 完了時に macOS通知でお知らせ
```

- パイプラインはローカルのバックグラウンドで実行されるため、ブラウザをそのまま使い続けられます
- 処理開始時にChrome通知、完了時にmacOS通知が表示されます
- 結果は通常のCLI実行と同じく `.env` の `OUTROOT` に保存されます

### 前提条件

- macOS
- Google Chrome
- [セットアップ](#%EF%B8%8F-セットアップ) が完了していること（venv構築、`.env`設定、Whisper.cpp準備）

### セットアップ手順

#### Step 1: Chrome拡張を読み込む

1. Chromeで `chrome://extensions` を開く
2. 右上の **「デベロッパーモード」** をONにする
3. **「パッケージ化されていない拡張機能を読み込む」** をクリック
4. このリポジトリの `chrome-extension/` フォルダを選択
5. 読み込まれた拡張のカードに表示される **Extension ID**（`abcdefg...` のような文字列）をコピーする

#### Step 2: Native Messaging Host をインストールする

```bash
# リポジトリ直下、または install-local.sh 後は PATH 上のコマンド
./clipmind-repair <コピーしたExtension ID>
# 例: clipmind-repair <コピーしたExtension ID>
```

実行すると、以下のファイルが生成されます:

```
~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.clipmind.host.json
```

#### Step 3: Chromeを再起動する

Chromeを完全に終了して再起動してください（タブの再読み込みだけでは反映されません）。

### リポジトリを移動したとき

clone 先を別のディレクトリへ移した場合は、**移動先**で次を実行してください。

```bash
cd /path/to/your/clipmind
./scripts/install-local.sh
clipmind-repair
```

その後に `chrome://extensions` で `chrome-extension/` を再読み込みしてください。
再読み込み後に Extension ID が変わった場合は、新しい ID で `clipmind-repair <new-extension-id>` をもう一度実行します。

### 使い方

1. YouTubeの動画ページを開く
2. ページ上で **右クリック**（またはリンク上で右クリック）
3. コンテキストメニューから **「clipmindで要約」** を選択
4. Chrome通知で **「処理を開始しました」** と表示される
5. バックグラウンドで音声DL→文字起こし→要約→翻訳→Discord投稿が実行される
6. 完了するとmacOS通知で **「要約が完了しました」** と表示される

### トラブルシューティング

**「clipmindで要約」がメニューに表示されない**
- `chrome://extensions` で拡張が有効になっているか確認
- YouTube以外のページでは表示されません

**「Native messaging host not found」エラー**
- `./clipmind-repair <Extension ID>` を再実行してください
- Chromeを完全に再起動してください

**YouTube の音声ダウンロードが失敗する（n-challenge / format not available）**

- 原因の多くは homebrew の `yt-dlp` が古いことです
- 更新: `brew upgrade yt-dlp`
- 確認: `./clipmind-repair` の `yt-dlp health:` ブロックでバージョンと status を確認
- パイプラインは回復可能な yt-dlp エラー時に自動で `brew upgrade yt-dlp` を1回試し、再実行します
- ログ: `cat /tmp/clipmind_status/*.log` または CLI の stderr 出力

**処理が開始されない・エラーになる**
- ログを確認: `cat /tmp/clipmind_status/*.log`
- ステータスを確認: `cat /tmp/clipmind_status/*.json`
- `.venv` が正しくセットアップされているか確認
- `.env` ファイルがプロジェクトルートにあるか確認

### ファイル構成（Chrome 関連）

```
chrome-extension/          # Chrome拡張本体
├── manifest.json          # Manifest V3 設定
├── background.js          # Service Worker（メニュー登録・NM通信）
└── icons/                 # アイコン
    ├── icon16.png
    ├── icon48.png
    └── icon128.png

native-host/               # Native Messaging Host
├── clipmind_host.py       # NMプロトコル処理（system pythonで動作）
├── clipmind_runner.py     # パイプライン実行（venvで動作）
├── com.clipmind.host.json # NMマニフェストテンプレート
└── install.sh             # レガシー: clipmind-repair へ委譲（新規は clipmind-repair を使用）
```

リポジトリ全体の構成は [リポジトリ構成（主要部分）](#リポジトリ構成主要部分) を参照してください。

---

## 🧠 動作イメージ

1. YouTubeのURLを入力（CLI / Alfred / Chrome拡張）
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


## 🤝 貢献方法

Pull Request・Issue・フィードバック歓迎！  
特に以下の貢献ポイントがあります：

- ローカルLLM対応の改善（Ollama / LM Studio）  
- Whisperモデル自動ダウンロード  
- RSSやGitHub Actionsとの連携  

---

## 🧩 開発メモ

- Alfred のログは `/tmp/clipmind.log` に出力されます。
- Chrome 拡張のジョブログは `/tmp/clipmind_status/` に出力されます。
- 出力ディレクトリは `.env` の `OUTROOT` で変更可能。  
- リポジトリ移動後は `./scripts/install-local.sh` と `clipmind-repair` でラッパー・Chrome 連携を更新します。
- `~/.local/bin` のラッパーだけ外すときは `./scripts/uninstall-local.sh`。
- `.venv/bin/activate` や `.venv/bin/pytest` が旧パスを保持する場合は `.venv` を再作成してください。
- Discord 投稿を無効にしたい場合は `.env` で `DISCORD_WEBHOOK_URL` を空欄に。

---

🧠 **ClipMind**  
_“Summarize the world’s knowledge, one clip at a time.”_
