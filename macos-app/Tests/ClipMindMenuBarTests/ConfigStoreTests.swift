import Foundation
import XCTest
@testable import ClipMindMenuBar

final class ConfigStoreTests: XCTestCase {
    private func validConfig() throws -> (ClipMindConfig, URL) {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let binary = root.appendingPathComponent("whisper")
        FileManager.default.createFile(atPath: binary.path, contents: Data())
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: binary.path)
        let model = root.appendingPathComponent("model.bin")
        FileManager.default.createFile(atPath: model.path, contents: Data())
        let id = "quality"
        let config = ClipMindConfig(
            schemaVersion: 1,
            activePresetId: id,
            presets: [Preset(
                id: id, name: "Quality", baseURL: "http://localhost:1234/v1",
                model: "model-a", apiKeyRef: "quality-api",
                summarizeSystemPrompt: "system", summarizeUserPrompt: "{text}",
                translateSystemPrompt: "system", translateUserPrompt: "{text}"
            )],
            shared: SharedSettings(
                whisperBinaryPath: binary.path, whisperModelPath: model.path,
                outputRoot: root.path, enabledDestinations: [],
                discordWebhookRef: nil, slackWebhookRef: nil
            )
        )
        return (config, root)
    }

    func testSaveAndLoadRoundTrip() throws {
        let (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = ConfigStore(configURL: root.appendingPathComponent("config.json"))

        try store.save(config)

        XCTAssertEqual(try store.load(), config)
    }

    func testValidationRejectsMissingActivePreset() {
        XCTAssertThrowsError(try ConfigStore.validate(.empty))
    }

    func testValidationRejectsEmptyPresetField() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        config.presets[0].model = " "

        XCTAssertThrowsError(try ConfigStore.validate(config))
    }

    func testValidationRequiresReferenceForEnabledDestination() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        config.shared.enabledDestinations = ["discord"]

        XCTAssertThrowsError(try ConfigStore.validate(config))
    }

    func testValidationRejectsDuplicateDestinations() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        config.shared.enabledDestinations = ["discord", "discord"]
        config.shared.discordWebhookRef = "discord-webhook"

        XCTAssertThrowsError(try ConfigStore.validate(config))
    }

    func testValidationAcceptsAppProfilePresetReferences() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        config.appProfiles = [
            "clipmind": AppProfile(activePresetId: config.activePresetId),
            "meeting-summary-local-llm": AppProfile(activePresetId: "")
        ]

        XCTAssertNoThrow(try ConfigStore.validate(config))
    }

    func testValidationRejectsMissingAppProfilePresetReference() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        config.appProfiles = [
            "clipmind": AppProfile(activePresetId: "missing")
        ]

        XCTAssertThrowsError(try ConfigStore.validate(config))
    }

    @MainActor
    func testDeletePresetClearsAppSpecificReference() throws {
        var (config, root) = try validConfig()
        defer { try? FileManager.default.removeItem(at: root) }
        let store = ConfigStore(configURL: root.appendingPathComponent("config.json"))
        let viewModel = SettingsViewModel(store: store)
        let first = try XCTUnwrap(config.presets.first)
        let second = Preset(
            id: "second", name: "Second", baseURL: "http://localhost:1234/v1",
            model: "model-b", apiKeyRef: "second-api",
            summarizeSystemPrompt: "summary", summarizeUserPrompt: "{text}",
            translateSystemPrompt: "translate", translateUserPrompt: "{text}"
        )
        config.presets.append(second)
        config.activePresetId = first.id
        config.appProfiles = [
            "clipmind": AppProfile(activePresetId: second.id)
        ]
        viewModel.config = config

        viewModel.deletePreset(second.id)

        XCTAssertEqual(viewModel.config.appProfiles["clipmind"], AppProfile(activePresetId: ""))
    }
}

@MainActor
final class SettingsViewModelTests: XCTestCase {
    func testDuplicatePresetCreatesIndependentIdentityAndSelectsIt() {
        let viewModel = SettingsViewModel()
        let source = Preset(
            id: "source", name: "Quality", baseURL: "http://localhost:1234/v1",
            model: "model-a", apiKeyRef: "source-api",
            summarizeSystemPrompt: "summary", summarizeUserPrompt: "{text}",
            translateSystemPrompt: "translate", translateUserPrompt: "{text}"
        )
        viewModel.config.presets = [source]
        viewModel.config.activePresetId = source.id

        viewModel.duplicatePreset(source)

        XCTAssertEqual(viewModel.config.presets.count, 2)
        XCTAssertNotEqual(viewModel.config.presets[1].id, source.id)
        XCTAssertNotEqual(viewModel.config.presets[1].apiKeyRef, source.apiKeyRef)
        XCTAssertEqual(viewModel.config.activePresetId, viewModel.config.presets[1].id)
    }
}
