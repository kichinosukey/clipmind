"""Tests for clipmind.repair."""

import json
import plistlib

from clipmind.repair import build_alfred_script, repair_installation, sync_alfred_workflow


def _write_workflow_plist(path, script):
    data = {
        "name": "clipmind",
        "objects": [
            {
                "type": "alfred.workflow.action.script",
                "config": {"script": script},
            }
        ],
    }
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)


class TestRepairInstallation:
    def test_repair_reuses_existing_extension_id(self, tmp_path):
        """Existing manifest extension ID is preserved while host path is refreshed."""
        repo_root = tmp_path / "clipmind"
        (repo_root / "native-host").mkdir(parents=True)
        manifest_path = tmp_path / "NativeMessagingHosts" / "com.clipmind.host.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "allowed_origins": ["chrome-extension://existing-extension-id/"],
                    "path": "/old/path/native-host/clipmind_host.py",
                }
            ),
            encoding="utf-8",
        )

        result = repair_installation(
            project_root=repo_root,
            manifest_path=manifest_path,
            workflows_dir=tmp_path / "empty-workflows",
        )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert result.extension_id == "existing-extension-id"
        assert manifest["allowed_origins"] == [
            "chrome-extension://existing-extension-id/"
        ]
        assert manifest["path"] == str(repo_root / "native-host" / "clipmind_host.py")

    def test_sync_alfred_workflow_replaces_legacy_script(self, tmp_path):
        """Legacy Alfred script is replaced with the standardized launcher wrapper."""
        info_path = tmp_path / "info.plist"
        _write_workflow_plist(
            info_path,
            """#!/bin/zsh
set -euo pipefail
: "${CLIPMIND_HOME:=$HOME/clipmind}"
source "$CLIPMIND_HOME/.venv/bin/activate"
cd "$CLIPMIND_HOME"
python -m clipmind.pipeline "$1"
""",
        )

        project_root = tmp_path / "projects" / "clipmind"
        changed = sync_alfred_workflow(info_path, project_root)

        with info_path.open("rb") as fh:
            plist_data = plistlib.load(fh)
        updated_script = plist_data["objects"][0]["config"]["script"]

        assert changed is True
        assert updated_script == build_alfred_script(project_root)
        assert "clipmind-run" in updated_script
        assert "activate" not in updated_script
        assert "python -m clipmind.pipeline" not in updated_script

    def test_repair_warns_for_stale_virtualenv_entrypoints(self, tmp_path):
        """Moved virtualenv helper scripts produce recreate warnings."""
        repo_root = tmp_path / "clipmind"
        (repo_root / "native-host").mkdir(parents=True)
        bin_dir = repo_root / ".venv" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "python").write_text("", encoding="utf-8")
        (bin_dir / "activate").write_text(
            "VIRTUAL_ENV='/old/location/.venv'\n",
            encoding="utf-8",
        )
        (bin_dir / "pytest").write_text(
            "#!/old/location/.venv/bin/python\n",
            encoding="utf-8",
        )

        result = repair_installation(
            project_root=repo_root,
            manifest_path=tmp_path / "com.clipmind.host.json",
            workflows_dir=tmp_path / "workflows",
            extension_id="abc123",
        )

        assert any("activate script" in warning for warning in result.warnings)
        assert any("entrypoint 'pytest'" in warning for warning in result.warnings)
