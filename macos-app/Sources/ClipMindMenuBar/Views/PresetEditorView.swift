import SwiftUI

struct PresetEditorView: View {
    @EnvironmentObject var settings: SettingsViewModel
    @State private var apiKey = ""

    var body: some View {
        HStack {
            List(selection: $settings.config.activePresetId) {
                ForEach(settings.config.presets) { Text($0.name).tag($0.id) }
            }
            .frame(width: 180)
            VStack(alignment: .leading) {
                Text("LLM presets are shared by ClipMind and other personal local AI tools.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if let index = settings.config.presets.firstIndex(where: {
                    $0.id == settings.config.activePresetId
                }) {
                    TextField("Name", text: $settings.config.presets[index].name)
                    TextField("Base URL", text: $settings.config.presets[index].baseURL)
                    TextField("Model", text: $settings.config.presets[index].model)
                    if !settings.discoveredModels.isEmpty {
                        Picker("Discovered model", selection: $settings.config.presets[index].model) {
                            ForEach(settings.discoveredModels, id: \.self) { Text($0).tag($0) }
                        }
                    }
                    SecureField("API key", text: $apiKey)
                    Text("Summary system prompt")
                    TextEditor(text: clipMindPromptBinding(\.summarizeSystemPrompt))
                    Text("Summary user prompt")
                    TextEditor(text: clipMindPromptBinding(\.summarizeUserPrompt))
                    Text("Translation system prompt")
                    TextEditor(text: clipMindPromptBinding(\.translateSystemPrompt))
                    Text("Translation user prompt")
                    TextEditor(text: clipMindPromptBinding(\.translateUserPrompt))
                    HStack {
                        Button("Test Connection") { Task { await settings.discoverModels() } }
                        Button("Save API Key") {
                            settings.saveSecret(
                                reference: settings.config.presets[index].apiKeyRef,
                                value: apiKey
                            )
                            apiKey = ""
                        }
                        Button("Save") { settings.save() }
                        Button("Duplicate") {
                            settings.duplicatePreset(settings.config.presets[index])
                        }
                        Button("Delete") { settings.deletePreset(settings.config.presets[index].id) }
                    }
                } else {
                    Button("Create first preset") { settings.addPreset() }
                }
                Button("Add Preset") { settings.addPreset() }
                if let error = settings.errorMessage { Text(error).foregroundStyle(.red) }
            }.padding()
        }
    }

    private func clipMindPromptBinding(_ keyPath: WritableKeyPath<AppProfileSettings, String?>) -> Binding<String> {
        Binding(
            get: {
                settings.config.appProfiles["clipmind"]?.settings?[keyPath: keyPath] ?? ""
            },
            set: { value in
                var profile = settings.config.appProfiles["clipmind"] ?? AppProfile(
                    activePresetId: settings.config.activePresetId,
                    settings: .defaultClipMind
                )
                var appSettings = profile.settings ?? .defaultClipMind
                appSettings[keyPath: keyPath] = value
                profile.settings = appSettings
                settings.config.appProfiles["clipmind"] = profile
            }
        )
    }
}
