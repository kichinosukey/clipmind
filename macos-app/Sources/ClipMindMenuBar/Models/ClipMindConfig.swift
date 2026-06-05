import Foundation

struct ClipMindConfig: Codable, Equatable {
    var schemaVersion: Int
    var activePresetId: String
    var presets: [Preset]
    var appProfiles: [String: AppProfile]
    var shared: SharedSettings

    init(
        schemaVersion: Int,
        activePresetId: String,
        presets: [Preset],
        appProfiles: [String: AppProfile] = [:],
        shared: SharedSettings
    ) {
        self.schemaVersion = schemaVersion
        self.activePresetId = activePresetId
        self.presets = presets
        self.appProfiles = appProfiles
        self.shared = shared
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        activePresetId = try container.decode(String.self, forKey: .activePresetId)
        presets = try container.decode([Preset].self, forKey: .presets)
        appProfiles = try container.decodeIfPresent([String: AppProfile].self, forKey: .appProfiles) ?? [:]
        shared = try container.decode(SharedSettings.self, forKey: .shared)
    }

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

struct AppProfile: Codable, Equatable {
    var activePresetId: String
}

struct SharedSettings: Codable, Equatable {
    var whisperBinaryPath: String
    var whisperModelPath: String
    var outputRoot: String
    var enabledDestinations: [String]
    var discordWebhookRef: String?
    var slackWebhookRef: String?
}
