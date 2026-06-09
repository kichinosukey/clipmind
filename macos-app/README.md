# ClipMind Menu Bar

ClipMind の共有設定、macOS Keychain の秘密情報、実行状況を管理する SwiftUI Menu Bar アプリです。

```bash
swift run --package-path macos-app ClipMindMenuBar
```

設定は `~/Library/Application Support/ClipMind/config.json` に atomic write されます。API key と Webhook は Keychain service `com.kichinosukey.clipmind` に保存されます。
Settings tabs:

- `LLM Presets` — shared LLM connection templates (`baseURL`, `model`, `apiKeyRef`)
- `Apps` — per-app preset selection and owned settings
  - `ClipMind` prompts and runtime/output/destination settings
  - `Meeting Summary` timeout and context length
- `Activity` — current and recent ClipMind job status

The menu bar popover provides per-app preset quick switching and a one-line activity summary. Changes persist automatically; routine Save buttons are not used.

開発時の確認:

```bash
swift test --package-path macos-app
swift build --package-path macos-app
```
