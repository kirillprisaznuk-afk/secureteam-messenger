# Security model

## Intended use and trust boundary

SecureTeam Messenger is a local educational/portfolio application. It has not
received an independent security assessment and is not appropriate for sensitive
real-world communications. Trust the host, server operator, database files,
certificate distribution, and accounts with administrative access.

Controls are designed to resist malformed TCP clients, unauthenticated requests,
nonmember message access, identity spoofing, and lower-role privilege escalation.
They are not intended to resist a compromised endpoint, malicious server/operator,
local filesystem access, or sustained distributed denial of service.

## Implemented controls

- `argon2-cffi.PasswordHasher` uses Argon2id with random salts and the library's
  default RFC 9106 low-memory profile (64 MiB, three passes, parallelism four).
  Password verification uses the library; hash parameters are refreshed at login.
  See the [official PasswordHasher API](https://argon2-cffi.readthedocs.io/en/stable/api.html).
- New passwords contain 12–128 characters; password spaces are preserved. New
  usernames are 3–32 ASCII letters, numbers, dots, underscores, or hyphens.
- Legacy 64-character lowercase SHA-256 hashes are accepted only for migration.
  After successful verification, a conditional update replaces that hash with
  Argon2id. Invalid logins do not change data. Existing short passwords can still
  authenticate; use the local password reset to replace weak credentials.
- An absent username incurs an Argon2 verification against a dummy hash. Login
  failures give the same user-facing error for missing, blocked, or wrong-password
  accounts. Exact timing equivalence across legacy and modern hashes is not claimed.
- Five attempts per IP in a five-minute window; attempts are reserved before
  hashing. Successful authentication clears that IP's counter. The table expires
  entries and is capped at 4,096 IPs; at most two login hashes run concurrently.
- Sessions are server-held identities tied to a single TCP connection, with a fixed
  one-hour lifetime. No bearer token is accepted. Logout/disconnect discards the
  identity; reconnecting requires login. Passwords are not cached for reconnect.
- Every authenticated request reloads the account's block status and role.
  Message reads and sends require membership. Sender IDs/roles supplied by clients
  do not establish identity. Archived conversations reject sends.
- Administrators can manage only lower-ranked accounts, cannot modify their own
  role/block/delete state, and cannot create a second owner through the protocol.
  Organisation administrators cannot modify owners or peer administrators.
- Owners and organisation administrators manage global conversation metadata and
  memberships. Managers can manage only conversations they own, can read the user
  directory for membership selection, and cannot read global audit logs.
- Administrative mutations and their audit entries share one transaction.
  SQLite parameters are bound, foreign keys are enabled, and messages retain their
  authors. The database is a trusted persistence interface, not a public API.
- Frames are bounded to 1 MiB before allocation. JSON objects/envelopes, IDs, roles,
  membership lists, and strings are validated. Duplicate keys, non-finite numbers,
  invalid UTF-8, and unknown frame types are rejected.
- Up to 32 sockets, including unauthenticated/TLS handshakes; five-second handshake,
  120-second idle, ten-second frame/write deadlines; 30 requests/second/connection.
  A protocol violation closes only its connection. Detailed errors stay in
  development logs; normal responses do not contain tracebacks or credentials.

These limits are modest abuse resistance, not a denial-of-service guarantee.
Users behind one NAT share the login limit. Restarting the server resets rate
limits. Anyone with a known valid account can reset their IP's login counter by
signing in. Deployments needing stronger controls need a separate assessment.

## Transport

Loopback TCP is plaintext, including login credentials and messages. The UI labels
this explicitly. Treat unencrypted mode as a local development convenience only.
A non-loopback server bind requires TLS. TLS is provided by Python's standard
`ssl` module with a minimum TLS version of 1.2. The client requires trusted
certificate verification and hostname/IP matching. It has no insecure bypass.
There is no automatic plaintext fallback or STARTTLS negotiation.

### Local development certificate

Install `requirements-dev.txt`, then run:

```bash
python -m scripts.dev_certificate
python run_server.py --cert certs/localhost.pem --key certs/localhost.key
python run_client.py --ca certs/localhost.pem
```

The utility uses the maintained `cryptography` library to generate an RSA-2048
self-signed certificate, valid for 30 days, with `localhost` and `127.0.0.1` subject
alternative names. It refuses to overwrite existing files. To renew, choose a new
output directory with `--output` and update both commands. It is for local demos,
not a public certificate authority. No custom encryption protocol is implemented.

For remote use, provision an appropriate certificate/key, bind with `--host` to
an IPv4 address, and configure clients to trust the issuing CA with `--ca` and to
connect to a matching hostname/IP. Certificate issuance/distribution and host
firewall policy are deployment responsibilities. Never commit private keys.

## Data preservation and recovery

Before upgrading, stop the old server and back up its database. Startup preserves
existing tables/records and creates two indexes; it does not perform a destructive
schema rewrite. Foreign-key enforcement may reveal old orphan records; there is
no automatic deletion/repair. Inspect and resolve them on a backed-up copy before
using affected admin actions. `PRAGMA foreign_key_check` is useful for that review.

On a new database, run `python run_server.py --init-admin`. A hidden password
prompt creates the first owner only when no users exist. There are no default
credentials. On an existing database, use `--reset-password USERNAME` with the
server stopped. This local administrator operation requires filesystem access,
retains user data, and takes effect for new logins. Stop/restart the server to
invalidate all existing sessions. Replace any password used by the old default
account; migrating its hash does not make a weak password stronger.

Database files, sidecars, uploads, backups, keys, logs, and environment files are
ignored by Git. Protect these with OS access controls and appropriate backup
policy. No account data is collected by the benchmark, tests, or screenshot demo;
all three create synthetic data in temporary databases.

## Security features not provided

No end-to-end encryption, message/database encryption at rest, MFA, identity
verification outside account provisioning, public registration, key rotation,
message signing, audit tamper resistance, distributed throttling, or guaranteed
exactly-once delivery. Administrators can grant themselves membership; the server
operator can read plaintext storage. TLS protects the link to the server, not
messages from the server. The audit table records administration, not a complete
immutable security event stream. PyPI advisory audits do not fully assess the
native Qt libraries shipped in PyQt wheels.

## Reporting

Do not post passwords, database files, messages, or private keys in public issues.
For a reproducible non-sensitive defect, provide synthetic steps, Python/OS
versions, and a redacted error. A private disclosure channel has not been configured.
