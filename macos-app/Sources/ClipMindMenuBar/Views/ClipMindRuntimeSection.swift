import SwiftUI

struct ClipMindRuntimeSection: View {
    @EnvironmentObject var settings: SettingsViewModel
    @State private var discordWebhook = ""
    @State private var slackWebhook = ""

    var body: some View {
        Group {
            AutoSaveTextField("Whisper binary", text: $settings.config.shared.whisperBinaryPath) {
                settings.persistConfig()
            }
            AutoSaveTextField("Whisper model", text: $settings.config.shared.whisperModelPath) {
                settings.persistConfig()
            }
            AutoSaveTextField("Output root", text: $settings.config.shared.outputRoot) {
                settings.persistConfig()
            }
            Toggle("Discord", isOn: destination("discord"))
            AutoSaveSecureField("Discord webhook", text: $discordWebhook) {
                settings.commitDestinationSecret(
                    reference: "destination-discord-webhook",
                    value: discordWebhook,
                    assignTo: \.discordWebhookRef
                )
                discordWebhook = ""
            }
            Toggle("Slack", isOn: destination("slack"))
            AutoSaveSecureField("Slack webhook", text: $slackWebhook) {
                settings.commitDestinationSecret(
                    reference: "destination-slack-webhook",
                    value: slackWebhook,
                    assignTo: \.slackWebhookRef
                )
                slackWebhook = ""
            }
        }
    }

    private func destination(_ name: String) -> Binding<Bool> {
        Binding(
            get: { settings.config.shared.enabledDestinations.contains(name) },
            set: { enabled in
                settings.config.shared.enabledDestinations.removeAll { $0 == name }
                if enabled { settings.config.shared.enabledDestinations.append(name) }
                settings.persistConfig()
            }
        )
    }
}
