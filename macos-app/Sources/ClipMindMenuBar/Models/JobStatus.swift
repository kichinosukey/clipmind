import Foundation

enum JobStage: String, Codable {
    case queued
    case downloadingAudio = "downloading_audio"
    case transcribingWithWhisper = "transcribing_with_whisper"
    case summarizing, translating, delivering, completed, failed

    var label: String {
        switch self {
        case .queued: "待機中"
        case .downloadingAudio: "音声をダウンロード中"
        case .transcribingWithWhisper: "Whisperで文字起こし中"
        case .summarizing: "要約中"
        case .translating: "翻訳中"
        case .delivering: "投稿中"
        case .completed: "完了"
        case .failed: "失敗"
        }
    }

    var isTerminal: Bool { self == .completed || self == .failed }
}

struct JobStatus: Codable, Equatable, Identifiable {
    var schemaVersion: Int
    var jobId: String
    var sourceURL: String
    var title: String?
    var stage: JobStage
    var startedAt: String
    var updatedAt: String
    var completedAt: String?
    var failedStage: String?
    var errorSummary: String?
    var deliveryResults: [String: String]?
    var id: String { jobId }
}
