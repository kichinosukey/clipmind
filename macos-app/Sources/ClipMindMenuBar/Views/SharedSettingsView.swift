import SwiftUI

struct SharedSettingsView: View {
    @EnvironmentObject var settings: SettingsViewModel
    @State private var discordWebhook = ""
    @State private var slackWebhook = ""

    var body: some View {
        Form {
            TextField("Whisper binary", text: $settings.config.shared.whisperBinaryPath)
            TextField("Whisper model", text: $settings.config.shared.whisperModelPath)
            TextField("Output root", text: $settings.config.shared.outputRoot)
            Toggle("Discord", isOn: destination("discord"))
            SecureField("Discord webhook", text: $discordWebhook)
            Button("Save Discord webhook") {
                let reference = "destination-discord-webhook"
                settings.config.shared.discordWebhookRef = reference
                settings.saveSecret(reference: reference, value: discordWebhook)
                discordWebhook = ""
            }
            Toggle("Slack", isOn: destination("slack"))
            SecureField("Slack webhook", text: $slackWebhook)
            Button("Save Slack webhook") {
                let reference = "destination-slack-webhook"
                settings.config.shared.slackWebhookRef = reference
                settings.saveSecret(reference: reference, value: slackWebhook)
                slackWebhook = ""
            }
            Button("Save") { settings.save() }
        }.padding()
    }

    private func destination(_ name: String) -> Binding<Bool> {
        Binding(
            get: { settings.config.shared.enabledDestinations.contains(name) },
            set: { enabled in
                settings.config.shared.enabledDestinations.removeAll { $0 == name }
                if enabled { settings.config.shared.enabledDestinations.append(name) }
            }
        )
    }
}
