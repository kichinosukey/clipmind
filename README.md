# ClipMind

YouTube URL を Whisper.cpp で文字起こしし、OpenAI 互換 API で要約・翻訳して、必要に応じて Discord / Slack に投稿する macOS 向けツールです。

設定は Menu Bar アプリで管理します。CLI、Alfred、Chrome 右クリックのどこから実行しても、Apps 設定で ClipMind に割り当てた LLM プリセットを使用します。割り当てが未設定ならグローバルのアクティブプリセットに戻ります。Menu Bar アプリを終了していても処理は実行できます。

## 構成

```text
YouTube URL
  |
  +-- CLI: clipmind-run
  +-- Alfred
  +-- Chrome: 右クリック「clipmindで要約」
  |
  v
Python pipeline
  |-- yt-dlp / ffmpeg
  |-- Whisper.cpp 文字起こし
  |-- OpenAI互換API 要約・翻訳
  `-- Discord / Slack

Menu Bar app
  |-- プリセット・共通設定
  |-- Keychain の秘密情報
  `-- 実行状況
```

## 必要なもの

- macOS 13+
- Python 3.10+
- Xcode Command Line Tools / Swift
- `yt-dlp`
- `ffmpeg`
- Whisper.cpp の `whisper-cli` とモデル
- OpenAI 互換 API

```bash
brew install yt-dlp ffmpeg
```

## インストール

```bash
curl -fsSL https://raw.githubusercontent.com/kichinosukey/clipmind/main/install.sh | bash
```

既定では `~/.local/share/clipmind` に clone し、Python venv と `~/.local/bin/clipmind-run` / `clipmind-repair` を用意します。

手動セットアップ:

```bash
git clone https://github.com/kichinosukey/clipmind.git
cd clipmind
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./scripts/install-local.sh
```

## 初期設定

Whisper.cpp を準備します。

```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
./models/download-ggml-model.sh base.en
```

ClipMind の Menu Bar アプリを起動します。

```bash
swift run --package-path macos-app ClipMindMenuBar
```

設定画面で次を手作業で入力して保存します。

1. LLM Presets で OpenAI 互換 API の Base URL とモデルを設定する
2. API key を保存する
3. Apps で ClipMind / Meeting Summary それぞれに使う LLM プリセットを選び、ClipMind の要約・翻訳プロンプトや Meeting Summary の上限値を設定する
4. Shared で `whisper-cli`、Whisper モデル、出力先の絶対パスを設定する
5. 必要なら Discord / Slack を有効化し、Webhook を保存する

旧 `.env` は自動読込・自動移行されません。値を確認しながら Menu Bar アプリへ手作業で移してください。

通常設定は次に保存されます。

```text
~/Library/Application Support/ClipMind/config.json
```

API key と Webhook は JSON には保存されず、macOS Keychain の service `com.kichinosukey.clipmind` に保存されます。

## 実行

```bash
clipmind-run "https://www.youtube.com/watch?v=UF8uR6Z6KLc"
```

リポジトリ直下からは `./clipmind-run URL` でも実行できます。処理中の状態は以下に書き込まれ、Menu Bar アプリで確認できます。

```text
~/Library/Application Support/ClipMind/jobs/
```

## Chrome 右クリック

1. `chrome://extensions` でデベロッパーモードを有効化する
2. `chrome-extension/` を「パッケージ化されていない拡張機能」として読み込む
3. 表示された Extension ID を使って Native Messaging Host を設定する

```bash
clipmind-repair <extension-id>
```

Chrome を完全に再起動すると、YouTube ページまたは YouTube リンクの右クリックから「clipmindで要約」を実行できます。Chrome、Alfred、CLI はすべて共有設定の ClipMind 用 LLM プリセットを使います。

## Alfred

`./scripts/install-local.sh` の後に `clipmind-repair` を実行すると、既存の ClipMind Alfred Workflow の clone パスを更新します。Workflow からは PATH 上の `clipmind-run` を呼び出してください。

## 設定ファイル契約

`config.json` は秘密情報そのものではなく Keychain の参照名だけを保持します。

```json
{
  "schemaVersion": 1,
  "activePresetId": "quality",
  "presets": [
    {
      "id": "quality",
      "name": "Quality",
      "baseURL": "http://localhost:1234/v1",
      "model": "model-name",
      "apiKeyRef": "preset-quality-api-key"
    }
  ],
  "appProfiles": {
    "clipmind": {
      "activePresetId": "quality",
      "settings": {
        "summarizeSystemPrompt": "Summarize the transcript.",
        "summarizeUserPrompt": "{text}",
        "translateSystemPrompt": "Translate the summary into Japanese.",
        "translateUserPrompt": "{text}"
      }
    },
    "meeting-summary-local-llm": {
      "activePresetId": "",
      "settings": {
        "timeout": 120,
        "contextLength": 8192
      }
    }
  },
  "shared": {
    "whisperBinaryPath": "/absolute/path/to/whisper-cli",
    "whisperModelPath": "/absolute/path/to/ggml-base.en.bin",
    "outputRoot": "/absolute/path/to/clipmind-data",
    "enabledDestinations": [],
    "discordWebhookRef": null,
    "slackWebhookRef": null
  }
}
```

## 開発

```bash
.venv/bin/python -m pytest -q
swift test --package-path macos-app
swift build --package-path macos-app
```

詳細:

- [macOS app](macos-app/README.md)
- [設計](docs/superpowers/specs/2026-06-04-macos-menu-bar-management-design.md)
- [実装計画](docs/superpowers/plans/2026-06-04-macos-menu-bar-management.md)

## アンインストール

PATH ラッパーだけ削除:

```bash
./scripts/uninstall-local.sh
```

bootstrap インストールした clone も削除:

```bash
CLIPMIND_REMOVE_REPO=1 ./uninstall.sh
```
