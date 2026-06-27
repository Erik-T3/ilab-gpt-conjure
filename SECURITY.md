# Security Policy

## Local-only assumptions

iLab GPT Conjure is designed for local personal workflows. Do not expose the
WebUI directly to the public internet unless you have reviewed and hardened the
deployment yourself.

## Secrets and local data

Do not publish OAuth tokens, API keys, account files, `.env` files, input images,
generated outputs, task metadata, SQLite databases, or debug logs.

Sensitive local paths include:

- `~/.codex/auth.json`
- `output/`
- `outputs/`
- `input/`
- `inputs/`

### API key at-rest encryption

API keys saved through the WebUI settings panel are encrypted before being
written to the `webui-api-settings.json` file:

- **Windows**: Uses the Windows Data Protection API (DPAPI), which ties the
  encrypted key to the current user's login credentials.
- **Other platforms**: Uses a machine-scoped obfuscation (HMAC-derived XOR
  masking) that prevents casual plaintext exposure.

Existing plaintext keys from older versions are accepted on read and
automatically re-encrypted on the next settings save.

> **Note**: This protects against accidental sharing, grep exposure, and
> other-user access.  A determined attacker with access to your OS session
> can still decrypt the key.  For stronger guarantees, use a secrets manager.

## Advanced local auth warning

> **⚠️  Codex / ChatGPT OAuth mode accesses your personal session tokens.**

The optional Codex auth mode reads, refreshes, and re-writes the OAuth
tokens stored at `~/.codex/auth.json`.  These tokens grant access to your
ChatGPT account.

- **New installs default to API mode** and will never touch
  `~/.codex/auth.json` unless you explicitly switch to codex mode.
- When codex mode is active, a warning is logged to the console each time
  the tokens are accessed.
- It is not an officially recommended OpenAI API integration path and
  may change or stop working without notice.
- **Prefer OpenAI-compatible API mode** for stable integrations.

## Local web server security

The iLab GPT Conjure local web server binds to `127.0.0.1` (loopback only) by default, meaning it cannot be accessed directly from other machines on the network.

To protect the local server from browser-based cross-site requests (CSRF):
- All state-changing endpoints (`POST`, `PATCH`, `DELETE`) are protected by a CSRF validation middleware.
- The middleware checks that requests either have a matching `Origin` or `Referer` matching the server's own `Host` header, or include the custom `X-Requested-With: codex-image-webui` header.
- Cross-origin requests from third-party websites visited in the user's browser are automatically blocked.

## Portable updater behavior

Portable startup launchers only start the local WebUI server and open the local
browser URL. They do not contact GitHub and do not update files automatically.

Portable update scripts are manually run. They fetch GitHub Release metadata and
the matching portable zip, verify the published SHA256 file, preserve local
`data/`, only replace package-managed files inside the extracted portable
folder, and keep backups under `.backup/`.

## Reporting issues

Please report security issues privately to the maintainer instead of opening a
public issue containing credentials, tokens, private prompts, or private images.

