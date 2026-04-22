import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.core.company_context import get_current_company_id
from app.core.roles import (
    PERM_MANAGE_COMPANY_SETTINGS,
    PERM_MANAGE_EMPLOYEES,
    PERM_MANAGE_LOCATIONS,
    PERM_MANAGE_TERMINALS,
    PERM_MANAGE_USERS,
    ROLE_COMPANY_ADMIN,
    ROLE_COMPANY_OWNER,
    ROLE_SUPER_ADMIN,
)
from app.core.security import has_permission
from app.core.zoned_sessions import (
    COMPANY_SESSION_COOKIE,
    ROLE_SESSION_COOKIE_NAMES,
    ZONE_COMPANY,
    build_session_payload,
    read_role_session,
    read_zone_session,
    serializer,
)


class SecurityContextTests(unittest.TestCase):
    def test_rejects_role_in_wrong_zone_cookie(self):
        platform_payload = build_session_payload(
            user_id=1,
            username="platform",
            role=ROLE_SUPER_ADMIN,
            company_id=None,
            auth_source="test",
        )
        request = SimpleNamespace(
            cookies={
                COMPANY_SESSION_COOKIE: serializer.dumps(platform_payload),
            }
        )

        self.assertIsNone(read_zone_session(request, ZONE_COMPANY))

    def test_platform_user_requires_selected_company(self):
        request = SimpleNamespace(
            session={
                "authenticated": True,
                "username": "superadmin",
                "role": ROLE_SUPER_ADMIN,
                "company_id": None,
            }
        )

        with self.assertRaises(HTTPException) as exc:
            get_current_company_id(request)

        self.assertEqual(exc.exception.status_code, 403)

    def test_platform_user_uses_explicit_selected_company(self):
        request = SimpleNamespace(
            session={
                "authenticated": True,
                "username": "superadmin",
                "role": ROLE_SUPER_ADMIN,
                "company_id": None,
                "selected_company_id": 42,
            }
        )

        self.assertEqual(get_current_company_id(request), 42)

    def test_company_user_uses_own_company(self):
        request = SimpleNamespace(
            session={
                "authenticated": True,
                "username": "owner",
                "role": ROLE_COMPANY_OWNER,
                "company_id": 7,
            }
        )

        self.assertEqual(get_current_company_id(request), 7)

    def test_role_cookie_keeps_company_owner_and_admin_separate(self):
        owner_payload = build_session_payload(
            user_id=1,
            username="owner",
            role=ROLE_COMPANY_OWNER,
            company_id=7,
            auth_source="test",
        )
        admin_payload = build_session_payload(
            user_id=2,
            username="admin",
            role=ROLE_COMPANY_ADMIN,
            company_id=7,
            auth_source="test",
        )
        request = SimpleNamespace(
            cookies={
                ROLE_SESSION_COOKIE_NAMES[ROLE_COMPANY_OWNER]: serializer.dumps(owner_payload),
                ROLE_SESSION_COOKIE_NAMES[ROLE_COMPANY_ADMIN]: serializer.dumps(admin_payload),
            }
        )

        self.assertIsNone(read_zone_session(request, ZONE_COMPANY))
        self.assertEqual(read_role_session(request, ROLE_COMPANY_OWNER)["username"], "owner")
        self.assertEqual(
            read_zone_session(request, ZONE_COMPANY, ROLE_COMPANY_ADMIN)["username"],
            "admin",
        )

    def test_company_admin_has_limited_permissions(self):
        admin_user = {"role": ROLE_COMPANY_ADMIN}

        self.assertTrue(has_permission(admin_user, PERM_MANAGE_EMPLOYEES))
        self.assertTrue(has_permission(admin_user, PERM_MANAGE_COMPANY_SETTINGS))
        self.assertTrue(has_permission(admin_user, PERM_MANAGE_LOCATIONS))
        self.assertTrue(has_permission(admin_user, PERM_MANAGE_TERMINALS))
        self.assertFalse(has_permission(admin_user, PERM_MANAGE_USERS))

    def test_company_owner_has_company_settings_permission(self):
        owner_user = {"role": ROLE_COMPANY_OWNER}

        self.assertTrue(has_permission(owner_user, PERM_MANAGE_COMPANY_SETTINGS))


if __name__ == "__main__":
    unittest.main()
