import SwiftUI

struct StatusView: View {
    @EnvironmentObject var jobs: JobMonitor

    var body: some View {
        Form {
            LabeledContent("実行中", value: "\(jobs.activeCount)")
            if let job = jobs.currentJob {
                LabeledContent("現在工程", value: job.stage.label)
                Text(job.title ?? job.sourceURL)
            }
            if let job = jobs.latestTerminalJob {
                LabeledContent("直近結果", value: job.stage.label)
                if let error = job.errorSummary { Text(error).foregroundStyle(.red) }
            }
        }.padding()
    }
}
