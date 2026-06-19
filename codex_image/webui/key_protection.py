"""At-rest protection for API keys stored in settings JSON files.

On Windows, uses the Data Protection API (DPAPI) to encrypt keys with the
current user's login credentials.  On other platforms, falls back to a
machine-scoped obfuscation using HMAC-derived XOR masking.

Protected values are prefixed so they can be distinguished from raw plaintext:
  - ``enc:dpapi:<base64>``  — Windows DPAPI
  - ``enc:local:<base64>``  — machine-scoped obfuscation (non-Windows)

If a value does *not* carry an ``enc:`` prefix it is treated as legacy
plaintext and returned as-is (enabling transparent migration).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import platform
import struct
import sys
from typing import Optional

logger = logging.getLogger(__name__)

_ENC_DPAPI_PREFIX = "enc:dpapi:"
_ENC_LOCAL_PREFIX = "enc:local:"


# ---------------------------------------------------------------------------
# Windows DPAPI helpers (loaded lazily so non-Windows imports don't break)
# ---------------------------------------------------------------------------

def _dpapi_available() -> bool:
    return sys.platform == "win32"


def _dpapi_protect(plaintext: bytes) -> bytes:
    """Encrypt *plaintext* with DPAPI (current-user scope)."""
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):  # noqa: N801
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    blob_in = DATA_BLOB(len(plaintext), ctypes.create_string_buffer(plaintext, len(plaintext)))
    blob_out = DATA_BLOB()

    if not crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,  # description
        None,  # optional entropy
        None,  # reserved
        None,  # prompt struct
        0,     # flags
        ctypes.byref(blob_out),
    ):
        raise OSError("CryptProtectData failed")

    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _dpapi_unprotect(cipher: bytes) -> bytes:
    """Decrypt *cipher* with DPAPI (current-user scope)."""
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):  # noqa: N801
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    blob_in = DATA_BLOB(len(cipher), ctypes.create_string_buffer(cipher, len(cipher)))
    blob_out = DATA_BLOB()

    if not crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,  # description out
        None,  # entropy
        None,  # reserved
        None,  # prompt struct
        0,     # flags
        ctypes.byref(blob_out),
    ):
        raise OSError("CryptUnprotectData failed")

    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


# ---------------------------------------------------------------------------
# Machine-scoped obfuscation fallback (non-Windows)
# ---------------------------------------------------------------------------

def _machine_key() -> bytes:
    """Derive a machine-scoped key from hostname + login user."""
    node = platform.node() or "unknown-host"
    try:
        user = os.getlogin()
    except OSError:
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown-user"
    seed = f"ilab-conjure:{node}:{user}".encode("utf-8")
    return hashlib.sha256(seed).digest()


def _xor_mask(data: bytes, key: bytes) -> bytes:
    """XOR *data* with a repeating HMAC-derived stream from *key*."""
    stream = b""
    block_index = 0
    while len(stream) < len(data):
        stream += hmac.new(key, struct.pack(">I", block_index), hashlib.sha256).digest()
        block_index += 1
    return bytes(a ^ b for a, b in zip(data, stream))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def protect_key(plaintext: str) -> str:
    """Encrypt/obfuscate an API key for at-rest storage.

    Returns a prefixed string suitable for writing to a JSON settings file.
    If *plaintext* is empty, returns an empty string.
    """
    if not plaintext:
        return ""

    raw = plaintext.encode("utf-8")

    if _dpapi_available():
        try:
            encrypted = _dpapi_protect(raw)
            return _ENC_DPAPI_PREFIX + base64.b64encode(encrypted).decode("ascii")
        except Exception:
            logger.warning("DPAPI encryption failed; falling back to local obfuscation")

    masked = _xor_mask(raw, _machine_key())
    return _ENC_LOCAL_PREFIX + base64.b64encode(masked).decode("ascii")


def unprotect_key(value: str) -> str:
    """Decrypt/deobfuscate an API key read from a settings file.

    Accepts both protected (``enc:...``) and legacy plaintext values.
    Returns the plaintext API key, or an empty string if decryption fails.
    """
    if not value:
        return ""

    if value.startswith(_ENC_DPAPI_PREFIX):
        payload = value[len(_ENC_DPAPI_PREFIX):]
        try:
            cipher = base64.b64decode(payload)
            return _dpapi_unprotect(cipher).decode("utf-8")
        except Exception:
            logger.warning(
                "Failed to decrypt DPAPI-protected API key (file may have been "
                "moved from another machine). Please re-enter your API key."
            )
            return ""

    if value.startswith(_ENC_LOCAL_PREFIX):
        payload = value[len(_ENC_LOCAL_PREFIX):]
        try:
            masked = base64.b64decode(payload)
            return _xor_mask(masked, _machine_key()).decode("utf-8")
        except Exception:
            logger.warning(
                "Failed to decrypt locally-protected API key. "
                "Please re-enter your API key."
            )
            return ""

    # Legacy plaintext — return as-is for backward compatibility.
    return value
