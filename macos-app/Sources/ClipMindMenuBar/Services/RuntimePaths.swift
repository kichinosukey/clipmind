import Foundation

enum RuntimePaths {
    static let applicationSupport = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/ClipMind")
    static let config = applicationSupport.appendingPathComponent("config.json")
    static let jobs = applicationSupport.appendingPathComponent("jobs")
}
