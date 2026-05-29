from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from snapshot_plan import validate


def base_args(**overrides):
    data = {
        "type": "erc20-holders",
        "contract": "0x0000000000000000000000000000000000000001",
        "wallets": None,
        "target_block": "latest",
        "from_block": None,
        "to_block": None,
        "token_ids": None,
        "min_balance": "1",
        "min_events": 0,
        "event": None,
        "output": "csv,json,xlsx",
    }
    data.update(overrides)
    return Namespace(**data)


class SnapshotPlanTests(unittest.TestCase):
    def test_valid_erc20_plan_is_review_because_latest_moves(self):
        plan = validate(base_args())
        self.assertEqual(plan["errors"], [])
        self.assertEqual(plan["status"], "review")
        self.assertIn("xlsx", plan["output_formats"])

    def test_invalid_contract_is_unsafe(self):
        plan = validate(base_args(contract="bad"))
        self.assertEqual(plan["status"], "unsafe")
        self.assertTrue(any("invalid contract" in error for error in plan["errors"]))

    def test_activity_requires_range(self):
        plan = validate(base_args(type="contract-activity", target_block="100"))
        self.assertEqual(plan["status"], "unsafe")
        self.assertTrue(any("--from-block and --to-block" in error for error in plan["errors"]))

    def test_large_range_warns(self):
        plan = validate(base_args(type="contract-activity", from_block="1", to_block="60002"))
        self.assertEqual(plan["errors"], [])
        self.assertEqual(plan["estimated_query_size"], "large")
        self.assertTrue(any("paginated" in warning for warning in plan["warnings"]))


if __name__ == "__main__":
    unittest.main()
