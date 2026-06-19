from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from codex_image.webui.app import create_app


class WebUICSRFTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        # Create app with stub auth checker so we don't hit auth failures
        self.app = create_app(
            output_root=self.root,
            auth_checker=lambda: True,
            auto_start_queue=False
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_csrf_allows_safe_methods(self) -> None:
        # GET should be allowed even if Origin looks malicious
        response = self.client.get(
            "/api/settings",
            headers={"Origin": "http://malicious.com", "Host": "127.0.0.1:8787"}
        )
        self.assertEqual(response.status_code, 200)

    def test_csrf_allows_same_origin_post(self) -> None:
        # POST with same origin/host should be allowed
        # Note: We test with a endpoint that returns 400/422 on empty body,
        # but if we get 403 it means it was blocked by CSRF.
        # We can try /api/auth which expects source in JSON.
        response = self.client.patch(
            "/api/auth",
            json={"source": "api"},
            headers={"Origin": "http://127.0.0.1:8787", "Host": "127.0.0.1:8787"}
        )
        # Should bypass CSRF, returns 200 since source "api" is valid
        self.assertEqual(response.status_code, 200)

    def test_csrf_blocks_cross_origin_post(self) -> None:
        # POST with malicious origin should be blocked (403)
        response = self.client.patch(
            "/api/auth",
            json={"source": "api"},
            headers={"Origin": "http://malicious.com", "Host": "127.0.0.1:8787"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "CSRF protection: Origin mismatch"})

    def test_csrf_allows_same_referer_post(self) -> None:
        # POST with no Origin but matching Referer should be allowed
        response = self.client.patch(
            "/api/auth",
            json={"source": "api"},
            headers={
                "Referer": "http://127.0.0.1:8787/history",
                "Host": "127.0.0.1:8787"
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_csrf_blocks_cross_referer_post(self) -> None:
        # POST with no Origin but malicious Referer should be blocked
        response = self.client.patch(
            "/api/auth",
            json={"source": "api"},
            headers={
                "Referer": "http://malicious.com/some-page",
                "Host": "127.0.0.1:8787"
            }
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "CSRF protection: Referer mismatch"})

    def test_csrf_allows_webui_custom_header(self) -> None:
        # POST with malicious origin but custom header X-Requested-With should be allowed
        response = self.client.patch(
            "/api/auth",
            json={"source": "api"},
            headers={
                "Origin": "http://malicious.com",
                "Host": "127.0.0.1:8787",
                "X-Requested-With": "codex-image-webui"
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_csrf_allows_missing_origin_and_referer(self) -> None:
        # POST with no Origin/Referer (like curl or cli client) should be allowed
        response = self.client.patch(
            "/api/auth",
            json={"source": "api"},
            headers={"Host": "127.0.0.1:8787"}
        )
        self.assertEqual(response.status_code, 200)
