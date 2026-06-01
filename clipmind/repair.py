"""Repair local integrations after moving the repository."""

from __future__ import annotations

import argparse
import json
import plistlib
import re
from dataclasses import dataclass
from pathlib import Path

from clipmind.paths import (
    ALFRED_WORKFLOWS_DIR,
    CHROME_NATIVE_HOST_MANIFEST,
    NATIVE_HOST_NAME,
    PROJECT_ROOT,
    embedded_venv_path_warnings,
)
from clipmind.ytdlp_health import report as ytdlp_health_report


@dataclass
class RepairResult:
    manifest_path: Path
    extension_id: str
    updated_workflows: list[Path]
    warnings: list[str]
    manual_steps: list[str]


def _shell_double_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_alfred_script(project_root: Path) -> str:
    """Return the standardized Alfred workflow script."""
    default_home = _shell_double_quote(str(project_root))
    return f"""#!/bin/zsh
set -euo pipefail

URL="${{1:-}}"
[[ -z "$URL" ]] && osascript -e 'display notification "URLが空です" with title "ClipMind"' && exit 1

DEFAULT_CLIPMIND_HOME="{default_home}"
CLIPMIND_HOME="${{CLIPMIND_HOME:-$DEFAULT_CLIPMIND_HOME}}"
LOG_PATH="/tmp/clipmind.log"
RUNNER="$CLIPMIND_HOME/clipmind-run"

if [[ ! -x "$RUNNER" ]]; then
  osascript -e 'display notification "ClipMind launcher が見つかりません" with title "ClipMind"'
  echo "⚠️ launcher が見つかりません: $RUNNER" >&2
  exit 1
fi

if "$RUNNER" "$URL" > "$LOG_PATH" 2>&1; then
  osascript -e 'display notification "処理が完了しました" with title "ClipMind"'
else
  osascript -e 'display notification "ClipMindでエラーが発生しました" with title "ClipMind"'
  echo "❌ ClipMind Pipeline failed. See log: $LOG_PATH" >&2
  exit 1
fi"""


def read_extension_id_from_manifest(manifest_path: Path) -> str | None:
    """Read the Chrome extension ID from an existing Native Messaging manifest."""
    if not manifest_path.exists():
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    for origin in manifest.get("allowed_origins", []):
        match = re.match(r"^chrome-extension://([^/]+)/$", origin)
        if match:
            return match.group(1)
    return None


def write_native_host_manifest(
    project_root: Path,
    manifest_path: Path,
    extension_id: str,
) -> None:
    """Write the Native Messaging manifest for the current repository location."""
    manifest = {
        "name": NATIVE_HOST_NAME,
        "description": "clipmind Native Messaging Host",
        "path": str(project_root / "native-host" / "clipmind_host.py"),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def should_manage_workflow_script(plist_data: dict) -> bool:
    """Return whether this Alfred workflow is clearly ClipMind-related."""
    workflow_name = str(plist_data.get("name", "")).lower()
    if "clipmind" in workflow_name:
        return True

    for obj in plist_data.get("objects", []):
        config = obj.get("config", {})
        for value in config.values():
            if isinstance(value, str) and "clipmind" in value.lower():
                return True
    return False


def sync_alfred_workflow(info_path: Path, project_root: Path) -> bool:
    """Replace ClipMind Alfred workflow scripts with the standardized launcher wrapper."""
    with info_path.open("rb") as fh:
        plist_data = plistlib.load(fh)

    if not should_manage_workflow_script(plist_data):
        return False

    desired_script = build_alfred_script(project_root)
    changed = False

    for obj in plist_data.get("objects", []):
        if obj.get("type") != "alfred.workflow.action.script":
            continue
        config = obj.get("config", {})
        current_script = config.get("script")
        if not isinstance(current_script, str):
            continue
        if "clipmind" not in current_script.lower() and "CLIPMIND_HOME" not in current_script:
            continue
        if current_script == desired_script:
            continue
        config["script"] = desired_script
        changed = True

    if not changed:
        return False

    with info_path.open("wb") as fh:
        plistlib.dump(plist_data, fh, sort_keys=False)
    return True


def repair_installation(
    *,
    project_root: Path = PROJECT_ROOT,
    manifest_path: Path = CHROME_NATIVE_HOST_MANIFEST,
    workflows_dir: Path = ALFRED_WORKFLOWS_DIR,
    extension_id: str | None = None,
) -> RepairResult:
    """Repair repo-path-sensitive local integrations."""
    resolved_extension_id = extension_id or read_extension_id_from_manifest(manifest_path)
    if not resolved_extension_id:
        raise SystemExit(
            "Chrome extension ID is required on first install. "
            "Run ./clipmind-repair <extension-id> after loading the unpacked extension."
        )

    write_native_host_manifest(project_root, manifest_path, resolved_extension_id)

    updated_workflows: list[Path] = []
    if workflows_dir.exists():
        for info_path in sorted(workflows_dir.glob("*/info.plist")):
            if sync_alfred_workflow(info_path, project_root):
                updated_workflows.append(info_path)

    warnings = embedded_venv_path_warnings(project_root)

    manual_steps = [
        f"Reload the unpacked Chrome extension from {project_root / 'chrome-extension'} in chrome://extensions.",
        "If Chrome assigns a new Extension ID after reload, rerun ./clipmind-repair <new-extension-id>.",
    ]

    return RepairResult(
        manifest_path=manifest_path,
        extension_id=resolved_extension_id,
        updated_workflows=updated_workflows,
        warnings=warnings,
        manual_steps=manual_steps,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair ClipMind integrations after moving the repository."
    )
    parser.add_argument(
        "extension_id",
        nargs="?",
        help="Chrome extension ID for the unpacked ClipMind extension",
    )
    parser.add_argument(
        "--extension-id",
        dest="extension_id_flag",
        help="Chrome extension ID for the unpacked ClipMind extension",
    )
    args = parser.parse_args()

    result = repair_installation(
        extension_id=args.extension_id_flag or args.extension_id,
    )

    print(f"Updated native host manifest: {result.manifest_path}")
    print(f"Allowed Chrome extension ID: {result.extension_id}")

    if result.updated_workflows:
        print("Updated Alfred workflows:")
        for info_path in result.updated_workflows:
            print(f"- {info_path}")
    else:
        print("Updated Alfred workflows: none")

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")

    print("Manual steps:")
    for step in result.manual_steps:
        print(f"- {step}")

    print()
    print(ytdlp_health_report())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
