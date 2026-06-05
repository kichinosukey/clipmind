import SwiftUI

struct AppProfilesView: View {
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        Form {
            Text("Choose an app-specific LLM preset, or use Default to follow the global active preset.")
                .font(.caption)
                .foregroundStyle(.secondary)

            ForEach(settings.supportedApps) { app in
                Picker(app.name, selection: appPresetBinding(for: app.id)) {
                    Text("Default").tag("")
                    ForEach(settings.config.presets) { preset in
                        Text(preset.name).tag(preset.id)
                    }
                }
            }
        }
        .padding()
    }

    private func appPresetBinding(for appId: String) -> Binding<String> {
        Binding(
            get: { settings.appPresetId(for: appId) },
            set: { settings.setAppPresetId($0, for: appId) }
        )
    }
}
