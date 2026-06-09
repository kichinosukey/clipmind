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
}
