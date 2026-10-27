"""Roles understood by the server and desktop administration interface."""

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ORG_ADMIN = "org_admin"
    DEPARTMENT_MANAGER = "department_manager"
    EMPLOYEE = "employee"
    GUEST = "guest"


ROLE_RANK = {"guest": 0, "employee": 1, "department_manager": 2, "org_admin": 3, "owner": 4}
