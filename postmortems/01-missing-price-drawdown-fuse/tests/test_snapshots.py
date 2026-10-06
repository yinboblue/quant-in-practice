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
    # 虚构示例：X007 在旧快照"已公告退出"，新快照中已摘牌消失
    return init_db([
        ("snapshot-1", "X007", "已公告退出"),
        ("snapshot-1", "A100", "正常"),
        ("snapshot-2", "A100", "正常"),
    ])


class TestSnapshots(unittest.TestCase):
    def test_latest_partition_loses_delisted(self):
        con = db_with_delisted_entity()
        self.assertIsNone(latest_partition_map(con, "X007"))

    def test_last_value_per_entity_recovers(self):
        con = db_with_delisted_entity()
        self.assertEqual(last_value_per_entity(con, "X007"), "已公告退出")

    def test_latest_status_still_correct_for_active(self):
        con = init_db([
            ("snapshot-1", "A100", "正常"),
            ("snapshot-2", "A100", "正常"),
        ])
        self.assertEqual(last_value_per_entity(con, "A100"), "正常")

    def test_monitor_flags_disappeared_entities(self):
        con = db_with_delisted_entity()
        self.assertEqual(codes_missing_in_latest_partition(con), ["X007"])

    def test_unknown_entity_is_none(self):
        con = db_with_delisted_entity()
        self.assertIsNone(last_value_per_entity(con, "Z999"))


if __name__ == "__main__":
    unittest.main()
