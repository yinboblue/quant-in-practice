import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from riskguard.valuation import (
    missing_holdings,
    position_value,
    position_value_buggy,
)


class TestValuation(unittest.TestCase):
    def setUp(self):
        # 2 只在可交易池，1 只持有但被剔除
        self.holdings = {
            "A": {"shares": 100, "cost_price": 10},
            "B": {"shares": 50, "cost_price": 20},
            "X": {"shares": 40, "cost_price": 30},  # 不可交易但仍持有
        }
        self.tradeable = {"A": 11.0, "B": 21.0}
        self.last_valid = {"X": 31.0}

    def test_buggy_drops_missing_as_zero(self):
        # X 的 40*31=1240 市值被静默抹去
        self.assertAlmostEqual(position_value_buggy(self.holdings, self.tradeable),
                               100 * 11 + 50 * 21)

    def test_fixed_uses_last_valid_price(self):
        val = position_value(self.holdings, self.tradeable, self.last_valid)
        self.assertAlmostEqual(val, 100 * 11 + 50 * 21 + 40 * 31)

    def test_fixed_cost_fallback_when_no_last_valid(self):
        val = position_value(self.holdings, self.tradeable, last_valid_prices={})
        # X 极端真空，用成本价 30，而非 0
        self.assertAlmostEqual(val, 100 * 11 + 50 * 21 + 40 * 30)

    def test_no_fallback_raises_instead_of_silent_zero(self):
        with self.assertRaises(ValueError):
            position_value(self.holdings, self.tradeable,
                           last_valid_prices={}, use_cost_fallback=False)

    def test_all_present_matches(self):
        prices = {"A": 11.0, "B": 21.0, "X": 31.0}
        self.assertAlmostEqual(position_value_buggy(self.holdings, prices),
                               position_value(self.holdings, prices))

    def test_missing_holdings_detected(self):
        self.assertEqual(missing_holdings(self.holdings, self.tradeable), ["X"])


if __name__ == "__main__":
    unittest.main()
