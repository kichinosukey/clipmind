import XCTest
@testable import ClipMindMenuBar

@MainActor
final class SettingsHubUITests: XCTestCase {
    func testOpenSettingsTabUpdatesSelection() {
        let viewModel = SettingsViewModel()
        XCTAssertEqual(viewModel.selectedSettingsTab, .llmPresets)

        viewModel.openSettings(tab: .activity)

        XCTAssertEqual(viewModel.selectedSettingsTab, .activity)
    }

    func testPresetDisplayNameUsesDefaultForEmptyAppProfileSelection() {
        let viewModel = SettingsViewModel()
        let preset = Preset(
            id: "p1", name: "Local Gemma", baseURL: "http://localhost:1234/v1",
            model: "google/gemma-4-12b", apiKeyRef: "p1-key"
        )
        viewModel.config.presets = [preset]
        viewModel.config.appProfiles = [
            "clipmind": AppProfile(activePresetId: "", settings: .defaultClipMind)
        ]

        XCTAssertEqual(viewModel.presetDisplayName(for: "clipmind"), "Default")
        XCTAssertEqual(viewModel.presetDisplayName(for: "meeting-summary-local-llm"), "Default")
    }

    func testPersistConfigInvokesStoreSave() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let binary = root.appendingPathComponent("whisper")
        FileManager.default.createFile(atPath: binary.path, contents: Data())
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: binary.path)
        let model = root.appendingPathComponent("model.bin")
        FileManager.default.createFile(atPath: model.path, contents: Data())

        let store = ConfigStore(configURL: root.appendingPathComponent("config.json"))
        let viewModel = SettingsViewModel(store: store)
        viewModel.config = ClipMindConfig(
            schemaVersion: 1,
            activePresetId: "p1",
            presets: [Preset(
                id: "p1", name: "Quality", baseURL: "http://localhost:1234/v1",
                model: "model-a", apiKeyRef: "p1-key"
            )],
            appProfiles: ["clipmind": AppProfile(activePresetId: "p1", settings: .defaultClipMind)],
            shared: SharedSettings(
                whisperBinaryPath: binary.path, whisperModelPath: model.path,
                outputRoot: root.path, enabledDestinations: [],
                discordWebhookRef: nil, slackWebhookRef: nil
            )
        )

        viewModel.persistConfig()

        let loaded = try store.load()
        XCTAssertEqual(loaded.presets.first?.name, "Quality")
    }
}
