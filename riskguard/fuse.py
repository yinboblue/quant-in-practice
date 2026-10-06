"""回撤熔断状态机。

关键行为（事故放大点）：
  - 只有"新触发"（之前不在熔断、本次跌破阈值）才真正执行降仓 sell_to_target；
  - "持续触发"只更新状态、不重复卖出。

事故中第一次触发因状态已为 True 而没有卖出；
人工把状态改回 False 后，下一次同口径假回撤被判定为"全新触发"，于是真的砍了仓。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

# 事件类型，便于测试和审计
EVENT_TRIGGER = "trigger"        # 新触发 → 执行砍仓
EVENT_HOLD = "hold_triggered"    # 持续熔断 → 不动
EVENT_RECOVER = "recover"        # 回撤恢复 → 解除
EVENT_NONE = "none"


@dataclass
class FuseState:
    peak_total: float
    is_triggered: bool = False
    trigger_threshold: float = -0.08
    recover_threshold: float = -0.05
    history: List[str] = field(default_factory=list)


def drawdown(current_total: float, peak_total: float) -> float:
    return current_total / peak_total - 1.0


def check_fuse(
    current_total: float,
    state: FuseState,
    as_of: str,
    sell_to_target: Optional[Callable[[float], None]] = None,
) -> str:
    """根据当前总资产检查熔断，返回本次事件类型。

    估值口径必须与沉淀 peak_total 的口径一致（见 valuation 模块），
    否则这里拿到的 current_total 本身就是错的。
    """
    dd = drawdown(current_total, state.peak_total)

    if dd <= state.trigger_threshold:
        if not state.is_triggered:
            # 仅"新触发"才执行不可逆的降仓
            if sell_to_target is not None:
                sell_to_target(0.5)
            state.is_triggered = True
            ev = EVENT_TRIGGER
        else:
            ev = EVENT_HOLD
        state.history.append(f"{as_of} {ev} {dd:+.1%} total={current_total:,.0f}")
        return ev

    if dd >= state.recover_threshold and state.is_triggered:
        state.is_triggered = False
        ev = EVENT_RECOVER
        state.history.append(f"{as_of} {ev} {dd:+.1%} total={current_total:,.0f}")
        return ev

    return EVENT_NONE
