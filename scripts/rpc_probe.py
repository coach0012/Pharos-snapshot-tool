from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

from snapshot_common import PHAROS_ATLANTIC, is_address


def rpc_call(method: str, params: list[object], rpc_url: str) -> object:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode())
    if "error" in body:
        raise RuntimeError(body["error"])
    return body.get("result")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Pharos RPC contract probe.")
    parser.add_argument("--contract", required=True, help="Contract address to probe.")
    parser.add_argument("--rpc-url", default=PHAROS_ATLANTIC["rpc_url"], help="Pharos RPC URL.")
    args = parser.parse_args()

    if not is_address(args.contract):
        print(json.dumps({"status": "unsafe", "error": "invalid contract address"}, indent=2))
        return 1

    try:
        code = rpc_call("eth_getCode", [args.contract, "latest"], args.rpc_url)
        block = rpc_call("eth_blockNumber", [], args.rpc_url)
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        print(json.dumps({"status": "review", "error": f"RPC probe failed: {exc}"}, indent=2))
        return 2

    has_code = isinstance(code, str) and code not in {"0x", "0X", ""}
    result = {
        "status": "safe" if has_code else "review",
        "network": PHAROS_ATLANTIC,
        "contract": args.contract,
        "has_code": has_code,
        "latest_block_hex": block,
        "warning": None if has_code else "No bytecode found at this address on latest block.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if has_code else 1


if __name__ == "__main__":
    raise SystemExit(main())

