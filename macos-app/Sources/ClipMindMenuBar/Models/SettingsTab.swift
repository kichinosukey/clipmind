import Foundation

enum SettingsTab: String, CaseIterable, Identifiable, Equatable {
    case llmPresets
    case apps
    case activity

    var id: String { rawValue }

    var title: String {
        switch self {
        case .llmPresets: "LLM Presets"
        case .apps: "Apps"
        case .activity: "Activity"
        }
    }

    var systemImage: String {
        switch self {
        case .llmPresets: "slider.horizontal.3"
        case .apps: "app.badge"
        case .activity: "waveform.path.ecg"
        }
    }
}
