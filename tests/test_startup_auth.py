from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_image.auth import AuthState


class StartupAuthTests(unittest.TestCase):
    def _auth_state(self, root: Path, token: str | None) -> AuthState:
        return AuthState(
            path=root / "auth.json",
            access_token=token,
            refresh_token=None,
            id_token=None,
            account_id="acct-local" if token else None,
            last_refresh=None,
            raw={},
        )

    def test_detect_startup_auth_source_always_defaults_to_api(self) -> None:
        """By default, detect_startup_auth_source returns 'api' so that
        ~/.codex/auth.json is not silently accessed."""
        from codex_image.webui.startup_auth import detect_startup_auth_source

        with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), "token")):
            self.assertEqual(detect_startup_auth_source(), "api")
            self.assertEqual(detect_startup_auth_source(enable_codex_auth=False), "api")

    def test_detect_startup_auth_source_with_flag(self) -> None:
        from codex_image.webui.startup_auth import detect_startup_auth_source

        # If enabled, but no token, fallback to api
        with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), None)):
            self.assertEqual(detect_startup_auth_source(enable_codex_auth=True), "api")

        # If enabled and token exists, return codex
        with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), "token")):
            self.assertEqual(detect_startup_auth_source(enable_codex_auth=True), "codex")

        # If loading state raises exception, fallback to api
        with patch("codex_image.auth.load_auth_state", side_effect=RuntimeError("missing")):
            self.assertEqual(detect_startup_auth_source(enable_codex_auth=True), "api")

    def test_detect_startup_auth_source_with_env_var(self) -> None:
        from codex_image.webui.startup_auth import detect_startup_auth_source

        # Set env var
        with patch.dict("os.environ", {"ILAB_ENABLE_CODEX_AUTH": "1"}):
            with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), "token")):
                self.assertEqual(detect_startup_auth_source(), "codex")

        # Env var set but no token
        with patch.dict("os.environ", {"ILAB_ENABLE_CODEX_AUTH": "1"}):
            with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), None)):
                self.assertEqual(detect_startup_auth_source(), "api")

        # Env var set to 0 or other value
        with patch.dict("os.environ", {"ILAB_ENABLE_CODEX_AUTH": "0"}):
            with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), "token")):
                self.assertEqual(detect_startup_auth_source(), "api")

    def test_main_cli_with_enable_codex_auth_flag(self) -> None:
        from codex_image.webui.startup_auth import main

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "webui-auth-settings.json"

            # Run without flag -> should write api source
            with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), "token")):
                main(["--settings-path", str(settings_path)])
                self.assertEqual(json.loads(settings_path.read_text(encoding="utf-8"))["source"], "api")

            # Run with flag -> should write codex source because we mock token presence
            with patch("codex_image.auth.load_auth_state", return_value=self._auth_state(Path("."), "token")):
                main(["--settings-path", str(settings_path), "--force", "--enable-codex-auth"])
                self.assertEqual(json.loads(settings_path.read_text(encoding="utf-8"))["source"], "codex")

    def test_initialize_auth_settings_preserves_user_selected_sources(self) -> None:
        from codex_image.webui.startup_auth import initialize_auth_settings

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "webui-auth-settings.json"
            settings_path.write_text(json.dumps({"source": "api"}), encoding="utf-8")
            with patch("codex_image.webui.startup_auth.detect_startup_auth_source", return_value="codex"):
                selected = initialize_auth_settings(settings_path)

            self.assertEqual(selected, "api")
            self.assertEqual(json.loads(settings_path.read_text(encoding="utf-8"))["source"], "api")

    def test_initialize_auth_settings_migrates_missing_or_legacy_sources(self) -> None:
        from codex_image.webui.startup_auth import initialize_auth_settings

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_path = root / "missing.json"
            legacy_path = root / "legacy.json"
            legacy_path.write_text(json.dumps({"source": "cock" + "pit"}), encoding="utf-8")

            with patch("codex_image.webui.startup_auth.detect_startup_auth_source", return_value="codex"):
                self.assertEqual(initialize_auth_settings(missing_path), "codex")
                self.assertEqual(initialize_auth_settings(legacy_path), "codex")

            self.assertEqual(json.loads(missing_path.read_text(encoding="utf-8"))["source"], "codex")
            self.assertEqual(json.loads(legacy_path.read_text(encoding="utf-8"))["source"], "codex")


if __name__ == "__main__":
    unittest.main()
