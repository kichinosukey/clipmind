import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    struct SupportedApp: Identifiable, Equatable {
        var id: String
        var name: String
    }

    @Published var config: ClipMindConfig
    @Published var errorMessage: String?
    @Published var discoveredModels: [String] = []
    @Published var selectedSettingsTab: SettingsTab = .llmPresets

    let supportedApps = [
        SupportedApp(id: "clipmind", name: "ClipMind"),
        SupportedApp(id: "meeting-summary-local-llm", name: "Meeting Summary")
    ]

    private let store: ConfigStore
    private let secrets: SecretStoring
    private let models: ModelDiscoveryClient

    init(
        store: ConfigStore = ConfigStore(),
        secrets: SecretStoring = KeychainStore(),
        models: ModelDiscoveryClient = ModelDiscoveryClient()
    ) {
        self.store = store
        self.secrets = secrets
        self.models = models
        self.config = (try? store.load()) ?? .empty
    }

    var activePreset: Preset? {
        config.presets.first { $0.id == config.activePresetId }
    }

    var clipMindSettings: AppProfileSettings {
        get {
            config.appProfiles["clipmind"]?.settings ?? .defaultClipMind
        }
        set {
            let activePresetId = config.appProfiles["clipmind"]?.activePresetId ?? ""
            config.appProfiles["clipmind"] = AppProfile(activePresetId: activePresetId, settings: newValue)
        }
    }

    var meetingSummarySettings: AppProfileSettings {
        get {
            config.appProfiles["meeting-summary-local-llm"]?.settings ?? AppProfileSettings()
        }
        set {
            let activePresetId = config.appProfiles["meeting-summary-local-llm"]?.activePresetId ?? ""
            config.appProfiles["meeting-summary-local-llm"] = AppProfile(
                activePresetId: activePresetId,
                settings: newValue
            )
        }
    }

    func selectPreset(_ id: String) {
        config.activePresetId = id
        save()
    }

    func appPresetId(for appId: String) -> String {
        config.appProfiles[appId]?.activePresetId ?? ""
    }

    func openSettings(tab: SettingsTab) {
        selectedSettingsTab = tab
    }

    func persistConfig() {
        save()
    }

    func presetDisplayName(for appId: String) -> String {
        let presetId = appPresetId(for: appId)
        guard !presetId.isEmpty,
              let preset = config.presets.first(where: { $0.id == presetId }) else {
            if let global = config.presets.first(where: { $0.id == config.activePresetId }) {
                return global.name
            }
            return "Default"
        }
        return preset.name
    }

    func setAppPresetId(_ presetId: String, for appId: String) {
        let settings = config.appProfiles[appId]?.settings
        config.appProfiles[appId] = AppProfile(activePresetId: presetId, settings: settings)
        save()
    }

    func addPreset() {
        let id = UUID().uuidString.lowercased()
        config.presets.append(Preset(
            id: id, name: "New Preset", baseURL: "http://localhost:1234/v1",
            model: "", apiKeyRef: "preset-\(id)-api-key"
        ))
        config.activePresetId = id
        if config.appProfiles["clipmind"] == nil {
            config.appProfiles["clipmind"] = AppProfile(activePresetId: "", settings: .defaultClipMind)
        }
    }

    func duplicatePreset(_ source: Preset) {
        let id = UUID().uuidString.lowercased()
        var copy = source
        copy.id = id
        copy.name = "\(source.name) Copy"
        copy.apiKeyRef = "preset-\(id)-api-key"
        config.presets.append(copy)
        config.activePresetId = id
    }

    func deletePreset(_ id: String) {
        guard config.presets.count > 1 else {
            errorMessage = "At least one preset is required"
            return
        }
        config.presets.removeAll { $0.id == id }
        if config.activePresetId == id { config.activePresetId = config.presets[0].id }
        for (appId, appProfile) in config.appProfiles where appProfile.activePresetId == id {
            config.appProfiles[appId] = AppProfile(activePresetId: "", settings: appProfile.settings)
        }
        save()
    }

    func save() {
        do { try store.save(config); errorMessage = nil }
        catch { errorMessage = error.localizedDescription }
    }

    func saveSecret(reference: String, value: String) {
        do { try secrets.set(reference: reference, value: value); errorMessage = nil }
        catch { errorMessage = String(describing: error) }
    }

    func commitPresetAPIKey(for preset: Preset, value: String) {
        guard !value.isEmpty else { return }
        saveSecret(reference: preset.apiKeyRef, value: value)
        persistConfig()
    }

    func commitDestinationSecret(reference: String, value: String, assignTo keyPath: WritableKeyPath<SharedSettings, String?>) {
        guard !value.isEmpty else { return }
        config.shared[keyPath: keyPath] = reference
        saveSecret(reference: reference, value: value)
        persistConfig()
    }

    func discoverModels() async {
        guard let preset = activePreset else { return }
        do {
            let key = try secrets.get(reference: preset.apiKeyRef)
            discoveredModels = try await models.fetchModels(baseURL: preset.baseURL, apiKey: key)
            errorMessage = nil
        } catch {
            errorMessage = "Connection failed: \(error)"
        }
    }
}
