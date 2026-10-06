"""端到端复现事故：错误口径假崩盘 → 误触发熔断砍仓；修复口径恢复正常。

为脱敏，所有金额一律不出现，改用"归一化净值指数"（历史峰值 peak = 100）：
  全量盯市总资产指数 ≈ 97.2 → 真实回撤约 -2.8%（≈ -3%），离熔断线很远
  过滤池估值（缺失误计0）= 84.3 → 假回撤 -15.7%，击穿 -8% 熔断线
  其中 6 只被剔除持仓合计 ≈ 12.9 个指数点，被当成 0 凭空抹去
（相对比例与真实事故一致；示例代码/编号均为虚构，不对应任何真实标的。）
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

# 归一化净值指数：历史峰值 = 100
PEAK = 100.0
CASH_INDEX = 24.0

# shares=1、price=指数权重的方式构造，让结果严格对齐事故的"相对比例"：
#   可交易 6 只合计 60.3；持有但被剔除 6 只合计 12.9。
#   全量盯市指数 = 24.0 + 60.3 + 12.9 = 97.2（真实回撤 -2.8%≈-3%）
#   过滤池指数   = 24.0 + 60.3        = 84.3（假回撤  -15.7%）
def _holding(weight):
    # 成本略低于市值（浮盈状态），不影响以市价估值的结论
    return {"shares": 1, "cost_price": round(weight * 0.98, 2)}


_a_w = [10.0, 10.0, 10.0, 10.0, 10.0, 10.3]      # 合计 60.3
_x_w = [2.0, 2.1, 2.2, 2.2, 2.2, 2.2]            # 合计 12.9

holdings = {f"A{i+1:03d}": _holding(v) for i, v in enumerate(_a_w)}
holdings.update({f"X{i+1:03d}": _holding(v) for i, v in enumerate(_x_w)})

# 全量盯市价：12 只都有（盯市含退市/临期品种的最后有效价）。shares=1 → 价格即权重
mark_prices = {f"A{i+1:03d}": float(v) for i, v in enumerate(_a_w)}
mark_prices.update({f"X{i+1:03d}": float(v) for i, v in enumerate(_x_w)})

# 当日"可交易价格表"：X001~X006 被可交易性过滤剔除
tradeable_prices = {k: v for k, v in mark_prices.items() if k.startswith("A")}

# 缺失品种的最后有效价（即盯市口径使用的价格）
last_valid = {k: v for k, v in mark_prices.items() if k.startswith("X")}


def show(title, total):
    dd = drawdown(total, PEAK)
    flag = "🔴 击穿 -8%" if dd <= -0.08 else "🟢 安全"
    print(f"{title:26s} 净值指数={total:>6.1f}  回撤={dd:+.1%}  {flag}")


def run_fuse(title, total):
    state = FuseState(peak_total=PEAK, is_triggered=False)
    sold = {}

    def sell_to_target(ratio):
        sold["ratio"] = ratio

    ev = check_fuse(total, state, as_of="incident-day", sell_to_target=sell_to_target)
    action = f"事件={ev}" + (f"，实际砍仓到 {sold['ratio']:.0%}" if sold else "，无成交")
    print(f"{title:26s} {action}")
    return state


def main():
    print("=" * 70)
    print("1) 估值口径对比（归一化净值指数，峰值=100）")
    print("=" * 70)
    buggy_pos = position_value_buggy(holdings, tradeable_prices)
    fixed_pos = position_value(holdings, tradeable_prices, last_valid)
    full_pos = position_value(holdings, mark_prices)

    missing = missing_holdings(holdings, tradeable_prices)
    print(f"持有但被可交易池剔除的品种: {len(missing)} 只 -> {missing}\n")

    show("全量盯市（记账/真实口径）", CASH_INDEX + full_pos)
    show("过滤池估值（事故口径）    ", CASH_INDEX + buggy_pos)
    show("修复：缺失取最后有效价    ", CASH_INDEX + fixed_pos)

    print("\n被凭空抹去的持仓权重 = {:.1f} 个指数点".format(full_pos - buggy_pos))

    print("\n" + "=" * 70)
    print("2) 熔断状态机：同一组合，不同输入")
    print("=" * 70)
    run_fuse("事故口径（假 -15.7%）", CASH_INDEX + buggy_pos)
    run_fuse("修复口径（真实 -3%）  ", CASH_INDEX + fixed_pos)

    print("\n" + "=" * 70)
    print("3) 全量快照：摘牌实体从最新分区消失（代码均为虚构示例）")
    print("=" * 70)
    con = init_db([
        ("snapshot-1", "X007", "已公告退出"),
        ("snapshot-1", "A100", "正常"),
        ("snapshot-2", "A100", "正常"),   # X007 已摘牌，不再出现在新快照
    ])
    print("只取最新分区  -> X007 状态:", latest_partition_map(con, "X007"),
          " (查不到，到期退出逻辑永不触发)")
    print("按实体取末值  -> X007 状态:", last_value_per_entity(con, "X007"),
          " (正确找回，可执行退出)")
    print("监控：最新分区消失的实体 ->", codes_missing_in_latest_partition(con))


if __name__ == "__main__":
    main()
