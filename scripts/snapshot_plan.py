from __future__ import annotations

import argparse
import json
from typing import Any

from snapshot_common import (
    PHAROS_ATLANTIC,
    SNAPSHOT_TYPES,
    parse_block,
    parse_formats,
    split_csv,
    validate_addresses,
    validate_formats,
)


RANGE_LIMIT = 50_000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and prepare a read-only Pharos snapshot plan.")
    parser.add_argument("--type", required=True, choices=sorted(SNAPSHOT_TYPES), help="Snapshot type.")
    parser.add_argument("--contract", help="Token or contract address.")
    parser.add_argument("--wallets", help="Comma-separated wallet addresses.")
    parser.add_argument("--target-block", default="latest", help="Target block number or latest.")
    parser.add_argument("--from-block", help="Start block for activity snapshots.")
    parser.add_argument("--to-block", help="End block for activity snapshots.")
    parser.add_argument("--token-ids", help="Comma-separated ERC-1155 token IDs.")
    parser.add_argument("--min-balance", default="0", help="Minimum human-readable balance for eligibility.")
    parser.add_argument("--min-events", type=int, default=0, help="Minimum event count for activity eligibility.")
    parser.add_argument("--event", help="Optional event signature, such as Transfer(address,address,uint256).")
    parser.add_argument("--output", default="csv", help="Comma-separated formats: csv,json,xlsx.")
    return parser


def validate(args: argparse.Namespace) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    formats = parse_formats(args.output)
    validate_formats(formats, errors)

    snapshot_type = args.type
    contract_types = {"erc20-holders", "erc721-owners", "erc1155-balances", "contract-activity", "campaign-eligibility"}
    if snapshot_type in contract_types and not args.contract:
        errors.append("--contract is required for this snapshot type")
    if args.contract:
        validate_addresses([args.contract], "contract", errors)

    wallets = split_csv(args.wallets)
    if snapshot_type == "wallet-activity" and not wallets:
        errors.append("--wallets is required for wallet-activity")
    validate_addresses(wallets, "wallet", errors)

    target_block = parse_block(args.target_block, "target block", errors)
    from_block = parse_block(args.from_block, "from block", errors)
    to_block = parse_block(args.to_block, "to block", errors)

    activity_type = snapshot_type in {"contract-activity", "wallet-activity", "campaign-eligibility"}
    if snapshot_type in {"contract-activity", "wallet-activity"}:
        if from_block is None or to_block is None:
            errors.append("--from-block and --to-block are required for activity snapshots")

    if isinstance(from_block, int) and isinstance(to_block, int):
        if to_block < from_block:
            errors.append("to block must be greater than or equal to from block")
        elif to_block - from_block > RANGE_LIMIT:
            warnings.append(f"block range is larger than {RANGE_LIMIT}; split into paginated jobs")

    token_ids = split_csv(args.token_ids)
    if snapshot_type == "erc1155-balances" and not token_ids:
        errors.append("--token-ids is required for erc1155-balances")
    for token_id in token_ids:
        if not token_id.isdigit() or int(token_id) < 0:
            errors.append(f"invalid token ID: {token_id}")

    try:
        min_balance = float(args.min_balance)
        if min_balance < 0:
            errors.append("--min-balance must not be negative")
    except ValueError:
        min_balance = 0.0
        errors.append("--min-balance must be numeric")

    if args.min_events < 0:
        errors.append("--min-events must not be negative")

    if target_block == "latest":
        warnings.append("latest is moving; use a fixed block for reproducible snapshots")
    if activity_type:
        warnings.append("RPC-only activity scans can miss historical logs if the provider limits old ranges")

    status = "unsafe" if errors else "review" if warnings else "safe"
    block_range = None
    if from_block is not None or to_block is not None:
        block_range = {"from": from_block, "to": to_block}

    estimated_query_size = "small"
    if isinstance(from_block, int) and isinstance(to_block, int):
        width = to_block - from_block + 1
        if width > 10_000:
            estimated_query_size = "large"
        elif width > 1_000:
            estimated_query_size = "medium"

    return {
        "status": status,
        "snapshot_type": snapshot_type,
        "network": PHAROS_ATLANTIC,
        "contracts": [args.contract] if args.contract else [],
        "wallets": wallets,
        "target_block": target_block if block_range is None else None,
        "block_range": block_range,
        "filters": {
            "min_balance": min_balance,
            "min_events": args.min_events,
            "token_ids": token_ids,
            "event": args.event,
        },
        "estimated_query_size": estimated_query_size,
        "warnings": warnings,
        "errors": errors,
        "output_formats": formats,
        "next_steps": [
            "confirm deployed contract bytecode with scripts/rpc_probe.py when a contract is present",
            "show this plan to the user before running heavy scans",
            "export fetched public rows with scripts/export_snapshot.py",
        ],
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    plan = validate(args)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 1 if plan["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

