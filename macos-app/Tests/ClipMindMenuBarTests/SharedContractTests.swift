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
