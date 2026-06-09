import SwiftUI

struct AutoSaveTextField: View {
    let title: String
    @Binding var text: String
    let onCommit: () -> Void

    @FocusState private var isFocused: Bool
    @State private var lastCommittedValue: String

    init(_ title: String, text: Binding<String>, onCommit: @escaping () -> Void) {
        self.title = title
        self._text = text
        self.onCommit = onCommit
        self._lastCommittedValue = State(initialValue: text.wrappedValue)
    }

    var body: some View {
        TextField(title, text: $text)
            .focused($isFocused)
            .onSubmit(commitIfNeeded)
            .onChange(of: isFocused) { focused in
                if !focused { commitIfNeeded() }
            }
    }

    private func commitIfNeeded() {
        guard text != lastCommittedValue else { return }
        lastCommittedValue = text
        onCommit()
    }
}

struct AutoSaveSecureField: View {
    let title: String
    @Binding var text: String
    let onCommit: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        SecureField(title, text: $text)
            .focused($isFocused)
            .onSubmit(onCommit)
            .onChange(of: isFocused) { focused in
                if !focused && !text.isEmpty { onCommit() }
            }
    }
}
