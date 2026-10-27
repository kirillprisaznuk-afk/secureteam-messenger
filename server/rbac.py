"""Server-side capabilities and explicit privilege hierarchy."""

from shared.models import ROLE_RANK, Role

ADMIN_ROLES = {Role.OWNER.value, Role.ORG_ADMIN.value}
CONSOLE_ROLES = ADMIN_ROLES | {Role.DEPARTMENT_MANAGER.value}
RANK = ROLE_RANK


class AccessDenied(PermissionError):
    pass


class RBAC:
    @staticmethod
    def require(condition: bool) -> None:
        if not condition:
            raise AccessDenied("Permission denied")

    @staticmethod
    def can_manage_user(actor, target, new_role: str | None = None) -> bool:
        if actor["role"] not in ADMIN_ROLES or actor["id"] == target["id"]:
            return False
        rank = RANK.get(actor["role"], -1)
        return RANK.get(target["role"], 99) < rank and (
            new_role is None or RANK.get(new_role, 99) < rank
        )

    @staticmethod
    def can_manage_chat(actor, chat) -> bool:
        return actor["role"] in ADMIN_ROLES or (
            actor["role"] == "department_manager" and chat["owner_id"] == actor["id"]
        )
