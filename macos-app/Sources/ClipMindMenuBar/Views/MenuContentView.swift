import AppKit
import SwiftUI

struct MenuContentView: View {
    @EnvironmentObject var jobs: JobMonitor
    @EnvironmentObject var settings: SettingsViewModel

    var body: some View {
        Picker("プリセット", selection: Binding(
            get: { settings.config.activePresetId },
            set: { settings.selectPreset($0) }
        )) {
            ForEach(settings.config.presets) { Text($0.name).tag($0.id) }
        }
        Divider()
        if let job = jobs.currentJob {
            Text("\(job.stage.label): \(job.title ?? job.sourceURL)")
        } else {
            Text("実行中: \(jobs.activeCount)")
        }
        if let recent = jobs.latestTerminalJob {
            Text("直近: \(recent.stage.label) \(recent.title ?? "")")
        }
        Divider()
        if #available(macOS 14.0, *) {
            OpenSettingsMenuItem()
        } else {
            Button("設定を開く...") {
                NSApplication.shared.sendAction(
                    Selector(("showSettingsWindow:")), to: nil, from: nil
                )
                NSApplication.shared.activate(ignoringOtherApps: true)
            }
        }
        Button("終了") { NSApplication.shared.terminate(nil) }
    }
}

@available(macOS 14.0, *)
private struct OpenSettingsMenuItem: View {
    @Environment(\.openSettings) private var openSettings

    var body: some View {
        Button("設定を開く...") {
            NSApplication.shared.setActivationPolicy(.regular)
            NSApplication.shared.activate(ignoringOtherApps: true)
            openSettings()
            DispatchQueue.main.async {
                NSApplication.shared.activate(ignoringOtherApps: true)
            }
        }
    }
}
