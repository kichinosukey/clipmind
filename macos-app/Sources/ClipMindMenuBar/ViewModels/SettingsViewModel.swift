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

    func selectPreset(_ id: String) {
        config.activePresetId = id
        save()
    }

    func appPresetId(for appId: String) -> String {
        config.appProfiles[appId]?.activePresetId ?? ""
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
        config.appProfiles["clipmind"] = AppProfile(activePresetId: id, settings: .defaultClipMind)
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
