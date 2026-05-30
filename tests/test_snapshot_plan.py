from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from snapshot_plan import validate
from live_erc20_snapshot import (
    decode_abi_string,
    format_units,
    pad_address,
    topic_to_address,
)


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

    def test_live_snapshot_helpers(self):
        self.assertEqual(
            pad_address("0x1111111111111111111111111111111111111111"),
            "0000000000000000000000001111111111111111111111111111111111111111",
        )
        self.assertEqual(
            topic_to_address("0x0000000000000000000000002222222222222222222222222222222222222222"),
            "0x2222222222222222222222222222222222222222",
        )
        self.assertEqual(format_units(125500000, 6), "125.5")

    def test_decode_abi_string(self):
        encoded = "0x" + f"{32:064x}" + f"{4:064x}" + "55534443".ljust(64, "0")
        self.assertEqual(decode_abi_string(encoded), "USDC")


if __name__ == "__main__":
    unittest.main()
