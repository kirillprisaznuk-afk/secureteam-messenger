# Protocol reference

## Framing and lifecycle

A TCP stream carries repeated `[uint32 big-endian length][JSON bytes]` frames.
Lengths must be 1 through 1,048,576 bytes. Exact reads handle fragmented headers,
fragmented payloads, and multiple frames in one read. A clean EOF between frames
is an orderly disconnect; EOF during a frame is malformed. A frame must finish
within ten seconds of its first byte. Idle sockets expire after 120 seconds.

The envelope has exactly `type` (a known uppercase enum name) and `data` (object).
Unknown envelope fields, invalid UTF-8/JSON, duplicate keys, non-finite numbers,
and invalid shapes are rejected. Application payload fields are validated by
operation; extra payload fields do not establish identity or role. Booleans and
strings are not accepted as integer identifiers. IDs are positive signed-64-bit
integers. New chat names are 1–100 characters, messages 1–10,000 characters with
non-whitespace content, and membership selections at most 100 IDs plus the owner.

There is one response per request and no unsolicited server messages. Clients
must serialize requests on a connection. The server returns type `ACK`:

```json
{"type":"ACK","data":{"success":true,"message_id":42}}
```

```json
{"type":"ACK","data":{"success":false,"code":"FORBIDDEN","error":"Permission denied"}}
```

Protocol violations receive `INVALID_FRAME` where a write is possible, then the
socket closes. A request rate violation receives `RATE_LIMITED`, then closes.
Capacity overflow closes the newly accepted socket. Silent peers may simply time
out; reconnect and authenticate. There are no request IDs, resumable sessions, or
automatic retries.

## Requests

| Type | Required / optional data | Response on success | Scope |
| --- | --- | --- | --- |
| `LOGIN` | `username`, `password` | `user_id`, `username`, `role` | Unauthenticated connection only |
| `LOGOUT` | `{}` | success | Authenticated; clears connection identity |
| `GET_CHAT_LIST` | `{}` | `chats`, `truncated` | Membership only |
| `CREATE_CHAT` | `name` | `chat_id` | Every role except guest; creator is sole initial member |
| `TEXT_MESSAGE` | `chat_id`, `content` | `message_id` | Current member; not archived |
| `GET_CHAT_HISTORY` | `chat_id`; optional `before_id` | `messages`, `has_more`, `next_before_id` | Current member |
| `GET_ALL_USERS` | `{}` | `users`, `truncated` | Owner, org admin, manager; no hashes returned |
| `CREATE_USER` | `username`, `password`; optional `role` (employee) | `user_id` | Owner/org admin, strictly lower role |
| `UPDATE_USER` | `user_id`, `role` | success | Strictly lower account and resulting role; not self |
| `BLOCK_USER` / `UNBLOCK_USER` / `DELETE_USER` | `user_id` | success | Strictly lower account; not self |
| `ADMIN_GET_ALL_CHATS` | `{}` | `chats`, `truncated` | Owner/org admin; managers see owned chats |
| `ADMIN_GET_CHAT_INFO` | `chat_id` | `chat` with membership IDs | Global admins or chat-owning manager |
| `ADMIN_CREATE_CHAT` | `name`; optional `members` | `chat_id` | Owner/org admin/manager |
| `ADMIN_UPDATE_CHAT` | `chat_id`, `name`; optional `members` | success | Global admins or chat-owning manager |
| `ADMIN_ARCHIVE_CHAT` / `ADMIN_UNARCHIVE_CHAT` / `ADMIN_DELETE_CHAT` | `chat_id` | success | Global admins or chat-owning manager |
| `PING` | `{}` | `message: pong` | Authenticated |
| `PING` | `audit: true`; optional `limit` (1–500, default 200) | `entries` | Owner/org admin |

`FILE_TRANSFER` is a reserved historical name and returns `UNSUPPORTED` after
authentication. `ACK` is response-only and is not a valid application request.
The existing `PING` audit convention is retained for client compatibility.

History message objects contain `id`, `content`, `created_at` (UTC ISO timestamp),
and `sender` (username). Use `next_before_id` to obtain older messages until it is
null; prepend older pages. A page contains at most 20 messages. The byte limit
can reduce this count for large Unicode text. A legacy individual message larger
than the protocol limit returns a maintenance error; it is not deleted.
List endpoints cap output at 1,000 records and expose `truncated`; lists do not yet
have cursor pagination. Audit results are newest-first, message pages oldest-first.

## Authentication, errors, and transport

After login, the server associates the socket with a user ID for one hour. A client
cannot choose another user ID by sending a field or token. Repeated login on an
authenticated connection gives `ALREADY_AUTHENTICATED`. Logout removes identity.
`SESSION_EXPIRED` closes the connection; a deleted/blocked account receives
`NOT_AUTHENTICATED` and loses its connection identity.

Error codes: `INVALID_CREDENTIALS`, `NOT_AUTHENTICATED`, `ALREADY_AUTHENTICATED`,
`SESSION_EXPIRED`, `FORBIDDEN`, `BAD_REQUEST`, `CONFLICT`, `DATABASE_ERROR`,
`INTERNAL_ERROR`, `UNSUPPORTED`, `INVALID_FRAME`, `RATE_LIMITED`, `BUSY`, and
`RESPONSE_TOO_LARGE`. Client transport failures use `DISCONNECTED` locally.
Validation/storage errors do not normally close a healthy framed connection.
Never automatically resend a write after a lost ACK; its transaction may already
have committed. This protocol does not guarantee deduplication after reconnect.

TLS wraps the entire stream from connection establishment when configured. There
is no TLS upgrade frame or encryption inside JSON. The framing/type names preserve
the original protocol's shape, with stricter validation, access checks, error
codes, and bounded history. Upgrade client and server together for the full UX.
