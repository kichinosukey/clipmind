"""Secret access boundaries for ClipMind."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol

from clipmind.paths import KEYCHAIN_SERVICE


class SecretLookupError(RuntimeError):
    """Raised when a configured secret cannot be loaded."""


class SecretStore(Protocol):
    """Read secrets by their stable configuration reference."""

    def get(self, reference: str) -> str: ...


@dataclass(frozen=True)
class KeychainSecretStore:
    """Read ClipMind generic passwords from macOS Keychain."""

    service: str = KEYCHAIN_SERVICE

    def get(self, reference: str) -> str:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                self.service,
                "-a",
                reference,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        secret = result.stdout.rstrip("\r\n")
        if result.returncode != 0 or not secret:
            raise SecretLookupError(f"Keychain secret is unavailable: {reference}")
        return secret


def redact_secrets(message: str, secrets: list[str | None]) -> str:
    """Replace known secret values without exposing partial matches."""

    redacted = message
    known = sorted({secret for secret in secrets if secret}, key=len, reverse=True)
    for secret in known:
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted
