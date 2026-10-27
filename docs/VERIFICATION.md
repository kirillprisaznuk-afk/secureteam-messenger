# Verification record

Validation date: **27 October 2026**. Local platform: **Windows, Python 3.12.14,
PyQt5 5.15.11 / Qt 5.15.2**. All account/message content was synthetic. Tests and
demos used temporary SQLite databases and OS-assigned loopback ports. The existing
ignored account database was never opened by the verification tools.

## Local results

| Check | Evidence |
| --- | --- |
| pytest | 82 tests passed; no skipped tests or reported warnings |
| Ruff lint | Passed with E4/E7/E9/F/I/UP/B rules |
| Ruff format | Passed |
| Source compilation | Passed |
| Editable packaging | `python -m pip install -e .` built/installed successfully in `.venv` |
| Dependency consistency | `python -m pip check` passed |
| Runtime advisory audit | `pip-audit --strict -r requirements.txt` reported no known vulnerabilities across 7 resolved runtime packages |
| Windows launchers | Both `START_SERVER.bat --help` and `START_CLIENT.bat --help` completed successfully |
| Private-file/token heuristics | Candidate Git-file scan passed; real database, sidecars, keys, logs, environments, backups and uploads excluded |
| Screenshots | Three actual offscreen widget captures generated, opened, and visually inspected |

A PyPI audit checks its available advisory data, not every upstream native-library
issue. In particular, it does not establish a comprehensive security assessment of
the bundled Qt libraries. The project has no independent penetration-test result.

## Test coverage by behaviour

- Authentication: administrator provisioning, valid/invalid logins, randomized
  Argon2id salts, correct/incorrect password verification, legacy hash migration
  preserving messages, input validation, duplicate usernames, per-IP throttling,
  logout/relogin, explicit bootstrap and data-preserving local password recovery.
- Authorization: unauthenticated/employee admin attempts, forged identity/role
  fields, nonmember history/sends, owner membership requirement, live block/role
  changes, manager ownership scope, global audit restriction, role escalation,
  self-modification protection, guests, archives, and removed membership.
- TCP: malformed JSON/envelopes/UTF-8, duplicate keys, non-finite/huge numbers,
  byte-by-byte fragmentation, coalesced frames, truncation, frame deadlines,
  oversized headers before body reads, per-connection limits, idle expiry, and
  isolation of malformed clients from the server.
- SQLite/messaging: atomic membership changes, foreign-key rollback, chat cascades,
  preserved user references, audit-write rollback, four simultaneous senders,
  per-sender sequence, monotonic IDs, history cursors, Unicode byte limits, and
  persistence after server/client restart.
- TLS: verified encrypted round trip, untrusted certificate rejection, wrong peer
  name rejection, remote plaintext refusal, certificate overwrite refusal.
- GUI: validation/invalid-login feedback, two real TCP-backed windows exchanging
  text, literal HTML display, composer state on disconnect, event-loop ticks while
  a deliberately delayed request runs on a worker, GUI-thread signal delivery,
  admin/member loading, duplicate send suppression, multi-page refresh bursts, and
  reauthentication replacing the previous window without stale account state.
- Resource lifecycle: teardown asserts no listener thread, tracked worker, socket,
  or authenticated registry entry remains; cancelled connection attempts do not
  restore sockets. Resource/unraisable/thread exceptions fail the suite.

Tests primarily use real SQLite/TCP/TLS connections. The deliberately slow login
transport and simulated audit failure are focused test doubles for GUI scheduling
and rollback, not substitutes for the integration suite. No coverage percentage is
claimed; behaviour and failure boundaries are the test criteria.

## Measured local workload

`python -m scripts.benchmark` created eight clients, logged them in sequentially,
and sent 80 messages through eight concurrent send loops. All 80 persisted.
This is one short local sample, not a capacity or latency guarantee.

| Measurement | Result |
| --- | ---: |
| Listener startup (after database/auth initialization) | 1.75 ms |
| Connect plus Argon2id login, median | 74.89 ms |
| Send through durable ACK, median | 61.33 ms |
| Send through durable ACK, p95 | 64.19 ms |
| Latest 20-message history page | 5.07 ms |
| Shutdown | 0.48 ms |
| Total workload including data setup | 1.38 s |
| Tracked connections / workers after shutdown | 0 / 0 |

`EXPLAIN QUERY PLAN` selected `idx_messages_chat_id (chat_id=? AND id<?)`.
The benchmark verifies cleanup but does not profile process RSS, prolonged disk
usage, WAN behaviour, distributed abuse, or enterprise-scale concurrency.

## End-to-end scenario

| Requested step | Verification |
| --- | --- |
| Start server | OS-assigned local listeners in integration/GUI fixtures |
| Start client A and create/login user A | Real owner `CREATE_USER`; Qt sign-in and valid-login tests |
| Start client B and create/login user B | Second synthetic account and TCP-backed Qt window |
| Send A → B | Qt composer/Enter integration test and screenshot demo |
| Confirm B receives | Polled history rendered and asserted in the second widget |
| Confirm persistence | SQLite queries and fresh Database instance |
| Restart components / confirm retained history | Real listener restart, new socket, same temporary database |
| Invalid credentials | Backend and Qt sign-in tests |
| Unauthorized action | Role, identity spoofing, and nonmember tests |
| Disconnect/reconnect | Backend restart plus actual Qt reconnect dialog/replacement-window test |
| Clean close | Explicit socket, timer and worker/listener teardown assertions |

These are automated local/offscreen results. No human mouse-driven desktop smoke
test is claimed. Native window decoration, high-DPI behaviour, screen readers,
Linux desktop interaction, and the full first-run SETUP.bat on a clean Windows
machine remain manual/platform checks. SETUP.bat's local dependency installation
was verified through the equivalent package-install commands in this environment.

## CI and publication evidence

The workflow runs six Windows/Linux/Python 3.11–3.13 test jobs and a separate
runtime advisory audit. Local results do not imply those remote jobs passed; use
the actual Actions run for the published commit. The final delivery message records
the commit hash, publication result, and observed CI result. Repository history
was preserved and publication uses a normal push to the confirmed default branch.
