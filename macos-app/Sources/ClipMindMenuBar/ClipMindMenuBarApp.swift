import SwiftUI

@main
struct ClipMindMenuBarApp: App {
    @StateObject private var jobs = JobMonitor()
    @StateObject private var settings = SettingsViewModel()

    var body: some Scene {
        MenuBarExtra("ClipMind", systemImage: "text.badge.checkmark") {
            MenuContentView()
                .environmentObject(jobs)
                .environmentObject(settings)
        }
        Settings {
            SettingsView()
                .environmentObject(jobs)
                .environmentObject(settings)
        }
    }
}
