import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.core.company_context import get_current_company_id
from app.core.roles import ROLE_COMPANY_OWNER, ROLE_SUPER_ADMIN
from app.core.zoned_sessions import (
    COMPANY_SESSION_COOKIE,
    ZONE_COMPANY,
    build_session_payload,
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


if __name__ == "__main__":
    unittest.main()
