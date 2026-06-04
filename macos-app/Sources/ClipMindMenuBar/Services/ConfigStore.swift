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
        guard Set(config.presets.map(\.id)).count == config.presets.count else {
            throw ConfigStoreError.invalid("Preset IDs must be unique")
        }
        guard config.presets.contains(where: { $0.id == config.activePresetId }) else {
            throw ConfigStoreError.invalid("Active preset is missing")
        }
        let supported = Set(["discord", "slack"])
        guard Set(config.shared.enabledDestinations).isSubset(of: supported) else {
            throw ConfigStoreError.invalid("Unsupported destination")
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
