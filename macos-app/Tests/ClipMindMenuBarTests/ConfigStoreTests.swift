import Foundation
import XCTest
@testable import ClipMindMenuBar

final class ConfigStoreTests: XCTestCase {
    func testSaveAndLoadRoundTrip() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let binary = root.appendingPathComponent("whisper")
        FileManager.default.createFile(atPath: binary.path, contents: Data())
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: binary.path)
        let model = root.appendingPathComponent("model.bin")
        FileManager.default.createFile(atPath: model.path, contents: Data())
        var config = ClipMindConfig.empty
        let id = "quality"
        config.activePresetId = id
        config.presets = [Preset(
            id: id, name: "Quality", baseURL: "http://localhost:1234/v1",
            model: "model-a", apiKeyRef: "quality-api",
            summarizeSystemPrompt: "system", summarizeUserPrompt: "{text}",
            translateSystemPrompt: "system", translateUserPrompt: "{text}"
        )]
        config.shared.whisperBinaryPath = binary.path
        config.shared.whisperModelPath = model.path
        config.shared.outputRoot = root.path
        let store = ConfigStore(configURL: root.appendingPathComponent("config.json"))

        try store.save(config)

        XCTAssertEqual(try store.load(), config)
    }

    func testValidationRejectsMissingActivePreset() {
        XCTAssertThrowsError(try ConfigStore.validate(.empty))
    }
}
