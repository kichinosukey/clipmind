import Foundation
import XCTest
@testable import ClipMindMenuBar

final class SharedContractTests: XCTestCase {
    private func fixture(_ name: String) -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("tests/fixtures/runtime/\(name)")
    }

    func testDecodesSharedConfigFixture() throws {
        let config = try JSONDecoder().decode(
            ClipMindConfig.self, from: Data(contentsOf: fixture("config-v1.json"))
        )
        XCTAssertEqual(config.activePresetId, "quality")
        XCTAssertEqual(config.presets.first?.model, "model-a")
    }

    func testPresetContractContainsExternalLLMFields() throws {
        let json = """
        {
          "schemaVersion": 1,
          "activePresetId": "preset-1",
          "presets": [
            {
              "id": "preset-1",
              "name": "Shared Local",
              "baseURL": "http://localhost:1234/v1",
              "model": "qwen3-8b-mlx",
              "apiKeyRef": "preset-1-api-key",
              "summarizeSystemPrompt": "",
              "summarizeUserPrompt": "",
              "translateSystemPrompt": "",
              "translateUserPrompt": ""
            }
          ],
          "shared": {
            "whisperBinaryPath": "/opt/homebrew/bin/whisper-cli",
            "whisperModelPath": "/tmp/ggml-base.en.bin",
            "outputRoot": "/tmp/out",
            "enabledDestinations": []
          }
        }
        """.data(using: .utf8)!

        let config = try JSONDecoder().decode(ClipMindConfig.self, from: json)
        let preset = try XCTUnwrap(config.presets.first)

        XCTAssertEqual(config.activePresetId, "preset-1")
        XCTAssertEqual(preset.baseURL, "http://localhost:1234/v1")
        XCTAssertEqual(preset.model, "qwen3-8b-mlx")
        XCTAssertEqual(preset.apiKeyRef, "preset-1-api-key")
    }

    func testDecodesConfigWithAppProfiles() throws {
        let json = """
        {
          "schemaVersion": 1,
          "activePresetId": "preset-1",
          "presets": [
            {
              "id": "preset-1",
              "name": "Shared Local",
              "baseURL": "http://localhost:1234/v1",
              "model": "qwen3-8b-mlx",
              "apiKeyRef": "preset-1-api-key",
              "summarizeSystemPrompt": "",
              "summarizeUserPrompt": "",
              "translateSystemPrompt": "",
              "translateUserPrompt": ""
            }
          ],
          "appProfiles": {
            "clipmind": {
              "activePresetId": "preset-1"
            },
            "meeting-summary-local-llm": {
              "activePresetId": ""
            }
          },
          "shared": {
            "whisperBinaryPath": "/opt/homebrew/bin/whisper-cli",
            "whisperModelPath": "/tmp/ggml-base.en.bin",
            "outputRoot": "/tmp/out",
            "enabledDestinations": []
          }
        }
        """.data(using: .utf8)!

        let config = try JSONDecoder().decode(ClipMindConfig.self, from: json)

        XCTAssertEqual(config.appProfiles["clipmind"], AppProfile(activePresetId: "preset-1"))
        XCTAssertEqual(config.appProfiles["meeting-summary-local-llm"], AppProfile(activePresetId: ""))
    }

    func testDecodesSharedJobFixtures() throws {
        let active = try JSONDecoder().decode(
            JobStatus.self, from: Data(contentsOf: fixture("job-active-v1.json"))
        )
        let failed = try JSONDecoder().decode(
            JobStatus.self, from: Data(contentsOf: fixture("job-failed-v1.json"))
        )
        XCTAssertEqual(active.stage, .transcribingWithWhisper)
        XCTAssertEqual(failed.failedStage, "summarizing")
    }
}

@MainActor
final class JobMonitorTests: XCTestCase {
    func testDerivesCurrentAndLatestTerminalJobs() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("tests/fixtures/runtime")
        try FileManager.default.copyItem(
            at: root.appendingPathComponent("job-active-v1.json"),
            to: directory.appendingPathComponent("active.json")
        )
        try FileManager.default.copyItem(
            at: root.appendingPathComponent("job-failed-v1.json"),
            to: directory.appendingPathComponent("failed.json")
        )

        let monitor = JobMonitor(jobsURL: directory, startPolling: false)

        XCTAssertEqual(monitor.activeCount, 1)
        XCTAssertEqual(monitor.currentJob?.jobId, "active-job")
        XCTAssertEqual(monitor.latestTerminalJob?.jobId, "failed-job")
    }
}
