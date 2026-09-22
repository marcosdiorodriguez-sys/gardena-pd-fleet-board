import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from refresh_board import build_fleet, update_board  # noqa: E402


class RefreshBoardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc)
        self.asset = {
            "name": "P1",
            "team": {"name": "Gardena Police Department"},
            "odometer": "10000",
            "engine_hours": "12.5",
            "last_service": {"title": "Oil", "date": "2026-08-01T00:00:00Z", "odometer": 9000},
        }

    def test_builds_overdue_due_soon_and_week_schedule(self):
        services = [
            {"asset_name": "P1", "title": "Oil", "status": "Overdue", "schedule": {}},
            {"asset_name": "P1", "title": "Tires", "status": "Active", "schedule": {"odometer": 10400}},
            {"asset_name": "P1", "title": "Inspection", "status": "Active", "schedule": {"date": "2026-09-20T18:00:00Z"}},
        ]
        fleet = build_fleet([self.asset], services, self.now)
        self.assertEqual(fleet[0]["overdueServices"], ["Oil"])
        self.assertEqual(fleet[0]["dueSoonServices"], ["Tires", "Inspection"])
        self.assertEqual(fleet[0]["scheduledThisWeek"][0]["title"], "Inspection")
        self.assertEqual(fleet[0]["engineHours"], 12.5)

    def test_preserves_whip_around_due_soon_status(self):
        services = [
            {
                "asset_name": "P1",
                "title": "Oil Change",
                "status": "Due Soon",
                "schedule": {"odometer": 10449},
            }
        ]
        fleet = build_fleet([self.asset], services, self.now)
        self.assertEqual(fleet[0]["dueSoonCount"], 1)
        self.assertEqual(fleet[0]["dueSoonServices"], ["Oil Change"])

    def test_filters_other_teams(self):
        other = dict(self.asset, team={"name": "Parks and Recreation"})
        self.assertEqual(build_fleet([other], [], self.now), [])

    def test_replaces_only_board_data_and_timestamp(self):
        html = '''<b id="lastRefreshed">old</b>\n// BOARD_DATA_START marker\nconst FLEET = [{"old":true}];\n// BOARD_DATA_END\n'''
        updated = update_board(html, [{"unit": "P1"}], self.now)
        self.assertIn('const FLEET = [{"unit":"P1"}];', updated)
        self.assertIn('Sep 16, 2026, 11:00 AM', updated)


if __name__ == "__main__":
    unittest.main()
