from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any



AUTH_SOURCES = {"codex", "api"}
LEGACY_AUTH_SOURCES = {"auto", "cock" + "pit"}


def detect_startup_auth_source(enable_codex_auth: bool = False) -> str:
    # Default to "api" mode to avoid silently reading ~/.codex/auth.json
    # (ChatGPT OAuth tokens).  Users who want codex mode must explicitly
    # select it via the WebUI auth settings panel, or enable it at startup
    # using --enable-codex-auth CLI flag or ILAB_ENABLE_CODEX_AUTH=1 env var.
    import os
    if enable_codex_auth or os.environ.get("ILAB_ENABLE_CODEX_AUTH") == "1":
        try:
            from codex_image.auth import load_auth_state
            state = load_auth_state()
            if getattr(state, "access_token", ""):
                return "codex"
        except Exception:
            pass
    return "api"


def _read_existing_source(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("source") or "").strip().lower()


def initialize_auth_settings(path: str | Path, *, force: bool = False, enable_codex_auth: bool = False) -> str:
    settings_path = Path(path)
    existing = _read_existing_source(settings_path)
    if not force and existing in AUTH_SOURCES:
        return existing
    source = detect_startup_auth_source(enable_codex_auth=enable_codex_auth)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"source": source}, indent=2), encoding="utf-8")
    return source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize WebUI auth source settings.")
    parser.add_argument("--settings-path", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--enable-codex-auth", action="store_true")
    args = parser.parse_args(argv)
    source = initialize_auth_settings(
        args.settings_path,
        force=bool(args.force),
        enable_codex_auth=bool(args.enable_codex_auth),
    )
    print(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
