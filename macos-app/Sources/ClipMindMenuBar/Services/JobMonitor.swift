import Combine
import Foundation

@MainActor
final class JobMonitor: ObservableObject {
    @Published private(set) var activeCount = 0
    @Published private(set) var currentJob: JobStatus?
    @Published private(set) var latestTerminalJob: JobStatus?
    let jobsURL: URL
    private var timer: Timer?

    init(jobsURL: URL = RuntimePaths.jobs, startPolling: Bool = true) {
        self.jobsURL = jobsURL
        reload()
        if startPolling {
            timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
                Task { @MainActor in self?.reload() }
            }
        }
    }

    func reload() {
        let urls = (try? FileManager.default.contentsOfDirectory(
            at: jobsURL, includingPropertiesForKeys: nil
        )) ?? []
        let decoder = JSONDecoder()
        let jobs = urls.filter { $0.pathExtension == "json" }.compactMap {
            try? decoder.decode(JobStatus.self, from: Data(contentsOf: $0))
        }
        let active = jobs.filter { !$0.stage.isTerminal }.sorted { $0.updatedAt > $1.updatedAt }
        let terminal = jobs.filter(\.stage.isTerminal).sorted { $0.updatedAt > $1.updatedAt }
        activeCount = active.count
        currentJob = active.first
        latestTerminalJob = terminal.first
    }
}
