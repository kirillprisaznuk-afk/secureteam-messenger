"""RBAC"""
from shared.models import Role

class RBAC:
    PERMISSIONS = {
        Role.OWNER: {
            'create_chat', 'delete_chat', 'send_message',
            'create_user', 'delete_user', 'change_role',
            'block_user', 'view_audit_log',
            'view_all_chats', 'view_all_users',
            'update_settings',
        },
        Role.ORG_ADMIN: {
            'create_chat', 'delete_chat', 'send_message',
            'create_user', 'delete_user', 'change_role',
            'block_user', 'view_audit_log',
            'view_all_chats', 'view_all_users',
        },
        Role.DEPARTMENT_MANAGER: {
            'create_chat', 'send_message',
            'manage_department_users', 'view_department_audit',
            'manage_department_chats',
        },
        Role.EMPLOYEE: {
            'create_chat', 'send_message',
        },
        Role.GUEST: {
            'send_message',
        }
    }
    
    @staticmethod
    def has_permission(user_role: Role, permission: str) -> bool:
        if user_role not in RBAC.PERMISSIONS:
            return False
        return permission in RBAC.PERMISSIONS[user_role]
    
    @staticmethod
    def can_access_chat(database, user_id: int, chat_id: int) -> bool:
        members = database.get_chat_members(chat_id)
        return user_id in members
