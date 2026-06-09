import AppKit
import SwiftUI

struct MenuContentView: View {
    @EnvironmentObject var jobs: JobMonitor
    @EnvironmentObject var settings: SettingsViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var openSettingsAction: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(settings.supportedApps) { app in
                LabeledContent(app.name) {
                    Picker("LLM preset", selection: appPresetBinding(for: app.id)) {
                        Text("Default").tag("")
                        ForEach(settings.config.presets) { preset in
                            Text(preset.name).tag(preset.id)
                        }
                    }
                    .labelsHidden()
                    .frame(maxWidth: 180)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }

            Divider()

            Button(action: openActivityTab) {
                HStack(spacing: 6) {
                    Image(systemName: jobs.activeCount > 0 ? "circle.fill" : "circle")
                        .font(.caption)
                        .foregroundStyle(jobs.activeCount > 0 ? .green : .secondary)
                    Text(activitySummary)
                        .font(.callout)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityHint("Opens Settings on the Activity tab")
            .padding(.horizontal, 12)
            .padding(.vertical, 10)

            Divider()

            VStack(spacing: 4) {
                Button("設定を開く…", action: openSettingsTab)
                Button("終了") { NSApplication.shared.terminate(nil) }
            }
            .padding(12)
        }
        .frame(width: 300)
        .background {
            if #available(macOS 14.0, *) {
                OpenSettingsCapture(action: $openSettingsAction)
            }
        }
    }

    private var activitySummary: String {
        let running = "実行中 \(jobs.activeCount)"
        if let recent = jobs.latestTerminalJob {
            let title = recent.title ?? recent.sourceURL
            return "\(running)  ·  直近: \(recent.stage.label) \(title)"
        }
        return running
    }

    private func appPresetBinding(for appId: String) -> Binding<String> {
        Binding(
            get: { settings.appPresetId(for: appId) },
            set: { settings.setAppPresetId($0, for: appId) }
        )
    }

    private func openSettingsTab() {
        settings.openSettings(tab: .llmPresets)
        presentSettings()
    }

    private func openActivityTab() {
        settings.openSettings(tab: .activity)
        presentSettings()
    }

    private func presentSettings() {
        dismiss()
        NSApplication.shared.setActivationPolicy(.regular)
        NSApplication.shared.activate(ignoringOtherApps: true)
        if #available(macOS 14.0, *), let openSettingsAction {
            openSettingsAction()
        } else {
            NSApplication.shared.sendAction(
                Selector(("showSettingsWindow:")), to: nil, from: nil
            )
        }
        DispatchQueue.main.async {
            NSApplication.shared.activate(ignoringOtherApps: true)
        }
    }
}

@available(macOS 14.0, *)
private struct OpenSettingsCapture: View {
    @Environment(\.openSettings) private var openSettings
    @Binding var action: (() -> Void)?

    var body: some View {
        Color.clear
            .onAppear { action = { openSettings() } }
    }
}
