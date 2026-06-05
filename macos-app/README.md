# ClipMind Menu Bar

ClipMind の共有設定、macOS Keychain の秘密情報、実行状況を管理する SwiftUI Menu Bar アプリです。

```bash
swift run --package-path macos-app ClipMindMenuBar
```

設定は `~/Library/Application Support/ClipMind/config.json` に atomic write されます。API key と Webhook は Keychain service `com.kichinosukey.clipmind` に保存されます。
The LLM preset section is intentionally treated as a shared local AI preset contract. Other personal tools may read the active preset for `baseURL`, `model`, and `apiKeyRef` while ClipMind-specific settings such as Whisper paths, output root, and destinations remain ClipMind-owned.

開発時の確認:

```bash
swift test --package-path macos-app
swift build --package-path macos-app
```
