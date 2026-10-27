# Initial audit and scope

## Baseline

Inspection started from commit `6a04546` on `master`, with a clean working tree and
origin pointing to the requested `kirillprisaznuk-afk/secureteam-messenger` repository.
There were 35 tracked files. A subsequent fetch found an existing README-only
commit, `02a52c7`, and it was fast-forwarded before the documentation rewrite;
remote history was preserved.

No `AGENTS.md`, tests, Ruff configuration, package metadata, or CI were present.
The local checkout initially lacked a README; the remote README described SHA-256
and prototype limitations. An ignored account database, uploads, and backups were
present locally and were left untouched. They were not used for tests or demos.

The default Windows `python` command was an unusable Store alias. The available
bundled Python 3.12.14 compiled the original source successfully. Baseline pytest
and Ruff could not initially run because neither was installed, and no tests
existed. A project-local environment was created; the bundled interpreter needed
`pip --python .venv` to seed its missing pip rather than the usual `ensurepip`.
After installing tools, Ruff was run on a saved copy of the original tracked source
using the chosen final rule set: **75 findings** (22 import sorting, 6 deprecated
imports, 5 unused imports, 18 collection annotations, 14 optional annotations,
1 wildcard import, and 9 wildcard-derived undefined-name checks).
There is no pre-existing passing test baseline to claim.

The sandbox initially blocked dependency DNS and localhost sockets. Authorized
network/test commands were run outside it. Early test failures from temp-directory
permissions and socket restrictions were environmental, not hidden or counted as
application successes. Temporary test data was redirected to an ignored workspace
folder for local verification. Normal CI uses pytest's standard temporary folder.

## Real original architecture

| Area | Actual runtime behaviour |
| --- | --- |
| Entry points | `run_server.py` started `MessengerServer`; `run_client.py` connected synchronously, then opened login and messenger dialogs |
| Server | Thread-per-client socket loop plus a large routing function; a socket-to-user dictionary held identity |
| Protocol | Four-byte length header and JSON type/data envelope; exact reads existed, but there were no byte limits/deadlines/shape checks |
| Authentication | SHA-256 of the supplied password compared in SQL; empty databases received a hardcoded owner account |
| Authorization | Ad hoc role checks for admin routes; message history/sends had no membership checks; active block state was not rechecked |
| Persistence | Five SQLite tables, parameterized queries, new connections per call and an RLock; connection contexts committed but did not explicitly close connections |
| Client | Blocking request/response socket wrapper; GUI timers made synchronous history/list requests |
| GUI | Dark PyQt5 login, conversation list, single-line composer, and user/chat/audit admin tabs; polling rather than push |
| Administration | User creation/role/block/delete; chat rename/members/archive/delete; audit writes after changes in separate transactions |
| Alternate modules | Token auth, AES-CBC, file upload, copy-based backup, cache, dataclasses, and a chat-widget stub were unused or incompatible with the live database API |
| Dependencies | PyQt5, old cryptography pin used only by disconnected code, and unused python-dotenv |
| Delivery | Messages stored in plaintext; no implemented transport TLS or end-to-end encryption |
| Git/launch | No tracked databases/secrets found in the initial file list; launchers assumed global Python, exposed default credentials, and depended on the current directory |

The project was an existing text/group-conversation messenger with administrator
provisioning. Public self-registration, working file transfer, integrated backup,
read receipts, and an active encryption path were not implemented features.

## Severity classification

| Severity | Finding | Final treatment |
| --- | --- | --- |
| CRITICAL | Any authenticated client could read/send to guessed chat IDs | Membership checked transactionally on every read/send; forged identity tests |
| CRITICAL | Shared default owner credential and unsalted fast hashes | Explicit hidden-prompt bootstrap, Argon2id, login migration and local reset |
| HIGH | Unbounded frame length and unvalidated JSON shapes | 1 MiB limit, strict envelopes, structured errors and frame deadlines |
| HIGH | Blocked sessions retained authority; loose role changes could grant excessive privileges | Live account checks, strict role hierarchy, self/owner protection |
| HIGH | Manager admin routes exposed unrelated chat management and global audit | Owned-conversation scope and no global audit access |
| HIGH | Admin changes/audit and chat/membership edits were not atomic | Shared nested transactions and rollback tests |
| HIGH | SQLite foreign keys disabled; sockets/dictionaries lacked consistent ownership/shutdown | FK enforcement, explicit close, bounded workers and synchronized registries |
| HIGH | GUI could hang on indefinite socket waits | Background Qt controller, bounded sockets, coalesced actions and disconnect flow |
| HIGH | External plaintext listener exposed credentials/messages | Loopback default; remote binds require verified TLS configuration |
| MEDIUM | Competing unused auth/encryption/data paths implied unsupported functionality | Consolidated live modules; removed dead implementations and misleading fields |
| MEDIUM | Unlimited histories and missing query indexes | Cursor paging, byte-bounded Unicode pages and query indexes |
| MEDIUM | Broad exception handling and raw server errors | Stable error codes, generic storage/internal messages, diagnostic logging |
| LOW | Prototype naming/default-password hints, weak launch experience, no evidence/docs/CI | Consistent UI, explicit setup, screenshots, professional docs and checks |

## Preservation and deliberate changes

TCP, SQLite, PyQt5, roles, existing conversation data, and live admin capabilities
remain. Unsafe access is intentionally narrowed. Managers are scoped by ownership
because the schema has no department entity. Owners cannot create peer owners via
the protocol; ownership transfer is outside scope. Credentials and ignored user
data were never reset as part of this task. Legacy orphan rows are not silently
repaired; enforced foreign keys may reveal existing integrity problems.
