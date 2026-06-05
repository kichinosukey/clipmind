# ClipMind Menu Bar

ClipMind の共有設定、macOS Keychain の秘密情報、実行状況を管理する SwiftUI Menu Bar アプリです。

```bash
swift run --package-path macos-app ClipMindMenuBar
```

設定は `~/Library/Application Support/ClipMind/config.json` に atomic write されます。API key と Webhook は Keychain service `com.kichinosukey.clipmind` に保存されます。
The LLM preset section is a shared local AI connection contract. Other personal tools may read `baseURL`, `model`, and `apiKeyRef` from the selected preset. App-specific settings, including ClipMind prompts and Meeting Summary limits, live under `appProfiles.<appId>.settings`.

開発時の確認:

```bash
swift test --package-path macos-app
swift build --package-path macos-app
```
