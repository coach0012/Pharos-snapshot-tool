from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from export_snapshot import build_payload, ordered_fields, write_csv, write_json, write_xlsx
from snapshot_common import (
    OUTPUT_FORMATS,
    PHAROS_ATLANTIC,
    ZERO_ADDRESS,
    block_to_rpc,
    is_address,
    normalize_address,
    parse_formats,
)


TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
BALANCE_OF_SELECTOR = "70a08231"
DECIMALS_SELECTOR = "313ce567"
SYMBOL_SELECTOR = "95d89b41"


class RpcClient:
    def __init__(self, rpc_url: str, timeout: int = 30, retries: int = 2) -> None:
        self.rpc_url = rpc_url
        self.timeout = timeout
        self.retries = retries
        self.request_id = 0

    def call(self, method: str, params: list[Any]) -> Any:
        self.request_id += 1
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params}
        ).encode()
        request = urllib.request.Request(
            self.rpc_url,
            data=payload,
            headers={"content-type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode())
                if "error" in body:
                    raise RuntimeError(body["error"])
                return body.get("result")
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
        raise RuntimeError(f"RPC call failed for {method}: {last_error}")


def pad_address(address: str) -> str:
    return normalize_address(address)[2:].rjust(64, "0")


def topic_to_address(topic: str) -> str:
    if not isinstance(topic, str) or len(topic) < 42:
        raise ValueError(f"invalid address topic: {topic}")
    return "0x" + topic[-40:].lower()


def hex_to_int(value: Any) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError(f"expected hex value, got {value}")
    return int(value, 16)


def decode_abi_string(value: Any) -> str | None:
    if not isinstance(value, str) or not value.startswith("0x") or value == "0x":
        return None
    raw = value[2:]
    try:
        data = bytes.fromhex(raw)
    except ValueError:
        return None
    if len(data) >= 64:
        offset = int.from_bytes(data[:32], "big")
        if offset + 32 <= len(data):
            size = int.from_bytes(data[offset : offset + 32], "big")
            start = offset + 32
            end = start + size
            if end <= len(data):
                try:
                    return data[start:end].decode("utf-8").strip("\x00") or None
                except UnicodeDecodeError:
                    pass
    if len(data) == 32:
        try:
            return data.rstrip(b"\x00").decode("utf-8") or None
        except UnicodeDecodeError:
            return None
    return None


def call_contract(client: RpcClient, contract: str, data: str, block: int | str) -> str:
    result = client.call("eth_call", [{"to": contract, "data": data}, block_to_rpc(block)])
    if not isinstance(result, str):
        raise RuntimeError(f"eth_call returned unexpected value: {result}")
    return result


def read_decimals(client: RpcClient, contract: str, block: int | str) -> int:
    result = call_contract(client, contract, "0x" + DECIMALS_SELECTOR, block)
    parsed = hex_to_int(result)
    if parsed < 0 or parsed > 255:
        raise RuntimeError("decimals() returned an invalid value")
    return parsed


def read_symbol(client: RpcClient, contract: str, block: int | str) -> str:
    try:
        result = call_contract(client, contract, "0x" + SYMBOL_SELECTOR, block)
        return decode_abi_string(result) or "UNKNOWN"
    except RuntimeError:
        return "UNKNOWN"


def read_balance(client: RpcClient, contract: str, wallet: str, block: int | str) -> int:
    data = "0x" + BALANCE_OF_SELECTOR + pad_address(wallet)
    return hex_to_int(call_contract(client, contract, data, block))


def format_units(raw: int, decimals: int) -> str:
    amount = Decimal(raw) / (Decimal(10) ** decimals)
    formatted = format(amount.normalize(), "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted or "0"


def parse_min_balance(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("--min-balance must be a number") from exc
    if amount < 0:
        raise ValueError("--min-balance must not be negative")
    return amount


def parse_to_block(client: RpcClient, value: str) -> int:
    if value == "latest":
        return hex_to_int(client.call("eth_blockNumber", []))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError("--to-block must be a non-negative integer or latest") from exc
    if parsed < 0:
        raise ValueError("--to-block must not be negative")
    return parsed


def parse_from_block(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError("--from-block must be a non-negative integer") from exc
    if parsed < 0:
        raise ValueError("--from-block must not be negative")
    return parsed


def scan_transfer_logs(
    client: RpcClient,
    contract: str,
    from_block: int,
    to_block: int,
    chunk_size: int,
) -> tuple[set[str], dict[str, dict[str, int]]]:
    wallets: set[str] = set()
    stats: dict[str, dict[str, int]] = {}
    current = from_block
    while current <= to_block:
        end = min(current + chunk_size - 1, to_block)
        logs = client.call(
            "eth_getLogs",
            [
                {
                    "address": contract,
                    "fromBlock": hex(current),
                    "toBlock": hex(end),
                    "topics": [TRANSFER_TOPIC],
                }
            ],
        )
        if not isinstance(logs, list):
            raise RuntimeError("eth_getLogs returned an unexpected value")
        for item in logs:
            if not isinstance(item, dict):
                continue
            topics = item.get("topics") or []
            if len(topics) < 3:
                continue
            block_number = hex_to_int(item.get("blockNumber", "0x0"))
            from_addr = topic_to_address(topics[1])
            to_addr = topic_to_address(topics[2])
            for wallet in (from_addr, to_addr):
                if wallet == ZERO_ADDRESS:
                    continue
                wallets.add(wallet)
                wallet_stats = stats.setdefault(
                    wallet,
                    {"transfer_event_count": 0, "first_seen_block": block_number, "last_seen_block": block_number},
                )
                wallet_stats["transfer_event_count"] += 1
                wallet_stats["first_seen_block"] = min(wallet_stats["first_seen_block"], block_number)
                wallet_stats["last_seen_block"] = max(wallet_stats["last_seen_block"], block_number)
        print(f"scanned blocks {current}-{end}; found {len(wallets)} unique wallets")
        current = end + 1
    return wallets, stats


def build_rows(
    client: RpcClient,
    contract: str,
    wallets: set[str],
    stats: dict[str, dict[str, int]],
    block: int,
    min_balance: Decimal,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    decimals = read_decimals(client, contract, block)
    symbol = read_symbol(client, contract, block)
    rows: list[dict[str, Any]] = []
    total_raw = 0
    minimum_raw = int(min_balance * (Decimal(10) ** decimals))
    for index, wallet in enumerate(sorted(wallets), start=1):
        raw_balance = read_balance(client, contract, wallet, block)
        if raw_balance >= minimum_raw and raw_balance > 0:
            total_raw += raw_balance
            row = {
                "address": wallet,
                "balance": format_units(raw_balance, decimals),
                "raw_balance": str(raw_balance),
                "token_symbol": symbol,
                "token_contract": contract,
                "block_number": block,
            }
            row.update(stats.get(wallet, {}))
            rows.append(row)
        if index % 25 == 0:
            print(f"checked {index}/{len(wallets)} balances")
    rows.sort(key=lambda row: int(row["raw_balance"]), reverse=True)
    summary = {
        "holder_count": len(rows),
        "candidate_wallet_count": len(wallets),
        "total_raw_balance": str(total_raw),
        "total_balance": format_units(total_raw, decimals),
        "token_symbol": symbol,
        "token_decimals": decimals,
    }
    return rows, summary


def write_outputs(
    rows: list[dict[str, Any]],
    output: Path,
    formats: list[str],
    contract: str,
    block: int,
    summary: dict[str, Any],
) -> list[str]:
    fields = ordered_fields("erc20-holders", rows)
    args = argparse.Namespace(snapshot_type="erc20-holders", contract=contract, block=str(block))
    payload = build_payload(args, rows, fields)
    payload["summary"].update(summary)
    written: list[str] = []
    if "csv" in formats:
        path = output.with_suffix(".csv")
        write_csv(path, rows, fields)
        written.append(str(path))
    if "json" in formats:
        path = output.with_suffix(".json")
        write_json(path, payload)
        written.append(str(path))
    if "xlsx" in formats:
        path = output.with_suffix(".xlsx")
        summary_rows = [[key, value] for key, value in payload["summary"].items()]
        data_rows = [fields] + [[row.get(field, "") for field in fields] for row in rows]
        write_xlsx(path, {"Summary": summary_rows, "Holders": data_rows})
        written.append(str(path))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Take a real read-only ERC-20 holder snapshot on Pharos Atlantic Testnet.")
    parser.add_argument("--contract", required=True, help="ERC-20 contract address on Pharos Atlantic Testnet.")
    parser.add_argument("--from-block", required=True, help="First block to scan for Transfer events.")
    parser.add_argument("--to-block", default="latest", help="Last block to scan and balance block. Use latest or a block number.")
    parser.add_argument("--min-balance", default="0", help="Minimum human-readable token balance to include.")
    parser.add_argument("--output", default="out/live_erc20_snapshot", help="Output path prefix without extension.")
    parser.add_argument("--formats", default="csv,json,xlsx", help="Comma-separated formats: csv,json,xlsx.")
    parser.add_argument("--chunk-size", type=int, default=2_000, help="Blocks per eth_getLogs request.")
    parser.add_argument("--rpc-url", default=PHAROS_ATLANTIC["rpc_url"], help="Pharos RPC URL.")
    parser.add_argument("--preview-only", action="store_true", help="Print the safe scan plan without querying logs.")
    args = parser.parse_args()

    if not is_address(args.contract):
        raise SystemExit("invalid contract address")
    if args.chunk_size < 1 or args.chunk_size > 10_000:
        raise SystemExit("--chunk-size must be between 1 and 10000")
    formats = parse_formats(args.formats)
    invalid_formats = sorted(set(formats) - OUTPUT_FORMATS)
    if invalid_formats:
        raise SystemExit(f"unsupported output format(s): {', '.join(invalid_formats)}")

    contract = normalize_address(args.contract)
    from_block = parse_from_block(args.from_block)
    min_balance = parse_min_balance(args.min_balance)
    client = RpcClient(args.rpc_url)
    to_block = parse_to_block(client, args.to_block)
    if to_block < from_block:
        raise SystemExit("--to-block must be greater than or equal to --from-block")

    preview = {
        "status": "safe",
        "snapshot_type": "erc20-holders",
        "network": PHAROS_ATLANTIC,
        "contract": contract,
        "block_range": {"from": from_block, "to": to_block},
        "filters": {"min_balance": str(min_balance)},
        "read_only": True,
        "private_key_required": False,
        "warning": "Large ranges may need smaller chunks or an indexed explorer if the RPC limits eth_getLogs.",
    }
    print(json.dumps({"plan_preview": preview}, indent=2, sort_keys=True))
    if args.preview_only:
        return 0

    chain_id = hex_to_int(client.call("eth_chainId", []))
    if chain_id != PHAROS_ATLANTIC["chain_id"]:
        raise SystemExit(f"RPC chain ID mismatch: expected {PHAROS_ATLANTIC['chain_id']}, got {chain_id}")
    code = client.call("eth_getCode", [contract, block_to_rpc(to_block)])
    if not isinstance(code, str) or code in {"0x", "0X", ""}:
        raise SystemExit("no contract bytecode found at this address on Pharos Atlantic Testnet")

    wallets, stats = scan_transfer_logs(client, contract, from_block, to_block, args.chunk_size)
    rows, summary = build_rows(client, contract, wallets, stats, to_block, min_balance)
    written = write_outputs(rows, Path(args.output), formats, contract, to_block, summary)
    result = {
        "status": "safe",
        "snapshot_type": "erc20-holders",
        "contract": contract,
        "block_range": {"from": from_block, "to": to_block},
        "summary": summary,
        "output_files": written,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
