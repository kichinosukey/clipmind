import Foundation

enum ModelDiscoveryError: Error { case invalidURL, invalidResponse, status(Int) }

struct ModelDiscoveryClient {
    var session: URLSession = .shared

    func fetchModels(baseURL: String, apiKey: String) async throws -> [String] {
        guard var components = URLComponents(string: baseURL) else {
            throw ModelDiscoveryError.invalidURL
        }
        components.path = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/")) + "/models"
        guard let url = components.url else { throw ModelDiscoveryError.invalidURL }
        var request = URLRequest(url: url)
        if !apiKey.isEmpty { request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization") }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw ModelDiscoveryError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw ModelDiscoveryError.status(http.statusCode) }
        let decoded = try JSONDecoder().decode(ModelsResponse.self, from: data)
        return Array(Set(decoded.data.map(\.id))).sorted()
    }

    private struct ModelsResponse: Decodable {
        struct Model: Decodable { let id: String }
        let data: [Model]
    }
}
