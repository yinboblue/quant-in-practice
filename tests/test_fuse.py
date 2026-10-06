import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from riskguard.fuse import (
    EVENT_HOLD,
    EVENT_NONE,
    EVENT_RECOVER,
    EVENT_TRIGGER,
    FuseState,
    check_fuse,
    drawdown,
)


class TestFuse(unittest.TestCase):
    def test_new_trigger_sells_once(self):
        st = FuseState(peak_total=100, is_triggered=False)
        sold = []
        ev = check_fuse(90, st, "d1", sell_to_target=lambda r: sold.append(r))
        self.assertEqual(ev, EVENT_TRIGGER)
        self.assertTrue(st.is_triggered)
        self.assertEqual(sold, [0.5])  # 真实砍仓只发生一次

    def test_persistent_trigger_does_not_resell(self):
        st = FuseState(peak_total=100, is_triggered=True)
        sold = []
        ev = check_fuse(90, st, "d2", sell_to_target=lambda r: sold.append(r))
        self.assertEqual(ev, EVENT_HOLD)
        self.assertEqual(sold, [])  # 持续熔断不再重复卖出

    def test_manual_reset_then_fake_drawdown_sells_again(self):
        """事故放大点：根因未修，人工把状态翻回 False，
        下一次同口径假回撤被判为"全新触发"，于是真的砍仓。"""
        st = FuseState(peak_total=100, is_triggered=True)
        st.is_triggered = False  # 人工解除
        sold = []
        ev = check_fuse(84.3, st, "d3", sell_to_target=lambda r: sold.append(r))
        self.assertEqual(ev, EVENT_TRIGGER)
        self.assertEqual(sold, [0.5])

    def test_recover_when_drawdown_heals(self):
        st = FuseState(peak_total=100, is_triggered=True)
        ev = check_fuse(97, st, "d4")  # -3% 回到 -5% 以内
        self.assertEqual(ev, EVENT_RECOVER)
        self.assertFalse(st.is_triggered)

    def test_no_event_in_neutral_zone(self):
        st = FuseState(peak_total=100, is_triggered=False)
        self.assertEqual(check_fuse(97, st, "d5"), EVENT_NONE)

    def test_drawdown_math(self):
        self.assertAlmostEqual(drawdown(84.3, 100), -0.157, places=2)


if __name__ == "__main__":
    unittest.main()
