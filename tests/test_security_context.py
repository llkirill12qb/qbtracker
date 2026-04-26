import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.company_context import get_current_company_id
from app.core.auth import is_login_allowed_for_user
from app.core.roles import (
    PERM_MANAGE_COMPANY_SETTINGS,
    PERM_MANAGE_EMPLOYEES,
    PERM_MANAGE_LOCATIONS,
    PERM_MANAGE_TERMINALS,
    PERM_MANAGE_USERS,
    PERM_VIEW_DASHBOARD,
    ROLE_COMPANY_ADMIN,
    ROLE_COMPANY_OWNER,
    ROLE_SUPER_ADMIN,
)
from app.core.security import has_permission, require_permission
from app.crud.company_contact_crud import get_primary_company_contact, upsert_primary_company_contact
from app.crud.employee_crud import (
    build_qr_payload,
    create_employee,
    get_employee_by_card_id,
    get_employee_by_id,
)
from app.crud.company_crud import (
    archive_company,
    delete_company_cascade,
    get_all_companies,
    get_company_by_id,
    get_company_summary,
    restore_company,
    update_company_profile,
)
from app.crud.location_crud import get_location_by_id
from app.crud.scan_crud import create_scan_log, get_report_logs
from app.crud.terminal_crud import get_terminal_by_id
from app.crud.user_crud import create_user, get_user_by_id
from app.core.zoned_sessions import (
    COMPANY_SESSION_COOKIE,
    ROLE_SESSION_COOKIE_NAMES,
    ZONE_COMPANY,
    build_session_payload,
    read_role_session,
    read_zone_session,
    serializer,
)
from app.models.company_model import Company
from app.models.company_contact_model import CompanyContact
from app.models.employee_model import Employee
from app.models.location_model import Location
from app.models.scan_log_model import ScanLog
from app.models.terminal_model import Terminal
from app.models.user_model import User
from app.services.scan_service import get_logs, process_scan


class SecurityContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

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

    def test_archived_company_workspace_access_is_blocked_for_company_user(self):
        db = self.SessionLocal()
        try:
            archived_company = Company(name="Archived Co", timezone="America/New_York", status="archived")
            db.add(archived_company)
            db.commit()
            db.refresh(archived_company)
        finally:
            db.close()

        request = SimpleNamespace(
            session={
                "authenticated": True,
                "username": "owner",
                "role": ROLE_COMPANY_OWNER,
                "company_id": archived_company.id,
            }
        )

        with patch("app.core.security.SessionLocal", self.SessionLocal):
            with self.assertRaises(HTTPException) as exc:
                require_permission(request, PERM_VIEW_DASHBOARD)

        self.assertEqual(exc.exception.status_code, 403)


class CrossCompanyIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.db = self.SessionLocal()
        for model in (ScanLog, User, Terminal, Location, Employee, Company):
            self.db.query(model).delete()
        self.db.commit()

        self.company_1 = Company(name="Company One", timezone="America/New_York", status="active")
        self.company_2 = Company(name="Company Two", timezone="America/Chicago", status="active")
        self.db.add_all([self.company_1, self.company_2])
        self.db.commit()
        self.db.refresh(self.company_1)
        self.db.refresh(self.company_2)

    def tearDown(self):
        self.db.close()

    def test_employee_lookup_is_scoped_by_company(self):
        employee = create_employee(
            db=self.db,
            full_name="Worker Two",
            card_id="EMP-C2-001",
            company_id=self.company_2.id,
        )

        self.assertIsNone(get_employee_by_id(self.db, employee.id, self.company_1.id))
        self.assertIsNone(get_employee_by_card_id(self.db, employee.card_id, self.company_1.id))
        self.assertEqual(get_employee_by_id(self.db, employee.id, self.company_2.id).id, employee.id)

    def test_user_location_and_terminal_lookup_are_scoped_by_company(self):
        location = Location(
            company_id=self.company_2.id,
            name="Site B",
            timezone="America/Chicago",
            is_active=True,
        )
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)

        terminal = Terminal(
            company_id=self.company_2.id,
            location_id=location.id,
            name="Terminal B",
            status="active",
            is_active=True,
        )
        self.db.add(terminal)
        self.db.commit()
        self.db.refresh(terminal)

        user = create_user(
            db=self.db,
            username="company2_admin",
            password_hash="hashed",
            role=ROLE_COMPANY_ADMIN,
            company_id=self.company_2.id,
            location_id=location.id,
            terminal_id=terminal.id,
        )

        self.assertIsNone(get_location_by_id(self.db, location.id, self.company_1.id))
        self.assertIsNone(get_terminal_by_id(self.db, terminal.id, self.company_1.id))
        self.assertIsNone(get_user_by_id(self.db, user.id, self.company_1.id))
        self.assertEqual(get_user_by_id(self.db, user.id, self.company_2.id).id, user.id)

    def test_report_logs_are_limited_to_current_company(self):
        employee_1 = create_employee(
            db=self.db,
            full_name="Worker One",
            card_id="EMP-C1-001",
            company_id=self.company_1.id,
        )
        employee_2 = create_employee(
            db=self.db,
            full_name="Worker Two",
            card_id="EMP-C2-001",
            company_id=self.company_2.id,
        )

        self.db.add_all([
            ScanLog(
                employee_id=employee_1.id,
                company_id=self.company_1.id,
                card_id=employee_1.card_id,
                event_type="check-in",
                scanned_at=datetime(2026, 4, 25, 12, 0, 0),
                scan_source="test",
            ),
            ScanLog(
                employee_id=employee_2.id,
                company_id=self.company_2.id,
                card_id=employee_2.card_id,
                event_type="check-out",
                scanned_at=datetime(2026, 4, 25, 13, 0, 0),
                scan_source="test",
            ),
        ])
        self.db.commit()

        company_1_rows = get_report_logs(self.db, self.company_1.id)
        company_2_rows = get_report_logs(self.db, self.company_2.id)

        self.assertEqual(len(company_1_rows), 1)
        self.assertEqual(company_1_rows[0][0].company_id, self.company_1.id)
        self.assertEqual(company_1_rows[0][1].company_id, self.company_1.id)

        self.assertEqual(len(company_2_rows), 1)
        self.assertEqual(company_2_rows[0][0].company_id, self.company_2.id)
        self.assertEqual(company_2_rows[0][1].company_id, self.company_2.id)

    def test_process_scan_rejects_foreign_company_card_and_qr(self):
        employee = create_employee(
            db=self.db,
            full_name="Worker Two",
            card_id="EMP-C2-QR",
            company_id=self.company_2.id,
        )

        result, error = process_scan(self.db, employee.card_id, self.company_1.id)
        self.assertIsNone(result)
        self.assertEqual(error, "Employee not found")

        qr_payload = build_qr_payload(employee)
        result, error = process_scan(self.db, qr_payload, self.company_1.id)
        self.assertIsNone(result)
        self.assertEqual(error, "QR code belongs to another company")

    def test_logs_feed_only_returns_current_company_events(self):
        employee_1 = create_employee(
            db=self.db,
            full_name="Worker One",
            card_id="EMP-C1-LOG",
            company_id=self.company_1.id,
        )
        employee_2 = create_employee(
            db=self.db,
            full_name="Worker Two",
            card_id="EMP-C2-LOG",
            company_id=self.company_2.id,
        )

        create_scan_log(
            db=self.db,
            employee_id=employee_1.id,
            company_id=self.company_1.id,
            card_id=employee_1.card_id,
            event_type="check-in",
            scan_source="test",
        )
        create_scan_log(
            db=self.db,
            employee_id=employee_2.id,
            company_id=self.company_2.id,
            card_id=employee_2.card_id,
            event_type="check-in",
            scan_source="test",
        )

        logs_company_1 = get_logs(self.db, self.company_1.id)
        logs_company_2 = get_logs(self.db, self.company_2.id)

        self.assertEqual(len(logs_company_1), 1)
        self.assertEqual(logs_company_1[0]["card_id"], employee_1.card_id)
        self.assertEqual(len(logs_company_2), 1)
        self.assertEqual(logs_company_2[0]["card_id"], employee_2.card_id)

    def test_archived_companies_are_filtered_and_can_be_restored(self):
        self.company_1.status = "demo"
        self.db.commit()

        archive_company(self.db, self.company_2)

        active_companies = get_all_companies(self.db)
        archived_companies = get_all_companies(self.db, status="archived")

        self.assertEqual([company.id for company in active_companies], [self.company_1.id])
        self.assertEqual([company.id for company in archived_companies], [self.company_2.id])
        self.assertEqual(get_company_by_id(self.db, self.company_2.id).status, "archived")

        restore_company(self.db, self.company_2)

        active_ids_after_restore = [company.id for company in get_all_companies(self.db)]
        self.assertIn(self.company_2.id, active_ids_after_restore)
        self.assertEqual(get_company_by_id(self.db, self.company_2.id).status, "active")

    def test_company_summary_counts_only_selected_company(self):
        employee = create_employee(
            db=self.db,
            full_name="Summary Worker",
            card_id="EMP-SUM-1",
            company_id=self.company_2.id,
        )
        location = Location(
            company_id=self.company_2.id,
            name="Summary Site",
            timezone="America/Chicago",
            is_active=True,
        )
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)

        terminal = Terminal(
            company_id=self.company_2.id,
            location_id=location.id,
            name="Summary Terminal",
            status="active",
            is_active=True,
        )
        contact = CompanyContact(
            company_id=self.company_2.id,
            full_name="Primary Contact",
            contact_type="owner",
            email="owner@example.com",
            is_primary=True,
        )
        self.db.add_all([terminal, contact])
        self.db.commit()

        create_user(
            db=self.db,
            username="summary_admin",
            password_hash="hashed",
            role=ROLE_COMPANY_ADMIN,
            company_id=self.company_2.id,
            location_id=location.id,
            terminal_id=terminal.id,
        )
        create_scan_log(
            db=self.db,
            employee_id=employee.id,
            company_id=self.company_2.id,
            card_id=employee.card_id,
            event_type="check-in",
            scan_source="test",
            terminal_id=terminal.id,
            location_id=location.id,
        )

        summary = get_company_summary(self.db, self.company_2.id)

        self.assertEqual(summary["employees_count"], 1)
        self.assertEqual(summary["users_count"], 1)
        self.assertEqual(summary["locations_count"], 1)
        self.assertEqual(summary["terminals_count"], 1)
        self.assertEqual(summary["contacts_count"], 1)
        self.assertIsNotNone(summary["primary_contact"])
        self.assertEqual(summary["primary_contact"].full_name, "Primary Contact")

    def test_primary_contact_upsert_sets_single_primary_contact(self):
        first_contact = upsert_primary_company_contact(
            self.db,
            self.company_1.id,
            full_name="Owner One",
            position="Owner",
            email="owner1@example.com",
        )
        second_contact = upsert_primary_company_contact(
            self.db,
            self.company_1.id,
            full_name="Owner Two",
            position="Director",
            email="owner2@example.com",
            phone="+1-555-2222",
        )

        primary_contact = get_primary_company_contact(self.db, self.company_1.id)
        all_contacts = self.db.query(CompanyContact).filter(CompanyContact.company_id == self.company_1.id).all()

        self.assertEqual(first_contact.id, second_contact.id)
        self.assertEqual(primary_contact.full_name, "Owner Two")
        self.assertEqual(primary_contact.position, "Director")
        self.assertEqual(primary_contact.email, "owner2@example.com")
        self.assertEqual(primary_contact.phone, "+1-555-2222")
        self.assertEqual(sum(1 for contact in all_contacts if contact.is_primary), 1)

    def test_update_company_profile_changes_core_fields(self):
        update_company_profile(
            self.db,
            self.company_1,
            name="Updated Company One",
            legal_name="Updated Legal",
            email="updated@example.com",
            phone="+1-555-1234",
            timezone="America/Los_Angeles",
        )

        updated_company = get_company_by_id(self.db, self.company_1.id)
        self.assertEqual(updated_company.name, "Updated Company One")
        self.assertEqual(updated_company.legal_name, "Updated Legal")
        self.assertEqual(updated_company.email, "updated@example.com")
        self.assertEqual(updated_company.phone, "+1-555-1234")
        self.assertEqual(updated_company.timezone, "America/Los_Angeles")

    def test_archived_company_blocks_login_for_company_user(self):
        archived_user = create_user(
            db=self.db,
            username="archived_owner",
            password_hash="hashed",
            role=ROLE_COMPANY_OWNER,
            company_id=self.company_2.id,
        )
        archive_company(self.db, self.company_2)

        self.assertFalse(is_login_allowed_for_user(self.db, archived_user))

    def test_delete_company_cascade_removes_related_records(self):
        employee = create_employee(
            db=self.db,
            full_name="Delete Target",
            card_id="EMP-DEL-1",
            company_id=self.company_2.id,
        )
        location = Location(
            company_id=self.company_2.id,
            name="Delete Site",
            timezone="America/Chicago",
            is_active=True,
        )
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)

        terminal = Terminal(
            company_id=self.company_2.id,
            location_id=location.id,
            name="Delete Terminal",
            status="active",
            is_active=True,
        )
        contact = CompanyContact(
            company_id=self.company_2.id,
            full_name="Delete Contact",
            contact_type="general",
        )
        self.db.add_all([terminal, contact])
        self.db.commit()
        self.db.refresh(terminal)

        user = create_user(
            db=self.db,
            username="delete_user",
            password_hash="hashed",
            role=ROLE_COMPANY_ADMIN,
            company_id=self.company_2.id,
            location_id=location.id,
            terminal_id=terminal.id,
        )
        employee_id = employee.id
        location_id = location.id
        terminal_id = terminal.id
        user_id = user.id
        company_id = self.company_2.id
        create_scan_log(
            db=self.db,
            employee_id=employee.id,
            company_id=company_id,
            card_id=employee.card_id,
            event_type="check-in",
            scan_source="test",
            terminal_id=terminal.id,
            location_id=location.id,
        )

        archive_company(self.db, self.company_2)
        delete_company_cascade(self.db, self.company_2)

        self.assertIsNone(get_company_by_id(self.db, company_id))
        self.assertIsNone(get_employee_by_id(self.db, employee_id, company_id))
        self.assertIsNone(get_location_by_id(self.db, location_id, company_id))
        self.assertIsNone(get_terminal_by_id(self.db, terminal_id, company_id))
        self.assertIsNone(get_user_by_id(self.db, user_id, company_id))
        self.assertEqual(self.db.query(CompanyContact).filter(CompanyContact.company_id == company_id).count(), 0)
        self.assertEqual(self.db.query(ScanLog).filter(ScanLog.company_id == company_id).count(), 0)


if __name__ == "__main__":
    unittest.main()
