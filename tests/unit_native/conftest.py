"""Add native-host directory to sys.path so its scripts can be imported."""

import os
import sys

_native_host_dir = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "native-host"
)
_native_host_dir = os.path.normpath(_native_host_dir)

if _native_host_dir not in sys.path:
    sys.path.insert(0, _native_host_dir)
