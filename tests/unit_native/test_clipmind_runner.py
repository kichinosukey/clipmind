"""Tests for native-host/clipmind_runner.py."""


class TestNotify:
    def test_notify_calls_osascript(self, mocker):
        import clipmind_runner

        run = mocker.patch("clipmind_runner.subprocess.run")
        clipmind_runner.notify("Test Title", "Test Message")
        assert run.call_args.args[0][0:2] == ["osascript", "-e"]

    def test_notify_silences_exception(self, mocker):
        import clipmind_runner

        mocker.patch("clipmind_runner.subprocess.run", side_effect=OSError("missing"))
        clipmind_runner.notify("Title", "Message")


class TestMain:
    def test_main_uses_shared_config_and_host_job_id(
        self, mocker, runtime_config, tmp_path
    ):
        import clipmind_runner

        mocker.patch(
            "sys.argv",
            ["clipmind_runner.py", "https://youtu.be/abc", "host-job-id", "discord"],
        )
        mocker.patch("clipmind_runner.os.chdir")
        mocker.patch("clipmind_runner.JOBS_DIR", tmp_path)
        mocker.patch("clipmind_runner.load_runtime_config", return_value=runtime_config)
        reporter = mocker.patch("clipmind_runner.JobStatusStore")
        run_pipeline = mocker.patch(
            "clipmind.pipeline.run_pipeline", return_value={"title": "My Video"}
        )
        notify = mocker.patch("clipmind_runner.notify")

        clipmind_runner.main()

        reporter.assert_called_once_with(
            tmp_path,
            job_id="host-job-id",
            source_url="https://youtu.be/abc",
            secrets=runtime_config.secrets,
        )
        assert run_pipeline.call_args.kwargs["config"] == runtime_config
        assert run_pipeline.call_args.kwargs["destinations"] == ["discord"]
        notify.assert_called_once()

    def test_main_exception_notifies(self, mocker, runtime_config, tmp_path):
        import clipmind_runner

        mocker.patch(
            "sys.argv", ["clipmind_runner.py", "https://youtu.be/abc", "job-id"]
        )
        mocker.patch("clipmind_runner.os.chdir")
        mocker.patch("clipmind_runner.JOBS_DIR", tmp_path)
        mocker.patch("clipmind_runner.load_runtime_config", return_value=runtime_config)
        mocker.patch("clipmind_runner.JobStatusStore")
        mocker.patch("clipmind.pipeline.run_pipeline", side_effect=RuntimeError("broken"))
        notify = mocker.patch("clipmind_runner.notify")

        clipmind_runner.main()

        assert "エラー" in notify.call_args.args[0]

    def test_main_uses_shared_default_destinations_when_not_overridden(
        self, mocker, runtime_config, tmp_path
    ):
        import clipmind_runner

        mocker.patch(
            "sys.argv", ["clipmind_runner.py", "https://youtu.be/abc", "job-id"]
        )
        mocker.patch("clipmind_runner.os.chdir")
        mocker.patch("clipmind_runner.JOBS_DIR", tmp_path)
        mocker.patch("clipmind_runner.load_runtime_config", return_value=runtime_config)
        mocker.patch("clipmind_runner.JobStatusStore")
        run_pipeline = mocker.patch(
            "clipmind.pipeline.run_pipeline", return_value={"title": "My Video"}
        )
        mocker.patch("clipmind_runner.notify")

        clipmind_runner.main()

        assert run_pipeline.call_args.kwargs["destinations"] is None

    def test_main_preserves_explicit_empty_destinations(
        self, mocker, runtime_config, tmp_path
    ):
        import clipmind_runner

        mocker.patch(
            "sys.argv", ["clipmind_runner.py", "https://youtu.be/abc", "job-id", ""]
        )
        mocker.patch("clipmind_runner.os.chdir")
        mocker.patch("clipmind_runner.JOBS_DIR", tmp_path)
        mocker.patch("clipmind_runner.load_runtime_config", return_value=runtime_config)
        mocker.patch("clipmind_runner.JobStatusStore")
        run_pipeline = mocker.patch(
            "clipmind.pipeline.run_pipeline", return_value={"title": "My Video"}
        )
        mocker.patch("clipmind_runner.notify")

        clipmind_runner.main()

        assert run_pipeline.call_args.kwargs["destinations"] == []
