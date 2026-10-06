import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from riskguard.snapshots import (
    codes_missing_in_latest_partition,
    init_db,
    last_value_per_entity,
    latest_partition_map,
)


def db_with_delisted_entity():
    return init_db([
        ("2026-09-24", "128134", "已公告强赎"),
        ("2026-09-24", "110000", "正常"),
        ("2026-09-30", "110000", "正常"),  # 128134 摘牌，新快照消失
    ])


class TestSnapshots(unittest.TestCase):
    def test_latest_partition_loses_delisted(self):
        con = db_with_delisted_entity()
        self.assertIsNone(latest_partition_map(con, "128134"))

    def test_last_value_per_entity_recovers(self):
        con = db_with_delisted_entity()
        self.assertEqual(last_value_per_entity(con, "128134"), "已公告强赎")

    def test_latest_status_still_correct_for_active(self):
        con = init_db([
            ("2026-09-24", "110000", "正常"),
            ("2026-09-30", "110000", "正常"),
        ])
        self.assertEqual(last_value_per_entity(con, "110000"), "正常")

    def test_monitor_flags_disappeared_entities(self):
        con = db_with_delisted_entity()
        self.assertEqual(codes_missing_in_latest_partition(con), ["128134"])

    def test_unknown_entity_is_none(self):
        con = db_with_delisted_entity()
        self.assertIsNone(last_value_per_entity(con, "999999"))


if __name__ == "__main__":
    unittest.main()
