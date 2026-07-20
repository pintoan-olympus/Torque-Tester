import unittest
import datetime
from utils.helpers import format_datetime, format_date, check_tolerance

class TestHelpers(unittest.TestCase):
    def test_check_tolerance_ok(self):
        is_ok, lower, upper = check_tolerance(10.0, 10.0, 1.0, 1.0)
        self.assertTrue(is_ok)
        self.assertEqual(lower, 9.0)
        self.assertEqual(upper, 11.0)

    def test_check_tolerance_nok_high(self):
        is_ok, lower, upper = check_tolerance(11.5, 10.0, 1.0, 1.0)
        self.assertFalse(is_ok)

    def test_check_tolerance_nok_low(self):
        is_ok, lower, upper = check_tolerance(8.5, 10.0, 1.0, 1.0)
        self.assertFalse(is_ok)

    def test_format_datetime_string(self):
        res = format_datetime("2026-07-20T10:00:00")
        self.assertEqual(res, "2026-07-20 10:00:00")

    def test_format_datetime_none(self):
        self.assertEqual(format_datetime(None), "N/A")

    def test_format_date_string(self):
        res = format_date("2026-07-20")
        self.assertEqual(res, "2026-07-20")

    def test_format_date_none(self):
        self.assertEqual(format_date(None), "N/A")

if __name__ == "__main__":
    unittest.main()
