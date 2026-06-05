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

        var clipMindProfile = appProfiles["clipmind"] ?? AppProfile(activePresetId: activePresetId)
        let clipMindPresetId = clipMindProfile.activePresetId.isEmpty ? activePresetId : clipMindProfile.activePresetId
        if clipMindProfile.settings == nil,
           let legacySettings = presets.first(where: { $0.id == clipMindPresetId })?.legacyClipMindSettings {
            clipMindProfile.settings = legacySettings
            appProfiles["clipmind"] = clipMindProfile
        }
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
    var legacyClipMindSettings: AppProfileSettings?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case baseURL
        case model
        case apiKeyRef
        case summarizeSystemPrompt
        case summarizeUserPrompt
        case translateSystemPrompt
        case translateUserPrompt
    }

    init(
        id: String,
        name: String,
        baseURL: String,
        model: String,
        apiKeyRef: String,
        legacyClipMindSettings: AppProfileSettings? = nil
    ) {
        self.id = id
        self.name = name
        self.baseURL = baseURL
        self.model = model
        self.apiKeyRef = apiKeyRef
        self.legacyClipMindSettings = legacyClipMindSettings
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        baseURL = try container.decode(String.self, forKey: .baseURL)
        model = try container.decode(String.self, forKey: .model)
        apiKeyRef = try container.decode(String.self, forKey: .apiKeyRef)

        let settings = AppProfileSettings(
            summarizeSystemPrompt: try container.decodeIfPresent(String.self, forKey: .summarizeSystemPrompt),
            summarizeUserPrompt: try container.decodeIfPresent(String.self, forKey: .summarizeUserPrompt),
            translateSystemPrompt: try container.decodeIfPresent(String.self, forKey: .translateSystemPrompt),
            translateUserPrompt: try container.decodeIfPresent(String.self, forKey: .translateUserPrompt)
        )
        legacyClipMindSettings = settings.hasClipMindPrompts ? settings : nil
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(baseURL, forKey: .baseURL)
        try container.encode(model, forKey: .model)
        try container.encode(apiKeyRef, forKey: .apiKeyRef)
    }
}

struct AppProfile: Codable, Equatable {
    var activePresetId: String
    var settings: AppProfileSettings?

    init(activePresetId: String, settings: AppProfileSettings? = nil) {
        self.activePresetId = activePresetId
        self.settings = settings
    }
}

struct AppProfileSettings: Codable, Equatable {
    var summarizeSystemPrompt: String?
    var summarizeUserPrompt: String?
    var translateSystemPrompt: String?
    var translateUserPrompt: String?
    var timeout: Int?
    var contextLength: Int?

    init(
        summarizeSystemPrompt: String? = nil,
        summarizeUserPrompt: String? = nil,
        translateSystemPrompt: String? = nil,
        translateUserPrompt: String? = nil,
        timeout: Int? = nil,
        contextLength: Int? = nil
    ) {
        self.summarizeSystemPrompt = summarizeSystemPrompt
        self.summarizeUserPrompt = summarizeUserPrompt
        self.translateSystemPrompt = translateSystemPrompt
        self.translateUserPrompt = translateUserPrompt
        self.timeout = timeout
        self.contextLength = contextLength
    }

    var hasClipMindPrompts: Bool {
        summarizeSystemPrompt != nil ||
            summarizeUserPrompt != nil ||
            translateSystemPrompt != nil ||
            translateUserPrompt != nil
    }

    static let defaultClipMind = AppProfileSettings(
        summarizeSystemPrompt: "Summarize the transcript.",
        summarizeUserPrompt: "{text}",
        translateSystemPrompt: "Translate the summary into Japanese.",
        translateUserPrompt: "{text}"
    )
}

struct SharedSettings: Codable, Equatable {
    var whisperBinaryPath: String
    var whisperModelPath: String
    var outputRoot: String
    var enabledDestinations: [String]
    var discordWebhookRef: String?
    var slackWebhookRef: String?
}
