# Release report

## PROJECT STATUS

Modernisation implemented and locally verified. Publication and the final commit
hash are recorded in the delivery message; remote Actions results are distinct
from local evidence. No independent production security certification is claimed.

## INITIAL ARCHITECTURE FINDINGS

Existing PyQt5 client, synchronous TCP request/response wrapper, thread-per-client
server with a monolithic router, five-table SQLite database, ad hoc administration,
and several disconnected alternate modules. See [initial audit](AUDIT.md).

## INITIAL CRITICAL / HIGH-RISK ISSUES

Missing membership authorization, shared default credentials, unsalted SHA-256,
unbounded frames, stale blocked-account authority, weak role hierarchy/manager
scope, non-atomic administration, disabled foreign keys, GUI-blocking I/O, and
plaintext external listening. The initial audit maps each issue to its treatment.

## ARCHITECTURAL IMPROVEMENTS

Separate transport, routing/authorization, authentication, messaging, persistence,
shared validation/TLS, and Qt orchestration. Consolidated entry points and removed
unused incompatible implementations without replacing TCP, SQLite, or PyQt5.

## CLIENT IMPROVEMENTS

Serialized framed requests, connection/write/read failure handling, explicit
reauthentication, cancellation-safe socket publication, paged histories, duplicate
request coalescing, preserved failed-send drafts, and honest connection status.

## SERVER IMPROVEMENTS

Bounded connection workers, synchronized registries, handshake/idle/frame/write
limits, session expiry, per-IP authentication limits, request throttling, isolated
malformed connections, and orderly socket/worker shutdown.

## AUTHENTICATION

Administrator-controlled provisioning retained. Explicit first-owner bootstrap;
no implicit accounts. Invalid credentials are generic. Logout and reconnect use
connection-bound server identity; sessions last one hour.

## AUTHORIZATION

Current account state checked every request. Message reads/sends require current
membership, even for owners. Strict lower-role account management; no self
role/block/delete or owner creation via protocol. Managers manage owned chats and
cannot read global audit. Archives reject sends.

## PASSWORD SECURITY

Argon2id via argon2-cffi; random salts, library verification and rehashing. Successful
legacy SHA-256 login upgrades in place; failed logins preserve hashes/data. Local
password recovery retains account/message IDs. Existing weak passwords should be
reset by their operator; a hash migration cannot improve password entropy.

## TRANSPORT SECURITY

Default loopback TCP remains explicitly unencrypted. Remote listeners require TLS.
Verified TLS 1.2+ uses standard-library ssl, configured trust, and hostname checks.
Development certificate generation is documented. No E2EE or storage encryption.

## TCP PROTOCOL

Four-byte big-endian length plus UTF-8 JSON. Maximum 1 MiB. Strict envelope parsing,
fragmentation/coalescing support, deadlines, bounded pages, consistent ACK/error
codes, and no automatic replay of ambiguous writes. See [protocol](PROTOCOL.md).

## CONCURRENCY / THREAD SAFETY

Server connection registries use locks; each socket has one sequential worker.
SQLite connections belong to the calling thread; nested repository calls reuse
only that thread's transaction. Client worker requests are serialized. Qt signals
resume widget code on the GUI thread; duplicate/timer work is coalesced.

## SQLITE / DATABASE

Existing five tables/data preserved; indexes added. Foreign keys, WAL, busy timeout,
explicit connection closure, transaction rollback, and atomic administration/audit.
Chat deletes cascade; account deletes refuse referenced history/ownership/audit.
Legacy orphan records are not silently removed.

## PYQT5 UI / UX

Restrained shared dark styling, consistent spacing, resizable conversation layout,
plain-text messages/labels, loading/error feedback, disabled disconnected/archived
composer, earlier-message paging, and a real reconnect dialog. Admin screens also
run their network work outside the GUI thread.

## ERROR HANDLING

Stable protocol errors and readable validation/access/storage feedback. Unexpected
details go to development logging without request/password logging. Interrupted
sends warn about uncertain commit state and are not retried automatically.

## CODE QUALITY

Ruff rules/formatting, package metadata, typed core interfaces, parameterized SQL,
shared limits/roles/validation, coherent naming, and removed dead code. Baseline
source had 75 findings under the selected Ruff rules; final lint is clean.

## TEST COVERAGE

82 behaviour-focused tests; no percentage target or invented manual test coverage.
Temporary data, real local TCP/TLS, meaningful rollback tests, and offscreen GUI
checks. See [verification](VERIFICATION.md) for the complete behaviour inventory.

## INTEGRATION TEST RESULTS

Registration through administration, two-client messaging, simultaneous clients,
history paging/order, committed storage, full server restart, and Qt reconnect
passed locally. All fixture-owned resources close cleanly.

## SECURITY TEST RESULTS

Nonmember access, forged identity/role, escalation, manager scope, self-modification,
blocked sessions, malformed frames, oversized data, login/request/connection limits,
certificate trust and hostname failures passed. Runtime advisory audit found no
known advisories in its seven resolved Python packages; native Qt review is separate.

## PERFORMANCE RESULTS

Eight clients / 80 persisted messages: median send-to-ACK 61.33 ms, p95 64.19 ms;
history page 5.07 ms. Indexed query plan confirmed. No tracked connections/workers
remained after shutdown. Single local sample; no RSS or WAN/capacity claim.

## DEPENDENCIES

Two pinned runtime dependencies: PyQt5 5.15.11 and argon2-cffi 25.1.0. Removed unused
python-dotenv and runtime custom-crypto dependency. Development-only cryptography
supports local certificates/TLS tests. Editable install and pip check passed.
Python 3.11–3.13 declared; local interpreter was 3.12.14.

## LOCAL STARTUP

SETUP.bat installs into .venv; server/client launchers change to their own directory,
check dependencies, pass CLI arguments, and report failures. Explicit owner setup;
exclusive server bind; client instance lock with --new-instance for demos. Both
launcher help paths passed. No global installation/process termination.

## README IMPROVEMENTS

Rebuilt around the real desktop/TCP/SQLite application, engineering motivations,
features, architecture, security boundaries, screenshots, quick start, existing-data
migration, tests, project structure, and honest limitations.

## SECURITY DOCUMENTATION

[SECURITY.md](SECURITY.md) separates implemented controls, trusted components,
plaintext/TLS behaviour, migration/recovery, and absent security features.

## ARCHITECTURE DOCUMENTATION

[ARCHITECTURE.md](ARCHITECTURE.md) explains modules, lifecycle, threading, database
ownership, transactions, delivery/order, errors, and removal of disconnected paths.

## SCREENSHOTS

Three real offscreen PyQt5 captures: login, active synthetic conversation, and
administration. Generated against a live TCP server; visually inspected. No
personal account database or invented screenshot mockup was used.

## GITHUB ACTIONS

Configured Windows/Linux × Python 3.11/3.12/3.13, lint/format/privacy checks, pytest,
and a runtime advisory-audit job. Remote execution results are reported separately
in the delivery message after publication, not inferred from local tests.

## LINT / FORMAT

Ruff check and format check passed. Source compilation and git diff whitespace
checks passed. Resource/unraisable/thread warnings are configured as test failures.

## END-TO-END DEMO VERIFICATION

Automated server/account/client A/client B/send/receive/persistence/restart/invalid
credentials/unauthorized action/disconnect/reconnect/clean-shutdown steps passed.
Native desktop DPI/accessibility/window-decoration checks remain manual.

## KNOWN LIMITATIONS

Educational scope; no independent assessment, E2EE, storage encryption, MFA,
attachments, public signup, automatic backups, push delivery, exactly-once replay,
or distributed abuse protection. One-hour sessions and IPv4 only; list views cap
at 1,000 records. Managers use ownership scope, not department entities. Historical
foreign-key problems need manual backed-up review. Qt native-library advisories
are outside the scope of the Python package audit. Full clean-machine setup and
native desktop UX require manual/platform verification.

## FILES ADDED

- `.gitattributes`
- `.github/workflows/ci.yml`
- `SETUP.bat`
- `client/controller.py`
- `docs/ARCHITECTURE.md`
- `docs/AUDIT.md`
- `docs/PROTOCOL.md`
- `docs/RELEASE_REPORT.md`
- `docs/SECURITY.md`
- `docs/VERIFICATION.md`
- `docs/screenshots/administration.png`
- `docs/screenshots/conversation.png`
- `docs/screenshots/login.png`
- `pyproject.toml`
- `requirements-dev.txt`
- `scripts/__init__.py`
- `scripts/benchmark.py`
- `scripts/capture_screenshots.py`
- `scripts/dev_certificate.py`
- `scripts/privacy_check.py`
- `server/router.py`
- `shared/tls.py`
- `shared/validation.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_authorization.py`
- `tests/test_gui.py`
- `tests/test_messaging.py`
- `tests/test_protocol.py`
- `tests/test_tls.py`

## FILES MODIFIED

- `.gitignore`
- `README.md`
- `START_CLIENT.bat`
- `START_SERVER.bat`
- `client/client.py`
- `client/config.py`
- `client/gui/admin/admin_window.py`
- `client/gui/admin/audit_tab.py`
- `client/gui/admin/chats_tab.py`
- `client/gui/admin/users_tab.py`
- `client/gui/login_window.py`
- `client/gui/main_window.py`
- `client/gui/styles.py`
- `client/network.py`
- `requirements.txt`
- `run_client.py`
- `run_server.py`
- `server/auth.py`
- `server/config.py`
- `server/database.py`
- `server/message_handler.py`
- `server/rbac.py`
- `server/server.py`
- `shared/constants.py`
- `shared/models.py`
- `shared/protocol.py`

## FILES REMOVED

- `client/cache.py`
- `client/gui/chat_widget.py`
- `server/backup.py`
- `server/encryption.py`
- `server/file_handler.py`

## GIT COMMIT HASH

Recorded in the final delivery message and obtainable with `git rev-parse HEAD`.
A commit cannot embed its own hash in its committed contents.

## GITHUB PUBLICATION STATUS

Normal push to the confirmed public origin/master after the final local
verification and privacy scan. Exact result and remote CI status are recorded in
the final delivery message. Existing remote README history was fast-forwarded first.
Repository description and all ten requested topics were updated successfully.

## GITHUB REPOSITORY URL

[SecureTeam Messenger](https://github.com/kirillprisaznuk-afk/secureteam-messenger)

## FINAL VERDICT

- CODEBASE MODERNISED: YES — implemented architecture/security/quality changes.
- CORE FUNCTIONALITY VERIFIED: YES — real network, persistence, and Qt integration.
- SECURITY CLAIMS VERIFIED: YES — scoped controls tested; limitations explicit.
- README PORTFOLIO READY: YES — actual features, screenshots and reproducible steps.
- PUBLIC REPOSITORY READY: pending final publication checks and observed CI result;
  the final delivery message gives the evidence-based YES/NO.
