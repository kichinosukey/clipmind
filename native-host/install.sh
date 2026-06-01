#!/bin/bash
# Legacy wrapper for the unified relocation repair command.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${SCRIPT_DIR}/../clipmind-repair" "$@"
