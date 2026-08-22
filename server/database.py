import sqlite3
import threading
import datetime
from typing import Optional, List, Dict


class Database:
    def __init__(self, path: str = "corporate_messenger.db"):
        self.path = path
        self.lock = threading.RLock()
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.lock, self._connect() as conn:
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

            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.datetime.utcnow().isoformat()


    def verify_user(self, username: str, password_hash: str) -> Optional[sqlite3.Row]:
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_blocked = 0",
                (username, password_hash),
            )
            return c.fetchone()

    def get_user_by_id(self, user_id: int) -> Optional[sqlite3.Row]:
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return c.fetchone()

    def create_user(self, username: str, password_hash: str, role: str) -> int:
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, password_hash, role, created_at) "
                "VALUES (?, ?, ?, ?)",
                (username, password_hash, role, self._now()),
            )
            conn.commit()
            return c.lastrowid

    def update_user_role(self, user_id: int, role: str):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            conn.commit()

    def block_user(self, user_id: int):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET is_blocked = 1 WHERE id = ?", (user_id,))
            conn.commit()

    def unblock_user(self, user_id: int):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET is_blocked = 0 WHERE id = ?", (user_id,))
            conn.commit()

    def delete_user(self, user_id: int):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def get_all_users(self) -> List[Dict]:
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users ORDER BY id")
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
        with self.lock, self._connect() as conn:
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
            conn.commit()
            return chat_id

    def add_chat_members(self, chat_id: int, member_ids: List[int]):
        if not member_ids:
            return
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.executemany(
                "INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)",
                [(chat_id, uid) for uid in set(member_ids)],
            )
            conn.commit()

    def set_chat_members(self, chat_id: int, member_ids: List[int]):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM chat_members WHERE chat_id = ?", (chat_id,))
            if member_ids:
                c.executemany(
                    "INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)",
                    [(chat_id, uid) for uid in set(member_ids)],
                )
            conn.commit()

    def get_chat_list_for_user(self, user_id: int) -> List[Dict]:
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT c.id, c.name, c.archived
                FROM chats c
                JOIN chat_members m ON m.chat_id = c.id
                WHERE m.user_id = ?
                ORDER BY c.id
                """,
                (user_id,),
            )
            rows = c.fetchall()
            return [
                {"id": r["id"], "name": r["name"], "archived": bool(r["archived"])}
                for r in rows
            ]

    def get_chat_messages(self, chat_id: int) -> List[Dict]:
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT m.id, m.content, m.created_at, u.username AS sender
                FROM messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.chat_id = ?
                ORDER BY m.id
                """,
                (chat_id,),
            )
            rows = c.fetchall()
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
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO messages (chat_id, sender_id, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (chat_id, sender_id, content, self._now()),
            )
            conn.commit()
            return c.lastrowid

    def admin_get_all_chats(self) -> List[Dict]:
        with self.lock, self._connect() as conn:
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
                ORDER BY c.id
                """
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

    def admin_get_chat_info(self, chat_id: int) -> Optional[Dict]:
        with self.lock, self._connect() as conn:
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

    def admin_create_chat(self, name: str, owner_id: int, members: List[int]) -> int:
        chat_id = self.create_chat(name, owner_id)
        all_members = set(members)
        all_members.add(owner_id)
        self.add_chat_members(chat_id, list(all_members))
        return chat_id

    def admin_update_chat(self, chat_id: int, name: str, members: List[int]):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("UPDATE chats SET name = ? WHERE id = ?", (name, chat_id))
            conn.commit()
        self.set_chat_members(chat_id, members)

    def admin_set_chat_archived(self, chat_id: int, archived: bool):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE chats SET archived = ? WHERE id = ?",
                (1 if archived else 0, chat_id),
            )
            conn.commit()

    def admin_delete_chat(self, chat_id: int):
        with self.lock, self._connect() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            conn.commit()

    def add_audit_entry(
        self,
        actor_id: int,
        actor_username: str,
        action: str,
        target_type: str,
        target_id: Optional[int],
        details: str = "",
    ):
        """
        action: 'user.create', 'user.block', 'chat.create', 'chat.update_members' и т.п.
        target_type: 'user' или 'chat'.
        """
        with self.lock, self._connect() as conn:
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
            conn.commit()

    def get_audit_entries(self, limit: int = 200) -> List[Dict]:

        with self.lock, self._connect() as conn:
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
