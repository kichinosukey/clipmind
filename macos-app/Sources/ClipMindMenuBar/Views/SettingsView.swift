import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var jobs: JobMonitor
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        TabView {
            PresetEditorView().tabItem { Label("LLM Presets", systemImage: "slider.horizontal.3") }
            AppProfilesView().tabItem { Label("Apps", systemImage: "app.badge") }
            SharedSettingsView().tabItem { Label("Shared", systemImage: "gearshape") }
            StatusView().tabItem { Label("Status", systemImage: "waveform.path.ecg") }
        }
        .frame(minWidth: 680, minHeight: 520)
    }
}
