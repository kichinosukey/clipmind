import SwiftUI

struct PresetEditorView: View {
    @EnvironmentObject var settings: SettingsViewModel
    @State private var apiKey = ""
    @State private var presetPendingDeletion: Preset?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 0) {
                List(selection: activePresetSelection) {
                    ForEach(settings.config.presets) { preset in
                        Text(preset.name)
                            .tag(preset.id)
                            .contextMenu {
                                Button("Duplicate") { settings.duplicatePreset(preset) }
                                Button("Delete…", role: .destructive) {
                                    presetPendingDeletion = preset
                                }
                            }
                    }
                }
                .frame(width: 180)
                .overlay(alignment: .topTrailing) {
                    Button(action: settings.addPreset) {
                        Image(systemName: "plus")
                    }
                    .buttonStyle(.borderless)
                    .help("Add Preset")
                    .padding(8)
                }

                if let index = selectedPresetIndex {
                    Form {
                        Section {
                            Text("LLM presets are shared connection settings. App-specific prompts and limits live under Apps.")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }

                        Section("Connection") {
                            AutoSaveTextField("Name", text: $settings.config.presets[index].name) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Base URL", text: $settings.config.presets[index].baseURL) {
                                settings.persistConfig()
                            }
                            AutoSaveTextField("Model", text: $settings.config.presets[index].model) {
                                settings.persistConfig()
                            }
                            if !settings.discoveredModels.isEmpty {
                                Picker("Discovered model", selection: $settings.config.presets[index].model) {
                                    ForEach(settings.discoveredModels, id: \.self) { Text($0).tag($0) }
                                }
                                .onChange(of: settings.config.presets[index].model) { _ in
                                    settings.persistConfig()
                                }
                            }
                            AutoSaveSecureField("API key", text: $apiKey) {
                                settings.commitPresetAPIKey(for: settings.config.presets[index], value: apiKey)
                                apiKey = ""
                            }
                        }

                        Section {
                            Button("接続を確認") {
                                Task { await settings.discoverModels() }
                            }
                            .buttonStyle(.link)
                        }
                    }
                    .formStyle(.grouped)
                    .padding()
                } else {
                    VStack(spacing: 8) {
                        Image(systemName: "slider.horizontal.3")
                            .font(.largeTitle)
                            .foregroundStyle(.secondary)
                        Text("No Preset Selected")
                            .font(.headline)
                        Text("Create a preset with the plus button in the sidebar.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            if let error = settings.errorMessage {
                Text(error).foregroundStyle(.red).padding()
            }
        }
        .alert(
            "Delete Preset?",
            isPresented: Binding(
                get: { presetPendingDeletion != nil },
                set: { if !$0 { presetPendingDeletion = nil } }
            ),
            presenting: presetPendingDeletion
        ) { preset in
            Button("Delete", role: .destructive) {
                settings.deletePreset(preset.id)
                presetPendingDeletion = nil
            }
            Button("Cancel", role: .cancel) {
                presetPendingDeletion = nil
            }
        } message: { preset in
            Text("“\(preset.name)” will be removed. App profiles using this preset will fall back to the global default.")
        }
    }

    private var activePresetSelection: Binding<String> {
        Binding(
            get: { settings.config.activePresetId },
            set: { settings.selectPreset($0) }
        )
    }

    private var selectedPresetIndex: Int? {
        settings.config.presets.firstIndex { $0.id == settings.config.activePresetId }
    }
}
