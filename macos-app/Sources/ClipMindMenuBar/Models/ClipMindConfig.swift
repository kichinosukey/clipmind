import Foundation

struct ClipMindConfig: Codable, Equatable {
    var schemaVersion: Int
    var activePresetId: String
    var presets: [Preset]
    var shared: SharedSettings

    static let empty = ClipMindConfig(
        schemaVersion: 1, activePresetId: "", presets: [],
        shared: SharedSettings(
            whisperBinaryPath: "", whisperModelPath: "", outputRoot: "",
            enabledDestinations: [], discordWebhookRef: nil, slackWebhookRef: nil
        )
    )
}

struct Preset: Codable, Equatable, Identifiable {
    var id: String
    var name: String
    var baseURL: String
    var model: String
    var apiKeyRef: String
    var summarizeSystemPrompt: String
    var summarizeUserPrompt: String
    var translateSystemPrompt: String
    var translateUserPrompt: String
}

struct SharedSettings: Codable, Equatable {
    var whisperBinaryPath: String
    var whisperModelPath: String
    var outputRoot: String
    var enabledDestinations: [String]
    var discordWebhookRef: String?
    var slackWebhookRef: String?
}
