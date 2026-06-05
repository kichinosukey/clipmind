import SwiftUI

struct AppProfilesView: View {
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        Form {
            Text("Choose the LLM preset each app uses. App-specific settings stay with the app.")
                .font(.caption)
                .foregroundStyle(.secondary)

            Section("ClipMind") {
                Picker("LLM preset", selection: appPresetBinding(for: "clipmind")) {
                    Text("Default").tag("")
                    ForEach(settings.config.presets) { preset in
                        Text(preset.name).tag(preset.id)
                    }
                }
                TextField(
                    "Summary system prompt",
                    text: clipMindSettingsBinding(\.summarizeSystemPrompt)
                )
                TextField(
                    "Summary user prompt",
                    text: clipMindSettingsBinding(\.summarizeUserPrompt)
                )
                TextField(
                    "Translation system prompt",
                    text: clipMindSettingsBinding(\.translateSystemPrompt)
                )
                TextField(
                    "Translation user prompt",
                    text: clipMindSettingsBinding(\.translateUserPrompt)
                )
            }

            Section("Meeting Summary") {
                Picker("LLM preset", selection: appPresetBinding(for: "meeting-summary-local-llm")) {
                    Text("Default").tag("")
                    ForEach(settings.config.presets) { preset in
                        Text(preset.name).tag(preset.id)
                    }
                }
                TextField("Timeout", text: meetingSummaryIntBinding(\.timeout))
                TextField("Context length", text: meetingSummaryIntBinding(\.contextLength))
            }

            Button("Save") { settings.save() }
        }
        .padding()
    }

    private func appPresetBinding(for appId: String) -> Binding<String> {
        Binding(
            get: { settings.appPresetId(for: appId) },
            set: { settings.setAppPresetId($0, for: appId) }
        )
    }

    private func clipMindSettingsBinding(_ keyPath: WritableKeyPath<AppProfileSettings, String?>) -> Binding<String> {
        Binding(
            get: { settings.clipMindSettings[keyPath: keyPath] ?? "" },
            set: { value in
                var appSettings = settings.clipMindSettings
                appSettings[keyPath: keyPath] = value
                settings.clipMindSettings = appSettings
            }
        )
    }

    private func meetingSummaryIntBinding(_ keyPath: WritableKeyPath<AppProfileSettings, Int?>) -> Binding<String> {
        Binding(
            get: {
                settings.meetingSummarySettings[keyPath: keyPath].map(String.init) ?? ""
            },
            set: { value in
                var appSettings = settings.meetingSummarySettings
                appSettings[keyPath: keyPath] = Int(value)
                settings.meetingSummarySettings = appSettings
            }
        )
    }
}
