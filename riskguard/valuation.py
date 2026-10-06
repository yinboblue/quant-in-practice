"""持仓市值估值：错误口径 vs 修复口径。

通用化版本，不绑定任何特定市场。核心问题：
"持仓里有这个品种，但当前价格表里查不到它" 时，应该按多少计值？
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional


# 持仓: {instrument_id: {"shares": 数量, "cost_price": 成本价}}
Holdings = Dict[str, Dict[str, float]]
PriceMap = Mapping[str, float]


def _is_valid_price(price: Optional[float]) -> bool:
    """有效正价。price != price 用于拦截 NaN（NaN != NaN）。"""
    return price is not None and price == price and price > 0


def position_value_buggy(holdings: Holdings, tradeable_prices: PriceMap) -> float:
    """事故版本（简化）。

    直接复用"当日可交易价格表"来估值。持有但已不可交易（临期/退市/强赎）
    的品种不在该表中，查不到价格时 continue —— 该笔持仓市值被当作 0。

    这是一个乐观的静默错误：不抛异常，却让总市值凭空少了一块。
    """
    total = 0.0
    for code, h in holdings.items():
        price = tradeable_prices.get(code)
        if not _is_valid_price(price):
            continue  # ← 缺失被当成 0
        total += h["shares"] * price  # type: ignore[operator]
    return total


def position_value(
    holdings: Holdings,
    tradeable_prices: PriceMap,
    last_valid_prices: Optional[PriceMap] = None,
    use_cost_fallback: bool = True,
) -> float:
    """修复版本：构造"风控专用估值表"。

    估值口径独立于"可交易过滤"：
      1. 先用当日可交易价；
      2. 持有但缺失的，取该品种最后一个有效价（退市/停牌估值的正确取法）；
      3. 极端数据真空下，用成本价兜底。
    任何情况下都不允许按 0 计。
    """
    last_valid_prices = last_valid_prices or {}
    value_map: Dict[str, float] = {}

    for code in holdings:
        px: Optional[float] = None
        if _is_valid_price(tradeable_prices.get(code)):
            px = tradeable_prices[code]
        elif _is_valid_price(last_valid_prices.get(code)):
            px = last_valid_prices[code]
        elif use_cost_fallback:
            px = holdings[code]["cost_price"]  # 数据真空：成本兜底，非 0
        if _is_valid_price(px):
            value_map[code] = px  # type: ignore[assignment]

    total = 0.0
    for code, h in holdings.items():
        price = value_map.get(code)
        if not _is_valid_price(price):
            # 走到这里说明调用方既没有该品种价格，也没有成本数据，
            # 这是真正的数据质量问题，必须显式暴露而不是静默计 0。
            raise ValueError(f"无法对持仓 {code} 估值：缺少价格且无成本兜底")
        total += h["shares"] * price  # type: ignore[operator]
    return total


def missing_holdings(holdings: Holdings, tradeable_prices: PriceMap) -> list[str]:
    """列出"持有但不在可交易价格表"的品种，供覆盖率告警使用。"""
    return [c for c in holdings if not _is_valid_price(tradeable_prices.get(c))]
