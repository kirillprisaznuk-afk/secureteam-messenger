"""Validated request routing, authorization, and atomic audited administration."""

import logging
import sqlite3

from server.auth import AuthManager, hash_password
from server.message_handler import MessageHandler
from server.rbac import ADMIN_ROLES, CONSOLE_ROLES, RANK, RBAC, AccessDenied
from shared import validation
from shared.constants import MAX_LIST_SIZE
from shared.protocol import MessageType as T

log = logging.getLogger(__name__)


def error(code: str, message: str) -> dict:
    return {"success": False, "code": code, "error": message}


class RequestRouter:
    def __init__(self, database, online_users):
        self.db = database
        self.auth = AuthManager(database)
        self.messaging = MessageHandler(database)
        self.online_users = online_users

    def process(self, kind: T, data: dict, user_id: int | None, ip: str) -> dict:
        try:
            if kind == T.LOGIN:
                if user_id is not None:
                    return error("ALREADY_AUTHENTICATED", "Sign out before changing accounts")
                return self.auth.login(data.get("username"), data.get("password"), ip)
            if user_id is None:
                return error("NOT_AUTHENTICATED", "Sign in to continue")
            with self.db.transaction():
                actor = self.db.get_user_by_id(user_id)
                if not actor or actor["is_blocked"] or actor["role"] not in RANK:
                    return error("NOT_AUTHENTICATED", "Account is unavailable; sign in again")
                return self._authenticated(kind, data, actor)
        except AccessDenied:
            return error("FORBIDDEN", "Permission denied")
        except ValueError as exc:
            return error("BAD_REQUEST", str(exc))
        except sqlite3.IntegrityError:
            return error(
                "CONFLICT", "Duplicate name or referenced record; check the selected users"
            )
        except sqlite3.Error:
            log.exception("Database request failed (%s)", kind.name)
            return error("DATABASE_ERROR", "Storage unavailable; try again later")
        except Exception:
            log.exception("Unexpected request failure (%s)", kind.name)
            return error("INTERNAL_ERROR", "Request could not be completed")

    @staticmethod
    def bounded_list(key: str, rows: list) -> dict:
        return {"success": True, key: rows[:MAX_LIST_SIZE], "truncated": len(rows) > MAX_LIST_SIZE}

    def _authenticated(self, kind: T, data: dict, actor) -> dict:
        uid, role = actor["id"], actor["role"]
        if kind == T.LOGOUT:
            return {"success": True}
        if kind == T.PING:
            if data.get("audit"):
                RBAC.require(role in ADMIN_ROLES)
                limit = data.get("limit", 200)
                if type(limit) is not int or not 1 <= limit <= 500:
                    raise ValueError("Audit limit must be between 1 and 500")
                return {"success": True, "entries": self.db.get_audit_entries(limit)}
            return {"success": True, "message": "pong"}
        if kind == T.GET_CHAT_LIST:
            return self.bounded_list("chats", self.db.get_chat_list_for_user(uid))
        if kind == T.GET_CHAT_HISTORY:
            return self.messaging.history(uid, data)
        if kind == T.TEXT_MESSAGE:
            return self.messaging.send(uid, data)
        if kind == T.CREATE_CHAT:
            RBAC.require(role != "guest")
            name = validation.text(data.get("name"), "Chat name")
            cid = self.db.create_chat(name, uid)
            self._audit(actor, "chat.create", "chat", cid)
            return {"success": True, "chat_id": cid}
        if kind == T.GET_ALL_USERS:
            RBAC.require(role in CONSOLE_ROLES)
            users = self.db.get_all_users()
            online = self.online_users()
            for user in users:
                user["is_online"] = user["id"] in online
            return self.bounded_list("users", users)
        if kind == T.CREATE_USER:
            RBAC.require(role in ADMIN_ROLES)
            username = validation.username(data.get("username"))
            password = validation.password(data.get("password"))
            new_role = validation.role(data.get("role", "employee"))
            RBAC.require(RANK[new_role] < RANK[role])
            target = self.db.create_user(username, hash_password(password), new_role)
            self._audit(actor, "user.create", "user", target)
            return {"success": True, "user_id": target}
        if kind in {T.UPDATE_USER, T.BLOCK_USER, T.UNBLOCK_USER, T.DELETE_USER}:
            target_id = validation.identifier(data.get("user_id"))
            target = self.db.get_user_by_id(target_id)
            RBAC.require(target is not None)
            new_role = validation.role(data.get("role")) if kind == T.UPDATE_USER else None
            RBAC.require(RBAC.can_manage_user(actor, target, new_role))
            if kind == T.UPDATE_USER:
                self.db.update_user_role(target_id, new_role)
            elif kind == T.BLOCK_USER:
                self.db.block_user(target_id)
            elif kind == T.UNBLOCK_USER:
                self.db.unblock_user(target_id)
            else:
                self.db.delete_user(target_id)
            action = {
                T.UPDATE_USER: "user.change_role",
                T.BLOCK_USER: "user.block",
                T.UNBLOCK_USER: "user.unblock",
                T.DELETE_USER: "user.delete",
            }[kind]
            self._audit(actor, action, "user", target_id)
            return {"success": True}
        if kind == T.ADMIN_GET_ALL_CHATS:
            RBAC.require(role in CONSOLE_ROLES)
            chats = self.db.admin_get_all_chats(uid if role == "department_manager" else None)
            return self.bounded_list("chats", chats)
        if kind == T.ADMIN_CREATE_CHAT:
            RBAC.require(role in CONSOLE_ROLES)
            name = validation.text(data.get("name"), "Chat name")
            members = validation.members(data.get("members", []))
            cid = self.db.admin_create_chat(name, uid, members)
            self._audit(actor, "chat.create", "chat", cid)
            return {"success": True, "chat_id": cid}
        if kind in {
            T.ADMIN_GET_CHAT_INFO,
            T.ADMIN_UPDATE_CHAT,
            T.ADMIN_ARCHIVE_CHAT,
            T.ADMIN_UNARCHIVE_CHAT,
            T.ADMIN_DELETE_CHAT,
        }:
            cid = validation.identifier(data.get("chat_id"))
            chat = self.db.admin_get_chat_info(cid)
            RBAC.require(chat is not None and RBAC.can_manage_chat(actor, chat))
            if kind == T.ADMIN_GET_CHAT_INFO:
                return {"success": True, "chat": chat}
            if kind == T.ADMIN_UPDATE_CHAT:
                name = validation.text(data.get("name"), "Chat name")
                members = validation.members(data.get("members", []))
                self.db.admin_update_chat(cid, name, members)
            elif kind == T.ADMIN_DELETE_CHAT:
                self.db.admin_delete_chat(cid)
            else:
                self.db.admin_set_chat_archived(cid, kind == T.ADMIN_ARCHIVE_CHAT)
            action = {
                T.ADMIN_UPDATE_CHAT: "chat.update",
                T.ADMIN_DELETE_CHAT: "chat.delete",
                T.ADMIN_ARCHIVE_CHAT: "chat.archive",
                T.ADMIN_UNARCHIVE_CHAT: "chat.unarchive",
            }[kind]
            self._audit(actor, action, "chat", cid)
            return {"success": True}
        return error("UNSUPPORTED", "Unsupported request type")

    def _audit(self, actor, action: str, target_type: str, target_id: int):
        self.db.add_audit_entry(actor["id"], actor["username"], action, target_type, target_id)
