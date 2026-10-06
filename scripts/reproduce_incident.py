"""端到端复现事故：错误口径假崩盘 → 误触发熔断砍仓；修复口径恢复正常。

数字对齐真实事故（单位：元）：
  历史峰值 peak          ≈ 200,500
  现金 cash              ≈ 48,000（演示用近似）
  6 只不可交易持仓合计    ≈ 25,900（有真实市值，但被过滤池剔除）
  全量盯市总资产         ≈ 194,900 → 真实回撤约 -3%
  过滤池估值（缺失误计0） = 168,994 → 假回撤 -15.7%，击穿 -8%
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from riskguard.fuse import FuseState, check_fuse, drawdown
from riskguard.snapshots import (
    codes_missing_in_latest_partition,
    init_db,
    last_value_per_entity,
    latest_partition_map,
)
from riskguard.valuation import (
    missing_holdings,
    position_value,
    position_value_buggy,
)

PEAK = 200_500.0
CASH = 48_000.0

# 为让端到端数字严格对齐真实事故，用 shares=1、price=市值的方式构造：
#   可交易 6 只合计 121,000；持有但被剔除 6 只合计 25,900。
#   全量盯市总资产 = 48,000 + 121,000 + 25,900 = 194,900（真实回撤 -2.8%≈-3%）
#   过滤池估值     = 48,000 + 121,000           = 169,000（假回撤  -15.7%）
def _holding(market_value):
    # 成本略低于市值，浮盈状态，不影响以市价估值的结论
    return {"shares": 1, "cost_price": round(market_value * 0.98, 2)}


_a_mv = [20_000, 20_000, 20_000, 20_000, 20_000, 21_000]      # 合计 121,000
_x_mv = [4_000, 4_200, 4_300, 4_400, 4_500, 4_500]            # 合计 25,900

holdings = {f"A{i+1:03d}": _holding(v) for i, v in enumerate(_a_mv)}
holdings.update({f"X{i+1:03d}": _holding(v) for i, v in enumerate(_x_mv)})

# 全量盯市价：12 只都有（盯市含退市/临期品种的最后有效价）。shares=1 → 价格即市值
mark_prices = {f"A{i+1:03d}": float(v) for i, v in enumerate(_a_mv)}
mark_prices.update({f"X{i+1:03d}": float(v) for i, v in enumerate(_x_mv)})

# 当日"可交易价格表"：X001~X006 被可交易性过滤剔除
tradeable_prices = {k: v for k, v in mark_prices.items() if k.startswith("A")}

# 缺失品种的最后有效价（即盯市口径使用的价格）
last_valid = {k: v for k, v in mark_prices.items() if k.startswith("X")}


def show(title, total):
    dd = drawdown(total, PEAK)
    flag = "🔴 击穿 -8%" if dd <= -0.08 else "🟢 安全"
    print(f"{title:28s} 总资产={total:>10,.0f}  回撤={dd:+.1%}  {flag}")


def run_fuse(title, total):
    state = FuseState(peak_total=PEAK, is_triggered=False)
    sold = {}

    def sell_to_target(ratio):
        sold["ratio"] = ratio

    ev = check_fuse(total, state, as_of="2026-09-30", sell_to_target=sell_to_target)
    action = f"事件={ev}" + (f"，实际砍仓到 {sold['ratio']:.0%}" if sold else "，无成交")
    print(f"{title:28s} {action}")
    return state


def main():
    print("=" * 72)
    print("1) 估值口径对比")
    print("=" * 72)
    buggy_pos = position_value_buggy(holdings, tradeable_prices)
    fixed_pos = position_value(holdings, tradeable_prices, last_valid)
    full_pos = position_value(holdings, mark_prices)

    missing = missing_holdings(holdings, tradeable_prices)
    print(f"持有但被可交易池剔除的品种: {len(missing)} 只 -> {missing}\n")

    show("全量盯市（记账/真实口径）", CASH + full_pos)
    show("过滤池估值（事故口径）    ", CASH + buggy_pos)
    show("修复：缺失取最后有效价    ", CASH + fixed_pos)

    print("\n被凭空抹去的持仓市值 = {:,.0f} 元".format(full_pos - buggy_pos))

    print("\n" + "=" * 72)
    print("2) 熔断状态机：同一账户，不同输入")
    print("=" * 72)
    run_fuse("事故口径（假 -15.7%）", CASH + buggy_pos)
    run_fuse("修复口径（真实 -3%）  ", CASH + fixed_pos)

    print("\n" + "=" * 72)
    print("3) 全量快照：摘牌实体从最新分区消失")
    print("=" * 72)
    con = init_db([
        ("2026-09-24", "128134", "已公告强赎"),
        ("2026-09-24", "110000", "正常"),
        ("2026-09-30", "110000", "正常"),   # 128134 已摘牌，不再出现在新快照
    ])
    print("只取最新分区  -> 128134 状态:", latest_partition_map(con, "128134"),
          " (查不到，到期强平逻辑永不触发)")
    print("按实体取末值  -> 128134 状态:", last_value_per_entity(con, "128134"),
          " (正确找回，可执行退出)")
    print("监控：最新分区消失的实体 ->", codes_missing_in_latest_partition(con))


if __name__ == "__main__":
    main()
