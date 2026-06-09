import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var jobs: JobMonitor
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        TabView(selection: $settings.selectedSettingsTab) {
            PresetEditorView()
                .tabItem { Label(SettingsTab.llmPresets.title, systemImage: SettingsTab.llmPresets.systemImage) }
                .tag(SettingsTab.llmPresets)

            AppProfilesView()
                .tabItem { Label(SettingsTab.apps.title, systemImage: SettingsTab.apps.systemImage) }
                .tag(SettingsTab.apps)

            ActivityView()
                .tabItem { Label(SettingsTab.activity.title, systemImage: SettingsTab.activity.systemImage) }
                .tag(SettingsTab.activity)
        }
        .frame(minWidth: 680, minHeight: 520)
    }
}
