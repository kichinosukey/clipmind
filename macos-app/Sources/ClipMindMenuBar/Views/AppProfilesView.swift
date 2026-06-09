import SwiftUI

struct AppProfilesView: View {
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Choose the LLM preset each app uses. App-specific settings stay with the app. ClipMind runtime paths and destinations now live under ClipMind → Runtime.")
                    .font(.callout)
                    .foregroundStyle(.secondary)

                GroupBox("ClipMind") {
                    Form {
                        Section("LLM") {
                            Picker("LLM preset", selection: appPresetBinding(for: "clipmind")) {
                                Text("Default").tag("")
                                ForEach(settings.config.presets) { preset in
                                    Text(preset.name).tag(preset.id)
                                }
                            }
                        }
                        Section("Prompts") {
                            AutoSaveTextField("Summary system prompt", text: clipMindSettingsBinding(\.summarizeSystemPrompt)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Summary user prompt", text: clipMindSettingsBinding(\.summarizeUserPrompt)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Translation system prompt", text: clipMindSettingsBinding(\.translateSystemPrompt)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Translation user prompt", text: clipMindSettingsBinding(\.translateUserPrompt)) {
                                settings.persistConfig()
                            }
                        }
                        Section("Runtime") {
                            ClipMindRuntimeSection()
                        }
                    }
                    .formStyle(.grouped)
                }

                GroupBox("Meeting Summary") {
                    Form {
                        Section("LLM") {
                            Picker("LLM preset", selection: appPresetBinding(for: "meeting-summary-local-llm")) {
                                Text("Default").tag("")
                                ForEach(settings.config.presets) { preset in
                                    Text(preset.name).tag(preset.id)
                                }
                            }
                        }
                        Section("Limits") {
                            AutoSaveTextField("Timeout", text: meetingSummaryIntBinding(\.timeout)) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Context length", text: meetingSummaryIntBinding(\.contextLength)) {
                                settings.persistConfig()
                            }
                        }
                    }
                    .formStyle(.grouped)
                }
            }
            .padding()
        }
        if let error = settings.errorMessage {
            Text(error).foregroundStyle(.red).padding()
        }
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
                let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
                var appSettings = settings.meetingSummarySettings
                appSettings[keyPath: keyPath] = trimmedValue.isEmpty ? nil : Int(trimmedValue)
                settings.meetingSummarySettings = appSettings
            }
        )
    }
}
