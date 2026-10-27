"""Conversation operations run inside the router's database transaction."""

import json

from server.rbac import RBAC
from shared import validation
from shared.constants import HISTORY_PAGE_SIZE, MAX_FRAME_SIZE


class MessageHandler:
    def __init__(self, database):
        self.db = database

    def chat_for_member(self, user_id: int, chat_id: int) -> dict:
        chat = self.db.admin_get_chat_info(chat_id)
        RBAC.require(chat is not None and user_id in chat["members"])
        return chat

    def history(self, user_id: int, data: dict) -> dict:
        chat_id = validation.identifier(data.get("chat_id"))
        self.chat_for_member(user_id, chat_id)
        before = validation.identifier(data.get("before_id", 2**63 - 1))
        rows = self.db.get_chat_messages(chat_id, before, HISTORY_PAGE_SIZE + 1)
        has_more = len(rows) > HISTORY_PAGE_SIZE
        rows = rows[-HISTORY_PAGE_SIZE:]
        # Unicode escaping can expand a valid message to 120 KB on the wire.
        while len(rows) > 1 and len(json.dumps(rows).encode()) > MAX_FRAME_SIZE - 1024:
            rows.pop(0)
            has_more = True
        if len(json.dumps(rows).encode()) > MAX_FRAME_SIZE - 1024:
            raise ValueError(
                "Legacy message exceeds the protocol limit; local database maintenance is required"
            )
        return {
            "success": True,
            "messages": rows,
            "has_more": has_more,
            "next_before_id": rows[0]["id"] if rows and has_more else None,
        }

    def send(self, user_id: int, data: dict) -> dict:
        chat_id = validation.identifier(data.get("chat_id"))
        chat = self.chat_for_member(user_id, chat_id)
        if chat["archived"]:
            raise ValueError("Archived conversations are read-only")
        content = validation.content(data.get("content"))
        message_id = self.db.add_message(chat_id, user_id, content)
        return {"success": True, "message_id": message_id}
