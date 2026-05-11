from typing import Callable

from app.permissions.policies import (
    PermissionPolicyError,
    allowed_permission_levels,
    can_access_permission,
    ensure_allowed_permission,
)


def _assert_raises(
    expected_error: type[Exception],
    message: str,
    callback: Callable[[], object],
) -> None:
    try:
        callback()
    except expected_error as exc:
        assert message in str(exc)
    else:
        raise AssertionError(f"Expected {expected_error.__name__} to be raised.")


def test_role_permission_hierarchy() -> None:
    assert allowed_permission_levels("guest") == ["public"]
    assert allowed_permission_levels("developer") == ["public", "developer"]
    assert allowed_permission_levels("data_analyst") == ["public", "developer", "analytics"]
    assert allowed_permission_levels("admin") == ["public", "developer", "analytics", "admin"]


def test_permission_checks_do_not_escalate_role() -> None:
    assert can_access_permission("developer", "developer")
    assert not can_access_permission("developer", "analytics")


def test_allowed_permissions_returns_copy() -> None:
    permissions = allowed_permission_levels("guest")
    permissions.append("admin")

    assert allowed_permission_levels("guest") == ["public"]


def test_unknown_role_is_rejected() -> None:
    _assert_raises(
        PermissionPolicyError,
        "Unknown role",
        lambda: allowed_permission_levels("owner"),
    )


def test_ensure_allowed_permission_raises_for_forbidden_level() -> None:
    _assert_raises(
        PermissionPolicyError,
        "cannot access",
        lambda: ensure_allowed_permission("guest", "developer"),
    )
