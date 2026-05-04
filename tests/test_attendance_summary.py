import unittest
from datetime import UTC, datetime, timedelta, timezone

from app.services.attendance_summary_service import build_day_attendance_status


class AttendanceSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tz = timezone(timedelta(hours=-4), "EDT")

    def test_marks_complete_day(self):
        result = build_day_attendance_status(
            first_check_in_at=datetime(2026, 5, 4, 12, 55, tzinfo=UTC),
            last_check_out_at=datetime(2026, 5, 4, 21, 10, tzinfo=UTC),
            has_check_in=True,
            has_check_out=True,
            last_event_type="check-out",
            scan_timezone=self.tz,
        )

        self.assertEqual(result["status"], "Complete")

    def test_marks_late_day(self):
        result = build_day_attendance_status(
            first_check_in_at=datetime(2026, 5, 4, 13, 25, tzinfo=UTC),
            last_check_out_at=datetime(2026, 5, 4, 21, 15, tzinfo=UTC),
            has_check_in=True,
            has_check_out=True,
            last_event_type="check-out",
            scan_timezone=self.tz,
        )

        self.assertEqual(result["status"], "Late")

    def test_marks_early_leave_day(self):
        result = build_day_attendance_status(
            first_check_in_at=datetime(2026, 5, 4, 12, 50, tzinfo=UTC),
            last_check_out_at=datetime(2026, 5, 4, 20, 30, tzinfo=UTC),
            has_check_in=True,
            has_check_out=True,
            last_event_type="check-out",
            scan_timezone=self.tz,
        )

        self.assertEqual(result["status"], "Early leave")

    def test_marks_late_and_early_leave_day(self):
        result = build_day_attendance_status(
            first_check_in_at=datetime(2026, 5, 4, 13, 45, tzinfo=UTC),
            last_check_out_at=datetime(2026, 5, 4, 20, 25, tzinfo=UTC),
            has_check_in=True,
            has_check_out=True,
            last_event_type="check-out",
            scan_timezone=self.tz,
        )

        self.assertEqual(result["status"], "Late / Early leave")

    def test_marks_missing_final_checkout(self):
        result = build_day_attendance_status(
            first_check_in_at=datetime(2026, 5, 4, 12, 50, tzinfo=UTC),
            last_check_out_at=datetime(2026, 5, 4, 21, 0, tzinfo=UTC),
            has_check_in=True,
            has_check_out=True,
            last_event_type="check-in",
            scan_timezone=self.tz,
        )

        self.assertEqual(result["status"], "Missing final check-out")


if __name__ == "__main__":
    unittest.main()
