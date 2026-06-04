import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var config: ClipMindConfig
    @Published var errorMessage: String?
    @Published var discoveredModels: [String] = []

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

    func addPreset() {
        let id = UUID().uuidString.lowercased()
        config.presets.append(Preset(
            id: id, name: "New Preset", baseURL: "http://localhost:1234/v1",
            model: "", apiKeyRef: "preset-\(id)-api-key",
            summarizeSystemPrompt: "", summarizeUserPrompt: "{text}",
            translateSystemPrompt: "", translateUserPrompt: "{text}"
        ))
        config.activePresetId = id
    }

    func deletePreset(_ id: String) {
        guard config.presets.count > 1 else {
            errorMessage = "At least one preset is required"
            return
        }
        config.presets.removeAll { $0.id == id }
        if config.activePresetId == id { config.activePresetId = config.presets[0].id }
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
