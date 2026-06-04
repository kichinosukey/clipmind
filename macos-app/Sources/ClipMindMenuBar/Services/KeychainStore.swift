import Foundation
import Security

protocol SecretStoring {
    func get(reference: String) throws -> String
    func set(reference: String, value: String) throws
    func delete(reference: String) throws
}

enum KeychainError: Error { case status(OSStatus), invalidData }

struct KeychainStore: SecretStoring {
    let service = "com.kichinosukey.clipmind"

    func get(reference: String) throws -> String {
        var query = base(reference)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess else { throw KeychainError.status(status) }
        guard let data = item as? Data, let value = String(data: data, encoding: .utf8) else {
            throw KeychainError.invalidData
        }
        return value
    }

    func set(reference: String, value: String) throws {
        try? delete(reference: reference)
        var query = base(reference)
        query[kSecValueData as String] = Data(value.utf8)
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else { throw KeychainError.status(status) }
    }

    func delete(reference: String) throws {
        let status = SecItemDelete(base(reference) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.status(status)
        }
    }

    private func base(_ reference: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: reference]
    }
}
