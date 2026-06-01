#!/usr/bin/env python3
"""Helper script to read .env and return available destinations as JSON.

Run with venv python from clipmind_host.py's get_config handler.
Outputs JSON to stdout: {"destinations": ["discord", "slack"]}
"""

import json
import os
import sys
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from clipmind.paths import load_project_dotenv

os.chdir(str(_PROJECT_DIR))
load_project_dotenv()

available = []
if os.getenv("DISCORD_WEBHOOK_URL", "").strip():
    available.append("discord")
if os.getenv("SLACK_WEBHOOK_URL", "").strip():
    available.append("slack")

# If neither is configured, show both as available (user may configure later).
if not available:
    available = ["discord", "slack"]

print(json.dumps({"destinations": available}))
