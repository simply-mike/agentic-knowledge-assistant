ROLE_PERMISSIONS: dict[str, list[str]] = {
    "guest": ["public"],
    "developer": ["public", "developer"],
    "data_analyst": ["public", "developer", "analytics"],
    "admin": ["public", "developer", "analytics", "admin"],
}


class PermissionPolicyError(ValueError):
    pass


def allowed_permission_levels(role: str) -> list[str]:
    try:
        return list(ROLE_PERMISSIONS[role])
    except KeyError as exc:
        raise PermissionPolicyError(f"Unknown role: {role}") from exc


def can_access_permission(role: str, permission_level: str) -> bool:
    return permission_level in allowed_permission_levels(role)


def ensure_allowed_permission(role: str, permission_level: str) -> None:
    if not can_access_permission(role, permission_level):
        raise PermissionPolicyError(
            f"Role {role} cannot access permission level {permission_level}."
        )
