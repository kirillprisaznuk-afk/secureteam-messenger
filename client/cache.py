from typing import Dict, List, Optional
from collections import OrderedDict
import client.config as config

class ClientCache:
    def __init__(self, max_size: int = config.MAX_CACHE_SIZE):
        self.max_size = max_size
        self.chats = {}
        self.messages = {}
    
    def add_chat(self, chat_id: int, chat_data: dict):
        self.chats[chat_id] = chat_data
        if chat_id not in self.messages:
            self.messages[chat_id] = OrderedDict()
    
    def get_messages(self, chat_id: int) -> List[dict]:
        return list(self.messages.get(chat_id, {}).values())
    
    def clear(self):
        self.chats.clear()
        self.messages.clear()
