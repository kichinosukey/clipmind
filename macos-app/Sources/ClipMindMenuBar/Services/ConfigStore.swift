import Foundation

enum ConfigStoreError: Error, LocalizedError {
    case invalid(String)
    var errorDescription: String? {
        if case let .invalid(message) = self { message } else { nil }
    }
}

struct ConfigStore {
    var configURL: URL = RuntimePaths.config

    func load() throws -> ClipMindConfig {
        try JSONDecoder().decode(ClipMindConfig.self, from: Data(contentsOf: configURL))
    }

    func save(_ config: ClipMindConfig) throws {
        try Self.validate(config)
        try FileManager.default.createDirectory(
            at: configURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(config).write(to: configURL, options: .atomic)
    }

    static func validate(_ config: ClipMindConfig) throws {
        guard config.schemaVersion == 1 else { throw ConfigStoreError.invalid("schemaVersion must be 1") }
        guard !config.presets.isEmpty else { throw ConfigStoreError.invalid("At least one preset is required") }
        guard Set(config.presets.map(\.id)).count == config.presets.count else {
            throw ConfigStoreError.invalid("Preset IDs must be unique")
        }
        let requiredPresetFields: [(Preset) -> String] = [
            \.id, \.name, \.baseURL, \.model, \.apiKeyRef,
        ]
        guard config.presets.allSatisfy({ preset in
            requiredPresetFields.allSatisfy { !$0(preset).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        }) else {
            throw ConfigStoreError.invalid("Preset fields must not be empty")
        }
        guard config.presets.contains(where: { $0.id == config.activePresetId }) else {
            throw ConfigStoreError.invalid("Active preset is missing")
        }
        let presetIds = Set(config.presets.map(\.id))
        for appProfile in config.appProfiles.values where !appProfile.activePresetId.isEmpty {
            guard presetIds.contains(appProfile.activePresetId) else {
                throw ConfigStoreError.invalid("App profile preset is missing")
            }
        }
        let supported = Set(["discord", "slack"])
        guard Set(config.shared.enabledDestinations).count == config.shared.enabledDestinations.count else {
            throw ConfigStoreError.invalid("Destinations must be unique")
        }
        guard Set(config.shared.enabledDestinations).isSubset(of: supported) else {
            throw ConfigStoreError.invalid("Unsupported destination")
        }
        if config.shared.enabledDestinations.contains("discord") {
            guard let reference = config.shared.discordWebhookRef,
                  !reference.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw ConfigStoreError.invalid("Discord webhook reference is required")
            }
        }
        if config.shared.enabledDestinations.contains("slack") {
            guard let reference = config.shared.slackWebhookRef,
                  !reference.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw ConfigStoreError.invalid("Slack webhook reference is required")
            }
        }
        guard FileManager.default.isExecutableFile(atPath: config.shared.whisperBinaryPath) else {
            throw ConfigStoreError.invalid("Whisper binary is not executable")
        }
        guard FileManager.default.fileExists(atPath: config.shared.whisperModelPath) else {
            throw ConfigStoreError.invalid("Whisper model is missing")
        }
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: config.shared.outputRoot, isDirectory: &isDirectory),
              isDirectory.boolValue else {
            throw ConfigStoreError.invalid("Output directory is missing")
        }
    }
}
