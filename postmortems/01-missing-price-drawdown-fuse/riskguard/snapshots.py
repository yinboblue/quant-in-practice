"""全量快照表取数：只取最新分区 vs 按实体取末值。

适用于任何"周期性全量覆盖、实体会消失"的快照表：
强赎/退市名单、指数成分股、设备清单、在职员工、好友关系……

实体一旦移出/退市/删除，就不会再出现在新的全量快照里。
只取 MAX(snapshot_date) 会让这些实体的历史属性全部丢失。
"""
from __future__ import annotations

import sqlite3
from typing import List, Sequence, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS entity_snapshot (
    snapshot_date TEXT NOT NULL,
    code          TEXT NOT NULL,
    status        TEXT NOT NULL
);
"""


def init_db(rows: Sequence[Tuple[str, str, str]]) -> sqlite3.Connection:
    """rows: [(snapshot_date, code, status), ...]"""
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO entity_snapshot(snapshot_date, code, status) VALUES (?,?,?)",
        rows,
    )
    con.commit()
    return con


def latest_partition_map(con: sqlite3.Connection, code: str) -> str | None:
    """事故写法：只取全表最新分区里的记录。

    实体在最新分区中已消失 → 查不到 → 依赖该状态的"到期强平/退出"
    逻辑永远命中不了。
    """
    row = con.execute(
        """
        SELECT status FROM entity_snapshot
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM entity_snapshot)
          AND code = ?
        """,
        (code,),
    ).fetchone()
    return row[0] if row else None


def last_value_per_entity(con: sqlite3.Connection, code: str) -> str | None:
    """修复写法：按实体取它自己最后一次出现的记录（对应 ROW_NUMBER 窗口函数）。"""
    row = con.execute(
        """
        SELECT status FROM (
            SELECT code, status,
                   ROW_NUMBER() OVER (
                       PARTITION BY code ORDER BY snapshot_date DESC
                   ) AS rn
            FROM entity_snapshot
        ) WHERE code = ? AND rn = 1
        """,
        (code,),
    ).fetchone()
    return row[0] if row else None


def codes_missing_in_latest_partition(con: sqlite3.Connection) -> List[str]:
    """监控辅助：找出"历史出现过、但最新分区消失"的实体，应触发数据核对告警。"""
    return [
        r[0]
        for r in con.execute(
            """
            SELECT DISTINCT code FROM entity_snapshot
            WHERE code NOT IN (
                SELECT code FROM entity_snapshot
                WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM entity_snapshot)
            )
            """
        ).fetchall()
    ]
