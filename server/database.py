import datetime
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager


class Database:
    def __init__(self, path: str = "corporate_messenger.db"):
        self.path = path
        self.lock = threading.RLock()
        self._local = threading.local()
        with closing(self._connect()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Nested repository calls share a short-lived transaction on this thread."""
        with self.lock:
            active = getattr(self._local, "connection", None)
            if active is not None:
                yield active
                return
            conn = self._connect()
            self._local.connection = conn
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
            finally:
                self._local.connection = None
                conn.close()

    def _init_db(self):
        with self.transaction() as conn:
            c = conn.cursor()

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner_id INTEGER NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                )
                """
            )

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_members (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id),
                    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    sender_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES users(id)
                )
                """
            )

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    actor_id INTEGER NOT NULL,
                    actor_username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id INTEGER,
                    details TEXT,
                    FOREIGN KEY (actor_id) REFERENCES users(id)
                )
                """
            )

            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id, id)")
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_members_user ON chat_members(user_id, chat_id)"
            )

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")

    def get_user_by_username(self, username: str) -> sqlite3.Row | None:
        with self.transaction() as conn:
            return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def upgrade_password(self, user_id: int, old_hash: str, new_hash: str):
        with self.transaction() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ? AND password_hash = ?",
                (new_hash, user_id, old_hash),
            )

    def user_count(self) -> int:
        with self.transaction() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def get_chat_members(self, chat_id: int) -> list[int]:
        with self.transaction() as conn:
            return [
                row[0]
                for row in conn.execute(
                    "SELECT user_id FROM chat_members WHERE chat_id = ?", (chat_id,)
                )
            ]

    def get_user_by_id(self, user_id: int) -> sqlite3.Row | None:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return c.fetchone()

    def create_user(self, username: str, password_hash: str, role: str) -> int:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, self._now()),
            )
            return c.lastrowid

    def update_user_role(self, user_id: int, role: str):
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))

    def block_user(self, user_id: int):
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET is_blocked = 1 WHERE id = ?", (user_id,))

    def unblock_user(self, user_id: int):
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET is_blocked = 0 WHERE id = ?", (user_id,))

    def delete_user(self, user_id: int):
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def get_all_users(self) -> list[dict]:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("SELECT id, username, role, is_blocked FROM users ORDER BY id LIMIT 1001")
            rows = c.fetchall()
            result = []
            for r in rows:
                result.append(
                    {
                        "id": r["id"],
                        "username": r["username"],
                        "role": r["role"],
                        "is_blocked": bool(r["is_blocked"]),
                        "is_online": False,
                    }
                )
            return result

    def create_chat(self, name: str, owner_id: int) -> int:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO chats (name, owner_id, created_at) VALUES (?, ?, ?)",
                (name, owner_id, self._now()),
            )
            chat_id = c.lastrowid
            c.execute(
                "INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)",
                (chat_id, owner_id),
            )
            return chat_id

    def add_chat_members(self, chat_id: int, member_ids: list[int]):
        if not member_ids:
            return
        with self.transaction() as conn:
            c = conn.cursor()
            c.executemany(
                "INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)",
                [(chat_id, uid) for uid in set(member_ids)],
            )

    def set_chat_members(self, chat_id: int, member_ids: list[int]):
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM chat_members WHERE chat_id = ?", (chat_id,))
            if member_ids:
                c.executemany(
                    "INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)",
                    [(chat_id, uid) for uid in set(member_ids)],
                )

    def get_chat_list_for_user(self, user_id: int) -> list[dict]:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT c.id, c.name, c.archived
                FROM chats c
                JOIN chat_members m ON m.chat_id = c.id
                WHERE m.user_id = ?
                ORDER BY c.id LIMIT 1001
                """,
                (user_id,),
            )
            rows = c.fetchall()
            return [
                {"id": r["id"], "name": r["name"], "archived": bool(r["archived"])} for r in rows
            ]

    def get_chat_messages(
        self, chat_id: int, before_id: int = 2**63 - 1, limit: int = 20
    ) -> list[dict]:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT m.id, m.content, m.created_at, u.username AS sender
                FROM messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.chat_id = ? AND m.id < ?
                ORDER BY m.id DESC LIMIT ?
                """,
                (chat_id, before_id, limit),
            )
            rows = list(reversed(c.fetchall()))
            return [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "created_at": r["created_at"],
                    "sender": r["sender"],
                }
                for r in rows
            ]

    def add_message(self, chat_id: int, sender_id: int, content: str) -> int:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO messages (chat_id, sender_id, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (chat_id, sender_id, content, self._now()),
            )
            return c.lastrowid

    def admin_get_all_chats(self, owner_id: int | None = None) -> list[dict]:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT c.id,
                       c.name,
                       c.archived,
                       u.username AS owner_username,
                       (SELECT COUNT(*) FROM chat_members m WHERE m.chat_id = c.id) AS members_count
                FROM chats c
                JOIN users u ON u.id = c.owner_id
                WHERE (? IS NULL OR c.owner_id = ?)
                ORDER BY c.id LIMIT 1001
                """,
                (owner_id, owner_id),
            )
            rows = c.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "archived": bool(r["archived"]),
                    "owner_username": r["owner_username"],
                    "members_count": r["members_count"],
                }
                for r in rows
            ]

    def admin_get_chat_info(self, chat_id: int) -> dict | None:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
            chat = c.fetchone()
            if not chat:
                return None
            c.execute("SELECT user_id FROM chat_members WHERE chat_id = ?", (chat_id,))
            members = [row["user_id"] for row in c.fetchall()]
            return {
                "id": chat["id"],
                "name": chat["name"],
                "owner_id": chat["owner_id"],
                "archived": bool(chat["archived"]),
                "members": members,
            }

    def admin_create_chat(self, name: str, owner_id: int, members: list[int]) -> int:
        with self.transaction():
            chat_id = self.create_chat(name, owner_id)
            self.add_chat_members(chat_id, list(set(members) | {owner_id}))
            return chat_id

    def admin_update_chat(self, chat_id: int, name: str, members: list[int]):
        with self.transaction() as conn:
            chat = self.admin_get_chat_info(chat_id)
            if not chat:
                raise ValueError("Chat not found")
            conn.execute("UPDATE chats SET name = ? WHERE id = ?", (name, chat_id))
            self.set_chat_members(chat_id, sorted(set(members) | {chat["owner_id"]}))

    def admin_set_chat_archived(self, chat_id: int, archived: bool):
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE chats SET archived = ? WHERE id = ?",
                (1 if archived else 0, chat_id),
            )

    def admin_delete_chat(self, chat_id: int):
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

    def add_audit_entry(
        self,
        actor_id: int,
        actor_username: str,
        action: str,
        target_type: str,
        target_id: int | None,
        details: str = "",
    ):
        """Record an administrative mutation in the caller's transaction."""
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO audit_log
                    (created_at, actor_id, actor_username, action, target_type, target_id, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    actor_id,
                    actor_username,
                    action,
                    target_type,
                    target_id,
                    details,
                ),
            )

    def get_audit_entries(self, limit: int = 200) -> list[dict]:
        with self.transaction() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT id, created_at, actor_id, actor_username,
                       action, target_type, target_id, details
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = c.fetchall()
            return [
                {
                    "id": r["id"],
                    "created_at": r["created_at"],
                    "actor_id": r["actor_id"],
                    "actor_username": r["actor_username"],
                    "action": r["action"],
                    "target_type": r["target_type"],
                    "target_id": r["target_id"],
                    "details": r["details"],
                }
                for r in rows
            ]
