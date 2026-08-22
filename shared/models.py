from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class Role(Enum):
    OWNER = "owner"
    ORG_ADMIN = "org_admin"
    DEPARTMENT_MANAGER = "department_manager"
    EMPLOYEE = "employee"
    GUEST = "guest"

class MessageStatus(Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

@dataclass
class User:
    id: int
    username: str
    role: Role
    is_blocked: bool = False
    is_online: bool = False
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None

@dataclass
class Message:
    id: int
    chat_id: int
    user_id: int
    username: str
    content: str
    timestamp: datetime
    status: MessageStatus = MessageStatus.SENT
    is_encrypted: bool = True
    file_name: Optional[str] = None
    file_size: Optional[int] = None

@dataclass
class Chat:
    id: int
    name: str
    created_by: int
    created_at: datetime
    members: List[int] = field(default_factory=list)
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0

@dataclass
class AuditEntry:
    id: int
    user_id: Optional[int]
    username: str
    action: str
    details: str
    ip_address: str
    timestamp: datetime
