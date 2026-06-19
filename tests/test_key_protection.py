from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_image.webui.key_protection import (
    _ENC_DPAPI_PREFIX,
    _ENC_LOCAL_PREFIX,
    _machine_key,
    _xor_mask,
    protect_key,
    unprotect_key,
)


class KeyProtectionTests(unittest.TestCase):
    """Tests for the at-rest key protection module."""

    def test_empty_string_roundtrips(self) -> None:
        self.assertEqual(protect_key(""), "")
        self.assertEqual(unprotect_key(""), "")

    def test_plaintext_legacy_passthrough(self) -> None:
        """Legacy plaintext values (no enc: prefix) are returned as-is."""
        self.assertEqual(unprotect_key("sk-abc123"), "sk-abc123")
        self.assertEqual(unprotect_key("my-plain-api-key"), "my-plain-api-key")

    def test_protect_returns_prefixed_value(self) -> None:
        protected = protect_key("test-secret-key")
        self.assertTrue(
            protected.startswith(_ENC_DPAPI_PREFIX) or protected.startswith(_ENC_LOCAL_PREFIX),
            f"Expected enc: prefix, got: {protected[:20]}",
        )

    def test_roundtrip(self) -> None:
        """protect → unprotect returns the original key."""
        original = "sk-X99ZXoOnRmYAb4zR0zDuEy8wi0PgCwqSLKRwqb7zvFP9hCXy"
        protected = protect_key(original)
        self.assertNotEqual(protected, original)
        self.assertEqual(unprotect_key(protected), original)

    def test_roundtrip_unicode(self) -> None:
        original = "密钥-测试-κλειδί-🔑"
        protected = protect_key(original)
        self.assertEqual(unprotect_key(protected), original)

    def test_different_keys_produce_different_ciphertexts(self) -> None:
        a = protect_key("key-alpha")
        b = protect_key("key-beta")
        self.assertNotEqual(a, b)

    def test_local_xor_mask_is_reversible(self) -> None:
        key = _machine_key()
        data = b"hello world 1234567890"
        masked = _xor_mask(data, key)
        self.assertNotEqual(masked, data)
        self.assertEqual(_xor_mask(masked, key), data)

    def test_corrupt_dpapi_returns_empty(self) -> None:
        """A mangled DPAPI blob returns '' rather than crashing."""
        import base64

        bad = _ENC_DPAPI_PREFIX + base64.b64encode(b"not-a-real-blob").decode()
        result = unprotect_key(bad)
        self.assertEqual(result, "")

    def test_corrupt_local_returns_empty_on_bad_base64(self) -> None:
        bad = _ENC_LOCAL_PREFIX + "!!!not-base64!!!"
        result = unprotect_key(bad)
        self.assertEqual(result, "")

    def test_settings_store_integration_roundtrip(self) -> None:
        """API key written through ApiSettings is encrypted on disk and readable back."""
        from codex_image.webui.settings_store import ApiSettings

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "api-settings.json"
            settings = ApiSettings(path)

            settings.write({
                "base_url": "https://api.example.com/v1",
                "api_key": "test-secret-roundtrip",
                "image_model": "gpt-image-2",
            })

            # On disk, the key must NOT be plaintext
            raw = json.loads(path.read_text(encoding="utf-8"))
            disk_key = raw.get("api_key", "")
            self.assertNotEqual(disk_key, "test-secret-roundtrip")
            self.assertTrue(
                disk_key.startswith("enc:"),
                f"Expected encrypted prefix on disk, got: {disk_key[:20]}",
            )

            # Provider-level key on disk must also be encrypted
            providers = raw.get("providers", [])
            if providers:
                provider_key = providers[0].get("api_key", "")
                self.assertTrue(
                    provider_key.startswith("enc:"),
                    f"Provider key not encrypted: {provider_key[:20]}",
                )

            # Read back should transparently decrypt
            read_back = settings.read()
            self.assertEqual(read_back["api_key"], "test-secret-roundtrip")

    def test_settings_store_legacy_plaintext_compat(self) -> None:
        """An old-format file with a plaintext key should read back correctly."""
        from codex_image.webui.settings_store import ApiSettings

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "api-settings.json"
            path.write_text(
                json.dumps({
                    "base_url": "https://api.example.com/v1",
                    "api_key": "legacy-plain-key",
                    "image_model": "gpt-image-2",
                    "api_mode": "images",
                }),
                encoding="utf-8",
            )
            settings = ApiSettings(path)
            read_back = settings.read()
            self.assertEqual(read_back["api_key"], "legacy-plain-key")

    def test_public_settings_never_expose_raw_or_encrypted_key(self) -> None:
        from codex_image.webui.settings_store import ApiSettings

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "api-settings.json"
            settings = ApiSettings(path)
            settings.write({
                "base_url": "https://api.example.com/v1",
                "api_key": "test-secret-never-leak",
                "image_model": "gpt-image-2",
            })
            public = settings.public_settings()
            public_text = json.dumps(public, ensure_ascii=False)
            self.assertNotIn("test-secret-never-leak", public_text)
            self.assertNotIn("enc:", public_text)
            self.assertTrue(public["api_key_set"])


if __name__ == "__main__":
    unittest.main()
